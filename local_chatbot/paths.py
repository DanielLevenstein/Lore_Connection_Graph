import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = Path(os.environ.get("LOCAL_CHATBOT_DATA_DIR", ROOT_DIR / "data")).resolve()
DOCS_LORE_DIR = Path(os.environ.get("LOCAL_CHATBOT_DOCS_LORE_DIR", ROOT_DIR / "docs" / "lore")).resolve()
LORE_FIXTURES_DIR = Path(os.environ.get("LOCAL_CHATBOT_LORE_FIXTURES_DIR", ROOT_DIR / "tests" / "fixtures")).resolve()
CHARACTERS_DIR = Path(
    os.environ.get("LOCAL_CHATBOT_CHARACTERS_DIR", DOCS_LORE_DIR / "character_sheets")
).resolve()
PLACES_DIR = Path(os.environ.get("LOCAL_CHATBOT_PLACES_DIR", DOCS_LORE_DIR / "places")).resolve()
SESSION_NOTES_DIR = Path(os.environ.get("LOCAL_CHATBOT_SESSION_NOTES_DIR", DOCS_LORE_DIR / "session_notes")).resolve()
GENERATED_LORE_DIR = DATA_DIR / "lore"
GENERATED_CHARACTER_SHEETS_DIR = GENERATED_LORE_DIR / "character_sheets"
CHARACTER_METADATA_DIR = GENERATED_CHARACTER_SHEETS_DIR
CHARACTER_GRAPHS_DIR = DATA_DIR / "character_graph"


def ensure_base_dirs() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    DOCS_LORE_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    PLACES_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_LORE_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CHARACTER_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTER_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTER_GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
