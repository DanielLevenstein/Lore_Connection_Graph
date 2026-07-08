import re
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .paths import CHARACTERS_DIR, ensure_base_dirs


SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_. -]+")
BACKSTORY_TEMPLATE_PATH = CHARACTERS_DIR / "TEMPLATE.md"


@dataclass(frozen=True)
class Character:
    name: str
    path: Path

    @property
    def backstory_path(self) -> Path:
        return self.path / "BACKSTORY.md"

    @property
    def memory_path(self) -> Path:
        return self.path / "MEMORY.md"

    @property
    def chatlogs_dir(self) -> Path:
        return self.path / "chatlogs"

    @property
    def profile_path(self) -> Path:
        return self.path / "PROFILE.json"


@dataclass(frozen=True)
class CharacterProfile:
    name: str
    pronouns: str
    level: str
    race: str
    character_class: str
    backstory: str
    summary: str = ""
    motivations: list[str] | None = None
    origin: str = ""
    gender: str = ""


def sanitize_name(name: str) -> str:
    cleaned = SAFE_NAME_PATTERN.sub("", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise ValueError("Character name must contain letters or numbers.")
    return cleaned[:80]


def list_characters() -> list[Character]:
    ensure_base_dirs()
    characters = []
    for path in sorted(CHARACTERS_DIR.iterdir()):
        if path.is_dir() and (path / "BACKSTORY.md").exists():
            characters.append(Character(name=path.name, path=path))
    return characters


def render_backstory(profile: CharacterProfile) -> str:
    first_name = character_first_name(profile.name)
    summary = profile.summary.strip() or default_summary(profile)
    return (
        f"# {profile.name}\n\n"
        "## Character Stats\n\n"
        "| Name | Level | Race | Class | Pronouns |\n"
        "|------|-------|------|-------|----------|\n"
        f"| {first_name} | {profile.level} | {profile.race} | {profile.character_class} | {profile.pronouns} |\n\n"
        "## Character Backstory\n\n"
        f"{profile.backstory.strip()}\n\n"
        "## Character Summary\n\n"
        f"{summary}\n"
    )


def character_first_name(name: str) -> str:
    return name.strip().split()[0] if name.strip() else ""


def default_summary(profile: CharacterProfile) -> str:
    first_name = character_first_name(profile.name)
    origin = profile.origin.strip() or "an unwritten origin"
    gender = profile.gender.strip() or gender_from_pronouns(profile.pronouns)
    return f"{first_name} is a {gender} character from {origin}."


def gender_from_pronouns(pronouns: str) -> str:
    normalized = pronouns.strip().lower()
    if normalized == "she/her":
        return "female"
    if normalized == "he/him":
        return "male"
    return "non-binary"


def create_character(profile: CharacterProfile) -> Character:
    ensure_base_dirs()
    safe_name = sanitize_name(profile.name)
    character = Character(name=safe_name, path=CHARACTERS_DIR / safe_name)
    character.path.mkdir(parents=True, exist_ok=False)
    character.chatlogs_dir.mkdir(exist_ok=True)
    write_character_profile(character, profile)
    character.memory_path.write_text(
        "# Memory\n\nAdd durable character memories here. The chat UI can append notes as you play.\n",
        encoding="utf-8",
    )
    return character


def read_backstory_template() -> str:
    return read_text(BACKSTORY_TEMPLATE_PATH)


def read_character_profile(character: Character) -> CharacterProfile:
    if character.profile_path.exists():
        payload = json.loads(character.profile_path.read_text(encoding="utf-8"))
        return CharacterProfile(
            name=payload.get("name", character.name),
            pronouns=payload.get("pronouns", ""),
            level=payload.get("level", ""),
            race=payload.get("race", ""),
            character_class=payload.get("character_class", payload.get("class", "")),
            backstory=payload.get("backstory", ""),
            summary=payload.get("summary", ""),
            motivations=payload.get("motivations", []),
            origin=payload.get("origin", ""),
            gender=payload.get("gender", ""),
        )
    return CharacterProfile(
        name=character.name,
        pronouns="",
        level="",
        race="",
        character_class="",
        backstory=read_text(character.backstory_path),
        summary="",
        motivations=[],
    )


def write_character_profile(character: Character, profile: CharacterProfile) -> None:
    character.profile_path.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
    character.backstory_path.write_text(render_backstory(profile), encoding="utf-8")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_memory(character: Character, memory: str) -> None:
    character.memory_path.write_text(memory.rstrip() + "\n", encoding="utf-8")


def append_memory(character: Character, note: str) -> None:
    note = note.strip()
    if not note:
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with character.memory_path.open("a", encoding="utf-8") as file:
        file.write(f"\n- {stamp}: {note}\n")


def start_chatlog(character: Character) -> Path:
    character.chatlogs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return character.chatlogs_dir / f"{timestamp}_CHAT.log"


def append_chatlog(chatlog: Path | str, speaker: str, text: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = Path(chatlog)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(f"[{stamp}] {speaker}: {text.rstrip()}\n\n")
