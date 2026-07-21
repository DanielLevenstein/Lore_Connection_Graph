from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from language_model.character_rewrites import RewriteClient, graph_generated_summary_result
from scripts.generate_single_character_backstory_rewrite_report import (
    build_character_rewrite_report,
    real_model_rewrite_client,
)


DEFAULT_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Jory_Ravenmark.md"
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "semantic_summary_improvement.md"
DEFAULT_SENTENCE_LENGTH_CHART_PATH = ROOT_DIR / "docs" / "reports" / "semantic_summary_sentence_lengths.png"


def build_report(
    character_path: Path = DEFAULT_CHARACTER_PATH,
    rewrite_client: RewriteClient | None = None,
    sentence_length_chart_path: Path | None = None,
) -> str:
    return build_character_rewrite_report(
        character_path=character_path,
        rewrite_client=rewrite_client,
        sentence_length_chart_path=sentence_length_chart_path,
        report_title="Semantic Summary Improvement Report: Jory Ravenmark",
        rewrite_kind="summary",
        generate_model_result=graph_generated_summary_result,
        existing_label="Existing Summary",
        original_label="Source Backstory",
        include_summary_length_score=True,
    )


def write_report(
    report_path: Path = DEFAULT_REPORT_PATH,
    sentence_length_chart_path: Path = DEFAULT_SENTENCE_LENGTH_CHART_PATH,
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(sentence_length_chart_path=sentence_length_chart_path), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    path = write_report()
    print(path)
