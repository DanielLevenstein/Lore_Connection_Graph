from pathlib import Path

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from language_model.character_rewrites import (
    clean_model_rewrite,
    graph_generated_backstory,
    graph_generated_backstory_result,
    graph_generated_summary,
    graph_generated_summary_result,
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
GOOD_JORY_BACKSTORY = (
    "Jory Ravenmark grew up reading the sea from an island watchtower, where her family taught her how to "
    "listen for storms and survive hard weather. The leviathan attack took both fathers from her and left her "
    "with grief, mercy she cannot explain, and a vow to find the beast again.\n\n"
    "She now turns that grief into protection for other families wounded by the sea. Every rumor, storm track, "
    "and old memory pulls Jory closer to the monster that shattered her home."
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


def test_backstory_prompt_has_two_paragraph_contract():
    profile, graph = jory_profile_and_graph()

    prompt = rewrite_prompt("backstory", graph, profile)

    assert "Rewrite the character backstory as exactly 2 concise paragraphs." in prompt
    assert "Preserve the named people, places, relationships, and drives." in prompt
    assert "Return only the rewritten prose." in prompt
    assert "2 to 4 concise paragraphs" not in prompt


def test_rewrite_api_sends_mode_specific_source_context_to_model_client():
    profile, graph = jory_profile_and_graph()
    prompts = []

    def capturing_client(messages):
        assert messages[0]["role"] == "system"
        assert "Rewrite roleplaying character lore" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        prompts.append(messages[1]["content"])
        if "character summary" in messages[1]["content"]:
            return GOOD_JORY_SUMMARY
        if "Rewrite the character backstory" in messages[1]["content"]:
            return GOOD_JORY_BACKSTORY
        raise AssertionError(f"Unexpected rewrite prompt: {messages[1]['content']}")

    assert graph_generated_summary(graph, profile, rewrite_client=capturing_client) == GOOD_JORY_SUMMARY
    assert graph_generated_backstory(graph, profile, rewrite_client=capturing_client) == GOOD_JORY_BACKSTORY

    summary_prompt, backstory_prompt = prompts
    assert "Current summary source: Haunted by the loss of her family" in summary_prompt
    assert "Current backstory source:" not in summary_prompt
    assert "Current backstory source: Jory was a sailor" in backstory_prompt
    assert "Current summary source:" not in backstory_prompt


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


def test_summary_generation_retries_once_and_returns_retry_candidate():
    profile, graph = jory_profile_and_graph()
    calls = []

    def retrying_client(messages):
        calls.append(messages[-1]["content"])
        if len(calls) == 1:
            return RUN_ON_JORY_SUMMARY
        return GOOD_JORY_SUMMARY

    result = graph_generated_summary_result(graph, profile, rewrite_client=retrying_client)

    assert result.text == GOOD_JORY_SUMMARY
    assert len(result.attempts) == 2
    assert result.attempts[0].normalized_text == RUN_ON_JORY_SUMMARY
    assert "summary sentence too long" in result.attempts[0].validation_issues
    assert result.attempts[1].validation_issues == ()
    assert "Previous candidate:" in calls[1]
    assert "Return only the final rewritten prose." in calls[1]


def test_backstory_generation_retries_once_and_returns_retry_candidate():
    profile, graph = jory_profile_and_graph()
    first_attempt = "Jory Ravenmark follows the sea after the leviathan."
    calls = []

    def retrying_client(messages):
        calls.append(messages[-1]["content"])
        if len(calls) == 1:
            return first_attempt
        return GOOD_JORY_BACKSTORY

    result = graph_generated_backstory_result(graph, profile, rewrite_client=retrying_client)

    assert result.text == GOOD_JORY_BACKSTORY
    assert len(result.attempts) == 2
    assert result.attempts[0].normalized_text == first_attempt
    assert "backstory paragraph count" in result.attempts[0].validation_issues
    assert result.attempts[1].validation_issues == ()
    assert "Previous candidate:" in calls[1]


def test_backstory_generation_strips_diagnostics_and_keeps_two_paragraphs():
    profile, graph = jory_profile_and_graph()

    def noisy_backstory_client(_messages):
        return (
            "llama.cpp build: fixture\n"
            f"Backstory: {GOOD_JORY_BACKSTORY}\n\n"
            "A third paragraph should not survive model-output normalization.\n"
            "prompt eval time = 12.00 ms\n"
        )

    backstory = graph_generated_backstory(graph, profile, rewrite_client=noisy_backstory_client)

    assert backstory == GOOD_JORY_BACKSTORY
    assert backstory.count("\n\n") == 1
    assert "Backstory:" not in backstory
    assert "llama.cpp" not in backstory
    assert "third paragraph" not in backstory
    assert "prompt eval time" not in backstory


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
