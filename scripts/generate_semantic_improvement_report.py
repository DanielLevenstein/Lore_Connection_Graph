from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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
from language_model.rewrite_quality import SENTENCE_LENGTH_PENALTY_PER_WORD, writing_quality_score
from language_model.storage import Character, read_character_profile


DEFAULT_CHARACTER_PATH = ROOT_DIR / "tests" / "fixtures" / "character_sheets" / "Orin_Nightbloom.md"
DEFAULT_REPORT_PATH = ROOT_DIR / "docs" / "reports" / "semantic_backstory_improvement.md"
DEFAULT_SENTENCE_LENGTH_CHART_PATH = ROOT_DIR / "docs" / "reports" / "semantic_sentence_lengths.png"
ACCEPTANCE_SCORE_THRESHOLD = 70.0
SUMMARY_LENGTH_TARGET_MIN_WORDS = 30
SUMMARY_LENGTH_TARGET_MAX_WORDS = 60


@dataclass(frozen=True)
class CandidateScore:
    label: str
    text: str
    semantic_score: object
    writing_score: object
    status: str


def build_report(
    character_path: Path = DEFAULT_CHARACTER_PATH,
    rewrite_client: RewriteClient | None = None,
    sentence_length_chart_path: Path | None = None,
) -> str:
    return build_character_rewrite_report(
        character_path=character_path,
        rewrite_client=rewrite_client,
        sentence_length_chart_path=sentence_length_chart_path,
        report_title="Semantic Improvement Report: Orin Nightbloom",
        rewrite_kind="backstory",
        generate_model_text=graph_generated_backstory,
        existing_label="Existing Generated Section",
        original_label="Original Backstory",
        include_summary_length_score=False,
    )


def build_character_rewrite_report(
    character_path: Path,
    rewrite_client: RewriteClient | None,
    sentence_length_chart_path: Path | None,
    report_title: str,
    rewrite_kind: str,
    generate_model_text: Callable,
    existing_label: str,
    original_label: str,
    include_summary_length_score: bool,
) -> str:
    character = Character(name=character_path.stem, path=character_path)
    profile = read_character_profile(character)
    graph = extract_character_graph(load_backstory(character_path, character_id=character.name))
    rewrite_client = rewrite_client or real_model_rewrite_client()
    model_rejected = False
    try:
        model_story = generate_model_text(graph, profile, rewrite_client=rewrite_client)
    except RuntimeError as exc:
        model_story = getattr(exc, "candidate_text", "")
        model_rejected = True
    model_metadata = getattr(rewrite_client, "last_metadata", {})
    existing_text = existing_candidate_text(profile, rewrite_kind)
    original_text = original_candidate_text(profile, rewrite_kind)
    source_context = rewrite_quality_context(graph, profile)
    required_terms = rewrite_required_terms(graph, profile)
    model_semantic_score = semantic_rewrite_score(model_story, source_context, required_terms)
    existing_generated_semantic_score = semantic_rewrite_score(existing_text, source_context, required_terms)
    original_semantic_score = semantic_rewrite_score(original_text, source_context, required_terms)
    model_writing_score = writing_quality_score(model_story)
    existing_generated_writing_score = writing_quality_score(existing_text)
    original_writing_score = writing_quality_score(original_text)
    delta = round(model_semantic_score.score - original_semantic_score.score, 4)
    candidate_scores = [
        CandidateScore(
            "Local model rewrite",
            model_story,
            model_semantic_score,
            model_writing_score,
            "Rejected" if model_rejected else status_for_score(model_semantic_score),
        ),
        CandidateScore(
            existing_label,
            existing_text,
            existing_generated_semantic_score,
            existing_generated_writing_score,
            status_for_score(existing_generated_semantic_score),
        ),
    ]
    if original_text.strip() != existing_text.strip():
        candidate_scores.append(CandidateScore(original_label, original_text, original_semantic_score, original_writing_score, "Source"))
    if sentence_length_chart_path:
        render_sentence_length_chart(
            [(candidate.label, candidate.writing_score) for candidate in candidate_scores],
            sentence_length_chart_path,
        )
    score_rows = [
        score_row(candidate, include_summary_length_score=include_summary_length_score)
        for candidate in candidate_scores
    ]
    score_headers = ["Candidate", "Status", "Overall", "Similarity", "Sentence Length Score", "Sentence Quality"]
    score_alignments = ["left", "left", "right", "right", "right", "right"]
    if include_summary_length_score:
        score_headers.insert(2, "Summary Length Score")
        score_alignments.insert(2, "right")
    score_table = markdown_table(
        score_headers,
        score_rows,
        alignments=score_alignments,
    )

    chart_markdown = sentence_length_chart_markdown(sentence_length_chart_path)
    return (
        f"# {report_title}\n\n"
        "## Rewrite Engine\n\n"
        f"- Rewrite engine: `{LOCAL_REWRITE_MODEL_ENGINE}`\n"
        "- Evaluation: semantic similarity, sentence length fit, and sentence quality.\n\n"
        "## Model Runtime\n\n"
        f"{model_runtime_section(model_metadata)}\n\n"
        "## Candidate\n\n"
        "### Local Model Rewrite\n\n"
        f"{model_candidate_section(model_story)}\n\n"
        f"### {existing_label}\n\n"
        f"{existing_text}\n\n"
        f"### {original_label}\n\n"
        f"{original_text}\n\n"
        "## Scores\n\n"
        f"{score_table}\n\n"
        "## Sentence Lengths\n\n"
        f"{chart_markdown}"
        "## Result\n\n"
        f"{result_summary(model_story, delta)}\n"
    )


def existing_candidate_text(profile, rewrite_kind: str) -> str:
    if rewrite_kind == "summary":
        return profile.summary
    return profile.backstory


def original_candidate_text(profile, rewrite_kind: str) -> str:
    if rewrite_kind == "summary":
        return profile.backstory or profile.original_backstory or profile.summary
    return profile.original_backstory or profile.backstory


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


def result_summary(model_story: str, delta: float) -> str:
    if not model_story.strip():
        return (
            "The local model run did not produce an acceptable rewrite, so its score is reported as `0.0000`. "
            "The existing generated section remains the better candidate for this fixture."
        )
    return (
        f"The local model rewrite changes the writing quality score versus the original section by `{delta:.4f}`."
    )


def real_model_rewrite_client() -> RewriteClient:
    return LocalRewriteModelClient(
        config=load_local_language_model_config(allow_download=True),
        status_callback=lambda message: print(message, file=sys.stderr),
    )


def score_row(candidate: CandidateScore, include_summary_length_score: bool = False) -> list[str]:
    row = [
        candidate.label,
        candidate.status,
        f"{normalized_score(candidate.semantic_score.score):.2f}",
        f"{normalized_score(candidate.semantic_score.semantic_similarity):.2f}",
        f"{candidate.writing_score.sentence_length:.2f}",
        f"{normalized_score(candidate.semantic_score.concision):.2f}",
    ]
    if include_summary_length_score:
        row.insert(2, f"{summary_length_score(candidate.text):.2f}")
    return row


def normalized_score(score: float) -> float:
    return score * 100


def status_for_score(score) -> str:
    return "Accepted" if normalized_score(score.score) >= ACCEPTANCE_SCORE_THRESHOLD else "Rejected"


def summary_word_count(summary: str) -> int:
    return len(summary.split())


def summary_length_score(summary: str) -> float:
    word_count = summary_word_count(summary)
    if SUMMARY_LENGTH_TARGET_MIN_WORDS <= word_count <= SUMMARY_LENGTH_TARGET_MAX_WORDS:
        return 100.0
    difference = min(
        abs(word_count - SUMMARY_LENGTH_TARGET_MIN_WORDS),
        abs(word_count - SUMMARY_LENGTH_TARGET_MAX_WORDS),
    )
    return max(0.0, 100.0 - (difference * SENTENCE_LENGTH_PENALTY_PER_WORD))


def sentence_length_rows(candidates: list[tuple[str, object]]) -> list[list[str]]:
    rows = []
    for label, score in candidates:
        for bucket in score.sentence_length_buckets:
            rows.append(
                [
                    label,
                    bucket.category,
                    bucket.word_range,
                    str(bucket.count),
                    f"{bucket.percentage:.2f}%",
                    f"{score.avg_sentence_length:.2f}",
                ]
            )
    return rows


def sentence_length_chart_markdown(chart_path: Path | None) -> str:
    if not chart_path:
        return ""
    try:
        display_path = chart_path.relative_to(DEFAULT_REPORT_PATH.parent)
    except ValueError:
        display_path = chart_path
    return f"![Sentence length distribution]({display_path.as_posix()})\n\n"


def sentence_length_chart_matrix(candidates: list[tuple[str, Any]]) -> tuple[list[str], list[str], list[list[float]]]:
    from sklearn.feature_extraction import DictVectorizer

    categories = ["Fragment", "Short", "Medium", "Long", "Run-on"]
    labels = [label for label, _score in candidates]
    records = []
    for _label, score in candidates:
        record = {category: 0.0 for category in categories}
        record.update({bucket.category: bucket.percentage for bucket in score.sentence_length_buckets})
        records.append(record)
    vectorizer = DictVectorizer(sparse=False)
    matrix = vectorizer.fit_transform(records)
    feature_names = list(vectorizer.get_feature_names_out())
    ordered_indexes = [feature_names.index(category) for category in categories]
    ordered_matrix = matrix[:, ordered_indexes]
    return labels, categories, ordered_matrix.tolist()


def render_sentence_length_chart(candidates: list[tuple[str, Any]], chart_path: Path) -> Path:
    import os
    import tempfile

    matplotlib_cache_dir = Path(tempfile.gettempdir()) / "lore_connection_graph_matplotlib"
    matplotlib_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(matplotlib_cache_dir))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.neighbors import KernelDensity

    labels, categories, matrix = sentence_length_chart_matrix(candidates)
    bucket_centers = np.array([2.5, 10.5, 20.5, 30.5, 40.5])
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(labels), figsize=(12, 3.8), sharey=True)
    if len(labels) == 1:
        axes = [axes]
    colors = ["#7c8da6", "#4c9a72", "#d6a03d", "#c66b45", "#b54848"]
    for axis, (label, score), percentages in zip(axes, candidates, matrix):
        bars = axis.bar(categories, percentages, color=colors)
        kde_values = sentence_length_kde_values(score.sentence_word_counts, bucket_centers, KernelDensity)
        if kde_values:
            axis.plot(
                categories,
                kde_values,
                color="#222222",
                marker="o",
                linewidth=2,
                label="KDE",
            )
        axis.set_title(label)
        axis.set_ylim(0, 100)
        axis.set_ylabel("Sentences (%)")
        axis.tick_params(axis="x", rotation=35)
        axis.grid(axis="y", linestyle=":", linewidth=0.8, alpha=0.6)
        for bar, percentage in zip(bars, percentages):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                min(percentage + 2, 96),
                f"{percentage:.0f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        if kde_values:
            axis.legend(loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(chart_path, dpi=160)
    plt.close(fig)
    return chart_path


def sentence_length_kde_values(
    sentence_word_counts: tuple[int, ...],
    bucket_centers,
    kernel_density_cls,
) -> list[float]:
    if not sentence_word_counts:
        return []
    samples = [[count] for count in sentence_word_counts]
    kde = kernel_density_cls(kernel="gaussian", bandwidth=6.0).fit(samples)
    densities = [float(value) for value in kde.score_samples([[center] for center in bucket_centers])]
    density_values = [2.718281828459045 ** value for value in densities]
    max_density = max(density_values)
    if max_density <= 0:
        return [0.0 for _center in bucket_centers]
    return [(density / max_density) * 100 for density in density_values]


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
