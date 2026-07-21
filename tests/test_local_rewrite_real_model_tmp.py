from pathlib import Path

import pytest

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from local_chatbot.character_rewrites import (
    clean_model_rewrite,
    model_rewrite_quality_issues,
    rewrite_prompt,
    trim_backstory_candidate,
)
from local_chatbot.rewrite_model import LocalRewriteModelClient, load_local_language_model_config
from local_chatbot.storage import Character, read_character_profile


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Orin_Nightbloom.md"


def test_tmp_real_local_model_generates_usable_orin_backstory():
    config = load_local_language_model_config(allow_download=False)
    if not config.model_path.exists():
        pytest.skip(f"Local model artifact is missing: {config.model_path}")
    character = Character(name=FIXTURE_CHARACTER_PATH.stem, path=FIXTURE_CHARACTER_PATH)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(FIXTURE_CHARACTER_PATH, character_id=character.name))

    client = LocalRewriteModelClient(config=config)
    raw = client(
        [
            {
                "role": "system",
                "content": "Rewrite roleplaying character lore using only facts from the supplied character sheet and knowledge graph context.",
            },
            {"role": "user", "content": rewrite_prompt("backstory", graph, profile)},
        ]
    )
    story = trim_backstory_candidate(clean_model_rewrite(raw))
    issues = model_rewrite_quality_issues(story)

    print("\nREAL_MODEL_STORY\n" + story)
    print("\nREAL_MODEL_ISSUES\n" + repr(issues))
    print("\nREAL_MODEL_METADATA\n" + repr(client.last_metadata))
    assert story.endswith((".", "!", "?"))
    assert "Orin Nightbloom" in story
    assert "Niightbloom" not in story
    assert "Sunstone Mage College" in story
    assert "Preserve" not in story
    assert not issues
