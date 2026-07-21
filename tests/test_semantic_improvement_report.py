import scripts.generate_semantic_improvement_report as report_script
from language_model.character_rewrites import rewrite_concision_score
from scripts.generate_semantic_improvement_report import build_report


MODEL_BACKSTORY = (
    "Orin Nightbloom is a Half-Orc Bard whose gifts were sharpened in the halls of Sunstone Mage College.\n\n"
    "The death of Orin Nightbloom's Mother left him with grief and the truth of a curse that only worsens "
    "when ignored.\n\n"
    "Now Orin turns music into defiance, determined to break the curse and stop a younger relative from "
    "repeating the family's worst choice."
)


class FakeRewriteClient:
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
        "prompt_hash": "abc123def4567890",
        "prompt_eval_time_ms": "12.34",
        "prompt_tokens": "321",
        "completion_tokens": "42",
        "total_tokens": "363",
    }

    def __call__(self, messages):
        return MODEL_BACKSTORY


class FailingRewriteClient(FakeRewriteClient):
    def __call__(self, messages):
        raise RuntimeError("fixture model echoed the prompt")


def test_semantic_report_formats_three_version_score_table():
    report = build_report(rewrite_client=FakeRewriteClient())
    score_table = report.split("## Scores", 1)[1].split("## Result", 1)[0]
    table_lines = [
        line
        for line in score_table.splitlines()
        if line.startswith("| ")
        and (
            "Candidate" in line
            or "Local model rewrite" in line
            or "Existing generated section" in line
            or "Original section" in line
            or "---" in line
        )
    ]

    assert "Source context similarity compares each candidate" in report
    assert "Prompt eval time" in report
    assert "12.34 ms" in report
    assert "Temperature" in report
    assert "0.65" in report
    assert "Top P" in report
    assert "0.85" in report
    assert "Repeat penalty" in report
    assert "1.15" in report
    assert "Seed" in report
    assert "2310" in report
    assert "Prompt hash" in report
    assert "abc123def4567890" in report
    assert "Status" in report
    assert "Sentence Quality" in report
    assert any("Local model rewrite" in line for line in table_lines)
    assert any("Existing generated section" in line for line in table_lines)
    assert any("Original section" in line for line in table_lines)
    assert len({len(line) for line in table_lines}) == 1


def test_semantic_report_defaults_to_real_model_client(monkeypatch):
    calls = []

    def fake_real_client():
        calls.append("real")
        return FakeRewriteClient()

    monkeypatch.setattr(report_script, "real_model_rewrite_client", fake_real_client)

    report = build_report()

    assert calls == ["real"]
    assert "Local model rewrite" in report


def test_semantic_report_records_rejected_model_candidate():
    report = build_report(rewrite_client=FailingRewriteClient())

    assert "No acceptable local model rewrite was produced" in report
    assert "fixture model echoed the prompt" in report
    assert "Local model rewrite        | Rejected" in report
    assert "existing generated section remains the better candidate" in report


def test_rewrite_concision_score_penalizes_run_on_sentences():
    concise = (
        "Orin studies at Sunstone Mage College. "
        "His mother's curse drives him to protect a younger relative."
    )
    run_on = (
        "Orin studies at Sunstone Mage College while remembering his mother and trying to break the curse "
        "and protect a younger relative and honor his lineage and prove himself and keep singing and keep "
        "fighting and keep searching for answers without pausing or changing direction."
    )

    assert rewrite_concision_score(concise) == 1.0
    assert rewrite_concision_score(run_on) < rewrite_concision_score(concise)


def test_rewrite_concision_score_penalizes_dangling_sentence_fragments():
    clean = (
        "Orin came of age at Sunstone Mage College. "
        "His mother's curse gave him a reason to protect his family."
    )
    malformed = (
        "Orin came of age at Sunstone Mage College. "
        "He excelled, his magic a beacon in. "
        "The curse gave Orin a reason to."
    )

    assert rewrite_concision_score(malformed) < rewrite_concision_score(clean)
    assert rewrite_concision_score(malformed) < 0.5


def test_rewrite_concision_score_penalizes_comma_heavy_sentences_that_should_split():
    split = (
        "Orin Nightbloom was born under the weight of half-orc heritage. "
        "Sunstone Mage College sharpened his talent and deepened his exile. "
        "His mother taught him to carry his lineage with discipline. "
        "Now he seeks to break the curse before it claims a younger relative."
    )
    should_split = (
        "Orin Nightbloom, a Half-Orc Bard, was born with the weight of a half-orc heritage clashing with "
        "the refined air of Sunstone Mage College, a place that sharpened both his talent and his sense of exile. "
        "He came of age at the prestigious institution, where he excelled in his magic, a beacon in the world."
    )

    assert rewrite_concision_score(split) == 1.0
    assert rewrite_concision_score(should_split) < 0.8
