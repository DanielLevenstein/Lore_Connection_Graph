import re
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .paths import CHARACTER_GRAPHS_DIR, CHARACTERS_DIR, ensure_base_dirs


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

    @property
    def graph_path(self) -> Path:
        return CHARACTER_GRAPHS_DIR / f"{self.name}.graph.json"


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
    drives: list[str] | None = None
    alliances: list[str] | None = None
    enemies: list[str] | None = None
    details: str = ""


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
    summary = profile.summary.strip() or default_summary(profile)
    stats = character_stats(profile)
    details = profile.details.strip() or default_details(profile)
    stats_table = render_stats_table(stats)
    details_section = f"\n\n### Character Details\n\n{details}\n" if details else "\n"
    return (
        f"# {profile.name}\n\n"
        "## Character Stats\n\n"
        f"{stats_table}\n\n"
        "## Character Backstory\n\n"
        f"{profile.backstory.strip()}\n\n"
        "## Character Summary\n\n"
        f"{summary}{details_section}"
    )


def character_stats(profile: CharacterProfile) -> list[tuple[str, str]]:
    stats = [
        ("Name", character_first_name(profile.name)),
        ("Level", profile.level),
        ("Race", profile.race),
        ("Class", profile.character_class),
    ]
    return [(label, value.strip()) for label, value in stats if value.strip()]


def render_stats_table(stats: list[tuple[str, str]]) -> str:
    if not stats:
        return ""
    headers = [label for label, _value in stats]
    values = [value for _label, value in stats]
    divider = ["-" * max(3, len(header)) for header in headers]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(divider) + " |",
            "| " + " | ".join(values) + " |",
        ]
    )


def default_details(profile: CharacterProfile) -> str:
    lines: list[str] = []
    if profile.pronouns.strip():
        lines.append(f"Pronouns: {profile.pronouns.strip()}")
    if profile.gender.strip():
        lines.append(f"Gender: {profile.gender.strip()}")
    if profile.origin.strip():
        lines.append(f"Home: {profile.origin.strip()}")
    lines.extend(labeled_list("Drives", profile.drives or profile.motivations or []))
    lines.extend(labeled_list("Allies", profile.alliances or []))
    lines.extend(labeled_list("Enemies", profile.enemies or []))
    return "\n".join(lines)


def labeled_list(label: str, values: list[str]) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        return []
    return [f"{label}:", *[f"- {value}" for value in cleaned]]


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
    markdown_profile = read_character_sheet(character)
    if character.profile_path.exists():
        payload = json.loads(character.profile_path.read_text(encoding="utf-8"))
        stored_profile = CharacterProfile(
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
            drives=payload.get("drives"),
            alliances=payload.get("alliances", []),
            enemies=payload.get("enemies", []),
            details=payload.get("details", ""),
        )
        if markdown_profile:
            return merge_profiles(stored_profile, markdown_profile)
        return stored_profile
    if markdown_profile:
        return markdown_profile
    return CharacterProfile(
        name=character.name,
        pronouns="",
        level="",
        race="",
        character_class="",
        backstory=read_text(character.backstory_path),
        summary="",
        motivations=[],
        drives=[],
        alliances=[],
        enemies=[],
    )


def read_character_sheet(character: Character) -> CharacterProfile | None:
    text = read_text(character.backstory_path)
    if not text.strip():
        return None
    sections = markdown_sections(text)
    title = markdown_title(text) or character.name
    stats = parse_stats_table(sections.get("character stats", ""))
    summary, details = split_summary_and_details(sections.get("character summary", ""))
    detail_values = parse_details(details)
    legacy_detail_values = parse_legacy_stats_details(stats)
    return CharacterProfile(
        name=title,
        pronouns=str(detail_values.get("pronouns") or legacy_detail_values.get("pronouns", "")),
        level=stats.get("level", ""),
        race=stats.get("race", ""),
        character_class=stats.get("class", ""),
        backstory=sections.get("character backstory", ""),
        summary=summary,
        motivations=[],
        origin=str(detail_values.get("home") or legacy_detail_values.get("home", "")),
        gender=str(detail_values.get("gender", "")),
        drives=detail_values.get("drives") or legacy_detail_values.get("drives", []),
        alliances=detail_values.get("allies") or legacy_detail_values.get("allies", []),
        enemies=detail_values.get("enemies") or legacy_detail_values.get("enemies", []),
        details=details,
    )


def merge_profiles(stored: CharacterProfile, sheet: CharacterProfile) -> CharacterProfile:
    drives = sheet.drives or stored.drives or []
    alliances = sheet.alliances or stored.alliances or []
    enemies = sheet.enemies or stored.enemies or []
    pronouns = sheet.pronouns or stored.pronouns
    origin = sheet.origin or stored.origin
    gender = sheet.gender or stored.gender
    details = sheet.details or default_details(
        CharacterProfile(
            name=sheet.name or stored.name,
            pronouns=pronouns,
            level=sheet.level,
            race=sheet.race,
            character_class=sheet.character_class,
            backstory=sheet.backstory,
            summary=sheet.summary,
            motivations=stored.motivations,
            origin=origin,
            gender=gender,
            drives=drives,
            alliances=alliances,
            enemies=enemies,
        )
    )
    return CharacterProfile(
        name=sheet.name or stored.name,
        pronouns=pronouns,
        level=sheet.level,
        race=sheet.race,
        character_class=sheet.character_class,
        backstory=sheet.backstory,
        summary=sheet.summary,
        motivations=stored.motivations,
        origin=origin,
        gender=gender,
        drives=drives,
        alliances=alliances,
        enemies=enemies,
        details=details,
    )


def markdown_title(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip().lower()] = text[start:end].strip()
    return sections


def parse_stats_table(text: str) -> dict[str, str]:
    rows = [parse_table_row(line) for line in text.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 2:
        return {}
    headers = [canonical_table_key(header) for header in rows[0]]
    data_row = next((row for row in rows[1:] if not all(set(cell) <= {"-"} for cell in row)), [])
    return {header: value.strip() for header, value in zip(headers, data_row) if value.strip()}


def parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def compact_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def canonical_table_key(value: str) -> str:
    key = compact_label(value)
    aliases = {
        "characterclass": "class",
        "classname": "class",
    }
    return aliases.get(key, key)


def split_summary_and_details(text: str) -> tuple[str, str]:
    match = re.search(r"^###\s+Character Details\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return text.strip(), ""
    return text[: match.start()].strip(), text[match.end() :].strip()


def parse_details(details: str) -> dict[str, str | list[str]]:
    values: dict[str, str | list[str]] = {}
    values.update(parse_details_table(details))
    current_list = ""
    list_values: list[str] = []
    for line in details.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-") and current_list:
            list_values.append(stripped.lstrip("-").strip())
            continue
        if current_list:
            values[current_list] = list_values
            current_list = ""
            list_values = []
        if ":" not in stripped:
            continue
        label, value = stripped.split(":", 1)
        key = normalize_detail_key(label)
        if value.strip():
            values[key] = value.strip()
        else:
            current_list = key
            list_values = []
    if current_list:
        values[current_list] = list_values
    return values


def parse_details_table(details: str) -> dict[str, str | list[str]]:
    rows = [parse_table_row(line) for line in details.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 3:
        return {}
    headers = [canonical_table_key(header) for header in rows[0]]
    if "field" not in headers or "description" not in headers:
        return {}
    field_index = headers.index("field")
    description_index = headers.index("description")
    values: dict[str, str | list[str]] = {}
    for row in rows[1:]:
        if len(row) <= max(field_index, description_index):
            continue
        if all(set(cell) <= {"-"} for cell in row):
            continue
        key = normalize_detail_key(row[field_index])
        description = row[description_index].strip()
        if not key or not description:
            continue
        if key in {"drives", "allies", "enemies"}:
            existing = values.get(key, [])
            values[key] = [*existing, description] if isinstance(existing, list) else [description]
        else:
            values[key] = description
    return values


def normalize_detail_key(value: str) -> str:
    key = compact_label(value)
    aliases = {
        "ally": "allies",
        "alliance": "allies",
        "alliances": "allies",
        "drive": "drives",
        "drives": "drives",
        "enemy": "enemies",
        "enemies": "enemies",
        "foe": "enemies",
        "foes": "enemies",
        "home": "home",
        "origin": "home",
        "pronoun": "pronouns",
        "pronouns": "pronouns",
    }
    return aliases.get(key, key)


def parse_legacy_stats_details(stats: dict[str, str]) -> dict[str, str | list[str]]:
    values: dict[str, str | list[str]] = {}
    if stats.get("pronouns"):
        values["pronouns"] = stats["pronouns"]
    if stats.get("home"):
        values["home"] = stats["home"]
    if stats.get("drives"):
        values["drives"] = split_detail_values(stats["drives"])
    if stats.get("allies"):
        values["allies"] = split_detail_values(stats["allies"])
    if stats.get("enemies"):
        values["enemies"] = split_detail_values(stats["enemies"])
    return values


def split_detail_values(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;\n,]+", value) if item.strip()]


def write_character_profile(character: Character, profile: CharacterProfile) -> None:
    character.profile_path.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
    character.backstory_path.write_text(render_backstory(profile), encoding="utf-8")
    regenerate_character_graph(character)


def regenerate_character_graph(character: Character) -> None:
    from character_graph.extraction import extract_character_graph
    from character_graph.ingest import load_backstory
    from character_graph.storage import save_graph

    document = load_backstory(character.backstory_path, character_id=sanitize_name(character.name))
    graph = extract_character_graph(document, primary_name=character.name)
    save_graph(graph, character.graph_path)


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
