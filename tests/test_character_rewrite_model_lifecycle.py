from pathlib import Path

import pytest

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from character_graph.schema import CharacterGraph, CharacterNode, PrimaryCharacterRef
from local_chatbot.character_generator import RandomCharacterGenerator
from local_chatbot.character_rewrites import (
    graph_generated_backstory,
    graph_generated_summary,
    rewrite_required_terms,
)
from local_chatbot.storage import Character, CharacterProfile, read_character_profile


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"


def test_graph_rewrite_uses_in_code_deterministic_engine():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    summary = graph_generated_summary(graph, profile)
    backstory = graph_generated_backstory(graph, profile)

    assert "Orin" in summary
    assert "Half-Orc Bard" in summary
    assert "Sunstone Mage College" in summary
    assert "Orin Nightbloom's Mother" in backstory
    assert "break a curse" in backstory


def test_graph_rewrite_preserves_profile_metadata_without_graph_relationships():
    graph = CharacterGraph(
        schema_version="0.3.0",
        primary_character=PrimaryCharacterRef(id="mara_voss", name="Mara Voss", source_file="Mara_Voss.md"),
        characters={"mara_voss": CharacterNode(name="Mara Voss", source_spans=["Mara keeps the archive safe."])},
    )
    profile = CharacterProfile(
        name="Mara Voss",
        pronouns="she/her",
        level="3",
        race="Elf",
        character_class="Wizard",
        backstory="Mara keeps a silver key.",
        summary="Mara is a careful archivist.",
        origin="the vanished city of Ilyr",
        drives=["protect the vanished city's records"],
        alliances=["The Silver Index"],
        enemies=["map thieves"],
        stat_fields={"patron": "Brindle Hall"},
    )

    summary = graph_generated_summary(graph, profile)
    backstory = graph_generated_backstory(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)

    assert "the vanished city of Ilyr" in summary
    assert "The Silver Index" in backstory
    assert "map thieves" in backstory
    assert "protect the vanished city's records" in backstory
    assert "The Silver Index" in required_terms
    assert "map thieves" in required_terms


def test_external_model_generation_is_disabled():
    generator = RandomCharacterGenerator(seed=7)

    with pytest.raises(RuntimeError, match="External language-model character generation is disabled"):
        generator.generate_profile(model_config=object())
