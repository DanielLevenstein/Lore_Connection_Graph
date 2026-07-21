import os
from datetime import date

import local_chatbot.session_notes as session_notes
from local_chatbot.session_notes import (
    child_markdown_sections,
    combine_markdown_section,
    date_from_line,
    hide_markdown_section_heading,
    insert_markdown_section,
    import_discord_session_notes,
    import_lore_document_text,
    import_markdown_text,
    markdown_sections,
    normalize_session_note_file_headings,
    prepare_markdown_import,
    remove_markdown_section,
    removing_markdown_section_removes_file,
    save_session_notes,
    split_discord_session_notes,
    split_session_notes,
    starts_with_searchable_markdown_heading,
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

    assert session_notes.read_session_note_body(saved[0].path) == markdown_body.replace("2026-07-10", "## 2026-07-10")
    assert "## Scene Notes" in saved[0].path.read_text(encoding="utf-8")
    assert "| Clue | Status |" in saved[0].path.read_text(encoding="utf-8")


def test_freeform_lore_import_preserves_undated_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_lore_document_text(
        """# Time Turning

Date and Time values in the days of yore are a fuzzy concept.

## The Nightbloom Family

Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College.
""",
        title="Atlantia Lore",
    )

    assert imported.note_date is None
    assert imported.path.name == "Atlantia_Lore.md"
    assert imported.path.read_text(encoding="utf-8").startswith("# Time Turning\n\nDate and Time")
    assert session_notes.list_session_notes() == [imported.path]


def test_freeform_lore_import_merges_new_section_titles(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    first = import_lore_document_text(
        """# Atlantia Lore

## Time Turning

Original time notes.
""",
        title="Atlantia Lore",
    )
    second = import_lore_document_text(
        """# Atlantia Lore

## Time Turning

Changed duplicate notes should not overwrite the original section.

## New Section

Only this section should be appended.
""",
        title="Atlantia Lore",
    )

    assert first.path == second.path
    assert second.path.name == "Atlantia_Lore.md"
    text = second.path.read_text(encoding="utf-8")
    assert text.count("## Time Turning") == 1
    assert "Original time notes." in text
    assert "Changed duplicate notes" not in text
    assert "## New Section\n\nOnly this section should be appended." in text


def test_freeform_lore_reimport_with_only_existing_last_section_preserves_prior_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    first = import_lore_document_text(
        """# Family Tree

## The Nightbloom Family

Original Nightbloom notes.

## The Ravenmark Family

Original Ravenmark notes.

## The Lovington Family

Original Lovington notes.
""",
        title="Family Tree",
    )
    second = import_lore_document_text(
        """# Family Tree

## The Lovington Family

Copied last section text should not replace the original.
""",
        title="Family Tree",
    )

    assert first.path == second.path
    text = second.path.read_text(encoding="utf-8")
    assert "## The Nightbloom Family\n\nOriginal Nightbloom notes." in text
    assert "## The Ravenmark Family\n\nOriginal Ravenmark notes." in text
    assert "## The Lovington Family\n\nOriginal Lovington notes." in text
    assert "Copied last section text should not replace the original." not in text


def test_markdown_import_with_date_detection_preserves_undated_lore(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_markdown_text(
        """# Atlantia Lore

## The Nightbloom Family

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


def test_prepare_markdown_import_extracts_dates_and_sections_as_headings():
    prepared, headings = prepare_markdown_import(
        """Lighthouse Log

2026-07-10

Harbor Trouble:
The party found a sealed brass door.

## Existing Section
More notes.
""",
        title="Lighthouse Log",
        today=date(2026, 7, 12),
    )

    assert prepared.startswith("# Lighthouse Log")
    assert "## July 2026" in prepared
    assert "### Harbor Trouble" in prepared
    assert "## Existing Section" in prepared
    assert [(heading.level, heading.text, heading.kind) for heading in headings] == [
        (1, "Lighthouse Log", "structure"),
        (2, "July 2026", "date"),
        (3, "Harbor Trouble", "heading"),
        (2, "Existing Section", "heading"),
    ]


def test_prepare_markdown_import_expands_single_newlines_for_markdown_paragraphs():
    prepared, _headings = prepare_markdown_import(
        "Lighthouse Log\nFirst observation line.\nSecond observation line.\n\nFinal paragraph.",
        title="Lighthouse Log",
        today=date(2026, 7, 12),
    )

    assert "# Lighthouse Log\n\nFirst observation line.\n\nSecond observation line." in prepared
    assert "Second observation line.\n\nFinal paragraph." in prepared
    assert "\n\n\n" not in prepared


def test_prepare_markdown_import_decodes_literal_escaped_newlines():
    prepared, headings = prepare_markdown_import(
        "# Test Session\\n\\n## Arrival\\nThe party arrives.\\n",
        title="session_import",
        today=date(2026, 7, 12),
    )

    assert "\\n" not in prepared
    assert "# Test Session\n\n## Arrival\n\nThe party arrives." in prepared
    assert [(heading.level, heading.text) for heading in headings] == [
        (1, "Test Session"),
        (2, "Arrival"),
    ]


def test_markdown_import_demotes_unselected_searchable_headings_to_h4(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    source = """# Session Import

2026-07-10

## Secret Thread
Private material.

## Public Thread
Searchable material.
"""
    _prepared, headings = prepare_markdown_import(source, title="Session Import", today=date(2026, 7, 12))
    selected = {heading.key for heading in headings if heading.text != "Secret Thread"}

    imported = import_markdown_text(
        source,
        title="Session Import",
        selected_heading_keys=selected,
        save_as_single_file=True,
        today=date(2026, 7, 12),
    )

    text = imported[0].path.read_text(encoding="utf-8")
    assert imported[0].path.name == "Session_Import.md"
    assert "## July 2026" in text
    assert "#### Secret Thread\n\nPrivate material." in text
    assert "## Secret Thread" not in text.splitlines()
    assert "## Public Thread" in text


def test_markdown_import_demotes_unselected_date_headings_to_h4(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_markdown_text(
        "2026-07-10\nThe party found a sealed brass door.",
        title="Session Import",
        selected_heading_keys=set(),
        save_as_single_file=True,
        today=date(2026, 7, 12),
    )

    text = imported[0].path.read_text(encoding="utf-8")
    assert "# Session Import" in text
    assert "#### July 2026" in text
    assert "## July 2026" not in text.splitlines()


def test_markdown_import_does_not_treat_poem_lines_as_headings():
    poem = """Within the Filthy swamps a Vermin king rises
The Soot on her fingers leave no surprises
To Ignis she would bow down her head
Where Elva lurks, you know there'll be red

Humming echoes through the dunes like shackles
Lizard men hide to the Flair of her cackle
"""

    prepared, headings = prepare_markdown_import(poem, title="Session Import", today=date(2026, 7, 12))

    assert prepared.startswith("# Session Import")
    assert "### Within the Filthy swamps" not in prepared
    assert "### Humming echoes" not in prepared
    assert [(heading.level, heading.text) for heading in headings] == [(1, "Session Import")]


def test_markdown_import_rewrites_discord_author_lines_as_h5_metadata():
    prepared, headings = prepare_markdown_import(
        """Jane Smith [OOZE], Server Tag: OOZEOOZE — 7/10/26, 11:36 PMFriday, July 10, 2026 at 11:36 PM
The party found a sealed brass door.

John [OOZE], Server Tag: OOZEOOZE — 7/11/26, 12:01 AMSaturday, July 11, 2026 at 12:01 AM
The party opened the lighthouse door.

Skunkman22 [CULT],  — 1/2/25, 6:49 PM
The party found another sign.
""",
        title="Session Import",
        today=date(2026, 7, 12),
    )

    assert "##### 2026/07/10 - Jane Smith" in prepared
    assert "##### 2026/07/11 - John" in prepared
    assert "##### 2025/01/02 - Skunkman22" in prepared
    assert "## July 2026" in prepared
    assert "## January 2025" in prepared
    assert "Server Tag" not in prepared
    assert [(heading.level, heading.text) for heading in headings] == [
        (1, "Session Import"),
        (2, "July 2026"),
        (2, "January 2025"),
    ]


def test_markdown_import_moves_chat_headings_below_following_higher_level_headings():
    prepared, headings = prepare_markdown_import(
        """This is the start of the #story channel.

Session 1:

Sean [DM],  — 2/19/23, 6:49 PM
The party awoke in strange cells.

Sean [DM],  — 2/20/23, 7:00 PM
The party found the piano.

Sean [DM],  — 8/3/23, 8:00 PM
Session 2:

The next session began.
""",
        title="Session Import",
        today=date(2026, 7, 12),
    )

    assert "## February 2023" in prepared
    assert "### Session 1" in prepared
    assert "##### 2023/02/19 - Sean" in prepared
    assert "##### 2023/02/20 - Sean" in prepared
    assert "## August 2023\n\n### Session 2\n\n##### 2023/08/03 - Sean" in prepared
    assert [(heading.level, heading.text) for heading in headings] == [
        (1, "Session Import"),
        (2, "February 2023"),
        (3, "Session 1"),
        (2, "August 2023"),
        (3, "Session 2"),
    ]

    session_1 = next(section for section in markdown_sections(prepared) if section.text == "February 2023")
    session_2 = next(section for section in markdown_sections(prepared) if section.text == "August 2023")

    assert "##### 2023/02/20 - Sean" in session_1.body
    assert "The party found the piano." in session_1.body
    assert "##### 2023/08/03 - Sean" not in session_1.body
    assert "August 2023" not in session_1.body
    assert "### Session 2" in session_2.body
    assert "##### 2023/08/03 - Sean" in session_2.body
    assert "The next session began." in session_2.body


def test_markdown_import_removes_duplicate_discovered_headings():
    prepared, headings = prepare_markdown_import(
        """### 2024/03/18 - Camryn
The next morning they meet with the towns mayor and assistant.

### 2024/03/18 - Camryn
The group follows the directions and arrive at a hut.
""",
        title="Session Import",
        today=date(2026, 7, 12),
    )

    assert "## March 2024" in prepared
    assert "### 2024/03/18 - Camryn\n\nThe next morning" in prepared
    assert "### 2024/03/18 - Camryn\n\nThe group follows" not in prepared
    assert "The group follows the directions and arrive at a hut." in prepared
    assert [(heading.level, heading.text) for heading in headings] == [
        (1, "Session Import"),
        (2, "March 2024"),
        (3, "2024/03/18 - Camryn"),
    ]

    sections = markdown_sections(prepared, today=date(2026, 7, 12))
    march_section = next(section for section in sections if section.text == "March 2024")
    assert "### 2024/03/18 - Camryn" in march_section.body


def test_markdown_import_detects_inline_dates_as_month_year_headings():
    prepared, headings = prepare_markdown_import(
        """Travel Notes

The party reached Greybend on March 18, 2024.
They returned on 2024-03-19 with the medallion.
""",
        title="Travel Notes",
        today=date(2026, 7, 12),
    )

    assert prepared.count("## March 2024") == 1
    assert "The party reached Greybend on March 18, 2024." in prepared
    assert [(heading.level, heading.text, heading.kind) for heading in headings] == [
        (1, "Travel Notes", "structure"),
        (2, "March 2024", "date"),
    ]


def test_markdown_import_preserves_atlantia_lore_h2_headings():
    source = """# Atlantia Lore

## Town Overview
Atlantia grew around the harbor.

## The Harbor
The harbor is the town's busiest edge.
"""

    prepared, headings = prepare_markdown_import(source, title="Imported Atlantia", today=date(2026, 7, 12))

    assert "## Town Overview" in prepared
    assert "## The Harbor" in prepared
    assert "### Town Overview" not in prepared
    assert "### The Harbor" not in prepared
    assert [(heading.level, heading.text, heading.kind) for heading in headings] == [
        (1, "Atlantia Lore", "structure"),
        (2, "Town Overview", "heading"),
        (2, "The Harbor", "heading"),
    ]


def test_markdown_import_keeps_orphan_discovered_h3_as_h3():
    prepared, headings = prepare_markdown_import(
        """### Town Overview
Atlantia grew around the harbor.
""",
        title="Atlantia Lore",
        today=date(2026, 7, 12),
    )

    assert "### Town Overview" in prepared
    assert [(heading.level, heading.text, heading.kind) for heading in headings] == [
        (1, "Atlantia Lore", "structure"),
        (3, "Town Overview", "heading"),
    ]


def test_markdown_import_keeps_user_markdown_h3_before_following_date():
    prepared, headings = prepare_markdown_import(
        """### Town Overview
Atlantia grew around the harbor.

March 18, 2024
The town held a spring festival.
""",
        title="Atlantia Lore",
        today=date(2026, 7, 12),
    )

    assert "### Town Overview\n\nAtlantia grew around the harbor.\n\n## March 2024" in prepared
    assert "## March 2024\n\n### Town Overview" not in prepared
    assert "__LCG_INFERRED_IMPORT_HEADING__" not in prepared
    assert [(heading.level, heading.text, heading.kind) for heading in headings] == [
        (1, "Atlantia Lore", "structure"),
        (3, "Town Overview", "heading"),
        (2, "March 2024", "date"),
    ]


def test_markdown_import_keeps_h4_headings_hidden_from_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    source = """### 2024/03/18 - Camryn
The next morning they meet with the towns mayor and assistant.
"""
    _prepared, headings = prepare_markdown_import(source, title="Session Import", today=date(2026, 7, 12))
    selected = {heading.key for heading in headings if heading.text != "2024/03/18 - Camryn"}

    imported = import_markdown_text(
        source,
        title="Session Import",
        selected_heading_keys=selected,
        save_as_single_file=True,
        today=date(2026, 7, 12),
    )

    text = imported[0].path.read_text(encoding="utf-8")
    assert "## March 2024" in text
    assert "#### 2024/03/18 - Camryn" in text


def test_session_note_file_heading_normalizer_removes_existing_duplicates(tmp_path):
    path = tmp_path / "Session_Import.md"
    path.write_text(
        """# Session Import

### 2024/03/18 - Camryn
The next morning they meet with the towns mayor and assistant.

### 2024/03/18 - Camryn
The group follows the directions and arrive at a hut.

## 2024-03-18
This date stays searchable.

## 2024-03-18
This duplicate date also stays searchable.
""",
        encoding="utf-8",
    )

    assert normalize_session_note_file_headings(path, today=date(2026, 7, 12))
    text = path.read_text(encoding="utf-8")

    assert "### 2024/03/18 - Camryn\nThe next morning" in text
    assert "### 2024/03/18 - Camryn\nThe group follows" not in text
    assert "The group follows the directions and arrive at a hut." in text
    assert text.count("## 2024-03-18") == 1
    assert "This duplicate date also stays searchable." in text
    assert not normalize_session_note_file_headings(path, today=date(2026, 7, 12))


def test_session_note_file_heading_normalizer_removes_exact_h5_duplicates(tmp_path):
    path = tmp_path / "Session_Import.md"
    path.write_text(
        """# Session Import

##### 2024/03/18 - Camryn
First message.

##### 2024/03/18 - Camryn
Second message.
""",
        encoding="utf-8",
    )

    assert normalize_session_note_file_headings(path, today=date(2026, 7, 12))
    text = path.read_text(encoding="utf-8")

    assert text.count("##### 2024/03/18 - Camryn") == 1
    assert "First message." in text
    assert "Second message." in text


def test_markdown_import_does_not_move_higher_level_headings_without_preceding_chat_heading():
    prepared, headings = prepare_markdown_import(
        """Introductory campaign note.

Session 1:
The party awoke in strange cells.

Session 2:
The party found the piano.
""",
        title="Session Import",
        today=date(2026, 7, 12),
    )

    assert "The party awoke in strange cells.\n\n### Session 2" in prepared
    assert "### Session 2\nThe party awoke" not in prepared
    assert [(heading.level, heading.text) for heading in headings] == [
        (1, "Session Import"),
        (3, "Session 1"),
        (3, "Session 2"),
    ]


def test_markdown_sections_expose_searchable_import_headings(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    source = """# Session Import

2026-07-10

## Harbor Trouble
The party found a sealed brass door.

## Lighthouse Door
The party opened the lighthouse door.
"""
    _prepared, headings = prepare_markdown_import(source, title="Session Import", today=date(2026, 7, 12))
    imported = import_markdown_text(
        source,
        title="Session Import",
        selected_heading_keys={heading.key for heading in headings},
        save_as_single_file=True,
        today=date(2026, 7, 12),
    )

    sections = markdown_sections(imported[0].path.read_text(encoding="utf-8"), today=date(2026, 7, 12))

    assert [(section.level, section.date_text, section.text) for section in sections] == [
        (1, "", "Session Import"),
        (2, "July 2026", "July 2026"),
        (2, "July 2026", "Harbor Trouble"),
        (2, "July 2026", "Lighthouse Door"),
    ]
    assert sections[2].body == "## Harbor Trouble\n\nThe party found a sealed brass door."


def test_markdown_sections_expose_user_promoted_h2_headings():
    sections = markdown_sections(
        """# Session Import

#### 2025/01/02 - Skunkman22
This H4 marker remains metadata.

## 2025/01/02 - Skunkman22
The user promoted this marker to a searchable section.
""",
        today=date(2026, 7, 12),
    )

    assert [(section.level, section.text) for section in sections] == [
        (1, "Session Import"),
        (2, "2025/01/02 - Skunkman22"),
    ]
    assert sections[1].body == (
        "## 2025/01/02 - Skunkman22\n"
        "The user promoted this marker to a searchable section."
    )


def test_markdown_section_insert_remove_and_combine_helpers(tmp_path):
    path = tmp_path / "Session_Import.md"
    path.write_text(
        """# Session Import

## Harbor Trouble
The party found a sealed brass door.

### Locked Door
The lock has silver runes.

#### 2026/07/10 - Keeper
This chat metadata should appear in delete warnings.

## Lighthouse Door
The party opened the lighthouse door.
""",
        encoding="utf-8",
    )

    harbor_section = next(section for section in markdown_sections(path.read_text(encoding="utf-8")) if section.text == "Harbor Trouble")
    child_sections = child_markdown_sections(path.read_text(encoding="utf-8"), harbor_section.key)
    assert [(section.level, section.text) for section in child_sections] == [
        (3, "Locked Door"),
        (4, "2026/07/10 - Keeper"),
    ]

    _note, previous_key = insert_markdown_section(path, harbor_section.key, "previous")
    text = path.read_text(encoding="utf-8")
    assert "## Harbor Trouble: (Previously)\n\n## Harbor Trouble" in text
    assert next(section for section in markdown_sections(text) if section.key == previous_key).text == "Harbor Trouble: (Previously)"

    harbor_section = next(section for section in markdown_sections(text) if section.text == "Harbor Trouble")
    _note, next_key = insert_markdown_section(path, harbor_section.key, "next")
    text = path.read_text(encoding="utf-8")
    assert "#### 2026/07/10 - Keeper\nThis chat metadata should appear in delete warnings.\n\n## Harbor Trouble: (Coming Next)" in text
    assert next(section for section in markdown_sections(text) if section.key == next_key).text == "Harbor Trouble: (Coming Next)"

    locked_section = next(section for section in markdown_sections(text) if section.text == "Locked Door")
    _note, parent_key = combine_markdown_section(path, locked_section.key)
    text = path.read_text(encoding="utf-8")
    assert "##### Locked Door\nThe lock has silver runes." in text
    assert "#### 2026/07/10 - Keeper\nThis chat metadata should appear in delete warnings." in text
    assert "### Locked Door" not in text.splitlines()
    assert not [section for section in markdown_sections(text) if section.text == "Locked Door"]
    assert next(section for section in markdown_sections(text) if section.key == parent_key).text == "Harbor Trouble"

    harbor_section = next(section for section in markdown_sections(text) if section.text == "Harbor Trouble")
    remove_markdown_section(path, harbor_section.key)
    text = path.read_text(encoding="utf-8")
    assert "## Harbor Trouble\n" not in text
    assert "##### Locked Door" not in text
    assert "## Lighthouse Door" in text


def test_hide_markdown_section_heading_demotes_h1_to_ignored_h4(tmp_path):
    path = tmp_path / "Family_Tree.md"
    path.write_text(
        """# Family Tree

Introductory family notes.

## The Ravenmark Family

Ravenmark details.
""",
        encoding="utf-8",
    )
    family_section = next(section for section in markdown_sections(path.read_text(encoding="utf-8")) if section.text == "Family Tree")

    hide_markdown_section_heading(path, family_section.key)

    text = path.read_text(encoding="utf-8")
    assert text.startswith("#### Family Tree\n\nIntroductory family notes.")
    assert "# The Ravenmark Family\n\nRavenmark details." in text
    assert [(section.level, section.text) for section in markdown_sections(text)] == [(1, "The Ravenmark Family")]


def test_removing_last_markdown_section_reports_file_removal():
    text = """# Single Section

Only one searchable section exists.
"""
    section = markdown_sections(text)[0]

    assert removing_markdown_section_removes_file(text, section.key)

    text = """# Multi Section

Intro.

## Second Section

More notes.
"""
    sections = markdown_sections(text)

    assert not removing_markdown_section_removes_file(text, sections[1].key)
    assert removing_markdown_section_removes_file(text, sections[0].key)


def test_section_markdown_must_start_with_h1_h2_or_h3():
    assert starts_with_searchable_markdown_heading("# Main Heading\nBody")
    assert starts_with_searchable_markdown_heading("## Section Heading\nBody")
    assert starts_with_searchable_markdown_heading("### Subsection Heading\nBody")
    assert not starts_with_searchable_markdown_heading("#### Chat Metadata\nBody")
    assert not starts_with_searchable_markdown_heading("Plain text heading\nBody")


def test_uploaded_session_importer_saves_single_lore_file_without_date_split(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    source = """2026-07-10
The party found a sealed brass door.

2026-07-11
The party opened the lighthouse door.
"""
    _prepared, headings = prepare_markdown_import(source, title="Session_Importer", today=date(2026, 7, 12))

    imported = import_markdown_text(
        source,
        title="Session_Importer",
        selected_heading_keys={heading.key for heading in headings},
        save_as_single_file=True,
        today=date(2026, 7, 12),
    )

    assert [note.path.name for note in imported] == ["Session_importer.md"]
    assert [path.name for path in session_notes.list_session_notes()] == ["Session_importer.md"]
    text = imported[0].path.read_text(encoding="utf-8")
    assert "# Session Importer" in text
    assert "## July 2026" in text
    assert "The party found a sealed brass door." in text
    assert "The party opened the lighthouse door." in text


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
        (date(2026, 7, 9), "## 7/9\nOpened the old archive."),
        (date(2026, 7, 10), "## 7/10\nFound the second key."),
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
        (date(2026, 7, 10), "## 2026-07-10\nFirst note.\n\n## 2026-07-10\nFollow-up note."),
        (date(2026, 7, 11), "## 2026-07-11\nMiddle note."),
    ]


def test_session_note_preamble_attaches_to_first_dated_file():
    notes = split_session_notes(
        """Campaign memory

2026-07-10
The date appears after the heading.""",
        today=date(2026, 7, 12),
    )

    assert notes == [
        (date(2026, 7, 10), "Campaign memory\n\n## 2026-07-10\nThe date appears after the heading.")
    ]


def test_markdown_import_sorts_same_date_sessions_by_heading_order(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    imported = import_markdown_text(
        """2026-07-10
Session 12:

The party found a silver key.

Session 13:

The party opened the lighthouse door.""",
        include_detected_dates=True,
    )

    assert [note.path.name for note in imported] == [
        "2026-07-10_Session_12.md",
        "2026-07-10_Session_13.md",
    ]
    assert [path.name for path in session_notes.list_session_notes()] == [
        "2026-07-10_Session_12.md",
        "2026-07-10_Session_13.md",
    ]


def test_imported_lore_without_session_date_sorts_by_import_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    first = import_markdown_text("# First Lore", title="First Lore")[0]
    second = import_markdown_text("# Second Lore", title="Second Lore")[0]
    os.utime(first.path, (100, 100))
    os.utime(second.path, (200, 200))

    assert session_notes.list_session_notes() == [second.path, first.path]


def test_session_notes_can_use_editable_campaign_date_text(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    saved = save_session_notes(
        "The party waited for the moon gate.",
        title="Moon Gate",
        session_date="Third Moon 17",
    )

    assert saved[0].note_date == "Third Moon 17"
    assert saved[0].path.name == "Third_Moon_17_Moon_Gate.md"
    assert session_notes.read_session_note_date_text(saved[0].path) == "Third Moon 17"
    assert session_notes.read_session_note(saved[0].path).startswith(
        "# Session Notes - Third Moon 17 - Moon Gate"
    )


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
