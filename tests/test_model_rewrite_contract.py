from pathlib import Path

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from language_model.character_rewrites import (
    clean_model_rewrite,
    graph_generated_summary,
    model_rewrite_quality_issues,
    rewrite_prompt,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from language_model.rewrite_quality import writing_quality_score
from language_model.storage import Character, read_character_profile
from scripts.generate_semantic_improvement_report import summary_length_score


ROOT_DIR = Path(__file__).resolve().parents[1]
JORY_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Jory_Ravenmark.md"

GOOD_JORY_SUMMARY = (
    "Jory Ravenmark is a Human Barbarian haunted by the loss of her family at sea. "
    "Shaped by island watchtower memories, she turns grief into a protective oath and hunts the monstrous "
    "leviathan that took her father."
)
RUN_ON_JORY_SUMMARY = (
    "Jory Ravenmark is a Human Barbarian haunted by the loss of her family and an inexplicable mercy shown by "
    "a monstrous leviathan that has driven her to blend nomadic hunter-memories with a burning oath to track "
    "and face the beast she seeks to vanquish."
)
REPETITIVE_JORY_SUMMARY = (
    "Jory Ravenmark keeps searching the sea for the beast that took her family. "
    "She follows every storm track and every rumor she can find. "
    "She follows every storm track and every rumor she can find. "
    "She follows every storm track and every rumor she can find."
)


def jory_profile_and_graph():
    character = Character(name=JORY_PATH.stem, path=JORY_PATH)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(JORY_PATH, character_id=character.name))
    return profile, graph


def test_summary_prompt_has_single_candidate_contract():
    profile, graph = jory_profile_and_graph()

    prompt = rewrite_prompt("summary", graph, profile)

    assert "Write one polished character summary paragraph in 30 to 60 words." in prompt
    assert "Return exactly one summary, not alternatives or drafts." in prompt
    assert "Use one to three short sentences." in prompt
    assert "Write three" not in prompt


def test_summary_generation_collapses_multiple_model_alternatives():
    profile, graph = jory_profile_and_graph()

    def multi_candidate_client(_messages):
        return (
            f"{GOOD_JORY_SUMMARY}\n\n"
            "Jory Ravenmark is another possible summary that should not reach scoring."
        )

    summary = graph_generated_summary(graph, profile, rewrite_client=multi_candidate_client)

    assert summary == GOOD_JORY_SUMMARY
    assert "another possible summary" not in summary
    assert "\n\n" not in summary


def test_summary_metrics_distinguish_usable_run_on_and_repetitive_candidates():
    profile, graph = jory_profile_and_graph()
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    good_semantic = semantic_rewrite_score(GOOD_JORY_SUMMARY, source_context, required_terms)
    run_on_writing = writing_quality_score(RUN_ON_JORY_SUMMARY)
    good_writing = writing_quality_score(GOOD_JORY_SUMMARY)

    assert summary_length_score(GOOD_JORY_SUMMARY) == 100.0
    assert good_semantic.score > semantic_rewrite_score(RUN_ON_JORY_SUMMARY, source_context, required_terms).score
    assert good_writing.sentence_length > run_on_writing.sentence_length
    assert good_writing.sentence_quality > run_on_writing.sentence_quality
    assert model_rewrite_quality_issues(GOOD_JORY_SUMMARY) == []
    assert model_rewrite_quality_issues(REPETITIVE_JORY_SUMMARY) == ["repeated sentence", "repetitive wording"]


def test_diagnostic_only_model_output_is_not_candidate_text():
    assert clean_model_rewrite("ERROR: local model rewrite returned an unusable rewrite: repetitive wording.") == ""
    assert clean_model_rewrite("Traceback (most recent call last):\nRuntimeError: worker failed") == ""
