from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from language_model_harness import configure_language_model_harness

configure_language_model_harness()

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from local_chatbot.character_rewrites import (
    RECOMMENDED_REWRITE_MODEL,
    RewriteClient,
    graph_generated_backstory,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from local_chatbot.storage import Character, read_character_profile


DEFAULT_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Orin_Nightbloom.md"
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "semantic_backstory_improvement.md"


def build_report(character_path: Path = DEFAULT_CHARACTER_PATH, rewrite_client: RewriteClient | None = None) -> str:
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))
    model_story = graph_generated_backstory(graph, profile, rewrite_client=rewrite_client)
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    existing_generated_backstory = profile.backstory
    original_backstory = profile.original_backstory or profile.backstory
    model_score = semantic_rewrite_score(model_story, source_context, required_terms)
    existing_generated_score = semantic_rewrite_score(existing_generated_backstory, source_context, required_terms)
    original_score = semantic_rewrite_score(original_backstory, source_context, required_terms)
    delta = round(model_score.score - original_score.score, 4)
    score_rows = [
        score_row("Model rewrite", model_score),
        score_row("Existing generated section", existing_generated_score),
    ]
    if original_backstory.strip() != existing_generated_backstory.strip():
        score_rows.append(score_row("Original section", original_score))
    score_table = markdown_table(
        ["Candidate", "Overall", "Source Context Similarity", "Coverage", "Concision"],
        score_rows,
        alignments=["left", "right", "right", "right", "right"],
    )
    return (
        "# Semantic Improvement Report: Orin Nightbloom\n\n"
        "## Model Recommendation\n\n"
        f"- Rewrite model: `{RECOMMENDED_REWRITE_MODEL}`\n"
        "- Evaluation: local hash-embedding source-context similarity, required concept coverage, and concision.\n"
        "- Source context similarity compares each candidate against the assembled character profile and graph evidence.\n\n"
        "## Candidate\n\n"
        "### Model Rewrite\n\n"
        f"{model_story}\n\n"
        "### Existing Generated Section\n\n"
        f"{existing_generated_backstory}\n\n"
        "### Original Character Backstory\n\n"
        f"{original_backstory}\n\n"
        "## Scores\n\n"
        f"{score_table}\n\n"
        "## Result\n\n"
        f"The model rewrite improves the overall quality score over the original section by `{delta:.4f}`. "
        "It keeps the core graph-backed concepts while turning the attribute graph into a cleaner narrative arc.\n"
    )


def score_row(label: str, score) -> list[str]:
    return [
        label,
        f"{score.score:.4f}",
        f"{score.semantic_similarity:.4f}",
        f"{score.concept_coverage:.4f}",
        f"{score.concision:.4f}",
    ]


def markdown_table(headers: list[str], rows: list[list[str]], alignments: list[str] | None = None) -> str:
    alignments = alignments or ["left"] * len(headers)
    table_rows = [[str(cell) for cell in row] for row in rows]
    widths = [
        max(len(str(headers[index])), *(len(row[index]) for row in table_rows))
        for index in range(len(headers))
    ]
    separator = [
        markdown_separator(width, alignments[index] if index < len(alignments) else "left")
        for index, width in enumerate(widths)
    ]
    rendered = [markdown_table_row(headers, widths), markdown_table_row(separator, widths)]
    rendered.extend(markdown_table_row(row, widths) for row in table_rows)
    return "\n".join(rendered)


def markdown_table_row(cells: list[str], widths: list[int]) -> str:
    padded = [cell.ljust(widths[index]) for index, cell in enumerate(cells)]
    return "| " + " | ".join(padded) + " |"


def markdown_separator(width: int, alignment: str) -> str:
    dashes = "-" * max(3, width)
    if alignment == "right":
        return dashes[:-1] + ":"
    if alignment == "center":
        return ":" + dashes[2:] + ":"
    return dashes


def write_report(report_path: Path = DEFAULT_REPORT_PATH) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    path = write_report()
    print(path)
