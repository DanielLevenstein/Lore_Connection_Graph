import json
import shutil
from pathlib import Path

import local_chatbot.storage as storage
from local_chatbot.character_generator import RandomCharacterGenerator
from local_chatbot.paths import CHARACTER_METADATA_DIR, CHARACTERS_DIR, ROOT_DIR
from local_chatbot.storage import (
    Character,
    CharacterProfile,
    PlaceProfile,
    create_character,
    create_generated_character,
    create_place,
    read_character_profile,
    render_backstory,
)


def test_render_backstory_matches_character_template_shape():
    profile = CharacterProfile(
        name="Mara Voss",
        pronouns="she/her",
        level="3",
        race="Elf",
        character_class="Wizard",
        backstory=(
            "Mara keeps a silver key from a city no map remembers.\n\n"
            "Mara trusts paper records more than promises.\n\n"
            "Mara still returns every borrowed tool cleaner than it was found."
        ),
        summary="Mara is a careful archivist trying to make courage feel practical.",
        origin="a vanished city",
        gender="female",
        drives=["protect the vanished city's records"],
        alliances=["The Silver Index"],
        enemies=["map thieves"],
    )

    assert render_backstory(profile) == (
        "# Mara Voss\n\n"
        "## Character Stats\n\n"
        "| Name | Level | Race | Class | Pronouns |\n"
        "| ---- | ----- | ---- | ----- | -------- |\n"
        "| Mara | 3 | Elf | Wizard | she/her |\n\n"
        "## Character Backstory\n\n"
        "Mara keeps a silver key from a city no map remembers.\n\n"
        "Mara trusts paper records more than promises.\n\n"
        "Mara still returns every borrowed tool cleaner than it was found.\n\n"
        "## Character Summary\n\n"
        "Mara is a careful archivist trying to make courage feel practical.\n\n"
        "### Character Details\n\n"
        "Gender: female\n"
        "Home: a vanished city\n"
        "Drives:\n"
        "- protect the vanished city's records\n"
        "Allies:\n"
        "- The Silver Index\n"
        "Enemies:\n"
        "- map thieves\n"
    )


def test_render_backstory_omits_blank_stat_columns():
    profile = CharacterProfile(
        name="Mara Voss",
        pronouns="",
        level="",
        race="Elf",
        character_class="",
        backstory="Mara keeps a silver key.",
        summary="Mara is careful.",
    )

    assert "| Name | Race |" in render_backstory(profile)
    assert "Level" not in render_backstory(profile)
    assert "Class" not in render_backstory(profile)
    assert "Pronouns" not in render_backstory(profile)


def test_render_backstory_marks_auto_generated_sections():
    profile = CharacterProfile(
        name="Mara Voss",
        pronouns="",
        level="",
        race="Elf",
        character_class="Wizard",
        backstory="Mara keeps a silver key.",
        summary="Mara is careful.",
        auto_generated_sections=["Character Summary", "Character Backstory"],
    )

    markdown = render_backstory(profile)

    assert "## Character Backstory (Auto Generated)" in markdown
    assert "## Character Summary (Auto Generated)" in markdown


def test_random_generator_produces_template_ready_profile():
    generator = RandomCharacterGenerator(seed=7)
    profile = generator.generate_profile()
    markdown = render_backstory(profile)

    assert profile.origin
    assert profile.gender in {"male", "female", "non-binary"}
    assert profile.motivations is not None
    assert len(profile.motivations) == 2
    assert profile.motivations[0] != profile.motivations[1]
    assert f"# {profile.name}" in markdown
    assert profile.name not in markdown.replace(f"# {profile.name}", "")
    assert "| Name | Level | Race | Class | Pronouns |" in markdown
    assert (
        f"| {profile.name.split()[0]} | {profile.level} | {profile.race} | "
        f"{profile.character_class} | {profile.pronouns} |"
    ) in markdown
    assert "## Character Summary" in markdown
    assert "### Character Details" in markdown


def test_read_character_profile_uses_manual_character_sheet_text(tmp_path):
    character_path = tmp_path / "Mara Voss"
    character_path.mkdir()
    character = Character(name="Mara Voss", path=character_path)
    character.backstory_path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory text.

## Character Summary

Manual summary text.

### Character Details

Pronouns: she/her
Home: a handwritten city
Drives:
- preserve the records
Allies:
- The Silver Index
""",
        encoding="utf-8",
    )

    profile = read_character_profile(character)

    assert profile.race == "Elf"
    assert profile.level == ""
    assert profile.character_class == ""
    assert profile.backstory == "Manual backstory text."
    assert profile.summary == "Manual summary text."
    assert profile.pronouns == "she/her"
    assert "Pronouns:" not in profile.details
    assert profile.origin == "a handwritten city"
    assert profile.drives == ["preserve the records"]
    assert profile.alliances == ["The Silver Index"]


def test_read_character_profile_supports_title_preamble_summary(tmp_path):
    character_path = tmp_path / "Mara Voss.md"
    character = Character(name="Mara Voss", path=character_path)
    character.backstory_path.write_text(
        """# Mara Voss

Mara is summarized directly below the title.

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory text.
""",
        encoding="utf-8",
    )

    profile = read_character_profile(character)

    assert profile.summary == "Mara is summarized directly below the title."
    assert profile.source_locations == {"summary": "title_preamble"}


def test_read_character_profile_does_not_restore_removed_stats_from_json(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Mara Voss"
    character_path.mkdir()
    character = Character(name="Mara Voss", path=character_path)
    character.profile_path.parent.mkdir(parents=True)
    character.profile_path.write_text(
        json.dumps(
            {
                "name": "Mara Voss",
                "level": "4",
                "race": "Elf",
                "character_class": "Wizard",
                "backstory": "Old backstory.",
                "summary": "Old summary.",
                "drives": ["JSON drive"],
                "alliances": ["JSON ally"],
                "enemies": ["JSON enemy"],
            }
        ),
        encoding="utf-8",
    )
    character.backstory_path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory text.

## Character Summary

Manual summary text.
""",
        encoding="utf-8",
    )

    profile = read_character_profile(character)

    assert profile.level == ""
    assert profile.character_class == ""
    assert profile.backstory == "Manual backstory text."
    assert profile.drives == ["JSON drive"]
    assert profile.alliances == ["JSON ally"]
    assert profile.enemies == ["JSON enemy"]
    assert profile.details == ""


def test_read_character_profile_accepts_field_description_details_table(tmp_path):
    character_path = tmp_path / "Mara Voss"
    character_path.mkdir()
    character = Character(name="Mara Voss", path=character_path)
    character.backstory_path.write_text(
        """# Mara Voss

## Character Stats

| Name | Race |
| ---- | ---- |
| Mara | Elf |

## Character Backstory

Manual backstory text.

## Character Summary

Manual summary text.

### Character Details

| Field | Description                              |
| ----- |------------------------------------------|
| Drive | Entertaining sailors on shore leave.     |
|Allies | Jory Ravenmark is their favorite client. |
| Enemies | Mrs Nighbloom wasn't happy when she learned what her husband was doing on her days off.  |
""",
        encoding="utf-8",
    )

    profile = read_character_profile(character)

    assert profile.drives == ["Entertaining sailors on shore leave."]
    assert profile.alliances == ["Jory Ravenmark is their favorite client."]
    assert profile.enemies == [
        "Mrs Nighbloom wasn't happy when she learned what her husband was doing on her days off."
    ]


def test_read_character_profile_removes_spacing_for_table_key_matching(tmp_path):
    character_path = tmp_path / "Mara Voss"
    character_path.mkdir()
    character = Character(name="Mara Voss", path=character_path)
    character.backstory_path.write_text(
        """# Mara Voss

## Character Stats

| N a m e | R a c e | Character Class |
| ------- | ------ | --------------- |
| Mara | Elf | Wizard |

## Character Backstory

Manual backstory text.

## Character Summary

Manual summary text.

### Character Details

| F i e l d | D e s c r i p t i o n |
| --------- | --------------------- |
| All ies | Jory Ravenmark is their favorite client. |
| En emies | Trouble at the docks. |
""",
        encoding="utf-8",
    )

    profile = read_character_profile(character)

    assert profile.race == "Elf"
    assert profile.character_class == "Wizard"
    assert profile.alliances == ["Jory Ravenmark is their favorite client."]
    assert profile.enemies == ["Trouble at the docks."]


def test_existing_character_sheets_save_without_losing_stat_values(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    source_dir = Path(__file__).resolve().parents[1] / "docs" / "lore" / "character_sheets"

    for source_file in source_dir.glob("*.md"):
        character_path = tmp_path / source_file.name
        shutil.copyfile(source_file, character_path)
        character = Character(name=source_file.stem, path=character_path)
        profile = read_character_profile(character)
        storage.write_character_profile(character, profile)

        saved_profile = read_character_profile(character)
        assert saved_profile.race == profile.race
        assert saved_profile.character_class == profile.character_class
        assert saved_profile.stat_fields


def test_character_sheet_file_path_save_adds_missing_default_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Orin_Nightbloom.md"
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "docs" / "lore" / "character_sheets" / character_path.name,
        character_path,
    )
    character = Character(name=character_path.stem, path=character_path)
    storage.write_character_profile(character, read_character_profile(character))

    text = character_path.read_text(encoding="utf-8")
    assert "| Name | Level | Race | Class | Pronouns |" in text
    assert "| Orin Nightbloom | 1 | Half-Orc | Bard | he/him |" in text


def test_character_file_path_metadata_is_saved_under_data_lore_character_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Orin_Nightbloom.md"
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "docs" / "lore" / "character_sheets" / character_path.name,
        character_path,
    )
    character = Character(name=character_path.stem, path=character_path)

    storage.write_character_profile(character, read_character_profile(character))

    assert character.profile_path == tmp_path / "data" / "lore" / "character_sheets" / "Orin_Nightbloom" / "PROFILE.json"
    assert character.profile_path.exists()
    assert not character_path.with_suffix(".PROFILE.json").exists()


def test_create_character_keeps_only_sheet_in_docs_lore_character_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTERS_DIR", tmp_path / "docs" / "lore" / "character_sheets")
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    storage.CHARACTERS_DIR.mkdir(parents=True)
    storage.CHARACTER_METADATA_DIR.mkdir(parents=True)

    character = create_character(
        CharacterProfile(
            name="Mara Voss",
            pronouns="she/her",
            level="3",
            race="Elf",
            character_class="Wizard",
            backstory="Manual backstory.",
            summary="Manual summary.",
        )
    )

    assert character.path == tmp_path / "docs" / "lore" / "character_sheets" / "Mara Voss.md"
    assert character.backstory_path.exists()
    assert not (tmp_path / "docs" / "lore" / "character_sheets" / "Mara Voss").exists()
    assert character.profile_path == tmp_path / "data" / "lore" / "character_sheets" / "Mara Voss" / "PROFILE.json"
    assert character.profile_path.exists()
    assert character.memory_path == tmp_path / "data" / "lore" / "character_sheets" / "Mara Voss" / "MEMORY.md"
    assert character.memory_path.exists()
    assert character.chatlogs_dir == tmp_path / "data" / "lore" / "character_sheets" / "Mara Voss" / "chatlogs"
    assert character.chatlogs_dir.exists()


def test_create_generated_character_writes_to_data_lore_character_sheets(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    monkeypatch.setattr(storage, "GENERATED_CHARACTER_SHEETS_DIR", tmp_path / "data" / "lore" / "character_sheets")

    character = create_generated_character(
        CharacterProfile(
            name="Mara Voss",
            pronouns="she/her",
            level="3",
            race="Elf",
            character_class="Wizard",
            backstory="Generated backstory.",
            summary="Generated summary.",
        )
    )

    assert character.path == tmp_path / "data" / "lore" / "character_sheets" / "Mara Voss.md"
    assert character.backstory_path.exists()


def test_create_place_writes_docs_lore_place_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PLACES_DIR", tmp_path / "docs" / "lore" / "places")

    place = create_place(
        PlaceProfile(
            name="Royal Tittles",
            place_type="Tavern",
            summary="A dockside tavern.",
            details="Private rooms upstairs.",
            connections=["Neal Lovington: Performs here"],
        )
    )

    text = place.path.read_text(encoding="utf-8")
    assert place.path == tmp_path / "docs" / "lore" / "places" / "Royal Tittles.md"
    assert "## Place Summary" in text
    assert "- Neal Lovington: Performs here" in text


def test_title_name_wins_when_stats_name_is_honorific_and_family_name(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mx. Lovington | Elf | Bard |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    original = character_path.read_text(encoding="utf-8")
    character = Character(name=character_path.stem, path=character_path)

    profile = read_character_profile(character)
    storage.write_character_profile(character, profile)

    assert profile.first_name == "Neal"
    assert profile.family_name == "Lovington"
    assert profile.stat_fields["name"] == "Mx. Lovington"
    assert character_path.read_text(encoding="utf-8") == original


def test_missing_default_stat_is_added_only_when_value_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mx. Lovington | Elf | Bard |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    updated = CharacterProfile(
        name=profile.name,
        pronouns=profile.pronouns,
        level="3",
        race=profile.race,
        character_class=profile.character_class,
        backstory=profile.backstory,
        first_name=profile.first_name,
        family_name=profile.family_name,
        summary=profile.summary,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
    )
    storage.write_character_profile(character, updated)

    text = character_path.read_text(encoding="utf-8")
    assert "| Name | Race | Class | Level |" in text
    assert "| Mx. Lovington | Elf | Bard | 3 |" in text
    assert "Pronouns |" not in text


def test_missing_default_stats_with_existing_values_are_added_on_save(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race |
| ---- | ---- |
| Mx. Lovington | Elf |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.

### Character Details

Pronouns: They/Them
""",
        encoding="utf-8",
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    updated = CharacterProfile(
        name=profile.name,
        pronouns=profile.pronouns,
        level="3",
        race=profile.race,
        character_class="Bard",
        backstory=profile.backstory,
        first_name=profile.first_name,
        family_name=profile.family_name,
        summary=profile.summary,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
    )
    storage.write_character_profile(character, updated)

    text = character_path.read_text(encoding="utf-8")
    assert "| Name | Race | Class | Level | Pronouns |" in text
    assert "| Mx. Lovington | Elf | Bard | 3 | They/Them |" in text
    assert "Pronouns:" not in text


def test_present_stat_update_does_not_add_unchanged_missing_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mx. Lovington | Elf | Bard |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    updated = CharacterProfile(
        name=profile.name,
        pronouns=profile.pronouns,
        level=profile.level,
        race=profile.race,
        character_class="Sorcerer",
        backstory=profile.backstory,
        first_name=profile.first_name,
        family_name=profile.family_name,
        summary=profile.summary,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
    )
    storage.write_character_profile(character, updated)

    text = character_path.read_text(encoding="utf-8")
    assert "| Name | Race | Class |" in text
    assert "| Mx. Lovington | Elf | Sorcerer |" in text
    assert "Level |" not in text
    assert "Pronouns |" not in text


def test_existing_name_stat_value_is_preserved_when_first_name_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Mx. Lovington | Elf | Bard |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    updated = CharacterProfile(
        name=profile.name,
        pronouns=profile.pronouns,
        level=profile.level,
        race="Half-Elf",
        character_class=profile.character_class,
        backstory=profile.backstory,
        first_name="Neal",
        family_name=profile.family_name,
        summary=profile.summary,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
    )
    storage.write_character_profile(character, updated)

    text = character_path.read_text(encoding="utf-8")
    assert "| Mx. Lovington | Half-Elf | Bard |" in text
    assert "| Neal |" not in text


def test_custom_stats_are_mirrored_into_character_details_on_save(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Neal_Lovington.md"
    character_path.write_text(
        """# Neal Lovington

## Character Stats

| Name | Race | Class | Favorite Color |
| ---- | ---- | ----- | -------------- |
| Mx. Lovington | Elf | Bard | Pink |

## Character Backstory

Manual backstory.

## Character Summary

Manual summary.
""",
        encoding="utf-8",
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    storage.write_character_profile(character, profile)

    text = character_path.read_text(encoding="utf-8")
    assert "| Name | Race | Class | Favorite Color |" in text
    assert "### Character Details\n\nFavorite Color: Pink" in text


def test_present_pronouns_stat_updates_in_stats_table(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "regenerate_character_graph", lambda character: None)
    monkeypatch.setattr(storage, "CHARACTER_METADATA_DIR", tmp_path / "data" / "lore" / "character_sheets")
    character_path = tmp_path / "Jory_Ravenmark.md"
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "docs" / "lore" / "character_sheets" / character_path.name,
        character_path,
    )
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)

    updated = CharacterProfile(
        name=profile.name,
        pronouns="they/them",
        level=profile.level,
        race=profile.race,
        character_class=profile.character_class,
        backstory=profile.backstory,
        first_name=profile.first_name,
        family_name=profile.family_name,
        summary=profile.summary,
        drives=profile.drives,
        alliances=profile.alliances,
        enemies=profile.enemies,
        details=profile.details,
    )
    storage.write_character_profile(character, updated)

    text = character_path.read_text(encoding="utf-8")
    assert "| Family Name | Level | Race | Class | Pronouns |" in text
    assert "| Ravenmark | 4 | Human | Barbarian | they/them |" in text


def test_app_reads_characters_from_docs_lore_character_sheets():
    assert CHARACTERS_DIR == ROOT_DIR / "docs" / "lore" / "character_sheets"
    assert CHARACTER_METADATA_DIR == ROOT_DIR / "data" / "lore" / "character_sheets"
    assert (CHARACTERS_DIR / "Orin_Nightbloom.md").exists()
    assert all(path.is_file() and path.suffix.lower() == ".md" for path in CHARACTERS_DIR.iterdir())
    assert (ROOT_DIR / "docs" / "lore" / "places").exists()


def test_read_character_profile_extracts_appended_character_connections():
    character = Character(
        name="Orin_Nightbloom",
        path=Path(__file__).resolve().parents[1] / "docs" / "lore" / "character_sheets" / "Orin_Nightbloom.md",
    )

    profile = read_character_profile(character)

    assert profile.first_name == "Orin"
    assert profile.family_name == "Nightbloom"
    assert profile.stat_fields["name"] == "Orin Nightbloom"
    assert profile.stat_fields["character_class"] == "Bard"
    assert profile.knowledge_graph_fields
    assert {
        "table": "Relationships",
        "item": "Family",
        "value": "Nightbloom",
    }.items() <= profile.knowledge_graph_fields[0].items()


def test_world_building_data_has_enough_options():
    world = RandomCharacterGenerator.load_world_building()

    assert world.races
    assert world.classes
    assert world.pronouns
    assert world.given_names
    assert world.family_names
    assert world.origins
    assert len(world.motivations) >= 50
    assert len(world.motivations) == len(set(world.motivations))


def test_parse_model_markdown_accepts_plain_sections():
    payload = RandomCharacterGenerator.parse_model_markdown(
        "BACKSTORY:\n"
        "One.\n\n"
        "Two.\n\n"
        "Three.\n\n"
        "SUMMARY:\n"
        "Mara is careful."
    )

    assert payload == {
        "backstory": "One.\n\nTwo.\n\nThree.",
        "summary": "Mara is careful.",
    }


def test_parse_model_markdown_accepts_fenced_sections():
    payload = RandomCharacterGenerator.parse_model_markdown(
        "```markdown\n"
        "BACKSTORY:\n"
        "One.\n\n"
        "Two.\n\n"
        "Three.\n\n"
        "SUMMARY:\n"
        "Mara is careful.\n"
        "```"
    )

    assert payload == {
        "backstory": "One.\n\nTwo.\n\nThree.",
        "summary": "Mara is careful.",
    }


def test_parse_model_markdown_rejects_missing_sections():
    try:
        RandomCharacterGenerator.parse_model_markdown("One.\n\nTwo.\n\nThree.")
    except ValueError as exc:
        assert "BACKSTORY" in str(exc)
    else:
        raise AssertionError("Expected missing sections to fail")


def test_parse_model_markdown_allows_any_backstory_paragraph_count():
    payload = RandomCharacterGenerator.parse_model_markdown(
        "BACKSTORY:\n"
        "One.\n\n"
        "Two.\n\n"
        "SUMMARY:\n"
        "Mara is careful."
    )

    assert payload == {
        "backstory": "One.\n\nTwo.",
        "summary": "Mara is careful.",
    }
