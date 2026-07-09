import json

from local_chatbot.character_generator import RandomCharacterGenerator
from local_chatbot.storage import Character, CharacterProfile, read_character_profile, render_backstory


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
        "| Name | Level | Race | Class |\n"
        "| ---- | ----- | ---- | ----- |\n"
        "| Mara | 3 | Elf | Wizard |\n\n"
        "## Character Backstory\n\n"
        "Mara keeps a silver key from a city no map remembers.\n\n"
        "Mara trusts paper records more than promises.\n\n"
        "Mara still returns every borrowed tool cleaner than it was found.\n\n"
        "## Character Summary\n\n"
        "Mara is a careful archivist trying to make courage feel practical.\n\n"
        "### Character Details\n\n"
        "Pronouns: she/her\n"
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
    assert "| Name | Level | Race | Class |" in markdown
    assert (
        f"| {profile.name.split()[0]} | {profile.level} | {profile.race} | "
        f"{profile.character_class} |"
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
    assert profile.origin == "a handwritten city"
    assert profile.drives == ["preserve the records"]
    assert profile.alliances == ["The Silver Index"]


def test_read_character_profile_does_not_restore_removed_stats_from_json(tmp_path):
    character_path = tmp_path / "Mara Voss"
    character_path.mkdir()
    character = Character(name="Mara Voss", path=character_path)
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
    assert "Drives:\n- JSON drive" in profile.details
    assert "Allies:\n- JSON ally" in profile.details
    assert "Enemies:\n- JSON enemy" in profile.details


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
