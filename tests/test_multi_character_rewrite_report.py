import scripts.generate_multi_character_rewrite_report as report_script
from scripts.generate_multi_character_rewrite_report import (
    build_report,
    generate_character_outputs,
    summary_length_score,
    summary_word_count,
)


class CapturingRewriteClient:
    last_metadata = {
        "model_id": "fixture-model",
        "quantization": "Q4_K_M",
        "prompt_version": "fixture-prompt",
        "max_tokens": "640",
        "temperature": "0.65",
        "top_p": "0.85",
        "repeat_penalty": "1.15",
        "seed": "2310",
        "n_ctx": "8192",
        "n_batch": "64",
        "n_threads": "2",
        "n_gpu_layers": "0",
        "device": "none",
        "timeout_seconds": "180",
        "prompt_hash": "multi1234567890",
    }

    def __init__(self) -> None:
        self.prompts = []

    def __call__(self, messages):
        prompt = messages[-1]["content"]
        self.prompts.append(prompt)
        if "character summary" in prompt:
            return (
                "Fixture summary mentions Sunstone Mage College and the character's central drive. "
                "It preserves the main relationship, keeps the prose compact, and stays inside the target length. "
                "The result remains easy to scan."
            )
        if "Rewrite the character backstory" in prompt:
            return (
                "Fixture backstory preserves the character's named place and central relationship.\n\n"
                "It keeps the important drive visible without adding unsupported lore."
            )
        raise AssertionError(f"Unexpected rewrite prompt: {prompt}")


class RetrySummaryClient(CapturingRewriteClient):
    def __init__(self) -> None:
        super().__init__()
        self.summary_calls = 0

    def __call__(self, messages):
        prompt = messages[-1]["content"]
        self.prompts.append(prompt)
        if "character summary" in prompt or "character summary paragraph" in prompt:
            self.summary_calls += 1
            if self.summary_calls == 1:
                return (
                    "Jory Ravenmark is a Human Barbarian haunted by family loss and a leviathan and a vow and "
                    "a hunt and a storm and a memory and a rage and a duty that all run together without pause."
                )
            return (
                "Jory Ravenmark is a Human Barbarian haunted by family loss at sea. "
                "She turns watchtower memories into a protective oath while hunting the monstrous leviathan."
            )
        if "Rewrite the character backstory" in prompt:
            return (
                "Fixture backstory preserves the character's named place and central relationship.\n\n"
                "It keeps the important drive visible without adding unsupported lore."
            )
        raise AssertionError(f"Unexpected rewrite prompt: {prompt}")


def test_multi_character_report_compares_three_characters():
    client = CapturingRewriteClient()

    report = build_report(rewrite_client=client)

    assert "# Multi-Character Rewrite Comparison" in report
    assert "## Model Runtime" in report
    assert "fixture-model" in report
    assert "fixture-prompt" in report
    assert "Temperature" in report
    assert "0.65" in report
    assert "Top P" in report
    assert "0.85" in report
    assert "Repeat penalty" in report
    assert "1.15" in report
    assert "Seed" in report
    assert "2310" in report
    assert "Prompt hash" in report
    assert "multi1234567890" in report
    assert "Orin Nightbloom uses the generation 1 auto-generated backstory as source material." in report
    assert "### Orin Nightbloom" in report
    assert "### Jory Ravenmark" in report
    assert "### Neal Lovington" in report
    assert "## Generated Summary Scores" in report
    assert "## Generated Backstory Scores" in report
    summary_table = report.split("## Generated Summary Scores", 1)[1].split("## Generated Backstory Scores", 1)[0]
    backstory_table = report.split("## Generated Backstory Scores", 1)[1].split("## Character Outputs", 1)[0]
    assert "Status" in summary_table
    assert "Status" in backstory_table
    assert "Summary Length Score" in summary_table
    assert summary_table.index("Overall") < summary_table.index("Summary Length Score")
    assert "Coverage" not in summary_table
    assert "Coverage" not in backstory_table
    assert "Sentence Length Score" in summary_table
    assert "Sentence Length Score" in backstory_table
    assert "Sentence Quality" in summary_table
    assert "Sentence Quality" in backstory_table
    assert "Summary Length" not in backstory_table
    assert "Sentence length distribution" not in report
    assert "semantic_sentence_lengths.png" not in report
    assert report.count("#### Generated Summary") >= 3
    assert report.count("#### Generated Backstory") >= 3
    assert "| Candidate" in report
    assert "### Rejection Reasons" in summary_table
    assert "### Rejection Reasons" in backstory_table
    summary_numeric_table = summary_table.split("### Rejection Reasons", 1)[0]
    backstory_numeric_table = backstory_table.split("### Rejection Reasons", 1)[0]
    assert "Rejection Reasons" not in summary_numeric_table
    assert "Rejection Reasons" not in backstory_numeric_table
    assert "- Jory Ravenmark: " in summary_table
    assert "- Jory Ravenmark: " in backstory_table
    assert "Length Score" in backstory_table
    assert "| Source material" not in summary_table
    assert "| Generated summary" not in summary_table
    assert "| Generated backstory" not in backstory_table
    assert len(client.prompts) == 6


def test_multi_character_report_displays_only_final_retry_candidate():
    client = RetrySummaryClient()
    jory_path = report_script.CHARACTER_SHEETS_DIR / "Jory_Ravenmark.md"

    result = generate_character_outputs(jory_path, client)

    assert client.summary_calls == 2
    assert "all run together without pause" not in result["summary"]
    assert "turns watchtower memories into a protective oath" in result["summary"]


def test_orin_report_uses_generation_one_backstory_as_model_source():
    client = CapturingRewriteClient()
    orin_path = report_script.CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md"

    result = generate_character_outputs(orin_path, client)
    prompt_text = "\n".join(client.prompts)

    assert result["source_label"] == "generation 1 auto-generated backstory"
    assert result["source"].startswith("Orin Nightbloom is a Half-Orc Bard whose life has been shaped")
    assert "Current backstory source: Orin Nightbloom is a Half-Orc Bard whose life has been shaped" in prompt_text
    assert "weight the world seldom places on a child" not in prompt_text


def test_multi_character_report_defaults_to_real_model_client(monkeypatch):
    calls = []

    def fake_real_client():
        calls.append("real")
        return CapturingRewriteClient()

    monkeypatch.setattr(report_script, "real_model_rewrite_client", fake_real_client)

    report = build_report()

    assert calls == ["real"]
    assert "Multi-Character Rewrite Comparison" in report


def test_summary_word_count_reports_generated_summary_length():
    assert summary_word_count("One two three.") == 3


def test_summary_length_score_uses_target_word_count():
    in_range_summary = (
        "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen twenty twentyone twentytwo twentythree twentyfour twentyfive twentysix "
        "twentyseven twentyeight twentynine thirty."
    )
    short_summary = "One two three four five."
    long_summary = " ".join(f"word{i}" for i in range(120))

    assert summary_length_score(in_range_summary) == 100.0
    assert summary_length_score(short_summary) == 16.67
    assert summary_length_score(long_summary) == 50.0
