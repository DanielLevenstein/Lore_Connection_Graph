from local_chatbot.character_generator import RandomCharacterGenerator
from local_chatbot.storage import CharacterProfile, render_backstory


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
        "| Name | Level | Race | Class | Pronouns | Drives | Home | Allies | Enemies |\n"
        "|------|-------|------|-------|----------|--------|------|--------|---------|\n"
        "| Mara | 3 | Elf | Wizard | she/her | protect the vanished city's records | "
        "a vanished city | The Silver Index | map thieves |\n\n"
        "## Character Backstory\n\n"
        "Mara keeps a silver key from a city no map remembers.\n\n"
        "Mara trusts paper records more than promises.\n\n"
        "Mara still returns every borrowed tool cleaner than it was found.\n\n"
        "## Character Summary\n\n"
        "Mara is a careful archivist trying to make courage feel practical.\n"
    )


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
    assert "| Name | Level | Race | Class | Pronouns | Drives | Home | Allies | Enemies |" in markdown
    assert (
        f"| {profile.name.split()[0]} | {profile.level} | {profile.race} | "
        f"{profile.character_class} | {profile.pronouns} |"
    ) in markdown
    assert "## Character Summary" in markdown


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
