from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from .paths import CONFIG_DIR, ROOT_DIR


LOCAL_REWRITE_MODEL_ENGINE = "local-language-model-llama-cli"
LOCAL_REWRITE_PROMPT_VERSION = "character-rewrite-v6-local-qwen-1.5b"
DEFAULT_MODEL_ID = "JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF"
DEFAULT_MODEL_QUANTIZATION = "Q4_K_M"
DEFAULT_MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF/resolve/main/"
    f"{DEFAULT_MODEL_FILENAME}"
)
DEFAULT_MODEL_CONFIG_PATH = CONFIG_DIR / "model" / "local_language_model.json"
DEFAULT_MODEL_CACHE_DIR = Path(
    os.environ.get("LOCAL_CHATBOT_MODEL_CACHE_DIR", ROOT_DIR / "models" / "local_language_model")
).resolve()

StatusCallback = Callable[[str], None]
WorkerRunner = Callable[["LocalRewriteModelConfig", list[dict[str, str]]], "WorkerResult"]


class LocalRewriteModelError(RuntimeError):
    """Raised when model-backed rewrite generation cannot produce safe candidate text."""


@dataclass(frozen=True)
class LocalRewriteModelConfig:
    model_id: str = DEFAULT_MODEL_ID
    quantization: str = DEFAULT_MODEL_QUANTIZATION
    filename: str = DEFAULT_MODEL_FILENAME
    download_url: str = DEFAULT_MODEL_URL
    cache_dir: Path = DEFAULT_MODEL_CACHE_DIR
    prompt_version: str = LOCAL_REWRITE_PROMPT_VERSION
    max_tokens: int = 640
    temperature: float = 0.2
    top_p: float = 0.85
    repeat_penalty: float = 1.15
    seed: int = -1
    n_ctx: int = 8192
    n_batch: int = 64
    n_threads: int = 2
    n_gpu_layers: int = 0
    device: str = "none"
    timeout_seconds: int = 180
    allow_download: bool = False

    @property
    def model_path(self) -> Path:
        return self.cache_dir / self.filename


def load_local_language_model_config(
    config_path: Path = DEFAULT_MODEL_CONFIG_PATH,
    allow_download: bool = False,
) -> LocalRewriteModelConfig:
    if not config_path.exists():
        return LocalRewriteModelConfig(allow_download=allow_download)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    values = {}
    for field_name in LocalRewriteModelConfig.__dataclass_fields__:
        if field_name in {"allow_download", "cache_dir"}:
            continue
        if field_name in data:
            values[field_name] = data[field_name]
    cache_dir_value = data.get("cache_dir")
    if cache_dir_value:
        cache_dir = Path(cache_dir_value)
        values["cache_dir"] = cache_dir if cache_dir.is_absolute() else (ROOT_DIR / cache_dir).resolve()
    values["allow_download"] = allow_download
    return LocalRewriteModelConfig(**values)


@dataclass(frozen=True)
class WorkerResult:
    ok: bool
    text: str = ""
    error: str = ""
    metadata: dict[str, str] | None = None


class LocalRewriteModelClient:
    def __init__(
        self,
        config: LocalRewriteModelConfig | None = None,
        status_callback: StatusCallback | None = None,
        worker_runner: WorkerRunner | None = None,
    ) -> None:
        self.config = config or LocalRewriteModelConfig()
        self.status_callback = status_callback
        self.worker_runner = worker_runner or run_worker_process
        self.last_metadata: dict[str, str] = {}

    def __call__(self, messages: list[dict[str, str]]) -> str:
        lifecycle = LocalRewriteModelLifecycle(self.config, self.status_callback, self.worker_runner)
        text = lifecycle.generate(messages)
        self.last_metadata = lifecycle.last_metadata
        return text


class LocalRewriteModelLifecycle:
    def __init__(
        self,
        config: LocalRewriteModelConfig | None = None,
        status_callback: StatusCallback | None = None,
        worker_runner: WorkerRunner | None = None,
    ) -> None:
        self.config = config or LocalRewriteModelConfig()
        self.status_callback = status_callback
        self.worker_runner = worker_runner or run_worker_process
        self.last_metadata: dict[str, str] = {}

    def is_runtime_available(self) -> bool:
        return shutil.which("llama") is not None

    def is_model_available(self) -> bool:
        return self.config.model_path.is_file()

    def ensure_model_available(self) -> Path:
        if self.is_model_available():
            return self.config.model_path
        if not self.config.allow_download:
            raise LocalRewriteModelError(
                f"Local rewrite model artifact is missing: {self.config.model_path}. "
                "Download the model or enable model downloads before using model-backed rewrites."
            )
        with model_lock(self.config.model_path):
            if self.is_model_available():
                return self.config.model_path
            self._status("Downloading local rewrite model. First run can take several minutes.")
            download_model(self.config.download_url, self.config.model_path, self._status)
            return self.config.model_path

    def generate(self, messages: list[dict[str, str]]) -> str:
        if not self.is_runtime_available():
            raise LocalRewriteModelError(
                "llama CLI is not installed. Install llama.cpp or use deterministic graph rewrites."
            )
        self.ensure_model_available()
        with model_lock(self.config.model_path):
            self._status("Generating model-backed rewrite.")
            result = self.worker_runner(self.config, messages)
        if not result.ok:
            detail = f": {result.error}" if result.error else "."
            raise LocalRewriteModelError(f"Local rewrite model generation failed{detail}")
        if not result.text.strip():
            raise LocalRewriteModelError("Local rewrite model returned an empty candidate.")
        self.last_metadata = result.metadata or {}
        return result.text

    def _status(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)


_MODEL_LOCKS: dict[str, threading.Lock] = {}
_MODEL_LOCKS_GUARD = threading.Lock()


def model_lock(model_path: Path) -> threading.Lock:
    key = str(model_path.resolve())
    with _MODEL_LOCKS_GUARD:
        if key not in _MODEL_LOCKS:
            _MODEL_LOCKS[key] = threading.Lock()
        return _MODEL_LOCKS[key]


def download_model(url: str, destination: Path, status_callback: StatusCallback | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        downloaded = 0
        last_percent = -1
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=destination.name,
            suffix=".part",
            delete=False,
        ) as partial_file:
            partial_path = Path(partial_file.name)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                partial_file.write(chunk)
                downloaded += len(chunk)
                if status_callback and total:
                    percent = int((downloaded / total) * 100)
                    if percent != last_percent:
                        status_callback(f"Downloading local rewrite model: {percent}%")
                        last_percent = percent
    partial_path.replace(destination)


def run_worker_process(config: LocalRewriteModelConfig, messages: list[dict[str, str]]) -> WorkerResult:
    prompt = prompt_from_messages(messages)
    command = [
        "llama",
        "completion",
        "--device",
        config.device,
        "--model",
        str(config.model_path),
        "--ctx-size",
        str(config.n_ctx),
        "--predict",
        str(config.max_tokens),
        "--batch-size",
        str(config.n_batch),
        "--ubatch-size",
        str(config.n_batch),
        "--threads",
        str(config.n_threads),
        "--gpu-layers",
        str(config.n_gpu_layers),
        "--no-kv-offload",
        "--no-op-offload",
        "--temp",
        str(config.temperature),
        "--top-p",
        str(config.top_p),
        "--repeat-penalty",
        str(config.repeat_penalty),
        "--seed",
        str(config.seed),
        "--no-display-prompt",
        "--no-conversation",
        "--simple-io",
        "--prompt",
        prompt,
    ]
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return WorkerResult(ok=False, error=f"llama completion timed out after {config.timeout_seconds} seconds")
    if process.returncode != 0:
        diagnostics = process.stderr.strip() or process.stdout.strip()
        if process.returncode < 0:
            return WorkerResult(ok=False, error=f"llama completion crashed with signal {-process.returncode}")
        return WorkerResult(ok=False, error=diagnostics or f"llama completion exited with code {process.returncode}")
    diagnostics = "\n".join(part for part in [process.stderr, process.stdout] if part)
    metadata = {
        "model_id": config.model_id,
        "quantization": config.quantization,
        "prompt_version": config.prompt_version,
        "max_tokens": str(config.max_tokens),
        "temperature": str(config.temperature),
        "top_p": str(config.top_p),
        "repeat_penalty": str(config.repeat_penalty),
        "seed": str(config.seed),
        "n_ctx": str(config.n_ctx),
        "n_batch": str(config.n_batch),
        "n_threads": str(config.n_threads),
        "n_gpu_layers": str(config.n_gpu_layers),
        "device": config.device,
        "timeout_seconds": str(config.timeout_seconds),
        "prompt_hash": prompt_hash(prompt),
    }
    metadata.update(parse_llama_timing(diagnostics))
    return WorkerResult(ok=True, text=process.stdout, metadata=metadata)


def prompt_from_messages(messages: list[dict[str, str]]) -> str:
    system = "\n\n".join(message["content"] for message in messages if message.get("role") == "system")
    user = "\n\n".join(message["content"] for message in messages if message.get("role") == "user")
    return (
        "<|im_start|>system\n"
        f"{system}<|im_end|>\n"
        "<|im_start|>user\n"
        f"{user}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def parse_llama_timing(diagnostics: str) -> dict[str, str]:
    metadata = {}
    for line in diagnostics.splitlines():
        lowered = line.lower()
        if "prompt eval time" in lowered:
            time_key = "prompt_eval_time_ms"
            token_key = "prompt_tokens"
            label = "prompt eval"
        elif "eval time" in lowered:
            time_key = "eval_time_ms"
            token_key = "completion_tokens"
            label = "eval"
        elif "total time" in lowered:
            time_key = "total_time_ms"
            token_key = None
            label = "total"
        else:
            continue
        match = re.search(rf"{label} time\s*=\s*([0-9.]+)\s*ms(?:\s*/\s*([0-9]+)\s*(?:tokens?|runs))?", line, flags=re.IGNORECASE)
        if match:
            metadata[time_key] = match.group(1)
            if token_key and match.group(2):
                metadata[token_key] = match.group(2)
    if "prompt_tokens" in metadata and "completion_tokens" in metadata:
        metadata["total_tokens"] = str(int(metadata["prompt_tokens"]) + int(metadata["completion_tokens"]))
    return metadata
