from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

from character_graph.embeddings import HashingEmbedder, cosine_similarity
from character_graph.schema import CharacterGraph
from model_harness.chat import chat_completion
from model_harness.downloads import (
    default_download_option,
    download_option,
    local_model_path,
    selected_downloaded_option,
)
from model_harness.models import ModelConfig, list_model_configs
from model_harness.server import start_server

from .storage import CharacterProfile, character_first_name


RECOMMENDED_REWRITE_MODEL = "qwen2.5-3b-instruct-gguf"
RewriteClient = Callable[[list[dict[str, str]]], str]


@dataclass(frozen=True)
class RewriteQualityScore:
    score: float
    semantic_similarity: float
    concept_coverage: float
    concision: float


def graph_generated_summary(
    graph: CharacterGraph,
    profile: CharacterProfile,
    rewrite_client: RewriteClient | None = None,
) -> str:
    prompt = rewrite_prompt("summary", graph, profile)
    return run_model_rewrite(prompt, rewrite_client=rewrite_client)


def graph_generated_backstory(
    graph: CharacterGraph,
    profile: CharacterProfile,
    rewrite_client: RewriteClient | None = None,
) -> str:
    prompt = rewrite_prompt("backstory", graph, profile)
    return run_model_rewrite(prompt, rewrite_client=rewrite_client)


def run_model_rewrite(prompt: str, rewrite_client: RewriteClient | None = None) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You rewrite roleplaying character lore. Use only facts from the supplied character sheet "
                "and knowledge graph context. Return only the requested prose, with no preface, loader text, "
                "or reasoning."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    try:
        response = (rewrite_client or local_rewrite_client)(messages)
    except Exception as exc:
        raise RuntimeError(
            f"Could not generate rewrite with local model `{RECOMMENDED_REWRITE_MODEL}`. "
            "Ensure the configured GGUF model is downloaded and try again."
        ) from exc
    cleaned = clean_model_rewrite(response)
    if not cleaned:
        raise RuntimeError(f"Local model `{RECOMMENDED_REWRITE_MODEL}` returned an empty rewrite.")
    return humanize_generated_text(cleaned)


StatusWriter = Callable[[str], None]


def local_rewrite_client(messages: list[dict[str, str]], status_writer: StatusWriter | None = None) -> str:
    config = rewrite_model_config()
    option = ensure_rewrite_model_downloaded(config, status_writer=status_writer)
    write_status = status_writer or default_download_status_writer
    write_status(f"Starting local model server for `{config.name}`.")
    server_status = start_server(config, wait_seconds=45, option=option)
    if not server_status.healthy:
        raise RuntimeError(
            f"Local model server for `{config.name}` is not ready. See log: {server_status.log_path}"
        )
    return chat_completion(config, messages, server_status=server_status)


def direct_local_rewrite_client(messages: list[dict[str, str]], status_writer: StatusWriter | None = None) -> str:
    config = rewrite_model_config()
    option = ensure_rewrite_model_downloaded(config, status_writer=status_writer)
    if option is None:
        raise RuntimeError(f"Local model `{RECOMMENDED_REWRITE_MODEL}` does not list downloadable GGUF options.")
    model_path = local_model_path(config, option)
    prompt = direct_rewrite_prompt(messages)
    result = subprocess.run(
        [
            "llama",
            "cli",
            "--log-disable",
            "--model",
            str(model_path),
            "--device",
            "none",
            "--gpu-layers",
            "0",
            "--prompt",
            prompt,
            "--single-turn",
            "--no-display-prompt",
            "--simple-io",
            "--temperature",
            "0.3",
            "--predict",
            "512",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Local model `{RECOMMENDED_REWRITE_MODEL}` failed: {detail}")
    return clean_llama_cli_output(result.stdout)


def ensure_rewrite_model_downloaded(config: ModelConfig, status_writer: StatusWriter | None = None) -> dict | None:
    option = selected_downloaded_option(config)
    if option:
        return option
    option = default_download_option(config)
    if option:
        write_status = status_writer or default_download_status_writer
        write_status(download_status_bar("Downloading", option, filled=1))
        download_option(config, option)
        write_status(download_status_bar("Ready", option, filled=20))
    return option


def default_download_status_writer(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def download_status_bar(label: str, option: dict, filled: int, width: int = 20) -> str:
    filled = max(0, min(width, filled))
    bar = "#" * filled + "-" * (width - filled)
    filename = option.get("filename", "model")
    return f"{label} local model [{bar}] {filename}"


def clean_llama_cli_output(output: str) -> str:
    lines = []
    skip_thinking = False
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "[Start thinking]":
            skip_thinking = True
            continue
        if line == "[End thinking]":
            skip_thinking = False
            continue
        if skip_thinking:
            continue
        if llama_cli_noise_line(line):
            continue
        lines.append(raw_line.strip())
    return "\n".join(lines).strip()


def llama_cli_noise_line(line: str) -> bool:
    if line in {"Loading model...", "Exiting...", "available commands:"}:
        return True
    if line.startswith(("build      :", "model      :", "ftype      :", "modalities :", "0.")):
        return True
    if line.startswith(("/exit", "/regen", "/clear", "/read", "/glob", "[ Prompt:", ">")):
        return True
    if set(line) <= {"▄", "▀", "█", " ", "\t"}:
        return True
    return False


def direct_rewrite_prompt(messages: list[dict[str, str]]) -> str:
    sections = []
    for message in messages:
        role = message.get("role", "user").strip().title()
        content = message.get("content", "").strip()
        if content:
            sections.append(f"{role}:\n{content}")
    sections.append("Assistant:")
    return "\n\n".join(sections)


def rewrite_model_config() -> ModelConfig:
    configs = {config.name: config for config in list_model_configs()}
    config = configs.get(RECOMMENDED_REWRITE_MODEL)
    if config is None:
        raise RuntimeError(f"Missing model config `{RECOMMENDED_REWRITE_MODEL}`.")
    return config


def rewrite_prompt(kind: str, graph: CharacterGraph, profile: CharacterProfile) -> str:
    if kind == "summary":
        instruction = (
            "Write one polished character summary sentence. Keep it under 70 words. "
            "Include the character's race, class, key place, important relationship, and main drive when present."
        )
    elif kind == "backstory":
        instruction = (
            "Rewrite the character backstory as 2 to 4 concise paragraphs. Preserve the named people, places, "
            "relationships, and drives. Make it read like authored campaign lore, not a bullet list."
        )
    else:
        raise ValueError(f"Unknown rewrite kind: {kind}")
    return "\n\n".join(
        [
            instruction,
            "Character profile:",
            character_profile_context(profile),
            "Knowledge graph context:",
            graph_context(graph),
        ]
    )


def character_profile_context(profile: CharacterProfile) -> str:
    values = [
        f"Name: {profile.name}",
        f"First name: {profile.first_name or character_first_name(profile.name)}",
        f"Race: {profile.race}",
        f"Class: {profile.character_class}",
        f"Pronouns: {profile.pronouns}",
        f"Summary: {profile.summary}",
        f"Backstory: {profile.backstory}",
        f"Original backstory: {profile.original_backstory}",
        f"Drives: {'; '.join(profile.drives or [])}",
        f"Alliances: {'; '.join(profile.alliances or [])}",
        f"Enemies: {'; '.join(profile.enemies or [])}",
    ]
    return "\n".join(value for value in values if value.split(":", 1)[1].strip())


def graph_context(graph: CharacterGraph) -> str:
    lines = [
        f"Primary character: {graph.primary_character.name}",
        "Characters:",
    ]
    for character in graph.characters.values():
        pieces = [character.name]
        if character.summary:
            pieces.append(character.summary)
        if character.traits:
            pieces.append("traits: " + ", ".join(character.traits))
        if character.source_spans:
            pieces.append("evidence: " + " ".join(character.source_spans[:3]))
        lines.append("- " + " | ".join(pieces))
    if graph.places:
        lines.append("Places:")
        for place in graph.places.values():
            pieces = [place.name]
            if place.summary:
                pieces.append(place.summary)
            if place.source_spans:
                pieces.append("evidence: " + " ".join(place.source_spans[:3]))
            lines.append("- " + " | ".join(pieces))
    if graph.attributes:
        lines.append("Attributes:")
        for attribute in graph.attributes.values():
            pieces = [attribute.attribute_type, attribute.value]
            if attribute.summary:
                pieces.append(attribute.summary)
            lines.append("- " + " | ".join(piece for piece in pieces if piece))
    if graph.relationships:
        lines.append("Relationships:")
        for edge in graph.relationships:
            target = graph.characters.get(edge.target)
            target_name = target.name if target else edge.target
            evidence = " ".join(edge.evidence[:2])
            lines.append(f"- {edge.relationship_label or edge.relationship_type}: {target_name}. {evidence}".strip())
    return "\n".join(lines)


def clean_model_rewrite(response: str) -> str:
    cleaned = response.strip()
    cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(r"^(?:summary|backstory)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def rewrite_quality_context(graph: CharacterGraph, profile: CharacterProfile) -> str:
    primary = graph.characters.get(graph.primary_character.id)
    sections = [
        profile.name,
        profile.race,
        profile.character_class,
        profile.pronouns,
        profile.summary,
        profile.backstory,
        " ".join(profile.drives or []),
        " ".join(profile.alliances or []),
        " ".join(profile.enemies or []),
    ]
    if primary:
        sections.extend([primary.summary, " ".join(primary.source_spans)])
    sections.extend(attribute.summary for attribute in graph.attributes.values())
    sections.extend(place.summary for place in graph.places.values())
    for edge in graph.relationships:
        sections.extend(edge.evidence)
    return "\n".join(section.strip() for section in sections if section and section.strip())


def rewrite_required_terms(graph: CharacterGraph, profile: CharacterProfile) -> list[str]:
    terms = [
        profile.name,
        profile.race,
        profile.character_class,
        *(profile.drives or []),
    ]
    terms.extend(story_place_names(graph))
    terms.extend(story_relationship_names(graph))
    return unique_values(term for term in terms if term)


def semantic_rewrite_score(
    candidate: str,
    source_context: str,
    required_terms: list[str] | None = None,
    embedder: HashingEmbedder | None = None,
) -> RewriteQualityScore:
    embedder = embedder or HashingEmbedder(dimensions=128)
    candidate_vector = embedder.embed(candidate)
    source_vector = embedder.embed(source_context)
    semantic_similarity = max(0.0, cosine_similarity(candidate_vector, source_vector))
    concept_coverage = covered_term_ratio(candidate, required_terms or [])
    concision = rewrite_concision_score(candidate)
    score = (0.35 * semantic_similarity) + (0.45 * concept_coverage) + (0.20 * concision)
    return RewriteQualityScore(
        score=round(score, 4),
        semantic_similarity=round(semantic_similarity, 4),
        concept_coverage=round(concept_coverage, 4),
        concision=round(concision, 4),
    )


def graph_drive_values(graph: CharacterGraph, profile: CharacterProfile) -> list[str]:
    values = list(profile.drives or [])
    values.extend(
        attribute.value
        for attribute in graph.attributes.values()
        if attribute.attribute_type.lower() == "drive" and attribute.value
    )
    return unique_values(values)


def story_place_names(graph: CharacterGraph) -> list[str]:
    return unique_values(
        place.name
        for place in graph.places.values()
        if place.name and place.source_spans and place.name.lower() not in {"school", "place"}
    )


def story_relationship_names(graph: CharacterGraph) -> list[str]:
    names = []
    primary_last_name = graph.primary_character.name.split()[-1].lower() if graph.primary_character.name.split() else ""
    for edge in graph.relationships:
        if edge.target not in graph.characters or edge.target == graph.primary_character.id:
            continue
        character = graph.characters[edge.target]
        name = character.name
        if not character.source_spans:
            continue
        if primary_last_name and name.lower() == primary_last_name:
            continue
        if name.lower() in {"mother", "father", "parent", "half", "orc", "bard"}:
            continue
        names.append(humanize_generated_text(name))
    return unique_values(names)


def humanize_generated_text(value: str) -> str:
    return re.sub(r"(?<=\w)_(?=\w)", " ", value)


def attribute_value(graph: CharacterGraph, attribute_type: str) -> str:
    for attribute in graph.attributes.values():
        if attribute.attribute_type.lower() == attribute_type.lower() and attribute.value:
            return attribute.value
    return ""


def covered_term_ratio(candidate: str, required_terms: list[str]) -> float:
    terms = [term for term in unique_values(required_terms) if term_tokens(term)]
    if not terms:
        return 1.0
    candidate_tokens = set(term_tokens(candidate))
    covered = 0
    for term in terms:
        tokens = set(term_tokens(term))
        if tokens and tokens <= candidate_tokens:
            covered += 1
    return covered / len(terms)


def rewrite_concision_score(candidate: str) -> float:
    word_count = len(term_tokens(candidate))
    if 18 <= word_count <= 90:
        return 1.0
    if word_count < 18:
        return max(0.0, word_count / 18)
    return max(0.0, 1.0 - ((word_count - 90) / 160))


def unique_values(values) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        normalized = " ".join(str(value).split())
        key = normalized.lower()
        if normalized and key not in seen:
            unique.append(normalized)
            seen.add(key)
    return unique


def term_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", value.lower())
