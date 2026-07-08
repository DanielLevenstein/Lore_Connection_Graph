#!/usr/bin/env python3
"""Generate local model config JSON files from Hugging Face model metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/v1"
HUGGING_FACE_BASE = "https://huggingface.co"
MODEL_EXTENSIONS = (
    ".safetensors",
    ".bin",
    ".gguf",
    ".ggml",
    ".pt",
    ".pth",
    ".onnx",
)


def repo_id_from_input(value: str) -> str:
    value = value.strip().rstrip("/")
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("Hugging Face URLs must include owner/model-name.")
        return "/".join(parts[:2])
    if "/" not in value:
        raise ValueError("Use a Hugging Face repo ID like owner/model-name.")
    return value


def api_port(api_base_url: str) -> str:
    parsed = urlparse(api_base_url)
    if parsed.port:
        return str(parsed.port)
    if parsed.scheme == "https":
        return "443"
    return "80"


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    if not cleaned:
        raise ValueError("Could not create a safe config filename.")
    return cleaned


def infer_parameter_size(repo_id: str, metadata: dict) -> str:
    text = " ".join(
        [
            repo_id,
            str(metadata.get("modelId", "")),
            " ".join(metadata.get("tags") or []),
        ]
    )
    match = re.search(r"(?i)(\d+(?:\.\d+)?)\s*([bmk])(?:\b|[-_])", text)
    if not match:
        return "Unknown"
    number, suffix = match.groups()
    return f"{number}{suffix.upper()}"


def summarize_bytes(size_bytes: int | None) -> str:
    if not size_bytes:
        return "Unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.2f} {unit}"


def decimal_gb(size_bytes: int | None) -> str:
    if not size_bytes:
        return "Unknown"
    return f"{size_bytes / 1_000_000_000:.2f} GB"


def fetch_json(url: str) -> dict | list:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_model_metadata(repo_id: str) -> dict:
    return fetch_json(f"{HUGGING_FACE_BASE}/api/models/{repo_id}")


def fetch_model_files(repo_id: str) -> list[dict]:
    tree_url = f"{HUGGING_FACE_BASE}/api/models/{repo_id}/tree/main?recursive=1&expand=true"
    tree = fetch_json(tree_url)
    if not isinstance(tree, list):
        return []
    files = []
    for item in tree:
        path = str(item.get("path") or item.get("rfilename") or "")
        size = item.get("size")
        if path.endswith(MODEL_EXTENSIONS) and isinstance(size, int):
            files.append({"filename": path, "size_bytes": size})
    return files


def extract_quant(filename: str) -> str:
    stem = Path(filename).stem
    patterns = [
        r"(?i)(IQ\d+_[A-Z]+)",
        r"(?i)(Q\d+_\d+(?:_\d+)*)",
        r"(?i)(Q\d+_[A-Z]+(?:_[A-Z]+)?)",
        r"(?i)(Q\d+_K_[MLS])",
        r"(?i)(Q\d+_K)",
    ]
    for pattern in patterns:
        match = re.search(pattern, stem)
        if match:
            return match.group(1).upper()
    return "default"


def build_download_options(files: list[dict]) -> list[dict]:
    options = []
    for file_info in files:
        filename = file_info["filename"]
        if not filename.endswith(".gguf"):
            continue
        size_bytes = file_info["size_bytes"]
        options.append(
            {
                "quant": extract_quant(filename),
                "filename": filename,
                "size": decimal_gb(size_bytes),
                "size_bytes": size_bytes,
            }
        )
    return sorted(options, key=lambda item: item["size_bytes"])


def choose_download_size(files: list[dict], quant: str | None) -> tuple[str, list[dict]]:
    options = build_download_options(files)
    if options:
        selected = None
        preferred_quant = (quant or "Q4_K_M").upper()
        for option in options:
            if option["quant"] == preferred_quant:
                selected = option
                break
        selected = selected or options[0]
        label = f"{selected['quant']} {selected['size']}"
        return label, options

    total = sum(file_info["size_bytes"] for file_info in files)
    return summarize_bytes(total), []


def selected_gguf_quant(download_size: str) -> str | None:
    match = re.match(r"([A-Z0-9_]+)\s+\d", download_size)
    if not match:
        return None
    return match.group(1)


def build_server_config(repo_id: str, api_base_url: str, download_size: str, has_gguf_options: bool) -> dict:
    if has_gguf_options:
        quant = selected_gguf_quant(download_size) or "Q4_K_M"
        return {
            "runner": "llama.cpp",
            "command": [
                "llama",
                "serve",
                "-hf",
                f"{repo_id}:{quant}",
                "--host",
                "127.0.0.1",
                "--port",
                api_port(api_base_url),
            ],
            "health_url": api_base_url.rstrip("/") + "/models",
        }
    return {
        "runner": "vLLM",
        "command": ["vllm", "serve", repo_id, "--host", "127.0.0.1", "--port", api_port(api_base_url)],
        "health_url": api_base_url.rstrip("/") + "/models",
    }


def make_description(metadata: dict, repo_id: str) -> str:
    card_data = metadata.get("cardData") or {}
    tags = set(metadata.get("tags") or [])
    license_name = card_data.get("license") or metadata.get("license")
    pipeline = metadata.get("pipeline_tag")

    pieces = []
    if license_name:
        display_license = str(license_name)
        if display_license.lower() == "apache-2.0":
            display_license = "Apache-2.0"
        pieces.append(f"{display_license} licensed")
    tag_text = " ".join(tags).lower()
    repo_text = repo_id.lower()
    if "gemma" in tag_text or "gemma" in repo_text:
        pieces.append("Gemma-based")
    elif "llama" in tag_text or "llama" in repo_text:
        pieces.append("Llama-based")
    if "gguf" in tag_text or "gguf" in repo_text:
        pieces.append("GGUF")

    size = infer_parameter_size(repo_id, metadata)
    if size != "Unknown":
        pieces.append(f"{size} model")
    else:
        pieces.append("local language model")

    if pipeline:
        pieces.append(f"for {pipeline.replace('-', ' ')}")
    else:
        pieces.append("for local chat and character roleplay")

    sentence = "An " + " ".join(pieces).strip() + "."
    return sentence.replace("An Apache", "An Apache")


def build_config(args: argparse.Namespace) -> dict:
    repo_id = repo_id_from_input(args.model)
    model_url = f"{HUGGING_FACE_BASE}/{repo_id}"
    metadata = fetch_model_metadata(repo_id) if not args.no_fetch else {}
    files = [] if args.no_fetch else fetch_model_files(repo_id)

    name = args.name or repo_id.split("/")[-1]
    inferred_download_size, download_options = choose_download_size(files, args.quant)
    download_size = args.download_size or ("Unknown" if args.no_fetch else inferred_download_size)
    description = args.description or make_description(metadata, repo_id)

    config = {
        "name": name,
        "model_id": repo_id,
        "model_url": model_url,
        "api_base_url": args.api_base_url,
        "size": args.size or infer_parameter_size(repo_id, metadata),
        "download_size": download_size,
        "description": description,
        "server": build_server_config(repo_id, args.api_base_url, download_size, bool(download_options)),
    }
    if download_options:
        config["download_options"] = download_options
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Hugging Face repo ID or URL, such as owner/model-name")
    parser.add_argument("--config-dir", default="config", help="Directory to write JSON configs into")
    parser.add_argument("--name", help="Display name and output filename stem")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help="Local OpenAI-compatible API base URL")
    parser.add_argument("--size", help="Parameter size label, such as 8B or 13B")
    parser.add_argument("--quant", help="Preferred GGUF quant to use for download_size, such as Q4_K_M")
    parser.add_argument("--download-size", help="Download size label, such as 4.78 GB or varies by quantization")
    parser.add_argument("--description", help="One-sentence model description")
    parser.add_argument("--no-fetch", action="store_true", help="Skip Hugging Face API calls and use overrides/defaults")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing config file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_config(args)

    config_dir = Path(args.config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    output_path = config_dir / f"{safe_filename(config['name'])}.json"
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"{output_path} already exists. Use --overwrite to replace it.")

    output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
