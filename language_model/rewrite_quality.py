from __future__ import annotations

import re
from dataclasses import dataclass

from .character_rewrites import candidate_sentences, rewrite_concision_score, term_tokens


# Mean sentence length from the initial character-sheet fixture backstories.
TARGET_SENTENCE_WORD_COUNT = 20
SENTENCE_LENGTH_PENALTY_PER_WORD = 4.0
MARKDOWN_HEADER_PENALTY = 50
BULLET_POINT_PENALTY = 15


@dataclass(frozen=True)
class SentenceLengthBucket:
    category: str
    word_range: str
    count: int
    percentage: float


@dataclass(frozen=True)
class WritingQualityScore:
    score: float
    formatting: float
    sentence_length: float
    sentence_quality: float
    avg_sentence_length: float
    markdown_headers: int
    bullet_points: int
    sentence_count: int
    sentence_word_counts: tuple[int, ...]
    sentence_length_buckets: tuple[SentenceLengthBucket, ...]


def writing_quality_score(candidate: str) -> WritingQualityScore:
    formatting = formatting_score(candidate)
    avg_sentence_length = average_sentence_length(candidate)
    sentence_length = sentence_length_score(candidate)
    sentence_quality = rewrite_concision_score(candidate) * 100
    sentence_word_counts = tuple(len(term_tokens(sentence)) for sentence in candidate_sentences(candidate))
    score = (0.35 * formatting) + (0.25 * sentence_length) + (0.40 * sentence_quality)
    return WritingQualityScore(
        score=round(score, 2),
        formatting=round(formatting, 2),
        sentence_length=round(sentence_length, 2),
        sentence_quality=round(sentence_quality, 2),
        avg_sentence_length=round(avg_sentence_length, 2),
        markdown_headers=markdown_header_count(candidate),
        bullet_points=bullet_point_count(candidate),
        sentence_count=len(sentence_word_counts),
        sentence_word_counts=sentence_word_counts,
        sentence_length_buckets=sentence_length_distribution(candidate),
    )


def formatting_score(candidate: str) -> float:
    penalty = (markdown_header_count(candidate) * MARKDOWN_HEADER_PENALTY) + (
        bullet_point_count(candidate) * BULLET_POINT_PENALTY
    )
    return max(0.0, 100.0 - penalty)


def sentence_length_score(candidate: str) -> float:
    sentences = candidate_sentences(candidate)
    if not sentences:
        return 0.0
    mean_difference = sum(
        abs(len(term_tokens(sentence)) - TARGET_SENTENCE_WORD_COUNT)
        for sentence in sentences
    ) / len(sentences)
    return max(0.0, 100.0 - (mean_difference * SENTENCE_LENGTH_PENALTY_PER_WORD))


def average_sentence_length(candidate: str) -> float:
    sentences = candidate_sentences(candidate)
    if not sentences:
        return 0.0
    return sum(len(term_tokens(sentence)) for sentence in sentences) / len(sentences)


def sentence_length_distribution(candidate: str) -> tuple[SentenceLengthBucket, ...]:
    counts = {"Fragment": 0, "Short": 0, "Medium": 0, "Long": 0, "Run-on": 0}
    sentence_lengths = [len(term_tokens(sentence)) for sentence in candidate_sentences(candidate)]
    for word_count in sentence_lengths:
        counts[sentence_length_category(word_count)] += 1
    total = len(sentence_lengths)
    return tuple(
        SentenceLengthBucket(
            category=category,
            word_range=word_range,
            count=counts[category],
            percentage=round((counts[category] / total) * 100, 2) if total else 0.0,
        )
        for category, word_range in (
            ("Fragment", "0-5"),
            ("Short", "6-15"),
            ("Medium", "16-25"),
            ("Long", "26-35"),
            ("Run-on", "36+"),
        )
    )


def sentence_length_category(word_count: int) -> str:
    if word_count <= 5:
        return "Fragment"
    if word_count <= TARGET_SENTENCE_WORD_COUNT:
        return "Short"
    if word_count <= 25:
        return "Medium"
    if word_count <= 35:
        return "Long"
    return "Run-on"


def markdown_header_count(candidate: str) -> int:
    return len(re.findall(r"^\s{0,3}#{1,6}\s+\S", candidate, flags=re.MULTILINE))


def bullet_point_count(candidate: str) -> int:
    return len(re.findall(r"^\s{0,3}[-*+]\s+\S", candidate, flags=re.MULTILINE))
