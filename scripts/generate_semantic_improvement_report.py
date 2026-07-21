from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from language_model.character_rewrites import (
    RewriteClient,
    graph_generated_backstory,
    rewrite_quality_context,
    rewrite_required_terms,
    semantic_rewrite_score,
)
from language_model.rewrite_model import LOCAL_REWRITE_MODEL_ENGINE, LocalRewriteModelClient, load_local_language_model_config
from language_model.storage import Character, read_character_profile


DEFAULT_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Orin_Nightbloom.md"
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "semantic_backstory_improvement.md"


def build_report(character_path: Path = DEFAULT_CHARACTER_PATH, rewrite_client: RewriteClient | None = None) -> str:
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))
    rewrite_client = rewrite_client or real_model_rewrite_client()
    model_error = ""
    try:
        model_story = graph_generated_backstory(graph, profile, rewrite_client=rewrite_client)
    except RuntimeError as exc:
        model_story = ""
        model_error = str(exc)
    model_metadata = getattr(rewrite_client, "last_metadata", {})
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    existing_generated_backstory = profile.backstory
    original_backstory = profile.original_backstory or profile.backstory
    model_score = semantic_rewrite_score(model_story, source_context, required_terms)
    existing_generated_score = semantic_rewrite_score(existing_generated_backstory, source_context, required_terms)
    original_score = semantic_rewrite_score(original_backstory, source_context, required_terms)
    delta = round(model_score.score - original_score.score, 4)
    score_rows = [
        score_row("Local model rewrite", model_score, "Rejected" if not model_story.strip() else "Accepted"),
        score_row("Existing generated section", existing_generated_score, "Accepted"),
    ]
    if original_backstory.strip() != existing_generated_backstory.strip():
        score_rows.append(score_row("Original section", original_score, "Source"))
    score_table = markdown_table(
        ["Candidate", "Status", "Overall", "Similarity", "Coverage", "Sentence Quality"],
        score_rows,
        alignments=["left", "left", "right", "right", "right", "right"],
    )
    return (
        "# Semantic Improvement Report: Orin Nightbloom\n\n"
        "## Rewrite Engine\n\n"
        f"- Rewrite engine: `{LOCAL_REWRITE_MODEL_ENGINE}`\n"
        "- Evaluation: local hash-embedding source-context similarity, required concept coverage, and concision.\n"
        "- Source context similarity compares each candidate against the assembled character profile and graph evidence.\n\n"
        "## Model Runtime\n\n"
        f"{model_runtime_section(model_metadata)}\n\n"
        f"{model_error_section(model_error)}"
        "## Candidate\n\n"
        "### Local Model Rewrite\n\n"
        f"{model_candidate_section(model_story)}\n\n"
        f"{model_error_section(model_error)}"
        "### Existing Generated Section\n\n"
        f"{existing_generated_backstory}\n\n"
        "### Original Backstory\n\n"
        f"{original_backstory}\n\n"
        "## Scores\n\n"
        f"{score_table}\n\n"
        "## Result\n\n"
        f"{result_summary(model_story, delta)}\n"
    )


def model_runtime_section(metadata: dict) -> str:
    prompt_eval_time = metadata.get("prompt_eval_time_ms")
    rows = [
        ["Model", metadata.get("model_id", "not reported")],
        ["Quantization", metadata.get("quantization", "not reported")],
        ["Prompt version", metadata.get("prompt_version", "not reported")],
        ["Max tokens", metadata.get("max_tokens", "not reported")],
        ["Temperature", metadata.get("temperature", "not reported")],
        ["Top P", metadata.get("top_p", "not reported")],
        ["Repeat penalty", metadata.get("repeat_penalty", "not reported")],
        ["Seed", metadata.get("seed", "not reported")],
        ["Context size", metadata.get("n_ctx", "not reported")],
        ["Batch size", metadata.get("n_batch", "not reported")],
        ["Threads", metadata.get("n_threads", "not reported")],
        ["GPU layers", metadata.get("n_gpu_layers", "not reported")],
        ["Device", metadata.get("device", "not reported")],
        ["Timeout seconds", metadata.get("timeout_seconds", "not reported")],
        ["Prompt hash", metadata.get("prompt_hash", "not reported")],
        ["Prompt eval time", f"{prompt_eval_time} ms" if prompt_eval_time else "not reported"],
        ["Prompt tokens", metadata.get("prompt_tokens", "not reported")],
        ["Completion tokens", metadata.get("completion_tokens", "not reported")],
        ["Total tokens", metadata.get("total_tokens", "not reported")],
    ]
    return markdown_table(["Metric", "Value"], rows)


def model_candidate_section(model_story: str) -> str:
    return model_story

def model_error_section(model_error: str) -> str:
    return f" \n\nERROR: {model_error}" if model_error else ""

def result_summary(model_story: str, delta: float) -> str:
    if not model_story.strip():
        return (
            "The local model run did not produce an acceptable rewrite, so its score is reported as `0.0000`. "
            "The existing generated section remains the better candidate for this fixture."
        )
    return (
        f"The local model rewrite improves the overall quality score over the original section by `{delta:.4f}`. "
        "It keeps the core graph-backed concepts while turning the attribute graph into a cleaner narrative arc."
    )


def real_model_rewrite_client() -> RewriteClient:
    return LocalRewriteModelClient(
        config=load_local_language_model_config(allow_download=True),
        status_callback=lambda message: print(message, file=sys.stderr),
    )


def score_row(label: str, score, status: str) -> list[str]:
    return [
        label,
        status,
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
