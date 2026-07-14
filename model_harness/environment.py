import os
from pathlib import Path
# TODO delete this file
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR_ENV = "LANGUAGE_MODEL_HARNESS_DATA_DIR"
CONFIG_DIR_ENV = "LANGUAGE_MODEL_HARNESS_CONFIG_DIR"


def data_dir() -> Path:
    if os.environ.get(DATA_DIR_ENV):
        return Path(os.environ[DATA_DIR_ENV]).resolve()
    return DEFAULT_PROJECT_DIR / "world_building" / "meta_data" / "model"


def config_dir() -> Path:
    if os.environ.get(CONFIG_DIR_ENV):
        return Path(os.environ[CONFIG_DIR_ENV]).resolve()
    return DEFAULT_PROJECT_DIR / "config"


def ensure_base_dirs() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    config_dir().mkdir(parents=True, exist_ok=True)
