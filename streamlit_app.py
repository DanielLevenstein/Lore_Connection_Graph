from dataclasses import replace
from datetime import date
from pathlib import Path
import os

import streamlit as st

from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_attribute_rows,
    combined_relationship_dot,
    combined_relationship_rows,
    compact,
)
from character_graph.extraction import extract_character_graph
from character_graph.graph_view import (
    evidence_rows,
)
from character_graph.ingest import load_backstory
from character_graph.prompt_context import build_prompt_context
from character_graph.retrieval import retrieve_relevant_context
from character_graph.storage import load_graph
from language_model_harness import configure_language_model_harness

configure_language_model_harness()

from model_harness.environment import ensure_base_dirs
from local_chatbot.storage import (
    Character,
    CharacterProfile,
    Place,
    PlaceProfile,
    append_character_connections,
    character_family_name,
    character_first_name,
    create_character,
    create_place_markdown,
    default_details,
    delete_character_profile,
    delete_place_profile,
    import_external_character_sheet,
    list_external_character_sheets,
    list_places,
    list_characters,
    read_place_markdown,
    read_character_profile,
    read_text,
    regenerate_character_graph,
    remove_character_connections,
    start_chatlog,
    write_character_connections,
    write_character_profile,
    write_place_markdown,
)
from local_chatbot.character_rewrites import (
    graph_generated_backstory as build_graph_generated_backstory,
    graph_generated_summary as build_graph_generated_summary,
)
from local_chatbot.session_notes import (
    import_markdown_text,
    delete_session_note,
    markdown_sections,
    prepare_markdown_import,
    list_session_notes,
    read_markdown_section,
    read_session_note,
    read_session_note_body,
    read_session_note_date_text,
    read_session_note_title,
    write_lore_document,
    write_session_note,
)
from local_chatbot.lore_import import clear_local_lore, import_lore_directory
from local_chatbot.paths import DOCS_LORE_DIR

ENABLE_CHARACTER_REWRITE = "1"
ENABLE_ATTRIBUTE_GRAPH_OVERRIDE = "LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE"
ENABLE_EXTERNAL_CHARACTER_IMPORT = "LOCAL_CHATBOT_ENABLE_EXTERNAL_CHARACTER_IMPORT"

st.set_page_config(page_title="Character Builder", page_icon=":material/forum:", layout="wide")
ensure_base_dirs()

st.markdown(
    """
    <style>
    .model-table-cell {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 0.82rem;
        line-height: 2.35rem;
    }
    .model-table-header {
        color: rgba(250, 250, 250, 0.72);
        font-weight: 700;
        line-height: 1.4rem;
    }
    div[data-testid="stButton"] > button {
        min-height: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def set_active_character(character: Character) -> None:
    if st.session_state.get("active_character") != character.name:
        st.session_state.active_character = character.name
        st.session_state.messages = []
        st.session_state.chatlog_path = str(start_chatlog(character))


def get_active_character() -> Character | None:
    name = st.session_state.get("active_character")
    if not name:
        return None
    return next((character for character in list_characters() if character.name == name), None)


def set_active_place(place: Place) -> None:
    st.session_state.active_place = place.name


def get_active_place() -> Place | None:
    name = st.session_state.get("active_place")
    if not name:
        return None
    return next((place for place in list_places() if place.name == name), None)


def set_active_session_note(path) -> None:
    st.session_state.active_session_note = path.name


def get_active_session_note():
    name = st.session_state.get("active_session_note")
    if not name:
        return None
    return next((path for path in list_session_notes() if path.name == name), None)


def set_active_session_note_section(section_key: str = "") -> None:
    if section_key:
        st.session_state.active_session_note_section = section_key
    else:
        st.session_state.pop("active_session_note_section", None)


def display_character_name(character: Character) -> str:
    profile = read_character_profile(character)
    return clean_display_name(profile.name or character.name)


def display_place_name(place: Place) -> str:
    return clean_display_name(markdown_document_title(read_place_markdown(place)) or place.name)


def display_place_option(place: Place) -> str:
    return f"{display_place_name(place)} ({place.path.name})"


def display_session_note_name(path, show_dates: bool = False) -> str:
    note_date = read_session_note_date_text(path)
    if not note_date:
        title = markdown_document_title(read_session_note(path))
        return clean_display_name(title or path.stem.replace("session_notes_", "").replace("_", " "))
    title = read_session_note_title(path)
    if show_dates:
        return f"{note_date} - {title}" if title else note_date
    return title or note_date


def display_session_note_option(path, show_dates: bool = False) -> str:
    note_date = read_session_note_date_text(path)
    heading = display_session_note_name(path, show_dates=False)
    if note_date and show_dates:
        return f"{path.name} - {note_date} - {heading}"
    return f"{path.name} - {heading}"


def session_note_select_options(paths, show_dates: bool = False) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for path in paths:
        note_date = read_session_note_date_text(path)
        if note_date:
            options.append({"label": display_session_note_option(path, show_dates=show_dates), "path": path.name, "section": ""})
        sections = markdown_sections(read_session_note(path))
        if not sections:
            if not note_date:
                options.append({"label": display_session_note_option(path, show_dates=show_dates), "path": path.name, "section": ""})
            continue
        for section in sections:
            if section.date_text and show_dates:
                label = f"{path.name} - {section.date_text} - {section.text}"
            else:
                label = f"{path.name} - {section.text}"
            options.append({"label": label, "path": path.name, "section": section.key})
    return options


def markdown_document_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("#").strip()
    return ""


def clean_display_name(name: str) -> str:
    cleaned = name.replace("_", " ")
    cleaned = cleaned.replace("(Auto Generated)", "")
    cleaned = cleaned.replace("(Generated)", "")
    cleaned = cleaned.replace("(Autogenerated)", "")
    cleaned = cleaned.replace("Auto Generated", "")
    cleaned = cleaned.replace("Generated", "")
    cleaned = cleaned.replace("Autogenerated", "")
    cleaned = " ".join(cleaned.split())
    return cleaned.rstrip(" -:|")


def graph_rewrites_enabled() -> bool:
    return ENABLE_CHARACTER_REWRITE


def attribute_graph_override_enabled() -> bool:
    return os.environ.get(ENABLE_ATTRIBUTE_GRAPH_OVERRIDE) == "1"


def external_character_import_enabled() -> bool:
    return os.environ.get(ENABLE_EXTERNAL_CHARACTER_IMPORT) == "1"


def build_character_messages(
    character_name: str,
    backstory: str,
    memory: str,
    history: list[dict[str, str]],
    user_text: str,
) -> list[dict[str, str]]:
    graph_context = st.session_state.get("graph_context", "").strip()
    graph_section = f"\n\nRELATED CHARACTER CONTEXT:\n{graph_context}" if graph_context else ""
    system_prompt = (
        f"You are roleplaying as {character_name}, the user's custom character. Stay in character, "
        "use the backstory and memory as ground truth, and keep replies conversational.\n\n"
        f"CHARACTER NAME:\n{character_name}\n\n"
        f"BACKSTORY:\n{backstory.strip()}\n\n"
        f"MEMORY:\n{memory.strip()}"
        f"{graph_section}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_text})
    return messages


def generate_fallback_reply(character: Character, backstory: str, memory: str, prompt: str) -> str:
    summary = first_meaningful_sentence(backstory) or f"I am {character.name}."
    memory_hint = first_meaningful_sentence(memory)
    reply_parts = [
        f"I hear you. {summary}",
        f"About that: {prompt.strip()}",
    ]
    if memory_hint:
        reply_parts.append(f"I keep this in mind: {memory_hint}")
    reply_parts.append("The local model is not ready, so I am answering from the character sheet for now.")
    return " ".join(reply_parts)


def first_meaningful_sentence(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        return stripped
    return ""


def graph_context_for_prompt(character: Character, prompt: str) -> str:
    try:
        graph = load_graph(character.graph_path)
    except (OSError, ValueError):
        return ""
    if not graph:
        return ""
    retrieved = retrieve_relevant_context(graph, prompt)
    return build_prompt_context(retrieved)


def parse_list_field(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").replace(";", ",").split(",") if item.strip()]


def render_list_field(values: list[str] | None) -> str:
    return "\n".join(values or [])


def normalized_story_text(value: str) -> str:
    return " ".join(value.split())


def has_distinct_original(current: str, original: str) -> bool:
    return bool(original.strip()) and normalized_story_text(current) != normalized_story_text(original)


def remove_auto_generated_section(profile: CharacterProfile, section: str) -> list[str]:
    section_key = section.lower()
    return [value for value in profile.auto_generated_sections or [] if value.lower() != section_key]


def accept_current_character_text(profile: CharacterProfile) -> CharacterProfile:
    accepted = profile
    if profile.original_backstory.strip():
        accepted = replace(
            accepted,
            original_backstory="",
            auto_generated_sections=remove_auto_generated_section(accepted, "Character Backstory"),
            updated_sections=remove_updated_section(accepted.updated_sections or [], "Character Backstory"),
        )
    if profile.original_summary.strip():
        accepted = replace(
            accepted,
            original_summary="",
            auto_generated_sections=remove_auto_generated_section(accepted, "Character Summary"),
            updated_sections=remove_updated_section(accepted.updated_sections or [], "Character Summary"),
        )
    return accepted


def graph_generated_summary(character: Character, profile: CharacterProfile) -> str:
    graph = load_graph(character.graph_path)
    if graph is None:
        raise ValueError("No Character Graph Is Available. Regenerate The Graph First.")
    return build_graph_generated_summary(graph, profile)


def graph_generated_backstory(character: Character, profile: CharacterProfile) -> str:
    graph = load_graph(character.graph_path)
    if graph is None:
        raise ValueError("No Character Graph Is Available. Regenerate The Graph First.")
    return build_graph_generated_backstory(graph, profile)


def mark_auto_generated(profile: CharacterProfile, section: str) -> list[str]:
    sections = list(profile.auto_generated_sections or [])
    if section not in sections:
        sections.append(section)
    return sections


def mark_updated_section(sections: list[str], section: str) -> list[str]:
    updated = list(sections)
    if section not in updated:
        updated.append(section)
    return updated


def remove_updated_section(sections: list[str], section: str) -> list[str]:
    section_key = section.lower()
    return [value for value in sections if value.lower() != section_key]


def push_character_undo(character: Character) -> None:
    key = f"character_undo_{character.name}"
    snapshots = st.session_state.setdefault(key, [])
    snapshots.append(read_text(character.backstory_path))
    st.session_state[key] = snapshots[-20:]


def undo_character_changes(character: Character) -> None:
    key = f"character_undo_{character.name}"
    snapshots = st.session_state.get(key, [])
    if not snapshots:
        st.warning("No Character Changes To Undo.")
        return
    previous = snapshots.pop()
    character.backstory_path.write_text(previous.rstrip() + "\n", encoding="utf-8")
    st.session_state[key] = snapshots
    regenerate_character_graph(character)
    st.session_state[f"character_status_{character.name}"] = "Character Changes Undone."
    st.rerun()


def save_character_update(character: Character, updated: CharacterProfile) -> None:
    push_character_undo(character)
    write_character_profile(character, updated)
    st.session_state[f"character_status_{character.name}"] = "Character Saved."
    st.session_state.pop(f"pending_character_save_{character.name}", None)
    st.rerun()


def needs_original_text_save_choice(updated: CharacterProfile) -> bool:
    return has_distinct_original(updated.backstory, updated.original_backstory) or has_distinct_original(
        updated.summary,
        updated.original_summary,
    )


@st.dialog("Save Character Text")
def render_character_save_choice(character: Character) -> None:
    pending_key = f"pending_character_save_{character.name}"
    updated = st.session_state.get(pending_key)
    if updated is None:
        st.warning("No Pending Character Changes Found.")
        if st.button("Close", icon=":material/close:"):
            st.rerun()
        return

    st.write("Do you want to replace the original text with this version, or keep both versions?")
    action_cols = st.columns(2)
    if action_cols[0].button("Replace Original", icon=":material/check:", width="stretch"):
        save_character_update(character, accept_current_character_text(updated))
    if action_cols[1].button("Keep Both", icon=":material/library_books:", width="stretch"):
        save_character_update(character, updated)


def push_place_undo(place: Place) -> None:
    key = f"place_undo_{place.name}"
    snapshots = st.session_state.setdefault(key, [])
    snapshots.append(read_text(place.path))
    st.session_state[key] = snapshots[-20:]


def undo_place_changes(place: Place) -> None:
    key = f"place_undo_{place.name}"
    snapshots = st.session_state.get(key, [])
    if not snapshots:
        st.warning("No Place Changes To Undo.")
        return
    previous = snapshots.pop()
    place.path.write_text(previous.rstrip() + "\n", encoding="utf-8")
    st.session_state[key] = snapshots
    st.session_state[f"place_editor_revision_{place.name}"] = st.session_state.get(
        f"place_editor_revision_{place.name}",
        0,
    ) + 1
    st.session_state[f"place_status_{place.name}"] = "Place Changes Undone."
    st.rerun()


def push_session_notes_undo() -> None:
    snapshots = st.session_state.setdefault("session_notes_undo", [])
    snapshots.append({path.name: read_session_note(path) for path in list_session_notes()})
    st.session_state["session_notes_undo"] = snapshots[-20:]


def undo_session_notes_changes() -> None:
    snapshots = st.session_state.get("session_notes_undo", [])
    if not snapshots:
        st.warning("No Session Note Changes To Undo.")
        return
    previous = snapshots.pop()
    current_paths = {path.name: path for path in list_session_notes()}
    for name, path in current_paths.items():
        if name not in previous:
            path.unlink(missing_ok=True)
    for path in current_paths.values():
        if path.name in previous:
            path.write_text(previous[path.name].rstrip() + "\n", encoding="utf-8")
    st.session_state["session_notes_undo"] = snapshots
    for name in set(current_paths) | set(previous):
        st.session_state[f"session_note_editor_revision_{name}"] = st.session_state.get(
            f"session_note_editor_revision_{name}",
            0,
        ) + 1
    st.session_state["session_notes_status"] = "Session Note Changes Undone."
    st.rerun()


def render_relationship_graph(character: Character) -> None:
    with st.expander("Character Attribute Graph", expanded=False):
        graph = None
        try:
            graph = load_graph(character.graph_path)
        except (OSError, ValueError) as exc:
            st.warning(f"Could Not Load Relationship Graph: {exc}")

        toolbar_cols = st.columns([1, 3])
        if toolbar_cols[0].button("Regenerate", icon=":material/sync:", key=f"regen_graph_{character.name}"):
            try:
                regenerate_character_graph(character)
            except (OSError, ValueError) as exc:
                st.error(f"Could Not Regenerate Graph: {exc}")
            else:
                st.success("Relationship Graph Regenerated.")
                st.rerun()

        if graph is None:
            toolbar_cols[1].caption("No Graph JSON Found Yet. Regenerate It From The Current Backstory.")
            return

        profile = read_character_profile(character)
        evidence = attribute_graph_display_rows(profile) or evidence_rows(graph)

        if not evidence:
            st.info("No Character Graph Attributes Were Extracted From This Backstory.")
            return

        attributes_tab = st.tabs(["Attributes"])[0]
        with attributes_tab:
            st.table(evidence, hide_index=True, width="stretch")
            if attribute_graph_override_enabled():
                render_attribute_graph_override_editor(character, evidence)


def render_attribute_graph_override_editor(character: Character, evidence: list[dict[str, str]]) -> None:
    with st.expander("Override Attribute Graph", expanded=False):
        st.caption("When a Character Connections table is present, graph regeneration uses these rows instead of inferred attributes.")
        override_key = f"attribute_graph_override_{character.name}"
        with st.form(f"attribute_graph_override_form_{character.name}"):
            edited_rows = st.data_editor(
                evidence,
                num_rows="dynamic",
                key=override_key,
                column_order=("Table", "Item", "Value", "Evidence"),
                width="stretch",
            )
            action_cols = st.columns(2)
            save_override = action_cols[0].form_submit_button(
                "Save Attribute Graph Override",
                icon=":material/edit_note:",
            )
            clear_override = action_cols[1].form_submit_button(
                "Use Extracted Graph Again",
                icon=":material/auto_awesome:",
            )
        if save_override:
            write_character_connections(character, edited_rows, manual_override=True)
            st.success("Attribute Graph Override Saved.")
            st.rerun()
        if clear_override:
            remove_character_connections(character)
            st.success("Attribute Graph Override Cleared.")
            st.rerun()


def attribute_graph_display_rows(profile: CharacterProfile) -> list[dict[str, str]]:
    rows = []
    for row in profile.knowledge_graph_fields or []:
        table = row.get("table") or row.get("source") or row.get("Table") or row.get("Source") or ""
        item = row.get("item") or row.get("relationship") or row.get("Item") or row.get("Relationship") or ""
        value = row.get("value") or row.get("name") or row.get("Value") or row.get("Name") or ""
        evidence = row.get("evidence") or row.get("Evidence") or ""
        if not any([table, item, value, evidence]):
            continue
        rows.append(
            {
                "Table": table,
                "Item": item,
                "Value": " ".join(value.replace("_", " ").split()),
                "Evidence": evidence,
            }
        )
    return rows


def render_combined_character_graph() -> None:
    if os.environ.get("LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH") != "1":
        return
    characters = list_characters()
    places = list_places()
    graphs = load_lore_graphs()

    st.header("Combined Knowledge Graph")
    place_sources = [(compact(place.name), place.name, str(place.path)) for place in places]
    with st.expander("Combined Knowledge Graph", expanded=False):
        render_pending_lore_drafts()
        if st.button("Regenerate All Lore Graphs", icon=":material/sync:", key="regen_all_lore_graphs"):
            failures = []
            for character in characters:
                try:
                    regenerate_character_graph(character)
                except (OSError, ValueError) as exc:
                    failures.append(f"{display_character_name(character)}: {exc}")
            if failures:
                st.error("Could Not Regenerate Every Lore Graph. " + " ".join(failures))
            else:
                st.success("All Lore Graphs Regenerated.")
                st.rerun()

        if not graphs and not place_sources:
            st.info("Add Character Or Place Lore To See The Combined Graph.")
            return
        combined = build_combined_character_graph(graphs, place_sources, place_lore_relationships(places))
        rows = combined_relationship_rows(combined)
        detail_rows = combined_attribute_rows(graphs)
        character_nodes = [node for node in combined.characters.values() if node.node_type == "character"]
        character_tabs = st.tabs([node.name for node in character_nodes] or ["Lore"])
        primary_ids = {compact(character.name) for character in characters}
        characters_by_id = {compact(character.name): character for character in characters}
        for tab, node in zip(character_tabs, character_nodes):
            with tab:
                character_id = node.id
                scoped_rows = [
                    row
                    for row in rows
                    if compact(row["Character"]) == character_id or compact(row["Connection"]) == character_id
                ]
                st.graphviz_chart(combined_relationship_dot(combined), width="stretch")
                scoped_detail_rows = [
                    row
                    for row in detail_rows
                    if compact(row["Character"]) == character_id
                ]
                if scoped_rows:
                    st.table(scoped_rows, hide_index=True, width="stretch")
                else:
                    st.info("No Combined Connections Were Found For This Character Yet.")
                if scoped_detail_rows:
                    st.subheader("Character Graph Details")
                    st.table(scoped_detail_rows, hide_index=True, width="stretch")
                if st.button(
                    "Add Character Connections",
                    icon=":material/account_tree:",
                    key=f"append_connections_{character_id}",
                    disabled=character_id not in characters_by_id,
                ):
                    append_character_connections(characters_by_id[character_id], connection_rows_for_character(combined, character_id))
                    st.success("Character Connections Added.")
                    st.rerun()

        secondary_characters = [
            node
            for node_id, node in combined.characters.items()
            if node.node_type == "character" and node_id not in primary_ids
        ]
        secondary_places = [
            node
            for node_id, node in combined.characters.items()
            if node.node_type == "place" and not any(compact(place.name) == node_id for place in places)
        ]
        action_cols = st.columns(2)
        with action_cols[0]:
            if secondary_characters:
                labels = [node.name for node in secondary_characters]
                selected = st.selectbox("Secondary Character", labels, key="secondary_character_file")
                if st.button("Create Character File", icon=":material/person_add:", key="create_secondary_character"):
                    prepare_pending_character(selected)
                    st.rerun()
        with action_cols[1]:
            if secondary_places:
                labels = [node.name for node in secondary_places]
                selected = st.selectbox("Secondary Place", labels, key="secondary_place_file")
                if st.button("Create Place File", icon=":material/add_location_alt:", key="create_secondary_place"):
                    prepare_pending_place(selected)
                    st.rerun()


def load_lore_graphs():
    graphs = []
    for path in lore_markdown_files():
        try:
            document = load_backstory(path, character_id=compact(path.stem))
            graphs.append(extract_character_graph(document))
        except (OSError, ValueError):
            continue
    return graphs


def lore_markdown_files():
    if not DOCS_LORE_DIR.exists():
        return []
    return [
        path
        for path in sorted(DOCS_LORE_DIR.rglob("*.md"))
        if "TEMPLATE" not in path.name.upper() and not path.name.startswith(".")
    ]


def place_lore_relationships(places) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    for place in places:
        text = read_text(place.path)
        source_id = compact(place.name)
        for line in place_connections_lines(text):
            if ":" in line:
                name, relationship = line.split(":", 1)
            else:
                name, relationship = line, "reference"
            target_name = name.strip().lstrip("-").strip()
            if not target_name:
                continue
            relationships.append(
                {
                    "source_id": source_id,
                    "source_name": place.name,
                    "source_type": "place",
                    "source_file": str(place.path),
                    "target_id": compact(target_name),
                    "target_name": target_name,
                    "target_type": "character",
                    "relationship": relationship.strip() or "reference",
                    "evidence": line.strip(),
                }
            )
    return relationships


def place_connections_lines(text: str) -> list[str]:
    sections = text.splitlines()
    lines: list[str] = []
    in_connections = False
    for line in sections:
        stripped = line.strip()
        if stripped.lower().startswith("## "):
            in_connections = stripped.lower() == "## place connections"
            continue
        if in_connections and stripped.startswith("-"):
            lines.append(stripped.lstrip("-").strip())
    return lines


def prepare_pending_character(name: str) -> None:
    clean_name = clean_display_name(name)
    st.session_state.pending_character_profile = CharacterProfile(
        name=clean_name,
        pronouns="",
        level="",
        race="",
        character_class="",
        backstory=f"{character_first_name(clean_name) or clean_name}'s story has not been written yet.",
        summary=f"{clean_name} is a secondary character awaiting a full sheet.",
    )


def prepare_pending_place(name: str) -> None:
    clean_name = clean_display_name(name)
    st.session_state.pending_place_profile = PlaceProfile(
        name=clean_name,
        place_type="Place",
        summary=f"{clean_name} is a referenced place awaiting full lore.",
    )


def render_pending_lore_drafts() -> None:
    if "pending_character_profile" in st.session_state:
        st.subheader("Draft Character")
        render_character_creator("graph_pending_character", st.session_state.pending_character_profile)
    if "pending_place_profile" in st.session_state:
        st.subheader("Draft Place")
        render_place_creator_form("graph_pending_place", st.session_state.pending_place_profile)


def connection_rows_for_character(combined, character_id: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for edge in combined.edges:
        source = combined.characters.get(edge.source)
        target = combined.characters.get(edge.target)
        if not source or not target:
            continue
        if compact(source.name) == character_id:
            rows.append(
                {
                    "Source": "Character Sheet",
                    "Relationship": edge.relationship_label,
                    "Name": target.name,
                    "Evidence": " ".join(edge.evidence),
                }
            )
        elif compact(target.name) == character_id:
            rows.append(
                {
                    "Source": "Place" if source.node_type == "place" else "Character Sheet",
                    "Relationship": edge.relationship_label,
                    "Name": source.name,
                    "Evidence": " ".join(edge.evidence),
                }
            )
    return rows


def render_character_creator(key_prefix: str = "new_character", draft_profile: CharacterProfile | None = None) -> None:
    draft_profile = draft_profile or CharacterProfile(
        name="",
        pronouns="",
        level="",
        race="",
        character_class="",
        backstory="",
    )
    with st.form(key_prefix):
        name = st.text_input("Name", value=draft_profile.name, placeholder="Mara Voss", key=f"{key_prefix}_name")
        name_cols = st.columns(2)
        first_name = name_cols[0].text_input(
            "First Name",
            value=draft_profile.first_name,
            placeholder="Mara",
            key=f"{key_prefix}_first_name",
        )
        family_name = name_cols[1].text_input(
            "Family Name",
            value=draft_profile.family_name,
            placeholder="Voss",
            key=f"{key_prefix}_family_name",
        )
        stat_cols = st.columns(4)
        level = stat_cols[0].text_input("Level", value=draft_profile.level, placeholder="3", key=f"{key_prefix}_level")
        race = stat_cols[1].text_input("Race", value=draft_profile.race, placeholder="Elf", key=f"{key_prefix}_race")
        character_class = stat_cols[2].text_input(
            "Class",
            value=draft_profile.character_class,
            placeholder="Wizard",
            key=f"{key_prefix}_class",
        )
        pronouns = stat_cols[3].text_input(
            "Pronouns",
            value=draft_profile.pronouns,
            placeholder="she/her",
            key=f"{key_prefix}_pronouns",
        )

        backstory = st.text_area(
            "Backstory",
            value=draft_profile.backstory,
            placeholder="A terse archivist from a vanished city who tests every lock twice...",
            height=160,
            key=f"{key_prefix}_backstory",
        )
        summary = st.text_area(
            "Summary",
            value=draft_profile.summary,
            placeholder="Mara is a wary archivist whose courage looks like preparation.",
            height=96,
            key=f"{key_prefix}_summary",
        )
        with st.expander("Optional Metadata", expanded=False):
            detail_cols = st.columns(3)
            drives = detail_cols[0].text_area(
                "Drives",
                value=render_list_field(draft_profile.drives),
                placeholder="Restore Family Name\nProtect Old Friends",
                height=96,
                key=f"{key_prefix}_drives",
            )
            alliances = detail_cols[1].text_area(
                "Alliances",
                value=render_list_field(draft_profile.alliances),
                placeholder="Silver Cartographers\nMara Voss",
                height=96,
                key=f"{key_prefix}_alliances",
            )
            enemies = detail_cols[2].text_area(
                "Enemies",
                value=render_list_field(draft_profile.enemies),
                placeholder="The Ash Court\nTorvak",
                height=96,
                key=f"{key_prefix}_enemies",
            )
            details = st.text_area(
                "Character Details",
                value=draft_profile.details,
                placeholder="Add Any Freeform Character Sheet Fields Here.",
                height=120,
                key=f"{key_prefix}_details",
            )

        submitted = st.form_submit_button("Create Character", icon=":material/person_add:")
        if submitted:
            if not all([name.strip(), race.strip(), character_class.strip(), backstory.strip()]):
                st.error("Complete Name, Race, Class, And Backstory.")
                return
            try:
                profile = CharacterProfile(
                    name=name.strip(),
                    pronouns=pronouns.strip(),
                    level=level.strip(),
                    race=race.strip(),
                    character_class=character_class.strip(),
                    backstory=backstory.strip(),
                    first_name=first_name.strip() or character_first_name(name),
                    family_name=family_name.strip() or character_family_name(name),
                    summary=summary.strip(),
                    motivations=[],
                    drives=parse_list_field(drives),
                    alliances=parse_list_field(alliances),
                    enemies=parse_list_field(enemies),
                    details=details.strip(),
                )
                character = create_character(profile)
            except FileExistsError:
                st.error("A Character With That Name Already Exists.")
            except ValueError as exc:
                st.error(str(exc))
            else:
                if key_prefix == "graph_pending_character":
                    st.session_state.pop("pending_character_profile", None)
                clear_character_creator_state(key_prefix)
                set_active_character(character)
                st.success(f"Created {character.name}.")
                st.rerun()


def clear_character_creator_state(key_prefix: str) -> None:
    for field in (
        "name",
        "first_name",
        "family_name",
        "level",
        "race",
        "class",
        "pronouns",
        "backstory",
        "summary",
        "drives",
        "alliances",
        "enemies",
        "details",
    ):
        st.session_state.pop(f"{key_prefix}_{field}", None)


def render_place_creator() -> None:
    st.subheader("New Place")
    places = list_places()
    if places:
        st.caption(f"{len(places)} Place Files Available.")
    with st.expander("Create Place", expanded=False):
        render_place_creator_form("new_place")


def render_place_creator_form(key_prefix: str, draft_profile: PlaceProfile | None = None) -> None:
    draft_profile = draft_profile or PlaceProfile(name="", place_type="", summary="")
    with st.form(key_prefix):
        name = st.text_input("Name", value=draft_profile.name, placeholder="Royal Tittles", key=f"{key_prefix}_name")
        markdown = st.text_area(
            "Place Markdown",
            value=draft_place_markdown(draft_profile),
            placeholder="# Royal Tittles\n\nA dockside tavern where private bargains sound like songs.",
            height=220,
            key=f"{key_prefix}_markdown",
        )
        submitted = st.form_submit_button("Create Place", icon=":material/add_location_alt:")
        if submitted:
            if not all([name.strip(), markdown.strip()]):
                st.error("Complete Name And Place Markdown.")
                return
            try:
                place = create_place_markdown(name.strip(), markdown.strip())
            except FileExistsError:
                st.error("A Place With That Name Already Exists.")
            except ValueError as exc:
                st.error(str(exc))
            else:
                if key_prefix == "graph_pending_place":
                    st.session_state.pop("pending_place_profile", None)
                clear_place_creator_state(key_prefix)
                set_active_place(place)
                st.success(f"Created {name.strip()}.")
                st.rerun()


def clear_place_creator_state(key_prefix: str) -> None:
    for field in ("name", "markdown"):
        st.session_state.pop(f"{key_prefix}_{field}", None)


def draft_place_markdown(draft_profile: PlaceProfile) -> str:
    if not any(
        [
            draft_profile.name.strip(),
            draft_profile.summary.strip(),
            draft_profile.details.strip(),
            draft_profile.connections,
        ]
    ):
        return ""
    lines = [f"# {draft_profile.name.strip()}"]
    if draft_profile.summary.strip():
        lines.extend(["", draft_profile.summary.strip()])
    if draft_profile.details.strip():
        lines.extend(["", draft_profile.details.strip()])
    if draft_profile.connections:
        lines.extend(["", "## Place Connections", ""])
        lines.extend(f"- {connection}" for connection in draft_profile.connections if connection.strip())
    return "\n".join(lines)


def render_place_panel() -> None:
    st.title("Places")
    place_panel_status = st.session_state.pop("place_panel_status", "")
    if place_panel_status:
        st.success(place_panel_status)
    places = list_places()
    if places:
        display_names = [display_place_option(place) for place in places]
        current = st.session_state.get("active_place", places[0].name)
        current_index = next((index for index, place in enumerate(places) if place.name == current), 0)
        selected_place_label = st.selectbox(
            "Place Files",
            display_names,
            index=current_index,
            key="main_existing_place",
        )
        selected_place = places[display_names.index(selected_place_label)]
        if st.button("Open Place", icon=":material/location_on:", key="main_open_place"):
            set_active_place(selected_place)
            st.rerun()
        if "active_place" not in st.session_state:
            set_active_place(selected_place)
    else:
        st.info("Create Your First Place To Begin.")

    active_place = get_active_place()
    if active_place:
        render_place_info(active_place)

    render_place_creator()


def render_place_info(place: Place) -> None:
    markdown = read_place_markdown(place).strip()
    if markdown:
        st.markdown(markdown)
    else:
        st.subheader(display_place_name(place))
    with st.expander("Edit Place", expanded=False):
        place_message = st.session_state.pop(f"place_status_{place.name}", "")
        if place_message:
            st.success(place_message)
        with st.form(f"edit_place_{place.name}"):
            st.text_input("Name", value=display_place_name(place), disabled=True)
            editor_revision = st.session_state.get(f"place_editor_revision_{place.name}", 0)
            body = st.text_area(
                "Place Markdown",
                value=markdown,
                height=260,
                key=f"place_markdown_{place.name}_{editor_revision}",
            )
            action_cols = st.columns(3)
            save_requested = action_cols[0].form_submit_button("Save Place", icon=":material/save:")
            delete_requested = action_cols[1].form_submit_button("Delete Place", icon=":material/delete_forever:")
            undo_requested = action_cols[2].form_submit_button("Undo Changes", icon=":material/undo:")
            if undo_requested:
                undo_place_changes(place)
            if delete_requested:
                delete_place_profile(place)
                st.session_state.pop(f"place_undo_{place.name}", None)
                st.session_state.pop(f"place_editor_revision_{place.name}", None)
                st.session_state.pop("active_place", None)
                st.session_state["place_panel_status"] = "Place Deleted."
                st.rerun()
            if save_requested:
                if not body.strip():
                    st.error("Add Place Markdown Before Saving.")
                    return
                push_place_undo(place)
                write_place_markdown(place, body)
                st.session_state[f"place_editor_revision_{place.name}"] = editor_revision + 1
                st.session_state[f"place_status_{place.name}"] = "Place Saved."
                st.rerun()


def render_lore_import_tools() -> None:
    import_status = st.session_state.pop("lore_import_status", "")
    if import_status:
        st.success(import_status)

    with st.expander("Lore Import", expanded=False):
        st.subheader("Bulk Lore Directory")
        source_dir = st.text_input(
            "Source Directory",
            value=str(DOCS_LORE_DIR),
            help="Choose the root directory that contains character_sheets, places, and session_notes folders.",
            key="lore_directory_import_source",
        )
        overwrite_existing = st.checkbox(
            "Overwrite Existing Files",
            value=True,
            key="lore_directory_import_overwrite",
        )
        action_cols = st.columns(2)
        if action_cols[0].button("Import Lore Directory", icon=":material/folder_copy:", key="import_lore_directory"):
            try:
                summary = import_lore_directory(Path(source_dir), overwrite=overwrite_existing)
            except FileNotFoundError:
                st.error("Choose An Existing Lore Directory Before Importing.")
                return
            st.session_state["lore_import_status"] = (
                f"Imported {summary.total} Lore File{'s' if summary.total != 1 else ''} "
                f"({summary.characters} Characters, {summary.places} Places, {summary.session_notes} Session Notes)."
            )
            st.rerun()
        if action_cols[1].button("Bulk Lore Removal", icon=":material/delete_forever:", key="bulk_lore_removal"):
            render_bulk_lore_removal_warning()


@st.dialog("Bulk Lore Removal")
def render_bulk_lore_removal_warning() -> None:
    st.warning(
        "This operation is destructive. Do you want to delete all local characters, places, and notes?"
    )
    st.write("This will clean the configured `docs/lore` and `data/lore` directories.")
    action_cols = st.columns(2)
    if action_cols[0].button("Yes, Delete Local Lore", icon=":material/delete_forever:", width="stretch"):
        summary = clear_local_lore()
        st.session_state["lore_import_status"] = (
            f"Deleted {summary.total} Local Lore File{'s' if summary.total != 1 else ''} "
            f"({summary.characters} Characters, {summary.places} Places, {summary.session_notes} Session Notes)."
        )
        for key in ("active_character", "active_place", "active_session_note"):
            st.session_state.pop(key, None)
        st.rerun()
    if action_cols[1].button("Cancel", icon=":material/close:", width="stretch"):
        st.rerun()


@st.dialog("Select Searchable Headings")
def render_session_import_heading_dialog(
    notes: str,
    source_name: str,
    session_date: str,
) -> None:
    import_title = os.path.splitext(source_name)[0]
    _normalized, headings = prepare_markdown_import(notes, title=import_title)
    st.write("Choose which extracted headings should remain searchable.")
    selected_heading_keys: set[str] = set()
    for heading in headings:
        label = f"H{heading.level} {heading.text}"
        if st.checkbox(
            label,
            value=True,
            disabled=heading.kind == "date",
            key=f"import_heading_{heading.key}",
        ):
            selected_heading_keys.add(heading.key)
    action_cols = st.columns(2)
    if action_cols[0].button("Save Selected Headings", icon=":material/check:", width="stretch"):
        st.session_state["main_navigation_tab"] = "Session Notes"
        push_session_notes_undo()
        saved = import_markdown_text(
            notes,
            title=import_title,
            session_date=session_date,
            selected_heading_keys=selected_heading_keys,
            save_as_single_file=True,
        )
        st.session_state["session_notes_saved_count"] = len(saved)
        if saved:
            set_active_session_note(saved[0].path)
            set_active_session_note_section()
        st.session_state["clear_session_notes_draft"] = True
        st.rerun()
    if action_cols[1].button("Cancel", icon=":material/close:", width="stretch"):
        st.session_state["main_navigation_tab"] = "Session Notes"
        st.rerun()


def render_session_notes() -> None:
    st.title("Session Notes")
    saved_count = st.session_state.pop("session_notes_saved_count", 0)
    if saved_count:
        st.success(f"Saved {saved_count} Session Note File{'s' if saved_count != 1 else ''}.")
    session_notes_status = st.session_state.pop("session_notes_status", "")
    if session_notes_status:
        st.success(session_notes_status)
    show_dates = True

    note_files = list_session_notes()
    if note_files:
        select_options = session_note_select_options(note_files, show_dates=show_dates)
        display_names = [option["label"] for option in select_options]
        current = st.session_state.get("active_session_note", note_files[0].name)
        current_section = st.session_state.get("active_session_note_section", "")
        current_index = next(
            (
                index
                for index, option in enumerate(select_options)
                if option["path"] == current and option["section"] == current_section
            ),
            next((index for index, option in enumerate(select_options) if option["path"] == current), 0),
        )
        selected_note_label = st.selectbox(
            "Session Note",
            display_names,
            index=current_index,
            key="main_existing_session_note",
        )
        selected_option = select_options[display_names.index(selected_note_label)]
        selected_note = next(path for path in note_files if path.name == selected_option["path"])
        if st.button("Open Session Note", icon=":material/event_note:", key="main_open_session_note"):
            set_active_session_note(selected_note)
            set_active_session_note_section(selected_option["section"])
            st.rerun()
        if "active_session_note" not in st.session_state:
            set_active_session_note(selected_note)
            set_active_session_note_section(selected_option["section"])
    else:
        st.info("Create Your First Session Note To Begin.")

    active_note = get_active_session_note()
    if active_note:
        render_session_note_editor(
            active_note,
            show_dates=show_dates,
            section_key=st.session_state.get("active_session_note_section", ""),
        )

    st.subheader("New Session Notes")
    with st.expander(
        "Add Or Import Session Note",
        expanded=st.session_state.get("session_notes_import_expanded", False),
    ):
        if st.session_state.pop("clear_session_notes_draft", False):
            st.session_state["session_notes_draft"] = ""
            st.session_state["session_notes_session_date"] = ""
            st.session_state["markdown_import_source_name"] = ""
        uploaded_notes = st.file_uploader(
            "File",
            type=["md", "txt"],
            key="markdown_import",
        )
        title = st.text_input(
            "Imported File Name",
            placeholder=uploaded_notes.name if uploaded_notes is not None else "Optional title or source filename",
            key="markdown_import_source_name",
        )
        session_date = st.text_input(
            "Import Session Date",
            placeholder=f"Optional campaign date, e.g. {date.today().isoformat()} or Third Moon 17",
            key="session_notes_session_date",
        )
        notes = st.text_area(
            "New Session Notes",
            height=180,
            placeholder="Write campaign memory in Markdown. Include dates to split notes into dated files.",
            key="session_notes_draft",
        )
        action_cols = st.columns(2)
        if action_cols[0].button("Save Session Notes", icon=":material/note_add:", key="save_session_notes"):
            st.session_state["session_notes_import_expanded"] = True
            source_name = title.strip() or (uploaded_notes.name if uploaded_notes is not None else "")
            if uploaded_notes is not None:
                try:
                    notes = uploaded_notes.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    st.error("Import File Must Be UTF-8 Text.")
                    return
            if not notes.strip():
                st.error("Add Session Notes Before Saving.")
                return
            if uploaded_notes is not None:
                st.session_state["main_navigation_tab"] = "Session Notes"
                render_session_import_heading_dialog(
                    notes,
                    source_name,
                    session_date,
                )
                return
            push_session_notes_undo()
            saved = import_markdown_text(
                notes,
                title=os.path.splitext(source_name)[0],
                include_detected_dates=True,
                split_sessions=True,
                session_date=session_date,
            )
            st.session_state["main_navigation_tab"] = "Session Notes"
            st.session_state["session_notes_saved_count"] = len(saved)
            st.session_state["session_notes_import_expanded"] = True
            if saved:
                set_active_session_note(saved[0].path)
                set_active_session_note_section()
            st.session_state["clear_session_notes_draft"] = True
            st.rerun()
        if action_cols[1].button("Undo Changes", icon=":material/undo:", key="undo_session_notes"):
            undo_session_notes_changes()


def render_session_note_editor(path, show_dates: bool = False, section_key: str = "") -> None:
    note_label = display_session_note_name(path, show_dates=False)
    note_date = read_session_note_date_text(path)
    note_title = read_session_note_title(path) if note_date else ""
    note_body = read_session_note_body(path) if note_date else read_session_note(path).strip()
    display_body = read_markdown_section(path, section_key) if section_key else note_body
    if markdown_document_title(note_body) != note_label:
        st.subheader(note_label)
    if display_body:
        st.markdown(display_body)
    expander_label = "Edit Session Note" if note_date else "Edit Lore Document"
    with st.expander(expander_label, expanded=False):
        editor_revision = st.session_state.get(f"session_note_editor_revision_{path.name}", 0)
        with st.form(f"edit_session_note_{path.name}"):
            if note_date:
                session_date = st.text_input(
                    "Session Date",
                    value=note_date,
                    placeholder="Campaign date",
                    key=f"session_note_date_{path.name}_{editor_revision}",
                )
                title = st.text_input(
                    "Title",
                    value=note_title,
                    placeholder="Optional session title",
                    key=f"session_note_title_{path.name}_{editor_revision}",
                )
            body = st.text_area(
                "Session Note" if note_date else "Lore Document",
                value=note_body,
                height=220,
                key=f"session_note_body_{path.name}_{editor_revision}",
            )
            action_cols = st.columns(3)
            save_requested = action_cols[0].form_submit_button("Save Session Note", icon=":material/save:")
            delete_requested = action_cols[1].form_submit_button(
                "Delete Session Note",
                icon=":material/delete_forever:",
            )
            undo_requested = action_cols[2].form_submit_button("Undo Changes", icon=":material/undo:")
            if undo_requested:
                undo_session_notes_changes()
            if delete_requested:
                push_session_notes_undo()
                delete_session_note(path)
                st.session_state.pop(f"session_note_editor_revision_{path.name}", None)
                st.session_state.pop("active_session_note", None)
                st.session_state["session_notes_status"] = "Session Note Deleted."
                st.rerun()
            if save_requested:
                if not body.strip():
                    st.error("Add Markdown Details Before Saving.")
                    return
                push_session_notes_undo()
                if note_date:
                    write_session_note(path, body, title, session_date=session_date)
                    st.session_state["session_notes_status"] = "Session Note Saved."
                else:
                    write_lore_document(path, body)
                    st.session_state["session_notes_status"] = "Lore Document Saved."
                st.session_state[f"session_note_editor_revision_{path.name}"] = editor_revision + 1
                st.rerun()


def render_character_panel() -> None:
    st.title("Characters")
    character_panel_status = st.session_state.pop("character_panel_status", "")
    if character_panel_status:
        st.success(character_panel_status)
    characters = list_characters()
    if characters:
        display_names = [display_character_name(character) for character in characters]
        current = st.session_state.get("active_character", characters[0].name)
        current_index = next(
            (index for index, character in enumerate(characters) if character.name == current),
            0,
        )
        selected_character_label = st.selectbox(
            "Existing Characters",
            display_names,
            index=current_index,
            key="main_existing_character",
        )
        selected_character = characters[display_names.index(selected_character_label)]
        if st.button("Open Character", icon=":material/chat:", key="main_open_character"):
            set_active_character(selected_character)
            st.rerun()
        if "active_character" not in st.session_state:
            set_active_character(selected_character)
    else:
            st.info("Create Your First Character To Begin.")
    # When a character is opened, show it here before the create character section.
    if "active_character" in st.session_state:
        character = get_active_character()
        if character:
            render_character_info(character)

    st.subheader("New Character")
    with st.expander("Create Character", expanded=not characters):
        render_character_creator("main_new_character")
    if external_character_import_enabled():
        render_external_character_sheet_import()
        render_external_character_sheet_list()


def render_external_character_sheet_import() -> None:
    with st.expander("Import External Character Sheet", expanded=False):
        external_sheet = st.file_uploader(
            "Character Sheet File",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key="external_character_sheet_import",
        )
        external_sheet_name = st.text_input(
            "Character Sheet Name",
            value="",
            placeholder="Optional display name",
            key="external_character_sheet_name",
        )
        if st.button("Import Character Sheet", icon=":material/upload_file:", key="import_external_character_sheet"):
            if external_sheet is None:
                st.error("Choose A PDF Or Image Character Sheet Before Importing.")
                return
            try:
                imported = import_external_character_sheet(
                    external_sheet.name,
                    external_sheet.getvalue(),
                    display_name=external_sheet_name,
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            st.session_state["main_navigation_tab"] = "Characters"
            st.session_state["character_panel_status"] = f"Imported External Character Sheet: {imported.path.name}."
            st.rerun()


def render_external_character_sheet_list() -> None:
    external_sheets = list_external_character_sheets()
    if not external_sheets:
        return
    with st.expander("External Character Sheets", expanded=False):
        rows = [
            {
                "Name": sheet.name,
                "Format": sheet.path.suffix.lower().lstrip(".").upper(),
                "File": sheet.path.name,
            }
            for sheet in external_sheets
        ]
        st.table(rows, hide_index=True, width="stretch")


def render_character_editor(character: Character) -> None:
    profile = read_character_profile(character)
    with st.expander("Edit Character", expanded=False):
        character_message = st.session_state.pop(f"character_status_{character.name}", "")
        if character_message:
            st.success(character_message)
        with st.form(f"edit_character_{character.name}"):
            st.text_input("Name", value=profile.name, disabled=True)
            name_cols = st.columns(2)
            first_name = name_cols[0].text_input("First Name", value=profile.first_name)
            family_name = name_cols[1].text_input("Family Name", value=profile.family_name)
            stat_cols = st.columns(4)
            level = stat_cols[0].text_input("Level", value=profile.level)
            race = stat_cols[1].text_input("Race", value=profile.race)
            character_class = stat_cols[2].text_input("Class", value=profile.character_class)
            pronouns = stat_cols[3].text_input("Pronouns", value=profile.pronouns)
            if has_distinct_original(profile.backstory, profile.original_backstory):
                backstory_cols = st.columns(2)
                backstory = backstory_cols[0].text_area(
                    section_label("Backstory", profile, "Character Backstory"),
                    value=profile.backstory,
                    height=180,
                )
                backstory_cols[1].text_area(
                    "Original Backstory",
                    value=profile.original_backstory,
                    height=180,
                    disabled=True,
                )
            else:
                backstory = st.text_area(section_label("Backstory", profile, "Character Backstory"), value=profile.backstory, height=180)
            if has_distinct_original(profile.summary, profile.original_summary):
                summary_cols = st.columns(2)
                summary = summary_cols[0].text_area(
                    section_label("Summary", profile, "Character Summary"),
                    value=profile.summary,
                    height=96,
                )
                summary_cols[1].text_area(
                    "Original Summary",
                    value=profile.original_summary,
                    height=96,
                    disabled=True,
                )
            else:
                summary = st.text_area(section_label("Summary", profile, "Character Summary"), value=profile.summary, height=96)
            with st.expander("Optional Metadata", expanded=False):
                detail_cols = st.columns(3)
                drives = detail_cols[0].text_area("Drives", value=render_list_field(profile.drives), height=96)
                alliances = detail_cols[1].text_area("Alliances", value=render_list_field(profile.alliances), height=96)
                enemies = detail_cols[2].text_area("Enemies", value=render_list_field(profile.enemies), height=96)
                details_value = profile.details or default_details(profile)
                details = st.text_area("Character Details", value=details_value, height=120)
            action_cols = st.columns(5 if graph_rewrites_enabled() else 3)
            save_requested = action_cols[0].form_submit_button("Save Character", icon=":material/save:")
            populate_summary = False
            repopulate_summary = False
            rewrite_backstory = False
            if graph_rewrites_enabled():
                repopulate_summary = action_cols[1].form_submit_button("Repopulate Summary", icon=":material/sync:")
                rewrite_backstory = action_cols[2].form_submit_button("Rewrite Backstory", icon=":material/edit_note:")
                delete_col = action_cols[3]
                undo_col = action_cols[4]
            else:
                delete_col = action_cols[1]
                undo_col = action_cols[2]
            delete_requested = delete_col.form_submit_button("Delete Character", icon=":material/delete_forever:")
            undo_requested = undo_col.form_submit_button("Undo Changes", icon=":material/undo:")
            if undo_requested:
                undo_character_changes(character)
            if delete_requested:
                delete_character_profile(character)
                st.session_state.pop(f"character_undo_{character.name}", None)
                st.session_state.pop("active_character", None)
                st.session_state.pop("messages", None)
                st.session_state.pop("chatlog_path", None)
                st.session_state["character_panel_status"] = "Character Deleted."
                st.rerun()
            if save_requested or populate_summary or repopulate_summary or rewrite_backstory:
                submitted_details = details.strip()

                if not profile.details.strip() and submitted_details == default_details(profile).strip():
                    submitted_details = ""
                next_summary = summary.strip()
                next_backstory = backstory.strip()
                auto_generated_sections = list(profile.auto_generated_sections or [])
                updated_sections = list(profile.updated_sections or [])
                original_summary = profile.original_summary
                original_backstory = profile.original_backstory
                try:
                    if populate_summary and not next_summary:
                        original_summary = profile.summary
                        next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                        updated_sections = remove_updated_section(updated_sections, "Character Summary")
                    elif repopulate_summary:
                        original_summary = profile.original_summary or profile.summary
                        next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                        updated_sections = remove_updated_section(updated_sections, "Character Summary")
                    elif rewrite_backstory:
                        original_backstory = profile.original_backstory or profile.backstory
                        next_backstory = graph_generated_backstory(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Backstory")
                        updated_sections = remove_updated_section(updated_sections, "Character Backstory")
                except ValueError as exc:
                    st.error(str(exc))
                    return
                generated = {value.lower() for value in auto_generated_sections}
                if save_requested and (
                    "character backstory" in generated
                    and original_backstory.strip()
                    and normalized_story_text(next_backstory) != normalized_story_text(profile.backstory)
                ):
                    updated_sections = mark_updated_section(updated_sections, "Character Backstory")
                if save_requested and (
                    "character summary" in generated
                    and original_summary.strip()
                    and normalized_story_text(next_summary) != normalized_story_text(profile.summary)
                ):
                    updated_sections = mark_updated_section(updated_sections, "Character Summary")
                updated = CharacterProfile(
                    name=profile.name,
                    pronouns=pronouns.strip(),
                    level=level.strip(),
                    race=race.strip(),
                    character_class=character_class.strip(),
                    backstory=next_backstory,
                    first_name=first_name.strip(),
                    family_name=family_name.strip(),
                    summary=next_summary,
                    motivations=profile.motivations,
                    drives=parse_list_field(drives),
                    alliances=parse_list_field(alliances),
                    enemies=parse_list_field(enemies),
                    origin=profile.origin,
                    gender=profile.gender,
                    details=submitted_details,
                    stat_fields=profile.stat_fields,
                    aliases=profile.aliases,
                    knowledge_graph_fields=profile.knowledge_graph_fields,
                    source_locations=profile.source_locations,
                    auto_generated_sections=auto_generated_sections,
                    updated_sections=updated_sections,
                    original_backstory=original_backstory,
                    original_summary=original_summary,
                )
                if save_requested and needs_original_text_save_choice(updated):
                    st.session_state[f"pending_character_save_{character.name}"] = updated
                else:
                    save_character_update(character, updated)
        if st.session_state.get(f"pending_character_save_{character.name}") is not None:
            render_character_save_choice(character)


def section_label(label: str, profile: CharacterProfile, section: str) -> str:
    generated = {value.lower() for value in profile.auto_generated_sections or []}
    return f"{label} (Generated)" if section.lower() in generated else label


def render_memory_tools(character: Character) -> None:
    with st.expander("Backstory And Memory", expanded=False):
        st.markdown("**Backstory**")
        st.markdown(read_text(character.backstory_path))
        st.markdown("**Memory**")
        st.markdown(read_text(character.memory_path))


def render_character_info(character: Character, model_config=None) -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatlog_path" not in st.session_state:
        st.session_state.chatlog_path = str(start_chatlog(character))

    st.subheader(display_character_name(character))
    render_character_editor(character)
    render_relationship_graph(character)


st.title("Roleplaying Character Creator")
st.caption("Create Character Sheets And Explore Relationship Graphs From Local Lore.")

render_lore_import_tools()

characters_tab, places_tab, session_notes_tab = st.tabs(
    ["Characters", "Places", "Session Notes"],
    default=st.session_state.get("main_navigation_tab", "Characters"),
    key="main_navigation_tab",
)

with characters_tab:
    render_character_panel()
    active_character = get_active_character()
    if active_character is None:
        st.info("Create Or Open A Character To Edit Its Sheet.")

with places_tab:
    render_place_panel()

with session_notes_tab:
    render_session_notes()

render_combined_character_graph()
