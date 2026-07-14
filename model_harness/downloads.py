from dataclasses import dataclass
from pathlib import Path

from .models import ModelConfig, is_runnable_model_filename
from .policy import require_codebase_owned_language_model

# TODO delete this file
@dataclass(frozen=True)
class DownloadStatus:
    filename: str
    path: Path
    part_path: Path
    exists: bool
    partial_bytes: int
    expected_bytes: int | None


def is_runnable_model_option(option: dict) -> bool:
    filename = str(option.get("filename", ""))
    return is_runnable_model_filename(filename)


def default_download_option(config: ModelConfig) -> dict | None:
    if not config.download_options:
        return None
    wanted = config.download_size.split(" ", 1)[0]
    runnable_options = [option for option in config.download_options if is_runnable_model_option(option)]
    options = runnable_options or config.download_options
    if wanted.upper() == wanted and any(character.isdigit() for character in wanted):
        for option in options:
            if option.get("quant") == wanted:
                return option
    for preferred_quant in ("Q4_K_M", "Q4_K", "Q5_K_M", "Q5_K"):
        for option in options:
            if option.get("quant") == preferred_quant:
                return option
    return options[0]


def local_model_path(config: ModelConfig, option: dict) -> Path:
    return config.local_dir / str(option["filename"])


def downloaded_options(config: ModelConfig) -> list[dict]:
    return [
        option
        for option in config.download_options
        if is_runnable_model_option(option) and local_model_path(config, option).exists()
    ]


def selected_downloaded_option(config: ModelConfig) -> dict | None:
    options = downloaded_options(config)
    return options[0] if options else None


def model_is_downloaded(config: ModelConfig) -> bool:
    return bool(selected_downloaded_option(config))


def option_by_filename(config: ModelConfig, filename: str) -> dict | None:
    return next((option for option in config.download_options if option.get("filename") == filename), None)


def status_for_option(config: ModelConfig, option: dict) -> DownloadStatus:
    path = local_model_path(config, option)
    part_path = path.with_suffix(path.suffix + ".part")
    return DownloadStatus(
        filename=str(option.get("filename", "")),
        path=path,
        part_path=part_path,
        exists=path.exists(),
        partial_bytes=part_path.stat().st_size if part_path.exists() else 0,
        expected_bytes=option.get("size_bytes"),
    )


def manifest_path(config: ModelConfig, option: dict) -> Path:
    return config.local_dir / f"{option.get('filename', 'model')}.download.json"


def write_download_manifest(config: ModelConfig, option: dict) -> Path:
    require_codebase_owned_language_model()


def write_downloads_index(config: ModelConfig) -> None:
    require_codebase_owned_language_model()


def download_option(config: ModelConfig, option: dict, chunk_size: int = 1024 * 1024) -> Path:
    require_codebase_owned_language_model()
