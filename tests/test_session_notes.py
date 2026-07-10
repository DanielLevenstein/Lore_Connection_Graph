from datetime import date

import local_chatbot.session_notes as session_notes
from local_chatbot.session_notes import date_from_line, save_session_notes, split_session_notes


def test_undated_session_notes_save_to_current_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes("The party found a sealed brass door.", today=date(2026, 7, 10))

    assert len(saved) == 1
    assert saved[0].path == tmp_path / "docs" / "lore" / "session_notes" / "session_notes_2026-07-10.md"
    assert saved[0].path.read_text(encoding="utf-8") == (
        "# Session Notes - 2026-07-10\n\n"
        "The party found a sealed brass door.\n"
    )


def test_session_notes_split_iso_dates_into_calendar_files(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes(
        """2026-07-10
Neal met Jory at the docks.

2026-07-11
The party followed the lighthouse trail.""",
        today=date(2026, 7, 12),
    )

    assert [note.note_date for note in saved] == [date(2026, 7, 10), date(2026, 7, 11)]
    assert "Neal met Jory" in saved[0].path.read_text(encoding="utf-8")
    assert "lighthouse trail" in saved[1].path.read_text(encoding="utf-8")
    assert "lighthouse trail" not in saved[0].path.read_text(encoding="utf-8")


def test_session_notes_support_slash_dates_without_year():
    notes = split_session_notes(
        """7/9
Opened the old archive.

7/10
Found the second key.""",
        today=date(2026, 7, 12),
    )

    assert notes == [
        (date(2026, 7, 9), "7/9\nOpened the old archive."),
        (date(2026, 7, 10), "7/10\nFound the second key."),
    ]


def test_session_notes_support_month_name_dates_without_year():
    assert date_from_line("July 10 - met the oracle", default_year=2026) == date(2026, 7, 10)
    assert date_from_line("December 2, 2027: winter court", default_year=2026) == date(2027, 12, 2)


def test_session_notes_ignore_invalid_dates():
    notes = split_session_notes("2026-99-99\nStill just text.", today=date(2026, 7, 10))

    assert notes == [(date(2026, 7, 10), "2026-99-99\nStill just text.")]


def test_session_notes_merge_repeated_calendar_dates():
    notes = split_session_notes(
        """2026-07-10
First note.

2026-07-11
Middle note.

2026-07-10
Follow-up note.""",
        today=date(2026, 7, 12),
    )

    assert notes == [
        (date(2026, 7, 10), "2026-07-10\nFirst note.\n\n2026-07-10\nFollow-up note."),
        (date(2026, 7, 11), "2026-07-11\nMiddle note."),
    ]


def test_session_note_preamble_attaches_to_first_dated_file():
    notes = split_session_notes(
        """Campaign memory

2026-07-10
The date appears after the heading.""",
        today=date(2026, 7, 12),
    )

    assert notes == [
        (date(2026, 7, 10), "Campaign memory\n\n2026-07-10\nThe date appears after the heading.")
    ]
