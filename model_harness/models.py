import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .environment import DEFAULT_PROJECT_DIR, CONFIG_DIR_ENV, config_dir, data_dir, ensure_base_dirs

# TODO delete this file
@dataclass(frozen=True)
class ModelConfig:
    name: str
    model_id: str
    model_url: str
    api_base_url: str
    size: str
    download_size: str
    download_options: list[dict[str, Any]]
    description: str
    server: dict[str, Any]
    config_path: Path

    @property
    def local_dir(self) -> Path:
        return data_dir() / self.name

    @property
    def is_downloaded(self) -> bool:
        if self.download_options:
            return any(
                is_runnable_model_filename(option["filename"]) and (self.local_dir / option["filename"]).exists()
                for option in self.download_options
            )
        return self.local_dir.exists()


def is_runnable_model_filename(filename: str) -> bool:
    normalized = filename.lower()
    return normalized.endswith(".gguf") and not normalized.startswith("mmproj")


def _read_config(path: Path) -> ModelConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ModelConfig(
        name=payload["name"],
        model_id=payload["model_id"],
        model_url=payload["model_url"],
        api_base_url=payload.get("api_base_url", "http://localhost:8000/v1"),
        size=payload["size"],
        download_size=payload.get("download_size", "Unknown"),
        download_options=payload.get("download_options", []),
        description=payload["description"],
        server=payload.get("server", {}),
        config_path=path,
    )


def list_model_configs(downloaded_only: bool = False) -> list[ModelConfig]:
    ensure_base_dirs()
    config_paths = sorted(config_dir().glob("*.json"))
    legacy_dir = DEFAULT_PROJECT_DIR / "config"
    if CONFIG_DIR_ENV not in os.environ and legacy_dir != config_dir():
        config_paths.extend(path for path in sorted(legacy_dir.glob("*.json")) if path not in config_paths)
    configs = [_read_config(path) for path in config_paths]
    if downloaded_only:
        configs = [config for config in configs if config.is_downloaded]
    return configs


def mark_model_downloaded(config: ModelConfig) -> Path:
    config.local_dir.mkdir(parents=True, exist_ok=True)
    marker = config.local_dir / "README.md"
    if not marker.exists():
        marker.write_text(
            "# Local model folder\n\n"
            "Place downloaded model files here, or keep this folder as the local "
            "availability marker when the model is served from another local cache.\n",
            encoding="utf-8",
        )
    return config.local_dir
