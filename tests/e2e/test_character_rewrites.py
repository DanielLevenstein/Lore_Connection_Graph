from pathlib import Path

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from character_graph.schema import CharacterGraph, CharacterNode, PrimaryCharacterRef, RelationshipEdge
from language_model.character_rewrites import (
    graph_generated_backstory,
    graph_generated_summary,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from language_model.storage import Character, read_character_profile
from scripts.generate_single_character_backstory_rewrite_report import build_report


ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"
MODEL_SUMMARY = (
    "Orin is a Half-Orc Bard shaped by Sunstone Mage College, the loss of Orin Nightbloom's Mother, "
    "and a vow to break a worsening family curse before it claims a younger relative."
)
MODEL_BACKSTORY = (
    "Orin Nightbloom is a Half-Orc Bard whose gifts were sharpened in the halls of Sunstone Mage College, "
    "where lineage and talent never sat comfortably together.\n\n"
    "The death of Orin Nightbloom's Mother left him with grief, forbidden notes, and the truth of a curse "
    "that only worsens when ignored.\n\n"
    "Now Orin turns music into defiance, determined to break the curse and stop a younger relative from "
    "repeating the family's worst choice."
)


def rewrite_client_with(summary: str = MODEL_SUMMARY, backstory: str = MODEL_BACKSTORY):
    def rewrite_client(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        if "character summary" in prompt:
            return summary
        if "Rewrite the character backstory" in prompt:
            return backstory
        raise AssertionError(f"Unexpected rewrite prompt: {prompt}")

    return rewrite_client


def test_orin_graph_generated_summary_scores_better_than_original_backstory():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    generated_summary = graph_generated_summary(graph, profile, rewrite_client=rewrite_client_with())
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    original_backstory = profile.original_backstory or profile.backstory
    generated_score = semantic_rewrite_score(generated_summary, source_context, required_terms)
    original_score = semantic_rewrite_score(original_backstory, source_context, required_terms)

    assert generated_summary.startswith("Orin is a Half-Orc Bard")
    assert "Sunstone Mage College" in generated_summary
    assert generated_score.score > original_score.score
    assert generated_score.concept_coverage >= original_score.concept_coverage
    assert generated_score.sentence_quality > original_score.sentence_quality


def test_graph_generated_summary_uses_default_graph_engine_without_model():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    generated_summary = graph_generated_summary(graph, profile)

    assert generated_summary.startswith("Orin is a Half-Orc Bard")
    assert "Sunstone Mage College" in generated_summary


def test_orin_graph_generated_story_scores_better_than_original_backstory():
    character_path = FIXTURE_CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))

    generated_story = graph_generated_backstory(graph, profile, rewrite_client=rewrite_client_with())
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    original_backstory = profile.original_backstory or profile.backstory
    generated_score = semantic_rewrite_score(generated_story, source_context, required_terms)
    original_score = semantic_rewrite_score(original_backstory, source_context, required_terms)

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

    generated_summary = graph_generated_summary(
        graph,
        profile,
        rewrite_client=rewrite_client_with(summary="Jory Ravenmark remembers Jory_Ravenmark's Mother through old evidence."),
    )

    assert "Jory Ravenmark's Mother" in generated_summary
    assert "Jory_Ravenmark" not in generated_summary


def test_semantic_improvement_report_includes_scores_and_result():
    report = build_report(rewrite_client=rewrite_client_with())

    assert "# Semantic Improvement Report: Orin Nightbloom" in report
    assert "semantic similarity, sentence length fit, and sentence quality" in report
    assert "Local model rewrite" in report
    assert "Existing Generated Section" in report
    assert "Original section" in report
    assert "## Sentence Lengths" in report
    assert "Sentence Length Score" in report
    assert "Coverage" not in report.split("## Scores", 1)[1].split("## Sentence Lengths", 1)[0]
    assert "changes the writing quality score versus the original section" in report
