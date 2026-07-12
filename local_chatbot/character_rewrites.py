from __future__ import annotations

import re
from dataclasses import dataclass

from character_graph.embeddings import HashingEmbedder, cosine_similarity
from character_graph.schema import CharacterGraph

from .storage import CharacterProfile, character_first_name


RECOMMENDED_REWRITE_MODEL = "qwen2.5-3b-instruct-gguf"


@dataclass(frozen=True)
class RewriteQualityScore:
    score: float
    semantic_similarity: float
    concept_coverage: float
    concision: float


def graph_generated_summary(graph: CharacterGraph, profile: CharacterProfile) -> str:
    primary = graph.characters.get(graph.primary_character.id)
    traits = ", ".join(primary.traits[:3]) if primary and primary.traits else ""
    drives = ", ".join(graph_drive_values(graph, profile)[:2])
    places = ", ".join(story_place_names(graph)[:2])
    relationships = story_relationship_names(graph)[:2]
    pieces = [profile.first_name or character_first_name(profile.name) or profile.name]
    descriptor = " is"
    if traits:
        trait_text = f" who is {traits}"
    else:
        trait_text = ""
    role = " ".join(value for value in [profile.race, profile.character_class] if value).strip()
    if role:
        descriptor += f" a {role}"
    descriptor += trait_text
    pieces.append(descriptor)
    if places:
        pieces.append(f" tied to {places}")
    if relationships:
        pieces.append(f" and connected to {', '.join(relationships)}")
    if drives:
        pieces.append(f", driven to {drives}")
    return humanize_generated_text("".join(pieces).strip() + ".")


def graph_generated_backstory(graph: CharacterGraph, profile: CharacterProfile) -> str:
    name = profile.first_name or character_first_name(profile.name) or profile.name
    full_name = profile.name
    role = " ".join(value for value in [profile.race, profile.character_class] if value).strip() or "wanderer"
    places = story_place_names(graph)
    drives = graph_drive_values(graph, profile)
    relationships = story_relationship_names(graph)
    home = profile.origin or attribute_value(graph, "home")
    relationship_focus = relationships[0] if relationships else ""
    place_focus = places[0] if places else home
    curse_drive = next((drive for drive in drives if "curse" in drive.lower()), "")
    protection_drive = next((drive for drive in drives if "relative" in drive.lower() or "history" in drive.lower()), "")

    origin_line = (
        f"{name} came of age at {place_focus}, a place that sharpened both his talent and his sense of exile."
        if place_focus
        else f"{name} came of age between inherited expectations and the uneasy promise of his own gifts."
    )
    first = (
        f"{full_name} is a {role} whose life has been shaped by the tension between legacy and self-invention. "
        f"{origin_line}"
    )

    if relationship_focus and curse_drive:
        second = (
            f"The loss of {relationship_focus} left more than grief behind; it gave {name} a reason to understand "
            f"the curse shadowing his family and to stop it from claiming anyone else."
        )
    elif curse_drive:
        second = (
            f"A family curse sits at the center of {name}'s story, turning old pain into a task he can no longer ignore."
        )
    elif relationship_focus:
        second = (
            f"His bond with {relationship_focus} gives the story its emotional weight and keeps his choices personal."
        )
    else:
        second = (
            f"The past keeps pressing on {name}, but he has learned to turn that pressure into purpose."
        )

    if protection_drive:
        third = (
            f"Now {name} carries his music forward as a form of defiance, trying to {protection_drive} while "
            "turning inherited sorrow into something brave enough to protect the living."
        )
    elif drives:
        third = (
            f"Now {name} moves with a clearer purpose: to {drives[0]}, without letting the old story decide who he becomes."
        )
    else:
        third = (
            f"Now {name} steps into the wider world with a clearer voice, determined to make the next verse his own."
        )
    return humanize_generated_text("\n\n".join([first, second, third]))


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
