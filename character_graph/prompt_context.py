from __future__ import annotations

from .retrieval import RetrievedCharacterContext


def build_prompt_context(retrieved: list[RetrievedCharacterContext]) -> str:
    if not retrieved:
        return ""
    sections = ["Relevant character attribute context:"]
    for item in retrieved:
        sections.append("")
        sections.append(f"{item.display_name}:")
        sections.append(item.node.summary.strip() or "No summary available.")
        for relationship in item.relationships:
            evidence = " ".join(relationship.evidence).strip()
            sections.append("")
            sections.append("Relationship metadata:")
            sections.append(f"- Relationship: {relationship.relationship_label}")
            if evidence:
                sections.append(f"- Evidence: {evidence}")
    return "\n".join(sections).strip()
