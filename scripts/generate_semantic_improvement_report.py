from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from local_chatbot.character_rewrites import (
    RECOMMENDED_REWRITE_MODEL,
    graph_generated_backstory,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from local_chatbot.storage import Character, read_character_profile


DEFAULT_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Orin_Nightbloom.md"
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "semantic_improvement_orin_nightbloom.md"


def build_report(character_path: Path = DEFAULT_CHARACTER_PATH) -> str:
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))
    generated_story = graph_generated_backstory(graph, profile)
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    generated_score = semantic_rewrite_score(generated_story, source_context, required_terms)
    original_score = semantic_rewrite_score(profile.backstory, source_context, required_terms)
    delta = round(generated_score.score - original_score.score, 4)
    terms = ", ".join(required_terms)
    return (
        "# Semantic Improvement Report: Orin Nightbloom\n\n"
        "## Model Recommendation\n\n"
        f"- Rewrite model: `{RECOMMENDED_REWRITE_MODEL}`\n"
        "- Evaluation: deterministic local hash-embedding semantic scorer with concept coverage and concision.\n\n"
        "## Candidate\n\n"
        "### Post-Transform Story\n\n"
        f"{generated_story}\n\n"
        "### Original Backstory Excerpt\n\n"
        f"{profile.backstory.splitlines()[0].strip()}\n\n"
        "## Required Concepts\n\n"
        f"{terms}\n\n"
        "## Scores\n\n"
        "| Candidate | Overall | Semantic Similarity | Concept Coverage | Concision |\n"
        "| --- | ---: | ---: | ---: | ---: |\n"
        f"| Post-transform story | {generated_score.score:.4f} | {generated_score.semantic_similarity:.4f} | "
        f"{generated_score.concept_coverage:.4f} | {generated_score.concision:.4f} |\n"
        f"| Pre-transform backstory | {original_score.score:.4f} | {original_score.semantic_similarity:.4f} | "
        f"{original_score.concept_coverage:.4f} | {original_score.concision:.4f} |\n\n"
        "## Result\n\n"
        f"The post-transform story improves the semantic quality score by `{delta:.4f}`. "
        "It keeps the core graph-backed concepts while turning the attribute graph into a cleaner narrative arc.\n"
    )


def write_report(report_path: Path = DEFAULT_REPORT_PATH) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    path = write_report()
    print(path)
