import os
from pathlib import Path


CONFIG_DIR_ENV = "LANGUAGE_MODEL_HARNESS_CONFIG_DIR"
DATA_DIR_ENV = "LANGUAGE_MODEL_HARNESS_DATA_DIR"
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parent.parent


def config_dir() -> Path:
    return Path(os.environ.get(CONFIG_DIR_ENV, DEFAULT_PROJECT_DIR / "config")).resolve()


def data_dir() -> Path:
    return Path(os.environ.get(DATA_DIR_ENV, DEFAULT_PROJECT_DIR / "data")).resolve()


def ensure_base_dirs() -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    data_dir().mkdir(parents=True, exist_ok=True)
