from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
CHARACTERS_DIR = DATA_DIR / "characters"


def ensure_base_dirs() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
