from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .paths import SESSION_NOTES_DIR


ISO_DATE_PATTERN = re.compile(r"\b(?P<year>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\b")
SLASH_DATE_PATTERN = re.compile(r"\b(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:/(?P<year>20\d{2}))?\b")
MONTH_DATE_PATTERN = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2})(?:,\s*(?P<year>20\d{2}))?\b",
    re.IGNORECASE,
)
DISCORD_AUTHOR_DATE_PATTERN = re.compile(r"—\s*\d{1,2}/\d{1,2}/(?:\d{2}|20\d{2}),\s*.+$")
DISCORD_AUTHOR_HEADING_PATTERN = re.compile(
    r"^(?P<username>.+?)\s*(?:\[[^\]]+\])?\s*,?\s*(?:Server Tag:[^—]*)?—",
    re.IGNORECASE,
)
DISCORD_SHORT_DATE_PATTERN = re.compile(r"—\s*(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{2}|20\d{2}),")
DISCORD_CONTINUATION_PATTERN = re.compile(r"^\[[^\]]+\](?P<date>.+)$")
DISCORD_DATE_DIVIDER_PATTERN = re.compile(
    r"^(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2}),\s*(?P<year>20\d{2})$",
    re.IGNORECASE,
)
DISCORD_NOISE_LINES = {
    "click to react",
    "add reaction",
    "reply",
    "forward",
    "more",
    "message #story",
    "spoiler",
}
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class SessionNote:
    note_date: date | str | None
    body: str
    path: Path
    title: str = ""


@dataclass(frozen=True)
class ImportHeading:
    key: str
    level: int
    text: str
    kind: str


@dataclass(frozen=True)
class MarkdownSection:
    key: str
    level: int
    text: str
    date_text: str
    body: str
    start_line: int = 0
    end_line: int = 0


def session_note_path(note_date: date | str, title: str = "") -> Path:
    date_slug = note_date.isoformat() if isinstance(note_date, date) else safe_session_note_title(note_date)
    return SESSION_NOTES_DIR / f"{date_slug}_{safe_session_note_title(title or 'Session Notes')}.md"


def safe_session_note_title(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", title.strip()).strip("_")
    if cleaned.lower() == "session_importer":
        return "Session_importer"
    return cleaned or "Session_Notes"


def lore_document_path(title: str) -> Path:
    return unique_markdown_path(SESSION_NOTES_DIR / f"{safe_session_note_title(title)}.md")


def unique_markdown_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(path)


def import_lore_document_text(text: str, title: str = "") -> SessionNote:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    inferred_title = title.strip() or markdown_title(text) or "Lore Document"
    path = lore_document_path(inferred_title)
    body = text.strip()
    path.write_text(f"{body}\n", encoding="utf-8")
    return SessionNote(note_date=None, body=body, path=path, title=inferred_title)


def prepare_markdown_import(
    text: str,
    title: str = "",
    selected_heading_keys: set[str] | None = None,
    today: date | None = None,
) -> tuple[str, list[ImportHeading]]:
    normalized = normalize_import_headings(text, title=title, today=today)
    headings = import_headings(normalized, today=today)
    if selected_heading_keys is None:
        return normalized, headings
    return restore_unselected_import_headings(normalized, selected_heading_keys, today=today), headings


def normalize_import_headings(text: str, title: str = "", today: date | None = None) -> str:
    default_year = (today or date.today()).year
    lines = text.strip().splitlines()
    document_title = clean_import_title(title.strip()) or markdown_title(text) or "Session Notes"
    normalized: list[str] = []
    found_document_title = False
    seen_content = False

    for line in lines:
        stripped = line.strip()
        discord_heading = discord_author_heading_text(stripped)
        if discord_heading:
            normalized.append(f"#### {discord_heading}")
            if stripped:
                seen_content = True
            continue
        heading = markdown_heading_parts(stripped)
        date_text = standalone_date_text(stripped, default_year)
        if date_text:
            normalized.append(f"## {date_text}")
            continue
        if heading:
            level, heading_text = heading
            if not found_document_title and level == 1:
                normalized.append(f"# {heading_text}")
                found_document_title = True
                seen_content = True
            else:
                normalized.append(f"{'#' * level} {heading_text}")
                seen_content = True
            continue
        if (
            stripped
            and not found_document_title
            and not seen_content
            and safe_session_note_title(stripped).lower() == safe_session_note_title(document_title).lower()
        ):
            normalized.append(f"# {document_title}")
            found_document_title = True
            seen_content = True
            continue
        if looks_like_plain_section_heading(stripped):
            heading_text = stripped.rstrip(":")
            if not found_document_title and not seen_content:
                if safe_session_note_title(heading_text).lower() == safe_session_note_title(document_title).lower():
                    heading_text = document_title
                normalized.append(f"# {heading_text}")
                found_document_title = True
            else:
                normalized.append(f"### {heading_text}")
            seen_content = True
            continue
        normalized.append(line)
        if stripped:
            seen_content = True

    if not found_document_title:
        normalized.insert(0, f"# {document_title}")
        if len(normalized) > 1 and normalized[1].strip():
            normalized.insert(1, "")
    return "\n".join(move_h3_headings_up_one_line(normalized)).strip()


def import_headings(text: str, today: date | None = None) -> list[ImportHeading]:
    default_year = (today or date.today()).year
    headings: list[ImportHeading] = []
    for line in text.splitlines():
        heading = markdown_heading_parts(line.strip())
        if not heading:
            continue
        level, heading_text = heading
        if level > 3:
            continue
        kind = "date" if standalone_date_text(heading_text, default_year) else "heading"
        key = f"{len(headings)}:{kind}:{safe_session_note_title(heading_text)}"
        headings.append(ImportHeading(key=key, level=level, text=heading_text, kind=kind))
    return headings


def clean_import_title(title: str) -> str:
    return title.replace("_", " ").strip()


def restore_unselected_import_headings(
    text: str,
    selected_heading_keys: set[str],
    today: date | None = None,
) -> str:
    heading_order = import_headings(text, today=today)
    key_by_index = {index: heading.key for index, heading in enumerate(heading_order)}
    heading_index = 0
    output: list[str] = []
    for line in text.splitlines():
        heading = markdown_heading_parts(line.strip())
        if not heading or heading[0] > 3:
            output.append(line)
            continue
        _level, heading_text = heading
        key = key_by_index.get(heading_index)
        heading_index += 1
        is_date_heading = standalone_date_text(heading_text, (today or date.today()).year)
        if key and key not in selected_heading_keys and not is_date_heading:
            output.append(heading_text)
        else:
            output.append(line)
    return "\n".join(output).strip()


def markdown_sections(text: str, today: date | None = None) -> list[MarkdownSection]:
    default_year = (today or date.today()).year
    lines = text.splitlines()
    heading_positions: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        heading = markdown_heading_parts(line.strip())
        if heading and heading[0] <= 3:
            heading_positions.append((index, heading[0], heading[1]))

    sections: list[MarkdownSection] = []
    current_date = ""
    for position, (line_index, level, heading_text) in enumerate(heading_positions):
        if level == 2 and standalone_date_text(heading_text, default_year):
            current_date = heading_text
        next_index = len(lines)
        for following_index, following_level, _following_text in heading_positions[position + 1 :]:
            if following_level <= level:
                next_index = following_index
                break
        body = "\n".join(lines[line_index:next_index]).strip()
        section_date = heading_text if level == 2 and standalone_date_text(heading_text, default_year) else current_date
        key = f"{position}:{level}:{safe_session_note_title(heading_text)}"
        sections.append(
            MarkdownSection(
                key=key,
                level=level,
                text=heading_text,
                date_text=section_date,
                body=body,
                start_line=line_index,
                end_line=next_index,
            )
        )
    return sections


def read_markdown_section(path: Path, section_key: str) -> str:
    for section in markdown_sections(read_session_note(path)):
        if section.key == section_key:
            return section.body
    return read_session_note(path).strip()


def write_markdown_section(path: Path, section_key: str, body: str) -> SessionNote:
    text = read_session_note(path)
    sections = markdown_sections(text)
    section = next((candidate for candidate in sections if candidate.key == section_key), None)
    if section is None:
        return write_lore_document(path, body)

    lines = text.splitlines()
    replacement = body.strip().splitlines()
    updated_lines = lines[: section.start_line] + replacement + lines[section.end_line :]
    updated = "\n".join(updated_lines).strip()
    path.write_text(f"{updated}\n", encoding="utf-8")
    title = markdown_title(updated) or path.stem.replace("_", " ")
    return SessionNote(note_date=None, body=updated, path=path, title=title)


def move_h3_headings_up_one_line(lines: list[str]) -> list[str]:
    reordered = list(lines)
    for index in range(1, len(reordered)):
        if markdown_heading_parts(reordered[index].strip()) and reordered[index].strip().startswith("### "):
            reordered[index - 1], reordered[index] = reordered[index], reordered[index - 1]
    return reordered


def import_markdown_text(
    text: str,
    title: str = "",
    include_detected_dates: bool = False,
    split_sessions: bool = True,
    session_date: str = "",
    selected_heading_keys: set[str] | None = None,
    save_as_single_file: bool = False,
    today: date | None = None,
) -> list[SessionNote]:
    if save_as_single_file:
        text, _headings = prepare_markdown_import(
            text,
            title=title,
            selected_heading_keys=selected_heading_keys,
            today=today,
        )
        return [import_lore_document_text(text, title=title)]
    if include_detected_dates:
        imported = import_discord_session_notes_text(text, split_sessions=split_sessions)
        if imported:
            return imported
        if selected_heading_keys is None:
            text = normalize_date_fields_to_markdown_headings(text, today)
        else:
            text, _headings = prepare_markdown_import(
                text,
                title=title,
                selected_heading_keys=selected_heading_keys,
                today=today,
            )
        if text_has_session_dates(text, today):
            return save_session_notes(text, today=today, title=title)
    else:
        if selected_heading_keys is None:
            text = normalize_date_fields_to_markdown_headings(text, today)
        else:
            text, _headings = prepare_markdown_import(
                text,
                title=title,
                selected_heading_keys=selected_heading_keys,
                today=today,
            )
    if session_date.strip():
        return save_session_notes(text, today=today, title=title, session_date=session_date)
    return [import_lore_document_text(text, title=title)]


def text_has_session_dates(text: str, today: date | None = None) -> bool:
    default_year = (today or date.today()).year
    return any(date_from_line(line, default_year) for line in text.splitlines())


def split_session_notes(text: str, today: date | None = None) -> list[tuple[date, str]]:
    today = today or date.today()
    text = normalize_date_fields_to_markdown_headings(text, today)
    lines = text.strip().splitlines()
    if not lines:
        return [(today, "")]

    buckets: dict[date, list[str]] = {}
    order: list[date] = []
    current_date: date | None = None
    preamble: list[str] = []

    for line in lines:
        line_date = date_from_line(line, today.year)
        if line_date:
            if current_date is None and preamble:
                append_lines(buckets, order, line_date, preamble)
                preamble = []
            current_date = line_date
        if current_date is None:
            preamble.append(line)
        else:
            append_lines(buckets, order, current_date, [line])

    if current_date is None:
        return [(today, text.strip())]
    if preamble:
        append_lines(buckets, order, order[0], preamble)
    return [(note_date, "\n".join(buckets[note_date]).strip()) for note_date in order]


def save_session_notes(
    text: str,
    today: date | None = None,
    title: str = "",
    session_date: str = "",
) -> list[SessionNote]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    text = normalize_date_fields_to_markdown_headings(text, today)
    notes: list[SessionNote] = []
    for note_date, note_title, body in extract_session_notes(text, today, title, session_date):
        path = session_note_path(note_date, note_title)
        content = render_session_note(note_date, body, note_title)
        path.write_text(content, encoding="utf-8")
        notes.append(SessionNote(note_date=note_date, body=body, path=path, title=note_title))
    return notes


def extract_session_notes(
    text: str,
    today: date | None = None,
    title: str = "",
    session_date: str = "",
) -> list[tuple[date | str, str, str]]:
    extracted: list[tuple[date | str, str, str]] = []
    explicit_session_date = parse_editable_session_date(session_date)
    dated_bodies: list[tuple[date | str, str]]
    if explicit_session_date:
        dated_bodies = [(explicit_session_date, text.strip())]
    else:
        dated_bodies = split_session_notes(text, today)
    for note_date, body in dated_bodies:
        for inferred_title, session_body in split_session_note_bodies(body):
            extracted.append((note_date, inferred_title, session_body))
    if title.strip() and len(extracted) == 1:
        note_date, _inferred_title, body = extracted[0]
        return [(note_date, title.strip(), body)]
    return extracted


def import_discord_session_notes(path: Path, split_sessions: bool = True) -> list[SessionNote]:
    text = path.read_text(encoding="utf-8")
    return import_discord_session_notes_text(text, split_sessions=split_sessions)


def import_discord_session_notes_text(text: str, split_sessions: bool = True) -> list[SessionNote]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes: list[SessionNote] = []
    for note_date, title, body in split_discord_session_notes(text, split_sessions=split_sessions):
        note_path = session_note_path(note_date, title)
        note_path.write_text(render_session_note(note_date, body, title), encoding="utf-8")
        notes.append(SessionNote(note_date=note_date, body=body, path=note_path, title=title))
    return notes


def split_discord_session_notes(text: str, split_sessions: bool = True) -> list[tuple[date, str, str]]:
    buckets: dict[date, list[str]] = {}
    order: list[date] = []
    current_date: date | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_date and buckets.get(current_date) and buckets[current_date][-1] != "":
                buckets[current_date].append("")
            continue
        if is_discord_noise_line(line):
            continue

        divider_date = discord_date_divider(line)
        if divider_date:
            current_date = divider_date
            append_lines(buckets, order, current_date, [])
            continue

        continuation_date = discord_continuation_date(line)
        if continuation_date:
            append_discord_message_break(buckets, continuation_date)
            current_date = continuation_date
            append_lines(buckets, order, current_date, [])
            continue

        header_date = discord_author_line_date(line)
        if header_date:
            append_discord_message_break(buckets, header_date)
            current_date = header_date
            append_lines(buckets, order, current_date, [])
            continue

        if current_date:
            append_lines(buckets, order, current_date, [clean_discord_line(line)])

    notes: list[tuple[date, str, str]] = []
    for note_date in order:
        body = "\n".join(buckets[note_date]).strip()
        if not body:
            continue
        if not split_sessions:
            notes.append((note_date, title_from_session_note_body(body), body))
            continue
        for title, session_body in split_session_note_bodies(body):
            notes.append((note_date, title, session_body))
    return notes


def discord_author_heading_text(line: str) -> str:
    match = DISCORD_AUTHOR_HEADING_PATTERN.match(line)
    if not match:
        return ""
    author_date = discord_author_line_date(line)
    if not author_date:
        return ""
    username = clean_discord_username(match.group("username"))
    if not username:
        return ""
    return f"{author_date:%Y/%m/%d} - {username}"


def clean_discord_username(username: str) -> str:
    return " ".join(username.strip().rstrip(",").split())


def split_session_note_bodies(body: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?im)^Session\s+(.+?):\s*$", body))
    if not matches:
        return [(title_from_session_note_body(body), body.strip())]

    notes = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        session_body = body[start:end].strip()
        title = f"Session {match.group(1).strip()}"
        notes.append((title, session_body))
    return notes


def discord_author_line_date(line: str) -> date | None:
    if not DISCORD_AUTHOR_DATE_PATTERN.search(line):
        return None
    return discord_full_date(line) or discord_short_date(line) or date_from_line(line, date.today().year)


def discord_continuation_date(line: str) -> date | None:
    match = DISCORD_CONTINUATION_PATTERN.match(line)
    if not match:
        return None
    date_text = match.group("date")
    return discord_full_date(date_text) or date_from_line(date_text, date.today().year)


def discord_date_divider(line: str) -> date | None:
    match = DISCORD_DATE_DIVIDER_PATTERN.match(line)
    if not match:
        return None
    month = MONTHS[match.group("month").lower()]
    return date(int(match.group("year")), month, int(match.group("day")))


def discord_short_date(line: str) -> date | None:
    match = DISCORD_SHORT_DATE_PATTERN.search(line)
    if not match:
        return None
    year = int(match.group("year"))
    if year < 100:
        year += 2000
    try:
        return date(year, int(match.group("month")), int(match.group("day")))
    except ValueError:
        return None


def discord_full_date(line: str) -> date | None:
    match = MONTH_DATE_PATTERN.search(line)
    if not match or not match.group("year"):
        return None
    month = MONTHS[match.group("month").lower()]
    return date(int(match.group("year")), month, int(match.group("day")))


def append_discord_message_break(buckets: dict[date, list[str]], note_date: date) -> None:
    if buckets.get(note_date) and buckets[note_date][-1] != "":
        buckets[note_date].append("")


def is_discord_noise_line(line: str) -> bool:
    lowered = line.lower()
    if lowered in DISCORD_NOISE_LINES:
        return True
    if re.fullmatch(r":\w+:", line):
        return True
    if re.fullmatch(r"\d+", line):
        return True
    return False


def clean_discord_line(line: str) -> str:
    return re.sub(r"\s*\(edited\).*$", "", line).rstrip()


def title_from_session_note_body(body: str) -> str:
    sessions = []
    for match in re.finditer(r"(?im)^Session\s+(.+?):\s*$", body):
        sessions.append(match.group(1))
    if len(sessions) == 1:
        return f"Session {sessions[0]}"
    if len(sessions) > 1:
        return f"Sessions {sessions[0]}-{sessions[-1]}"
    return "Session Notes"


def list_session_notes() -> list[Path]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(
        [
            path
            for path in SESSION_NOTES_DIR.glob("*.md")
            if path.name != "DISCORD.md" and "TEMPLATE" not in path.name.upper()
        ],
        key=session_note_sort_key,
    )


def session_note_sort_key(path: Path) -> tuple[Any, ...]:
    session_date = read_session_note_date_text(path)
    if session_date:
        parsed_date = date_from_line(session_date, date.today().year)
        if parsed_date:
            return (0, 0, -parsed_date.toordinal(), natural_sort_key(read_session_note_title(path)), path.name.lower())
        return (0, 1, natural_sort_key(session_date), natural_sort_key(read_session_note_title(path)), path.name.lower())
    return (1, -path_import_timestamp(path), natural_sort_key(path.stem), path.name.lower())


def has_session_note_date(path: Path) -> bool:
    try:
        session_note_date_from_path(path)
    except ValueError:
        return False
    return True


def read_session_note(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_session_note_body(path: Path) -> str:
    text = read_session_note(path)
    lines = text.splitlines()
    if lines and lines[0].strip().lower().startswith("# session notes -"):
        return "\n".join(lines[1:]).strip()
    if lines and re.fullmatch(r"##\s*20\d{2}-\d{1,2}-\d{1,2}", lines[0].strip()):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def parse_session_note_heading(path: Path) -> tuple[str, str]:
    text = read_session_note(path)
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    match = re.match(r"^#\s+Session Notes\s+-\s+(?P<session_date>.+?)(?:\s+-\s+(?P<title>.+))?$", first_line)
    if match:
        return match.group("session_date").strip(), (match.group("title") or "").strip()
    try:
        return session_note_date_from_path(path).isoformat(), ""
    except ValueError:
        return "", ""


def read_session_note_date_text(path: Path) -> str:
    session_date, _title = parse_session_note_heading(path)
    return session_date


def read_session_note_title(path: Path) -> str:
    _session_date, title = parse_session_note_heading(path)
    return title


def markdown_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("#").strip()
    return ""


def markdown_heading_parts(line: str) -> tuple[int, str] | None:
    match = re.fullmatch(r"(#{1,6})\s+(.+?)\s*", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def looks_like_plain_section_heading(line: str) -> bool:
    if not line or len(line) > 80:
        return False
    if line.startswith(("-", "*", "|", ">")):
        return False
    if not line.endswith(":"):
        return False
    line = line.rstrip(":").strip()
    if re.search(r"[.!?]$", line):
        return False
    if standalone_date_text(line, date.today().year):
        return False
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9'’&/ -]+", line))


def session_note_date_from_path(path: Path) -> date:
    match = re.search(r"(?P<year>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})", path.stem)
    if not match:
        raise ValueError(f"Could not find a session note date in {path.name}.")
    return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))


def write_session_note(path: Path, body: str, title: str = "", session_date: str = "") -> SessionNote:
    note_date = parse_editable_session_date(session_date) or parse_editable_session_date(read_session_note_date_text(path))
    if not note_date:
        note_date = session_note_date_from_path(path)
    path.write_text(render_session_note(note_date, body, title), encoding="utf-8")
    return SessionNote(note_date=note_date, body=body.strip(), path=path, title=title.strip())


def write_lore_document(path: Path, body: str) -> SessionNote:
    title = markdown_title(body) or path.stem.replace("_", " ")
    path.write_text(f"{body.strip()}\n", encoding="utf-8")
    return SessionNote(note_date=None, body=body.strip(), path=path, title=title)


def delete_session_note(path: Path) -> None:
    path.unlink(missing_ok=True)


def render_session_note(note_date: date | str, body: str, title: str = "") -> str:
    session_date = note_date.isoformat() if isinstance(note_date, date) else note_date.strip()
    title_suffix = f" - {title.strip()}" if title.strip() else ""
    return f"# Session Notes - {session_date}{title_suffix}\n\n{body.strip()}\n"


def append_lines(buckets: dict[date, list[str]], order: list[date], note_date: date, lines: list[str]) -> None:
    if note_date not in buckets:
        buckets[note_date] = []
        order.append(note_date)
    buckets[note_date].extend(lines)


def parse_editable_session_date(session_date: str) -> date | str | None:
    cleaned = session_date.strip()
    if not cleaned:
        return None
    parsed = date_from_line(cleaned, date.today().year)
    return parsed or cleaned


def natural_sort_key(value: str) -> tuple[Any, ...]:
    parts: list[Any] = []
    for part in re.split(r"(\d+)", value.lower()):
        if part.isdigit():
            parts.append((0, int(part)))
        elif part:
            parts.append((1, part))
    return tuple(parts)


def path_import_timestamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def date_from_line(line: str, default_year: int) -> date | None:
    for pattern in (ISO_DATE_PATTERN, SLASH_DATE_PATTERN, MONTH_DATE_PATTERN):
        match = pattern.search(line)
        if not match:
            continue
        parts = match.groupdict()
        year = int(parts.get("year") or default_year)
        month_value = parts["month"]
        month = int(month_value) if month_value.isdigit() else MONTHS.get(month_value.lower(), 0)
        day = int(parts["day"])
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def normalize_date_fields_to_markdown_headings(text: str, today: date | None = None) -> str:
    default_year = (today or date.today()).year
    normalized_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        date_text = standalone_date_text(stripped, default_year)
        if date_text:
            normalized_lines.append(f"## {date_text}")
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def standalone_date_text(line: str, default_year: int) -> str:
    heading_match = re.fullmatch(r"#{1,6}\s*(?P<date_text>.+)", line)
    date_text = heading_match.group("date_text").strip() if heading_match else line
    if not date_text:
        return ""
    if not date_from_line(date_text, default_year):
        return ""
    exact_patterns = (
        r"20\d{2}-\d{1,2}-\d{1,2}",
        r"\d{1,2}/\d{1,2}(?:/20\d{2})?",
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2}(?:,\s*20\d{2})?",
    )
    if any(re.fullmatch(pattern, date_text, re.IGNORECASE) for pattern in exact_patterns):
        return date_text
    return ""
