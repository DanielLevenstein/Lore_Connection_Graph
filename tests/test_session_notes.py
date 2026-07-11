from datetime import date

import local_chatbot.session_notes as session_notes
from local_chatbot.session_notes import (
    date_from_line,
    import_discord_session_notes,
    import_lore_document_text,
    import_markdown_text,
    save_session_notes,
    split_discord_session_notes,
    split_session_notes,
)


def test_undated_session_notes_save_to_current_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes("The party found a sealed brass door.", today=date(2026, 7, 10))

    assert len(saved) == 1
    assert saved[0].path == tmp_path / "docs" / "lore" / "session_notes" / "2026-07-10_Session_Notes.md"
    assert saved[0].title == "Session Notes"
    assert saved[0].path.read_text(encoding="utf-8") == (
        "# Session Notes - 2026-07-10 - Session Notes\n\n"
        "The party found a sealed brass door.\n"
    )


def test_manual_session_notes_can_use_optional_title(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes("2026-07-10\nThe party found a sealed brass door.", title="Silver Key")

    assert len(saved) == 1
    assert saved[0].path.name == "2026-07-10_Silver_Key.md"
    assert saved[0].title == "Silver Key"
    assert saved[0].path.read_text(encoding="utf-8").startswith("# Session Notes - 2026-07-10 - Silver Key")


def test_session_notes_preserve_markdown_body(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    markdown_body = """2026-07-10
## Scene Notes

- Found a **silver key**
- Met `Jory`

| Clue | Status |
| ---- | ------ |
| Door | Open |"""

    saved = save_session_notes(markdown_body, title="Silver Key")

    assert session_notes.read_session_note_body(saved[0].path) == markdown_body
    assert "## Scene Notes" in saved[0].path.read_text(encoding="utf-8")
    assert "| Clue | Status |" in saved[0].path.read_text(encoding="utf-8")


def test_freeform_lore_import_preserves_undated_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_lore_document_text(
        """# Time Turning

Date and Time values in the days of yore are a fuzzy concept.

## The Nighbloom Family

Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College.
""",
        title="Atlantia Lore",
    )

    assert imported.note_date is None
    assert imported.path.name == "Atlantia_Lore.md"
    assert imported.path.read_text(encoding="utf-8").startswith("# Time Turning\n\nDate and Time")
    assert session_notes.list_session_notes() == [imported.path]


def test_freeform_lore_import_uses_unique_markdown_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    first = import_lore_document_text("# Time Turning", title="Atlantia Lore")
    second = import_lore_document_text("# Time Turning", title="Atlantia Lore")

    assert first.path.name == "Atlantia_Lore.md"
    assert second.path.name == "Atlantia_Lore_2.md"


def test_markdown_import_with_date_detection_preserves_undated_lore(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_markdown_text(
        """# Atlantia Lore

## The Nighbloom Family

Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College.
""",
        title="Atlantia_Lore",
        include_detected_dates=True,
    )

    assert len(imported) == 1
    assert imported[0].note_date is None
    assert imported[0].path.name == "Atlantia_Lore.md"
    assert imported[0].path.read_text(encoding="utf-8").startswith("# Atlantia Lore")


def test_markdown_import_with_date_detection_saves_detected_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_markdown_text(
        "2026-07-10\nThe party found a sealed brass door.",
        title="Silver Key",
        include_detected_dates=True,
        today=date(2026, 7, 12),
    )

    assert imported[0].note_date == date(2026, 7, 10)
    assert imported[0].path.name == "2026-07-10_Silver_Key.md"


def test_legacy_session_note_body_only_strips_date_heading(tmp_path):
    legacy = tmp_path / "session_notes_2026-07-10.md"
    legacy.write_text("##2026-07-10\n\n## Scene Notes\n\n- Found a **silver key**\n", encoding="utf-8")

    assert session_notes.read_session_note_body(legacy) == "## Scene Notes\n\n- Found a **silver key**"


def test_manual_session_notes_split_multiple_session_titles_on_same_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes(
        """2026-07-10
Session 1:

The party found a sealed brass door.

Session 2:

The party opened the door."""
    )

    assert [note.path.name for note in saved] == [
        "2026-07-10_Session_1.md",
        "2026-07-10_Session_2.md",
    ]
    assert "The party opened the door." not in saved[0].path.read_text(encoding="utf-8")


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


def test_discord_export_splits_dates_and_removes_export_noise():
    notes = split_discord_session_notes(
        """Jane Smith [OOZE], Server Tag: OOZEOOZE — 2/19/23, 11:36 PMSunday, February 19, 2023 at 11:36 PM
Session 1:

The party awoke.
:thumbsup:
Click to react
Add Reaction
Reply
Forward
More
February 20, 2023

John Smith [OOZE], Server Tag: OOZEOOZE — 2/20/23, 12:01 AMMonday, February 20, 2023 at 12:01 AM
The party found a piano. (edited)Thursday, August 3, 2023 at 1:55 AM
[12:02 AM]Monday, February 20, 2023 at 12:02 AM
The piano was on fire.
"""
    )

    assert notes == [
        (date(2023, 2, 19), "Session 1", "Session 1:\n\nThe party awoke."),
        (date(2023, 2, 20), "Session Notes", "The party found a piano.\n\nThe piano was on fire."),
    ]


def test_discord_export_splits_multiple_sessions_on_same_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")
    source = tmp_path / "DISCORD.md"
    source.write_text(
        """August 3, 2023

Jory Smith [OOZE], Server Tag: OOZEOOZE — 8/3/23, 2:41 AMThursday, August 3, 2023 at 2:41 AM
Session 2:

The party met Lilith

Fred Smith [OOZE], Server Tag: OOZEOOZE — 8/3/23, 3:22 AMThursday, August 3, 2023 at 3:22 AM
Session 3:

The party met Lucifer.
""",
        encoding="utf-8",
    )

    notes = import_discord_session_notes(source)

    assert [note.title for note in notes] == ["Session 2", "Session 3"]
    assert [note.path.name for note in notes] == [
        "2023-08-03_Session_2.md",
        "2023-08-03_Session_3.md",
    ]
    assert "The party met Lilith" in notes[0].path.read_text(encoding="utf-8")
    assert "The party met Lucifer." not in notes[0].path.read_text(encoding="utf-8")


def test_discord_export_can_keep_multiple_sessions_in_one_note(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")
    source = tmp_path / "DISCORD.md"
    source.write_text(
        """August 3, 2023

Bob Roth [OOZE], Server Tag: OOZEOOZE — 8/3/23, 2:41 AMThursday, August 3, 2023 at 2:41 AM
Session 2:

The party met Lilith

Mary Jones [OOZE], Server Tag: OOZEOOZE — 8/3/23, 3:22 AMThursday, August 3, 2023 at 3:22 AM
Session 3:

The party met Lucifer.
""",
        encoding="utf-8",
    )

    notes = import_discord_session_notes(source, split_sessions=False)

    assert len(notes) == 1
    assert notes[0].title == "Sessions 2-3"
    assert notes[0].path.name == "2023-08-03_Sessions_2_3.md"
    assert "The party met Lilith" in notes[0].path.read_text(encoding="utf-8")
    assert "The party met Lucifer." in notes[0].path.read_text(encoding="utf-8")
