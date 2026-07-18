from datetime import date

import local_chatbot.session_notes as session_notes
import local_chatbot.storage as storage
from local_chatbot.storage import (
    CharacterProfile,
    PlaceProfile,
    create_character,
    create_place,
    create_place_markdown,
    delete_character_profile,
    delete_place_profile,
    import_external_character_sheet,
    list_external_character_sheets,
    read_character_profile,
    read_place_profile,
    write_character_profile,
    write_place_markdown,
    write_place_profile,
)


def test_character_file_save_round_trips_updated_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CHARACTERS_DIR", tmp_path / "docs" / "lore" / "character_sheets")
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "character_metadata")
    monkeypatch.setattr(storage, "CHARACTER_GRAPHS_DIR", tmp_path / "data" / "character_graph")
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)

    character = create_character(
        CharacterProfile(
            name="Della Moor",
            pronouns="she/her",
            level="5",
            race="Gnome",
            character_class="Rogue",
            backstory="Della maps locked doors beneath the old city.",
            first_name="Della",
            family_name="Moor",
            summary="Della is a careful scout.",
            drives=["Find the sunken archive"],
            alliances=["Brindle Hall"],
            enemies=["The Brass Knife"],
        )
    )

    first_read = read_character_profile(character)
    assert first_read.name == "Della Moor"
    assert first_read.summary == "Della is a careful scout."
    assert first_read.drives == ["Find the sunken archive"]

    write_character_profile(
        character,
        CharacterProfile(
            name="Della Moor",
            pronouns="she/her",
            level="6",
            race="Gnome",
            character_class="Rogue",
            backstory="Della maps locked doors beneath the old city and marks every hinge.",
            first_name="Della",
            family_name="Moor",
            summary="Della is a careful scout with brass lockpicks.",
            drives=["Find the sunken archive", "Protect Brindle Hall"],
            alliances=["Brindle Hall"],
            enemies=["The Brass Knife"],
        ),
    )

    reloaded = read_character_profile(character)
    text = character.backstory_path.read_text(encoding="utf-8")
    assert reloaded.level == "6"
    assert reloaded.backstory == "Della maps locked doors beneath the old city and marks every hinge."
    assert reloaded.summary == "Della is a careful scout with brass lockpicks."
    assert reloaded.drives == ["Find the sunken archive", "Protect Brindle Hall"]
    assert "| Della | 6 | Gnome | Rogue | she/her |" in text


def test_character_delete_removes_sheet_metadata_and_graph(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CHARACTERS_DIR", tmp_path / "docs" / "lore" / "character_sheets")
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "character_metadata")
    monkeypatch.setattr(storage, "CHARACTER_GRAPHS_DIR", tmp_path / "data" / "character_graph")
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)

    character = create_character(
        CharacterProfile(
            name="Della Moor",
            pronouns="she/her",
            level="5",
            race="Gnome",
            character_class="Rogue",
            backstory="Della maps locked doors beneath the old city.",
            summary="Della is a careful scout.",
        )
    )
    character.profile_path.parent.mkdir(parents=True, exist_ok=True)
    character.profile_path.write_text("{}", encoding="utf-8")
    character.graph_path.parent.mkdir(parents=True, exist_ok=True)
    character.graph_path.write_text("{}", encoding="utf-8")

    delete_character_profile(character)

    assert not character.backstory_path.exists()
    assert not character.data_dir.exists()
    assert not character.graph_path.exists()


def test_external_character_sheet_import_saves_pdf_or_image_as_is(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CHARACTERS_DIR", tmp_path / "docs" / "lore" / "character_sheets")

    first = import_external_character_sheet("della sheet.pdf", b"%PDF-1.4 raw bytes", display_name="Della Moor")
    second = import_external_character_sheet("della sheet.pdf", b"%PDF-1.4 second copy", display_name="Della Moor")

    assert first.path == tmp_path / "docs" / "lore" / "character_sheets" / "external" / "Della Moor.pdf"
    assert first.path.read_bytes() == b"%PDF-1.4 raw bytes"
    assert second.path.name == "Della Moor_2.pdf"
    assert second.path.read_bytes() == b"%PDF-1.4 second copy"
    assert [sheet.path.name for sheet in list_external_character_sheets()] == ["Della Moor.pdf", "Della Moor_2.pdf"]


def test_place_file_save_round_trips_updated_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place(
        PlaceProfile(
            name="Brindle Hall",
            place_type="Guildhall",
            summary="A narrow guildhall where maps are traded.",
            details="Lanterns burn blue near the archives.",
            connections=["Della Moor: Stores maps"],
        )
    )

    first_read = read_place_profile(place)
    assert first_read.name == "Brindle Hall"
    assert first_read.connections == ["Della Moor: Stores maps"]

    write_place_profile(
        place,
        PlaceProfile(
            name="Brindle Hall",
            place_type="Guildhall",
            summary="A crowded guildhall where maps are traded.",
            details="Lanterns burn green after midnight.",
            connections=["Della Moor: Stores maps", "Jory Ravenmark: Buys charts"],
        ),
    )

    reloaded = read_place_profile(place)
    assert reloaded.place_type == "Guildhall"
    assert reloaded.summary == "A crowded guildhall where maps are traded."
    assert reloaded.details == "Lanterns burn green after midnight."
    assert reloaded.connections == ["Della Moor: Stores maps", "Jory Ravenmark: Buys charts"]


def test_place_markdown_save_round_trips_freeform_headings(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place_markdown(
        "Atlantia",
        """# Atlantia

# Time Turning

Date and Time values in the days of yore are a fuzzy concept.

## The Nighbloom Family

Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College.
""",
    )

    assert place.path.read_text(encoding="utf-8").startswith("# Atlantia\n\n# Time Turning")

    write_place_markdown(place, "# Atlantia\n\n## The Ravenmark Family\n\nJory still believes the sea took her father.")

    assert "## The Ravenmark Family" in place.path.read_text(encoding="utf-8")


def test_place_markdown_create_replaces_stale_default_title(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place_markdown("Brindle Hall", "# New Place\n\nA bright guildhall.")

    assert place.path.name == "Brindle Hall.md"
    assert place.path.read_text(encoding="utf-8").startswith("# Brindle Hall\n\nA bright guildhall.")


def test_place_markdown_save_preserves_edited_markdown_title(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place_markdown("Markdown Inn", "This Inn serves non-technical guests.")

    assert place.path.read_text(encoding="utf-8").startswith("# Markdown Inn\n\n")

    write_place_markdown(place, "# Markdown Tavern\n\nThe sign has changed.")

    assert place.path.read_text(encoding="utf-8") == "# Markdown Tavern\n\nThe sign has changed.\n"


def test_place_delete_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place(
        PlaceProfile(
            name="Brindle Hall",
            place_type="Guildhall",
            summary="A narrow guildhall where maps are traded.",
        )
    )

    delete_place_profile(place)

    assert not place.path.exists()


def test_session_note_file_save_overwrites_and_reloads_by_date(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")

    first_save = session_notes.save_session_notes(
        "2026-07-10\nThe party found a silver key.",
        today=date(2026, 7, 10),
    )
    second_save = session_notes.save_session_notes(
        "2026-07-10\nThe party found a silver key and a brass map.",
        today=date(2026, 7, 10),
    )

    assert first_save[0].path == second_save[0].path
    assert session_notes.list_session_notes() == [second_save[0].path]
    assert second_save[0].path.name == "2026-07-10_Session_Notes.md"
    assert session_notes.read_session_note(second_save[0].path) == (
        "# Session Notes - 2026-07-10 - Session Notes\n\n"
        "## 2026-07-10\n"
        "The party found a silver key and a brass map.\n"
    )
    assert session_notes.read_session_note_body(second_save[0].path) == (
        "## 2026-07-10\n"
        "The party found a silver key and a brass map."
    )

    session_notes.write_session_note(second_save[0].path, "The party kept better notes.", "Silver Key")

    assert session_notes.read_session_note(second_save[0].path) == (
        "# Session Notes - 2026-07-10 - Silver Key\n\n"
        "The party kept better notes.\n"
    )
    assert session_notes.read_session_note_title(second_save[0].path) == "Silver Key"
    assert session_notes.read_session_note_body(second_save[0].path) == "The party kept better notes."


def test_markdown_section_save_updates_section_title(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")
    path = tmp_path / "docs" / "lore" / "session_notes" / "Family_Tree.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Family Tree\n\n"
        "## The Lovington Family: (Coming Next)\n\n"
        "Notes coming soon.\n",
        encoding="utf-8",
    )
    section_key = session_notes.markdown_sections(path.read_text(encoding="utf-8"))[1].key

    session_notes.write_markdown_section(path, section_key, "## The Rapture Family\n\nNotes coming soon.")

    sections = session_notes.markdown_sections(path.read_text(encoding="utf-8"))
    assert [(section.level, section.text) for section in sections] == [
        (1, "Family Tree"),
        (2, "The Rapture Family"),
    ]


def test_session_note_delete_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(session_notes, "SESSION_NOTES_DIR", tmp_path / "docs" / "lore" / "session_notes")
    saved = session_notes.save_session_notes(
        "2026-07-10\nThe party found a silver key.",
        today=date(2026, 7, 10),
    )

    session_notes.delete_session_note(saved[0].path)

    assert not saved[0].path.exists()
