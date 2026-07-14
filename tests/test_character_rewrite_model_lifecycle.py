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
from model_harness.downloads import download_option
from model_harness.chat import SYSTEM_PROMPT, normalized_chat_messages
from model_harness.chat import chat_completion as harness_chat_completion
from model_harness.models import ModelConfig
from model_harness.server import start_server


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"


def model_config() -> ModelConfig:
    return ModelConfig(
        name="external-test-model",
        model_id="test/model",
        model_url="https://example.test/test/model",
        api_base_url="https://example.test/v1",
        size="3B",
        download_size="1 GB",
        download_options=[{"filename": "model.gguf", "quant": "Q4_K_M"}],
        description="External test model",
        server={},
        config_path=Path("config/model/test.json"),
    )


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
        generator.generate_profile(model_config=model_config())


def test_model_harness_runtime_boundaries_are_disabled():
    config = model_config()

    with pytest.raises(RuntimeError, match="External language-model use is disabled"):
        harness_chat_completion(config, [{"role": "user", "content": "Hello"}])
    with pytest.raises(RuntimeError, match="External language-model use is disabled"):
        download_option(config, config.download_options[0])
    with pytest.raises(RuntimeError, match="External language-model use is disabled"):
        start_server(config)


def test_chat_message_normalization_respects_rewrite_system_prompt():
    messages = normalized_chat_messages(
        [
            {"role": "system", "content": "Use only supplied character facts."},
            {"role": "user", "content": "Rewrite."},
        ]
    )

    assert messages[0] == {"role": "system", "content": "Use only supplied character facts."}
    assert all(message["content"] != SYSTEM_PROMPT for message in messages)
