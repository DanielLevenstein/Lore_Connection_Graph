from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from character_graph.embeddings import HashingEmbedder, cosine_similarity
from character_graph.schema import CharacterGraph

from .storage import CharacterProfile, character_first_name


REWRITE_ENGINE_NAME = "deterministic-graph-rewrite"
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
    return run_graph_rewrite(prompt, graph, profile, "summary", rewrite_client=rewrite_client)


def graph_generated_backstory(
    graph: CharacterGraph,
    profile: CharacterProfile,
    rewrite_client: RewriteClient | None = None,
) -> str:
    prompt = rewrite_prompt("backstory", graph, profile)
    return run_graph_rewrite(prompt, graph, profile, "backstory", rewrite_client=rewrite_client)


def run_graph_rewrite(
    prompt: str,
    graph: CharacterGraph,
    profile: CharacterProfile,
    kind: str,
    rewrite_client: RewriteClient | None = None,
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Rewrite roleplaying character lore using only facts from the supplied character sheet "
                "and knowledge graph context."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response = rewrite_client(messages) if rewrite_client else deterministic_graph_rewrite(kind, graph, profile)
    cleaned = clean_model_rewrite(response)
    if not cleaned:
        raise RuntimeError(f"{REWRITE_ENGINE_NAME} returned an empty rewrite.")
    return humanize_generated_text(cleaned)


def deterministic_graph_rewrite(kind: str, graph: CharacterGraph, profile: CharacterProfile) -> str:
    if kind == "summary":
        return deterministic_graph_summary(graph, profile)
    if kind == "backstory":
        return deterministic_graph_backstory(graph, profile)
    raise ValueError(f"Unknown rewrite kind: {kind}")


def deterministic_graph_summary(graph: CharacterGraph, profile: CharacterProfile) -> str:
    first_name = profile.first_name or character_first_name(profile.name)
    descriptors = [value for value in [profile.race, profile.character_class] if value]
    identity = " ".join(descriptors) if descriptors else "adventurer"
    places = story_place_names(graph)
    relationships = story_relationship_names(graph)
    drives = graph_drive_values(graph, profile)
    clauses = [f"{profile.name} is {article_for(identity)} {identity}"]
    if places:
        clauses.append(f"shaped by {places[0]}")
    if relationships:
        clauses.append(f"bound to {relationships[0]}")
    if drives:
        clauses.append(f"driven to {drives[0]}")
    summary = ", ".join(clauses) + "."
    return summary.replace(
        profile.name,
        first_name if len(profile.name.split()) > 1 else profile.name,
        1,
    )


def deterministic_graph_backstory(graph: CharacterGraph, profile: CharacterProfile) -> str:
    first_name = profile.first_name or character_first_name(profile.name)
    places = story_place_names(graph)
    relationships = story_relationship_names(graph)
    drives = graph_drive_values(graph, profile)
    traits = primary_traits(graph)
    identity = " ".join(value for value in [profile.race, profile.character_class] if value) or "adventurer"
    origin = attribute_value(graph, "Home") or profile.origin

    opening_parts = [f"{first_name} is {article_for(identity)} {identity}"]
    if origin:
        opening_parts.append(f"from {origin}")
    if places:
        opening_parts.append(f"whose story keeps circling back to {places[0]}")
    opening = " ".join(opening_parts) + "."

    middle_bits = []
    if relationships:
        middle_bits.append(f"Their ties to {', '.join(relationships[:3])} give the story its sharpest edges")
    if traits:
        middle_bits.append(f"{first_name} is remembered as {', '.join(traits[:3])}")
    if not middle_bits:
        middle_bits.append(profile.summary or f"{first_name}'s source notes keep the focus on hard-won choices")
    middle = ". ".join(middle_bits) + "."

    if drives:
        ending = f"Now {first_name} is driven to {drives[0]}"
        if len(drives) > 1:
            ending += f" while still needing to {drives[1]}"
        ending += "."
    else:
        ending = f"Now {first_name} carries those graph-backed connections forward without losing sight of the established lore."
    return "\n\n".join([opening, middle, ending])


def article_for(value: str) -> str:
    return "an" if value[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def primary_traits(graph: CharacterGraph) -> list[str]:
    primary = graph.characters.get(graph.primary_character.id)
    return unique_values(primary.traits if primary else [])


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
