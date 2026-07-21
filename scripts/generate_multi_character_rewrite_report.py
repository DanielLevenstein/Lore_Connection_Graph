from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from language_model.character_rewrites import (
    RewriteClient,
    graph_generated_backstory,
    graph_generated_summary,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from language_model.rewrite_model import LOCAL_REWRITE_MODEL_ENGINE, LocalRewriteModelClient, load_local_language_model_config
from language_model.rewrite_quality import writing_quality_score
from language_model.storage import Character, CharacterProfile, read_character_profile
from scripts.generate_semantic_improvement_report import (
    markdown_table,
    model_runtime_section,
    normalized_score,
    status_for_score,
    summary_length_score,
)


CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"
DEFAULT_CHARACTER_PATHS = [
    CHARACTER_SHEETS_DIR / "Orin_Nightbloom.md",
    CHARACTER_SHEETS_DIR / "Jory_Ravenmark.md",
    CHARACTER_SHEETS_DIR / "Neal_Lovington.md",
]
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "multi_character_rewrite_comparison.md"

def build_report(
    character_paths: list[Path] | None = None,
    rewrite_client: RewriteClient | None = None,
) -> str:
    paths = character_paths or DEFAULT_CHARACTER_PATHS
    rewrite_client = rewrite_client or real_model_rewrite_client()
    results = [generate_character_outputs(path, rewrite_client) for path in paths]
    model_metadata = getattr(rewrite_client, "last_metadata", {})
    sections = [
        "# Multi-Character Rewrite Comparison",
        "",
        "## Model Runtime",
        "",
        model_runtime_section(model_metadata),
        "",
        "## Rewrite Engine",
        "",
        f"- Rewrite engine: `{LOCAL_REWRITE_MODEL_ENGINE}`",
        "- Candidates: source material, generated summary, and generated backstory.",
        "- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.",
        "",
        "## Generated Summary Scores",
        "",
        summary_score_table_for_results(results),
        "",
        "## Generated Backstory Scores",
        "",
        backstory_score_table_for_results(results),
        "",
        "## Character Outputs",
        "",
    ]
    for result in results:
        sections.append(character_output_section(result))
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def summary_score_table_for_results(results: list[dict]) -> str:
    rows = [
        summary_score_row(result["name"], result["summary"], result["summary_score"], result["summary_writing_score"])
        for result in results
    ]
    return markdown_table(
        ["Character", "Status", "Overall", "Summary Length Score", "Similarity", "Sentence Length Score", "Sentence Quality"],
        rows,
        alignments=["left", "left", "right", "right", "right", "right", "right"],
    )


def backstory_score_table_for_results(results: list[dict]) -> str:
    rows = [
        score_row(result["name"], result["backstory_score"], result["backstory_writing_score"])
        for result in results
    ]
    return markdown_table(
        ["Character", "Status", "Overall", "Similarity", "Sentence Length Score", "Sentence Quality"],
        rows,
        alignments=["left", "left", "right", "right", "right", "right"],
    )


def character_output_section(result: dict) -> str:
    return (
        f"### {result['name']}\n\n"
        f"Source material: {result['source_label']}\n\n"
        "#### Generated Summary\n\n"
        f"{result['summary']}\n\n"
        "#### Generated Backstory\n\n"
        f"{result['backstory']}"
    )


def generate_character_outputs(path: Path, rewrite_client: RewriteClient) -> dict:
    character = Character(name=path.stem, path=path)
    profile = read_character_profile(character)
    source_profile = source_profile_for_report(profile)
    graph = extract_character_graph(load_backstory(path, character_id=character.name))
    source_context = rewrite_quality_context(graph, source_profile)
    required_terms = rewrite_required_terms(graph, source_profile)
    source_text = source_material(source_profile)
    summary = generated_candidate(lambda: graph_generated_summary(graph, source_profile, rewrite_client=rewrite_client))
    backstory = generated_candidate(lambda: graph_generated_backstory(graph, source_profile, rewrite_client=rewrite_client))
    return {
        "name": profile.name,
        "source_label": source_label(profile),
        "source": source_text,
        "summary": summary,
        "backstory": backstory,
        "source_score": semantic_rewrite_score(source_text, source_context, required_terms),
        "summary_score": semantic_rewrite_score(summary, source_context, required_terms),
        "summary_writing_score": writing_quality_score(summary),
        "backstory_score": semantic_rewrite_score(backstory, source_context, required_terms),
        "backstory_writing_score": writing_quality_score(backstory),
    }


def source_profile_for_report(profile: CharacterProfile) -> CharacterProfile:
    if profile.name == "Orin Nightbloom" and "Character Backstory" in (profile.auto_generated_sections or []):
        return replace(profile, original_backstory="")
    return profile


def source_material(profile: CharacterProfile) -> str:
    return profile.backstory or profile.original_backstory or profile.summary


def source_label(profile: CharacterProfile) -> str:
    if profile.name == "Orin Nightbloom" and "Character Backstory" in (profile.auto_generated_sections or []):
        return "generation 1 auto-generated backstory"
    return "current character backstory"


def generated_candidate(generate) -> str:
    try:
        return generate()
    except RuntimeError as exc:
        return getattr(exc, "candidate_text", "")

def summary_score_row(character_name: str, summary: str, score, writing_score) -> list[str]:
    return [
        character_name,
        status_for_score(score),
        f"{normalized_score(score.score):.2f}",
        f"{summary_length_score(summary):.2f}",
        f"{normalized_score(score.semantic_similarity):.2f}",
        f"{writing_score.sentence_length:.2f}",
        f"{normalized_score(score.concision):.2f}",
    ]


def score_row(character_name: str, score, writing_score) -> list[str]:
    return [
        character_name,
        status_for_score(score),
        f"{normalized_score(score.score):.2f}",
        f"{normalized_score(score.semantic_similarity):.2f}",
        f"{writing_score.sentence_length:.2f}",
        f"{normalized_score(score.concision):.2f}",
    ]


def summary_word_count(summary: str) -> int:
    return len(summary.split())


def real_model_rewrite_client() -> RewriteClient:
    return LocalRewriteModelClient(
        config=load_local_language_model_config(allow_download=True),
        status_callback=lambda message: print(message, file=sys.stderr),
    )


def write_report(report_path: Path = DEFAULT_REPORT_PATH) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    path = write_report()
    print(path)
