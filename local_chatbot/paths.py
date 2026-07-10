import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = Path(os.environ.get("LOCAL_CHATBOT_DATA_DIR", ROOT_DIR / "data")).resolve()
CHARACTERS_DIR = Path(os.environ.get("LOCAL_CHATBOT_CHARACTERS_DIR", ROOT_DIR / "characters")).resolve()
CHARACTER_METADATA_DIR = DATA_DIR / "characters"
CHARACTER_GRAPHS_DIR = DATA_DIR / "character_graph"


def ensure_base_dirs() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTER_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTER_GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
