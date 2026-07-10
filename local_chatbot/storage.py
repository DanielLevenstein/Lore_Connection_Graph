import re
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .paths import (
    CHARACTER_GRAPHS_DIR,
    CHARACTER_METADATA_DIR,
    CHARACTERS_DIR,
    GENERATED_CHARACTER_SHEETS_DIR,
    PLACES_DIR,
    ensure_base_dirs,
)


SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_. -]+")
BACKSTORY_TEMPLATE_PATH = CHARACTER_METADATA_DIR / "TEMPLATE.md"
DEFAULT_STAT_LABELS = ["Name", "Race", "Class", "Level", "Pronouns"]
DEFAULT_ADDABLE_STAT_FIELDS = [
    ("Race", "race", "race"),
    ("Class", "class", "character_class"),
    ("Level", "level", "level"),
    ("Pronouns", "pronouns", "pronouns"),
]
CUSTOM_STAT_EXCLUDED_KEYS = {
    "name",
    "familyname",
    "family_name",
    "race",
    "class",
    "character_class",
    "level",
    "pronouns",
}
DEFAULT_SECTION_HEADINGS = [
    "Character Name",
    "Character Stats",
    "Character Backstory",
    "Character Details",
    "Character Summary",
    "Character Connections",
]
AUTO_GENERATED_MARKER = "Auto Generated"
HONORIFIC_TOKENS = {"ms", "miss", "mr", "mrs", "mx", "dr"}


@dataclass(frozen=True)
class Character:
    name: str
    path: Path

    @property
    def data_dir(self) -> Path:
        return CHARACTER_METADATA_DIR / self.name

    @property
    def backstory_path(self) -> Path:
        if self.path.suffix.lower() == ".md":
            return self.path
        return self.path / "BACKSTORY.md"

    @property
    def memory_path(self) -> Path:
        return self.data_dir / "MEMORY.md"

    @property
    def chatlogs_dir(self) -> Path:
        return self.data_dir / "chatlogs"

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "PROFILE.json"

    @property
    def graph_path(self) -> Path:
        return CHARACTER_GRAPHS_DIR / f"{self.name}.graph.json"


@dataclass(frozen=True)
class Place:
    name: str
    path: Path


@dataclass(frozen=True)
class PlaceProfile:
    name: str
    place_type: str
    summary: str
    details: str = ""
    connections: list[str] | None = None


@dataclass(frozen=True)
class CharacterProfile:
    name: str
    pronouns: str
    level: str
    race: str
    character_class: str
    backstory: str
    first_name: str = ""
    family_name: str = ""
    summary: str = ""
    motivations: list[str] | None = None
    origin: str = ""
    gender: str = ""
    drives: list[str] | None = None
    alliances: list[str] | None = None
    enemies: list[str] | None = None
    details: str = ""
    stat_fields: dict[str, str] | None = None
    aliases: dict[str, dict[str, str]] | None = None
    knowledge_graph_fields: list[dict[str, str]] | None = None
    source_locations: dict[str, str] | None = None
    auto_generated_sections: list[str] | None = None
    original_backstory: str = ""
    original_summary: str = ""


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
        if path.is_file() and path.suffix.lower() == ".md" and path.name != "TEMPLATE.md":
            characters.append(Character(name=path.stem, path=path))
        elif path.is_dir() and (path / "BACKSTORY.md").exists():
            characters.append(Character(name=path.name, path=path))
    return characters


def list_places() -> list[Place]:
    ensure_base_dirs()
    return [
        Place(name=path.stem, path=path)
        for path in sorted(PLACES_DIR.glob("*.md"))
        if path.name != "PLACE_TEMPLATE.md"
    ]


def render_place(profile: PlaceProfile) -> str:
    connections = "\n".join(f"- {value}" for value in profile.connections or [] if value.strip())
    connection_section = f"\n\n## Place Connections\n\n{connections}" if connections else ""
    details = profile.details.strip()
    details_section = f"\n\n## Place Details\n\n{details}" if details else ""
    return (
        f"# {profile.name}\n\n"
        "## Place Stats\n\n"
        "| Name | Type |\n"
        "| ---- | ---- |\n"
        f"| {profile.name} | {profile.place_type} |\n\n"
        "## Place Summary\n\n"
        f"{profile.summary.strip()}"
        f"{details_section}"
        f"{connection_section}\n"
    )


def create_place(profile: PlaceProfile) -> Place:
    ensure_base_dirs()
    PLACES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_name(profile.name)
    place = Place(name=safe_name, path=PLACES_DIR / f"{safe_name}.md")
    if place.path.exists():
        raise FileExistsError(place.path)
    place.path.write_text(render_place(profile), encoding="utf-8")
    return place


def render_backstory(profile: CharacterProfile) -> str:
    summary = profile.summary.strip() or default_summary(profile)
    stats = character_stats(profile)
    details = profile.details.strip() or default_details(profile)
    stats_table = render_stats_table(stats)
    details_section = f"\n\n### Character Details\n\n{details}\n" if details else "\n"
    backstory_heading = section_heading("Character Backstory", profile)
    summary_heading = section_heading("Character Summary", profile)
    original_backstory = original_section("Original Character Backstory", profile.original_backstory)
    original_summary = original_section("Original Character Summary", profile.original_summary)
    return (
        f"# {profile.name}\n\n"
        "## Character Stats\n\n"
        f"{stats_table}\n\n"
        f"## {backstory_heading}\n\n"
        f"{profile.backstory.strip()}{original_backstory}\n\n"
        f"## {summary_heading}\n\n"
        f"{summary}{original_summary}{details_section}"
    )


def section_heading(heading: str, profile: CharacterProfile) -> str:
    generated = {compact_label(value) for value in profile.auto_generated_sections or []}
    if compact_label(heading) in generated:
        return f"{heading} ({AUTO_GENERATED_MARKER})"
    return heading


def original_section(heading: str, text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    return f"\n\n### {heading}\n\n{cleaned}"


def character_stats(profile: CharacterProfile) -> list[tuple[str, str]]:
    stats = [
        ("Name", profile.first_name or character_first_name(profile.name)),
        ("Level", profile.level),
        ("Race", profile.race),
        ("Class", profile.character_class),
        ("Pronouns", profile.pronouns),
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
    parts = name_tokens_without_honorifics(name)
    return parts[0] if parts else ""


def character_family_name(name: str) -> str:
    parts = name_tokens_without_honorifics(name)
    return parts[-1] if len(parts) > 1 else ""


def name_tokens_without_honorifics(name: str) -> list[str]:
    parts = name.strip().split()
    return [part for part in parts if compact_label(part) not in HONORIFIC_TOKENS]


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


def create_character(profile: CharacterProfile, destination_dir: Path | None = None) -> Character:
    ensure_base_dirs()
    safe_name = sanitize_name(profile.name)
    target_dir = destination_dir or CHARACTERS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    character = Character(name=safe_name, path=target_dir / f"{safe_name}.md")
    if character.backstory_path.exists():
        raise FileExistsError(character.backstory_path)
    character.data_dir.mkdir(parents=True, exist_ok=False)
    character.chatlogs_dir.mkdir(exist_ok=True)
    write_character_profile(character, profile)
    character.memory_path.write_text(
        "# Memory\n\nAdd durable character memories here. The chat UI can append notes as you play.\n",
        encoding="utf-8",
    )
    return character


def create_generated_character(profile: CharacterProfile) -> Character:
    return create_character(profile, GENERATED_CHARACTER_SHEETS_DIR)


def create_stub_character(name: str) -> Character:
    clean_name = sanitize_name(name)
    return create_character(
        CharacterProfile(
            name=clean_name,
            pronouns="",
            level="",
            race="",
            character_class="",
            backstory=f"{character_first_name(clean_name) or clean_name}'s story has not been written yet.",
            summary=f"{clean_name} is a secondary character awaiting a full sheet.",
        )
    )


def append_character_connections(character: Character, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    text = read_text(character.backstory_path).rstrip()
    table = render_character_connections_table(rows)
    if re.search(r"^##\s+Character Connections\s*$", text, re.IGNORECASE | re.MULTILINE):
        next_text = replace_section(text, "Character Connections", table)
    else:
        next_text = f"{text}\n\n## Character Connections\n\n{table}\n"
    character.backstory_path.write_text(next_text, encoding="utf-8")
    regenerate_character_graph(character)


def render_character_connections_table(rows: list[dict[str, str]]) -> str:
    sorted_rows = sorted(rows, key=lambda row: 0 if row.get("Source") in {"Character Sheet", "Place"} else 1)
    lines = [
        "| Source | Relationship | Name | Evidence |",
        "| ------ | ------------ | ---- | -------- |",
    ]
    for row in sorted_rows:
        lines.append(
            "| "
            + " | ".join(
                escape_table_cell(row.get(key, ""))
                for key in ("Source", "Relationship", "Name", "Evidence")
            )
            + " |"
        )
    return "\n".join(lines)


def escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


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
            first_name=payload.get("first_name", ""),
            family_name=payload.get("family_name", ""),
            summary=payload.get("summary", ""),
            motivations=payload.get("motivations", []),
            origin=payload.get("origin", ""),
            gender=payload.get("gender", ""),
            drives=payload.get("drives"),
            alliances=payload.get("alliances", []),
            enemies=payload.get("enemies", []),
            details=payload.get("details", ""),
            stat_fields=payload.get("stat_fields") or payload.get("stats"),
            aliases=payload.get("aliases"),
            knowledge_graph_fields=payload.get("knowledge_graph_fields", []),
            source_locations=payload.get("source_locations", {}),
            auto_generated_sections=payload.get("auto_generated_sections", []),
            original_backstory=payload.get("original_backstory", ""),
            original_summary=payload.get("original_summary", ""),
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
    raw_sections = raw_markdown_section_headings(text)
    title = markdown_title(text) or character.name
    stats_section = section_content(sections, "character stats")
    summary_section = section_content(sections, "character summary")
    title_summary = title_preamble(text)
    stat_items = parse_stats_table_items(stats_section)
    stats = stats_dict_from_items(stat_items)
    backstory, original_backstory = split_original_subsection(
        section_content(sections, "character backstory"),
        "Original Character Backstory",
    )
    summary_section, original_summary = split_original_subsection(summary_section, "Original Character Summary")
    summary, details = split_summary_and_details(summary_section)
    summary_source = "character_summary_section"
    if not summary.strip() and title_summary.strip():
        summary = title_summary.strip()
        summary_source = "title_preamble"
    details = append_custom_stat_details(details, stat_items)
    connections_section = section_content(sections, "character connections") or markdown_subsection(
        text, "Character Connections"
    )
    detail_values = parse_details(details)
    details = remove_detail_fields(details, {"pronouns"})
    legacy_detail_values = parse_legacy_stats_details(stats)
    first_name, family_name = name_parts(title, stats)
    aliases = sheet_aliases(title, sections, stats_section)
    stat_fields = normalized_stat_fields(stats)
    knowledge_graph_fields = parse_character_connections(connections_section)
    return CharacterProfile(
        name=title,
        pronouns=str(detail_values.get("pronouns") or legacy_detail_values.get("pronouns", "")),
        level=stats.get("level", ""),
        race=stats.get("race", ""),
        character_class=stats.get("class", ""),
        backstory=backstory,
        first_name=first_name,
        family_name=family_name,
        summary=summary,
        motivations=[],
        origin=str(detail_values.get("home") or legacy_detail_values.get("home", "")),
        gender=str(detail_values.get("gender", "")),
        drives=detail_values.get("drives") or legacy_detail_values.get("drives", []),
        alliances=detail_values.get("allies") or legacy_detail_values.get("allies", []),
        enemies=detail_values.get("enemies") or legacy_detail_values.get("enemies", []),
        details=details,
        stat_fields=stat_fields,
        aliases=aliases,
        knowledge_graph_fields=knowledge_graph_fields,
        source_locations={"summary": summary_source},
        auto_generated_sections=auto_generated_sections(raw_sections),
        original_backstory=original_backstory,
        original_summary=original_summary,
    )


def merge_profiles(stored: CharacterProfile, sheet: CharacterProfile) -> CharacterProfile:
    drives = sheet.drives or stored.drives or []
    alliances = sheet.alliances or stored.alliances or []
    enemies = sheet.enemies or stored.enemies or []
    pronouns = sheet.pronouns or stored.pronouns
    origin = sheet.origin or stored.origin
    gender = sheet.gender or stored.gender
    return CharacterProfile(
        name=sheet.name or stored.name,
        pronouns=pronouns,
        level=sheet.level,
        race=sheet.race,
        character_class=sheet.character_class,
        backstory=sheet.backstory,
        first_name=sheet.first_name or stored.first_name,
        family_name=sheet.family_name or stored.family_name,
        summary=sheet.summary,
        motivations=stored.motivations,
        origin=origin,
        gender=gender,
        drives=drives,
        alliances=alliances,
        enemies=enemies,
        details=sheet.details,
        stat_fields=sheet.stat_fields or stored.stat_fields,
        aliases=merge_aliases(stored.aliases, sheet.aliases),
        knowledge_graph_fields=sheet.knowledge_graph_fields or stored.knowledge_graph_fields or [],
        source_locations={**(stored.source_locations or {}), **(sheet.source_locations or {})},
        auto_generated_sections=sheet.auto_generated_sections or stored.auto_generated_sections or [],
        original_backstory=sheet.original_backstory or stored.original_backstory,
        original_summary=sheet.original_summary or stored.original_summary,
    )


def split_original_subsection(text: str, heading: str) -> tuple[str, str]:
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return text.strip(), ""
    next_heading = re.search(r"^###\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    main = text[: match.start()].strip()
    original = text[match.end() : end].strip()
    return main, original


def markdown_title(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[canonical_section_key(match.group(1))] = text[start:end].strip()
    return sections


def raw_markdown_section_headings(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE)]


def canonical_section_key(heading: str) -> str:
    return re.sub(r"\s*\(auto generated\)\s*$", "", heading.strip(), flags=re.IGNORECASE).lower()


def auto_generated_sections(headings: list[str]) -> list[str]:
    sections: list[str] = []
    for heading in headings:
        if AUTO_GENERATED_MARKER.lower() not in heading.lower():
            continue
        canonical = default_section_heading(canonical_section_key(heading))
        if canonical:
            sections.append(canonical)
    return sections


def title_preamble(text: str) -> str:
    title = re.search(r"^#\s+.+?\s*$", text, re.MULTILINE)
    if not title:
        return ""
    next_section = re.search(r"^##\s+.+?\s*$", text[title.end() :], re.MULTILINE)
    end = title.end() + next_section.start() if next_section else len(text)
    return text[title.end() : end].strip()


def section_content(sections: dict[str, str], heading: str) -> str:
    return sections.get(heading, "")


def parse_stats_table(text: str) -> dict[str, str]:
    return stats_dict_from_items(parse_stats_table_items(text))


def stats_dict_from_items(items: list[tuple[str, str, str]]) -> dict[str, str]:
    return {canonical_key: value for canonical_key, _label, value in items if value.strip()}


def parse_stats_table_items(text: str) -> list[tuple[str, str, str]]:
    rows = [parse_table_row(line) for line in text.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 2:
        return []
    labels = rows[0]
    headers = [canonical_table_key(header) for header in labels]
    data_row = next((row for row in rows[1:] if not all(set(cell) <= {"-"} for cell in row)), [])
    return [
        (canonical_key, label, value.strip())
        for canonical_key, label, value in zip(headers, labels, data_row)
        if value.strip()
    ]


def normalized_stat_fields(stats: dict[str, str]) -> dict[str, str]:
    fields = dict(stats)
    if "class" in fields:
        fields["character_class"] = fields["class"]
    return fields


def custom_stat_items(items: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    return [
        (label, value.strip())
        for canonical_key, label, value in items
        if canonical_key not in CUSTOM_STAT_EXCLUDED_KEYS and value.strip()
    ]


def append_custom_stat_details(details: str, items: list[tuple[str, str, str]]) -> str:
    custom_items = custom_stat_items(items)
    if not custom_items:
        return details.strip()
    existing_keys = set(parse_details(details).keys())
    lines = [details.strip()] if details.strip() else []
    for label, value in custom_items:
        if normalize_detail_key(label) in existing_keys:
            continue
        lines.append(f"{label}: {value}")
    return "\n".join(line for line in lines if line).strip()


def remove_detail_fields(details: str, field_keys: set[str]) -> str:
    lines = details.splitlines()
    filtered: list[str] = []
    table_field_index: int | None = None
    skip_list = False
    for line in lines:
        row = parse_table_row(line)
        if row:
            normalized_row = [canonical_table_key(cell) for cell in row]
            if "field" in normalized_row:
                table_field_index = normalized_row.index("field")
                filtered.append(line)
                continue
            if table_field_index is not None and len(row) > table_field_index:
                field_key = normalize_detail_key(row[table_field_index])
                if field_key in field_keys:
                    continue
            filtered.append(line)
            continue

        stripped = line.strip()
        if skip_list:
            if stripped.startswith("-") or not stripped:
                continue
            skip_list = False
        if ":" in stripped and not stripped.startswith("-"):
            label, value = stripped.split(":", 1)
            if normalize_detail_key(label) in field_keys:
                skip_list = not value.strip()
                continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def name_parts(name: str, stats: dict[str, str]) -> tuple[str, str]:
    stat_name = stats.get("name", "").strip()
    full_name = best_full_name(name, stat_name)
    first_name = character_first_name(full_name)
    family_name = (
        stats.get("familyname")
        or stats.get("family_name")
        or character_family_name(full_name)
    )
    return first_name.strip(), family_name.strip()


def best_full_name(title_name: str, stat_name: str) -> str:
    title_parts = name_tokens_without_honorifics(title_name)
    stat_parts = name_tokens_without_honorifics(stat_name)
    title_compact = compact_label(" ".join(title_parts))
    stat_compact = compact_label(" ".join(stat_parts))
    if len(stat_parts) >= 2 and title_compact.startswith(stat_compact):
        return stat_name
    if len(stat_parts) >= 2 and len(stat_parts) >= len(title_parts):
        return stat_name
    if len(title_parts) >= 2:
        return title_name
    return stat_name or title_name


def sheet_aliases(title: str, sections: dict[str, str], stats_section: str) -> dict[str, dict[str, str]]:
    aliases: dict[str, dict[str, str]] = {}
    section_aliases: dict[str, str] = {}
    if title and title != "Character Name":
        section_aliases["Character Name"] = title
    for actual in sections:
        canonical = default_section_heading(actual)
        if canonical and actual != canonical.lower():
            section_aliases[canonical] = actual
    if section_aliases:
        aliases["sections"] = section_aliases

    stat_aliases: dict[str, str] = {}
    rows = [parse_table_row(line) for line in stats_section.splitlines()]
    header_row = next((row for row in rows if row), [])
    for header in header_row:
        canonical = default_stat_label(header)
        if canonical and header != canonical:
            stat_aliases[canonical] = header
    if stat_aliases:
        aliases["stats"] = stat_aliases
    return aliases


def default_section_heading(heading: str) -> str:
    compact = compact_label(heading)
    defaults = {compact_label(value): value for value in DEFAULT_SECTION_HEADINGS}
    return defaults.get(compact, "")


def default_stat_label(label: str) -> str:
    compact = compact_label(label)
    defaults = {compact_label(value): value for value in DEFAULT_STAT_LABELS}
    aliases = {"characterclass": "Class", "classname": "Class", "familyname": "Name"}
    return defaults.get(compact) or aliases.get(compact, "")


def merge_aliases(
    stored: dict[str, dict[str, str]] | None,
    sheet: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for source in (stored or {}, sheet or {}):
        for key, values in source.items():
            merged.setdefault(key, {}).update(values)
    return merged


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
        "familyname": "familyname",
    }
    return aliases.get(key, key)


def split_summary_and_details(text: str) -> tuple[str, str]:
    match = re.search(r"^###\s+Character Details\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return text.strip(), ""
    summary = text[: match.start()].strip()
    details = strip_markdown_subsection(text[match.end() :], "Character Connections").strip()
    return summary, details


def markdown_subsection(text: str, heading: str) -> str:
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^#{1,3}\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def strip_markdown_subsection(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$.*?(?=^###\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return pattern.sub("", text)


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


def parse_character_connections(text: str) -> list[dict[str, str]]:
    rows = [parse_table_row(line) for line in text.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 3:
        return []
    headers = [normalize_label(header) for header in rows[0]]
    values: list[dict[str, str]] = []
    for row in rows[1:]:
        if all(set(cell) <= {"-"} for cell in row):
            continue
        item = {header: value.strip() for header, value in zip(headers, row) if value.strip()}
        if item:
            values.append(item)
    return values


def normalize_detail_key(value: str) -> str:
    key = compact_label(value)
    aliases = {
        "ally": "allies",
        "alliance": "allies",
        "alliances": "allies",
        "client": "clients",
        "clients": "clients",
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
    profile = enrich_profile(profile)
    character.profile_path.parent.mkdir(parents=True, exist_ok=True)
    character.profile_path.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
    if character.backstory_path.exists():
        current_profile = read_character_sheet(character)
        current_text = read_text(character.backstory_path)
        if current_profile and profiles_match(current_profile, profile) and not sheet_needs_save_update(current_text, current_profile, profile):
            next_text = current_text
        else:
            next_text = update_existing_backstory(current_text, current_profile, profile)
        if next_text != current_text:
            character.backstory_path.write_text(next_text, encoding="utf-8")
    else:
        character.backstory_path.write_text(render_backstory(profile), encoding="utf-8")
    regenerate_character_graph(character)


def enrich_profile(profile: CharacterProfile) -> CharacterProfile:
    first_name = profile.first_name or character_first_name(profile.name)
    family_name = profile.family_name or character_family_name(profile.name)
    stats = normalized_stat_fields(parse_stats_table(render_stats_table(character_stats(profile))))
    if family_name:
        stats.setdefault("family_name", family_name)
    return CharacterProfile(
        name=profile.name,
        pronouns=profile.pronouns,
        level=profile.level,
        race=profile.race,
        character_class=profile.character_class,
        backstory=profile.backstory,
        first_name=first_name,
        family_name=family_name,
        summary=profile.summary,
        motivations=profile.motivations,
        origin=profile.origin,
        gender=profile.gender,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
        stat_fields=profile.stat_fields or stats,
        aliases=profile.aliases or {},
        knowledge_graph_fields=profile.knowledge_graph_fields or [],
        source_locations=profile.source_locations or {},
        auto_generated_sections=profile.auto_generated_sections or [],
        original_backstory=profile.original_backstory,
        original_summary=profile.original_summary,
    )


def profiles_match(left: CharacterProfile, right: CharacterProfile) -> bool:
    return profile_edit_fields(left) == profile_edit_fields(right)


def sheet_needs_save_update(text: str, current_profile: CharacterProfile, profile: CharacterProfile) -> bool:
    return stats_changed(current_profile, profile) or details_section_needs_custom_stats(text)


def profile_edit_fields(profile: CharacterProfile) -> dict[str, object]:
    return {
        "name": profile.name.strip(),
        "first_name": profile.first_name.strip(),
        "family_name": profile.family_name.strip(),
        "pronouns": profile.pronouns.strip(),
        "level": profile.level.strip(),
        "race": profile.race.strip(),
        "character_class": profile.character_class.strip(),
        "backstory": profile.backstory.strip(),
        "summary": profile.summary.strip(),
        "details": profile.details.strip(),
        "drives": profile.drives or [],
        "alliances": profile.alliances or [],
        "enemies": profile.enemies or [],
        "original_backstory": profile.original_backstory.strip(),
        "original_summary": profile.original_summary.strip(),
    }


def update_existing_backstory(
    text: str,
    current_profile: CharacterProfile | None,
    profile: CharacterProfile,
) -> str:
    if not text.strip() or current_profile is None:
        return render_backstory(profile)
    updated = text
    if current_profile.name != profile.name:
        updated = replace_markdown_title(updated, profile.name)
    if stats_changed(current_profile, profile):
        updated = replace_section(updated, "Character Stats", render_updated_stats_table(text, current_profile, profile))
    if current_profile.backstory.strip() != profile.backstory.strip():
        backstory_content = profile.backstory.strip() + original_section(
            "Original Character Backstory",
            profile.original_backstory,
        )
        updated = replace_section(updated, "Character Backstory", backstory_content)
    summary_location = (profile.source_locations or {}).get("summary")
    summary_handled = False
    if summary_location == "title_preamble" and current_profile.summary.strip() != profile.summary.strip():
        updated = replace_title_preamble(updated, profile.summary.strip())
        summary_handled = True
    desired_details = remove_detail_fields(profile.details.strip() or default_details(profile), {"pronouns"})
    desired_details = append_custom_stat_details(
        desired_details,
        parse_stats_table_items(section_content(markdown_sections(updated), "character stats")),
    )
    if (
        (current_profile.summary.strip() != profile.summary.strip() and not summary_handled)
        or current_profile.details.strip() != desired_details.strip()
        or details_section_needs_custom_stats(updated)
    ):
        summary = "" if summary_location == "title_preamble" else profile.summary.strip()
        content = (
            f"{summary}"
            f"{original_section('Original Character Summary', profile.original_summary)}"
            f"\n\n### Character Details\n\n{desired_details}"
        ).strip()
        updated = replace_section(updated, "Character Summary", content)
    return mark_auto_generated_headings(updated, profile)


def details_section_needs_custom_stats(text: str) -> bool:
    sections = markdown_sections(text)
    stat_items = parse_stats_table_items(section_content(sections, "character stats"))
    summary, details = split_summary_and_details(section_content(sections, "character summary"))
    normalized_details = remove_detail_fields(details, {"pronouns"})
    normalized_details = append_custom_stat_details(normalized_details, stat_items)
    return normalized_details != details.strip()


def stats_changed(left: CharacterProfile, right: CharacterProfile) -> bool:
    stat_fields = left.stat_fields or {}
    checks: list[tuple[str, str]] = []
    if "name" in stat_fields:
        checks.append(("first_name", "first_name"))
    if "familyname" in stat_fields or "family_name" in stat_fields:
        checks.append(("family_name", "family_name"))
    checks.extend(
        [
            ("level", "level"),
            ("race", "race"),
            ("class", "character_class"),
            ("character_class", "character_class"),
            ("pronouns", "pronouns"),
        ]
    )
    for stat_key, profile_field in checks:
        if stat_key not in stat_fields:
            continue
        if getattr(left, profile_field, "").strip() != getattr(right, profile_field, "").strip():
            return True
    for _label, stat_key, profile_field in DEFAULT_ADDABLE_STAT_FIELDS:
        if stat_key in stat_fields:
            continue
        if getattr(right, profile_field, "").strip():
            return True
    return False


def render_updated_stats_table(
    text: str,
    current_profile: CharacterProfile,
    profile: CharacterProfile,
) -> str:
    stats_section = section_content(markdown_sections(text), "character stats")
    current_items = parse_stats_table_items(stats_section)
    stats: list[tuple[str, str]] = [
        (label, stat_value_for(canonical_key, value, current_profile, profile))
        for canonical_key, label, value in current_items
    ]
    existing_keys = {canonical_key for canonical_key, _label, _value in current_items}
    for label, canonical_key, profile_field in DEFAULT_ADDABLE_STAT_FIELDS:
        if canonical_key in existing_keys:
            continue
        value = getattr(profile, profile_field, "").strip()
        if value:
            stats.append((label, value))
    return render_stats_table(stats)


def stat_value_for(
    canonical_key: str,
    original_value: str,
    current_profile: CharacterProfile,
    profile: CharacterProfile,
) -> str:
    field_map = {
        "level": "level",
        "race": "race",
        "class": "character_class",
        "character_class": "character_class",
        "pronouns": "pronouns",
    }
    profile_field = field_map.get(canonical_key)
    if not profile_field:
        return original_value
    if getattr(current_profile, profile_field, "").strip() == getattr(profile, profile_field, "").strip():
        return original_value
    return getattr(profile, profile_field, "").strip()


def replace_markdown_title(text: str, title: str) -> str:
    return re.sub(r"^#\s+.+?\s*$", f"# {title}", text, count=1, flags=re.MULTILINE)


def replace_title_preamble(text: str, summary: str) -> str:
    title = re.search(r"^#\s+.+?\s*$", text, re.MULTILINE)
    if not title:
        return text
    next_section = re.search(r"^##\s+.+?\s*$", text[title.end() :], re.MULTILINE)
    end = title.end() + next_section.start() if next_section else len(text)
    replacement = f"\n\n{summary.strip()}\n\n" if summary.strip() else "\n\n"
    return f"{text[: title.end()]}{replacement}{text[end:].lstrip()}"


def replace_section(text: str, heading: str, content: str) -> str:
    pattern = re.compile(
        rf"(^##\s+{re.escape(heading)}(?:\s+\({AUTO_GENERATED_MARKER}\))?\s*$)(.*?)(?=^##\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        suffix = "" if text.endswith("\n") else "\n"
        return f"{text}{suffix}\n## {heading}\n\n{content.strip()}\n"
    replacement = f"{match.group(1)}\n\n{content.strip()}\n"
    return f"{text[: match.start()]}{replacement}{text[match.end():]}"


def mark_auto_generated_headings(text: str, profile: CharacterProfile) -> str:
    generated = {compact_label(value) for value in profile.auto_generated_sections or []}
    updated = text
    for heading in ("Character Backstory", "Character Summary"):
        wants_marker = compact_label(heading) in generated
        marked = f"{heading} ({AUTO_GENERATED_MARKER})"
        if wants_marker:
            updated = re.sub(
                rf"^##\s+{re.escape(heading)}(?:\s+\({AUTO_GENERATED_MARKER}\))?\s*$",
                f"## {marked}",
                updated,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        else:
            updated = re.sub(
                rf"^##\s+{re.escape(marked)}\s*$",
                f"## {heading}",
                updated,
                flags=re.IGNORECASE | re.MULTILINE,
            )
    return updated


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
