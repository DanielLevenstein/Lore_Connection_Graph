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
    note_date: date
    body: str
    path: Path


def session_note_path(note_date: date) -> Path:
    return SESSION_NOTES_DIR / f"session_notes_{note_date.isoformat()}.md"


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


def save_session_notes(text: str, today: date | None = None) -> list[SessionNote]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes: list[SessionNote] = []
    for note_date, body in split_session_notes(text, today):
        path = session_note_path(note_date)
        content = render_session_note(note_date, body)
        path.write_text(content, encoding="utf-8")
        notes.append(SessionNote(note_date=note_date, body=body, path=path))
    return notes


def list_session_notes() -> list[Path]:
    SESSION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(SESSION_NOTES_DIR.glob("session_notes_*.md"), reverse=True)


def read_session_note(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_session_note(note_date: date, body: str) -> str:
    return f"# Session Notes - {note_date.isoformat()}\n\n{body.strip()}\n"


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
