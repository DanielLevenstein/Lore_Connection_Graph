from pathlib import Path

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from character_graph.schema import CharacterGraph, CharacterNode, PrimaryCharacterRef, RelationshipEdge
from local_chatbot.character_rewrites import (
    graph_generated_backstory,
    graph_generated_summary,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from local_chatbot.storage import Character, read_character_profile
from scripts.generate_semantic_improvement_report import build_report


ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"


def test_orin_graph_generated_summary_scores_better_than_original_backstory():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    generated_summary = graph_generated_summary(graph, profile)
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    generated_score = semantic_rewrite_score(generated_summary, source_context, required_terms)
    original_score = semantic_rewrite_score(profile.backstory, source_context, required_terms)

    assert generated_summary.startswith("Orin is a Half-Orc Bard")
    assert "Sunstone Mage College" in generated_summary
    assert generated_score.score > original_score.score
    assert generated_score.concept_coverage >= original_score.concept_coverage
    assert generated_score.concision > original_score.concision


def test_orin_graph_generated_story_scores_better_than_original_backstory():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    generated_story = graph_generated_backstory(graph, profile)
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    generated_score = semantic_rewrite_score(generated_story, source_context, required_terms)
    original_score = semantic_rewrite_score(profile.backstory, source_context, required_terms)

    assert "Sunstone Mage College" in generated_story
    assert "Orin Nightbloom's Mother" in generated_story
    assert "curse" in generated_story.lower()
    assert generated_score.score > original_score.score


def test_graph_generated_summary_humanizes_underscored_character_names():
    graph = CharacterGraph(
        schema_version="0.3.0",
        primary_character=PrimaryCharacterRef(id="jory_ravenmark", name="Jory Ravenmark", source_file="Jory_Ravenmark.md"),
        characters={
            "jory_ravenmark": CharacterNode(name="Jory Ravenmark", source_spans=["Jory was a sailor."]),
            "jory_ravenmark_s_mother": CharacterNode(
                name="Jory_Ravenmark's Mother",
                source_spans=["Jory_Ravenmark's Mother died at sea."],
            ),
        },
        relationships=[
            RelationshipEdge(
                source="jory_ravenmark",
                target="jory_ravenmark_s_mother",
                relationship_type="family",
                relationship_label="Family",
                evidence=["Jory_Ravenmark's Mother died at sea."],
            )
        ],
    )
    profile = read_character_profile(Character(name="Jory_Ravenmark", path=FIXTURE_CHARACTER_SHEETS_DIR / "Jory_Ravenmark.md"))

    generated_summary = graph_generated_summary(graph, profile)

    assert "Jory Ravenmark's Mother" in generated_summary
    assert "Jory_Ravenmark" not in generated_summary


def test_semantic_improvement_report_includes_scores_and_result():
    report = build_report()

    assert "# Semantic Improvement Report: Orin Nightbloom" in report
    assert "| Post-transform story |" in report
    assert "| Pre-transform backstory |" in report
    assert "improves the semantic quality score" in report
