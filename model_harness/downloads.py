import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

from .models import ModelConfig


@dataclass(frozen=True)
class DownloadStatus:
    filename: str
    path: Path
    part_path: Path
    exists: bool
    partial_bytes: int
    expected_bytes: int | None


def default_download_option(config: ModelConfig) -> dict | None:
    if not config.download_options:
        return None
    wanted = config.download_size.split(" ", 1)[0]
    runnable_options = [option for option in config.download_options if is_runnable_model_option(option)]
    options = runnable_options or config.download_options
    for preferred_quant in ("Q4_K_M", "Q4_K", "Q5_K_M", "Q5_K"):
        for option in options:
            if option.get("quant") == preferred_quant:
                return option
    for option in options:
        if option.get("quant") == wanted:
            return option
    return options[0]


def is_runnable_model_option(option: dict) -> bool:
    filename = str(option.get("filename", "")).lower()
    if not filename.endswith(".gguf"):
        return False
    return not filename.startswith("mmproj")


def option_by_filename(config: ModelConfig, filename: str) -> dict | None:
    for option in config.download_options:
        if option.get("filename") == filename:
            return option
    return None


def local_model_path(config: ModelConfig, option: dict) -> Path:
    return config.local_dir / option["filename"]


def artifact_variant(option: dict) -> str:
    filename = option["filename"].removesuffix(".gguf")
    quant = str(option.get("quant", "unknown"))
    for token in (f"-D_AU-{quant}", f"-D_AU-{quant.lower()}", f"-{quant}", f"-{quant.lower()}"):
        filename = filename.replace(token, "")
    parts = [part for part in filename.split("-") if part.lower() in {"max", "cpu"}]
    return "-".join(parts) if parts else "standard"


def manifest_stem(option: dict) -> str:
    quant = str(option.get("quant") or "unknown")
    variant = artifact_variant(option)
    safe = f"{quant}.{variant}".replace("/", "_").replace(" ", "_")
    return safe


def manifest_path(config: ModelConfig, option: dict) -> Path:
    return config.local_dir / f"download.{manifest_stem(option)}.json"


def downloads_index_path(config: ModelConfig) -> Path:
    return config.local_dir / "downloads.json"


def downloaded_options(config: ModelConfig) -> list[dict]:
    return [
        option
        for option in config.download_options
        if is_runnable_model_option(option) and local_model_path(config, option).exists()
    ]


def selected_downloaded_option(config: ModelConfig) -> dict | None:
    options = downloaded_options(config)
    if not options:
        return None
    preferred = default_download_option(config)
    if preferred:
        for option in options:
            if option.get("filename") == preferred.get("filename"):
                return option
    return options[0]


def model_is_downloaded(config: ModelConfig) -> bool:
    if config.download_options:
        return selected_downloaded_option(config) is not None
    return config.local_dir.exists()


def download_url(config: ModelConfig, option: dict) -> str:
    encoded_filename = quote(option["filename"])
    return f"https://huggingface.co/{config.model_id}/resolve/main/{encoded_filename}?download=true"


def status_for_option(config: ModelConfig, option: dict) -> DownloadStatus:
    path = local_model_path(config, option)
    part_path = path.with_suffix(path.suffix + ".part")
    expected = option.get("size_bytes")
    return DownloadStatus(
        filename=option["filename"],
        path=path,
        part_path=part_path,
        exists=path.exists(),
        partial_bytes=part_path.stat().st_size if part_path.exists() else 0,
        expected_bytes=expected if isinstance(expected, int) else None,
    )


def write_download_manifest(config: ModelConfig, option: dict) -> None:
    manifest = {
        "model_id": config.model_id,
        "filename": option["filename"],
        "quant": option.get("quant"),
        "variant": artifact_variant(option),
        "size": option.get("size"),
        "size_bytes": option.get("size_bytes"),
        "local_path": str(local_model_path(config, option)),
    }
    manifest_path(config, option).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_downloads_index(config)


def write_downloads_index(config: ModelConfig) -> None:
    manifests = []
    for option in downloaded_options(config):
        path = manifest_path(config, option)
        if path.exists():
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        else:
            manifests.append(
                {
                    "model_id": config.model_id,
                    "filename": option["filename"],
                    "quant": option.get("quant"),
                    "variant": artifact_variant(option),
                    "size": option.get("size"),
                    "size_bytes": option.get("size_bytes"),
                    "local_path": str(local_model_path(config, option)),
                }
            )
    downloads_index_path(config).write_text(json.dumps({"downloads": manifests}, indent=2) + "\n", encoding="utf-8")


def download_option(config: ModelConfig, option: dict, chunk_size: int = 1024 * 1024) -> Path:
    config.local_dir.mkdir(parents=True, exist_ok=True)
    target = local_model_path(config, option)
    if target.exists():
        write_download_manifest(config, option)
        return target

    part_path = target.with_suffix(target.suffix + ".part")
    headers = {}
    if part_path.exists():
        headers["Range"] = f"bytes={part_path.stat().st_size}-"

    with requests.get(download_url(config, option), headers=headers, stream=True, timeout=60) as response:
        if response.status_code == 416:
            part_path.rename(target)
            write_download_manifest(config, option)
            return target
        response.raise_for_status()
        mode = "ab" if response.status_code == 206 else "wb"
        with part_path.open(mode + "") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)

    part_path.rename(target)
    write_download_manifest(config, option)
    return target
