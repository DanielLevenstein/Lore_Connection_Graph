from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .paths import SESSION_NOTES_DIR


ISO_DATE_PATTERN = re.compile(r"\b(?P<year>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\b")
SLASH_DATE_PATTERN = re.compile(r"\b(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:/(?P<year>20\d{2}))?\b")
MONTH_DATE_PATTERN = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2})(?:,\s*(?P<year>20\d{2}))?\b",
    re.IGNORECASE,
)
DISCORD_AUTHOR_DATE_PATTERN = re.compile(r"—\s*\d{1,2}/\d{1,2}/\d{2},\s*.+$")
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
    note_date: date | None
    body: str
    path: Path
    title: str = ""


def session_note_path(note_date: date, title: str = "") -> Path:
    return SESSION_NOTES_DIR / f"{note_date.isoformat()}_{safe_session_note_title(title or 'Session Notes')}.md"


def safe_session_note_title(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", title.strip()).strip("_")
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


def import_markdown_text(
    text: str,
    title: str = "",
    include_detected_dates: bool = False,
    split_sessions: bool = True,
    today: date | None = None,
) -> list[SessionNote]:
    if include_detected_dates:
        imported = import_discord_session_notes_text(text, split_sessions=split_sessions)
        if imported:
            return imported
        if text_has_session_dates(text, today):
            return save_session_notes(text, today=today, title=title)
    return [import_lore_document_text(text, title=title)]


def text_has_session_dates(text: str, today: date | None = None) -> bool:
    default_year = (today or date.today()).year
    return any(date_from_line(line, default_year) for line in text.splitlines())


def split_session_notes(text: str, today: date | None = None) -> list[tuple[date, str]]:
    today = today or date.today()
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


def save_session_notes(text: str, today: date | None = None, title: str = "") -> list[SessionNote]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes: list[SessionNote] = []
    for note_date, note_title, body in extract_session_notes(text, today, title):
        path = session_note_path(note_date, note_title)
        content = render_session_note(note_date, body, note_title)
        path.write_text(content, encoding="utf-8")
        notes.append(SessionNote(note_date=note_date, body=body, path=path, title=note_title))
    return notes


def extract_session_notes(text: str, today: date | None = None, title: str = "") -> list[tuple[date, str, str]]:
    extracted: list[tuple[date, str, str]] = []
    for note_date, body in split_session_notes(text, today):
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
    return discord_full_date(line) or date_from_line(line, date.today().year)


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
        reverse=True,
    )


def session_note_sort_key(path: Path) -> tuple[int, date, str]:
    try:
        return (1, session_note_date_from_path(path), path.name.lower())
    except ValueError:
        return (0, date.min, path.name.lower())


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


def read_session_note_title(path: Path) -> str:
    text = read_session_note(path)
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line.lower().startswith("# session notes -"):
        return ""
    try:
        note_date = session_note_date_from_path(path).isoformat()
    except ValueError:
        return ""
    prefix = f"# Session Notes - {note_date} - "
    if first_line.lower().startswith(prefix.lower()):
        return first_line[len(prefix):].strip()
    return ""


def markdown_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("#").strip()
    return ""


def session_note_date_from_path(path: Path) -> date:
    match = re.search(r"(?P<year>20\d{2})-(?P<month>\d{1,2})-(?P<day>\d{1,2})", path.stem)
    if not match:
        raise ValueError(f"Could not find a session note date in {path.name}.")
    return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))


def write_session_note(path: Path, body: str, title: str = "") -> SessionNote:
    note_date = session_note_date_from_path(path)
    path.write_text(render_session_note(note_date, body, title), encoding="utf-8")
    return SessionNote(note_date=note_date, body=body.strip(), path=path, title=title.strip())


def write_lore_document(path: Path, body: str) -> SessionNote:
    title = markdown_title(body) or path.stem.replace("_", " ")
    path.write_text(f"{body.strip()}\n", encoding="utf-8")
    return SessionNote(note_date=None, body=body.strip(), path=path, title=title)


def delete_session_note(path: Path) -> None:
    path.unlink(missing_ok=True)


def render_session_note(note_date: date, body: str, title: str = "") -> str:
    title_suffix = f" - {title.strip()}" if title.strip() else ""
    return f"# Session Notes - {note_date.isoformat()}{title_suffix}\n\n{body.strip()}\n"


def append_lines(buckets: dict[date, list[str]], order: list[date], note_date: date, lines: list[str]) -> None:
    if note_date not in buckets:
        buckets[note_date] = []
        order.append(note_date)
    buckets[note_date].extend(lines)


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
