from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
import os
import re

import streamlit as st

from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_attribute_rows,
    clean_evidence_text,
    graph_view_root_nodes,
    compact,
)
from character_graph.extraction import extract_character_graph
from character_graph.graph_view import (
    evidence_rows,
)
from character_graph.ingest import load_backstory
from character_graph.session_entities import derived_lore_entity_relationships
from character_graph.storage import load_graph
from graphviz_rendering import render_knowledge_graph_tabs


from local_chatbot.storage import (
    Character,
    CharacterProfile,
    Place,
    PlaceProfile,
    character_family_name,
    character_first_name,
    create_character,
    create_place_markdown,
    default_details,
    delete_character_profile,
    delete_place_profile,
    list_places,
    list_characters,
    read_place_markdown,
    read_character_profile,
    read_text,
    regenerate_character_graph,
    remove_character_connections,
    write_character_connections,
    write_character_profile,
    write_place_markdown,
)
from local_chatbot.character_rewrites import (
    graph_generated_backstory as build_graph_generated_backstory,
    graph_generated_summary as build_graph_generated_summary,
)
from local_chatbot.rewrite_model import (
    LocalRewriteModelClient,
    LocalRewriteModelError,
    LocalRewriteModelLifecycle,
    load_local_language_model_config,
)
from local_chatbot.session_notes import (
    child_markdown_sections,
    combine_markdown_section,
    hide_markdown_section_heading,
    import_markdown_text,
    delete_session_note,
    insert_markdown_section,
    markdown_sections,
    normalize_session_note_file_headings,
    prepare_markdown_import,
    list_session_notes,
    read_markdown_section,
    read_session_note,
    read_session_note_body,
    read_session_note_date_text,
    read_session_note_title,
    remove_markdown_section,
    removing_markdown_section_removes_file,
    starts_with_searchable_markdown_heading,
    write_lore_document,
    write_markdown_section,
    write_session_note,
)
from local_chatbot.lore_import import (
    BACKUP_KIND_SNAPSHOT,
    backup_lore_files,
    clear_local_lore,
    import_lore_directory,
    list_lore_backups,
    read_lore_backup_date,
    restore_lore_backup,
)
from local_chatbot.paths import (
    CHARACTERS_DIR,
    LORE_DIR,
    PLACES_DIR,
    SESSION_NOTES_DIR,
    TEST_FIXTURES_DIRECTORY,
    WORLD_BUILDING_BACKUP_DIR,
)

ENABLE_CHARACTER_REWRITE = "LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES"
ENABLE_LOCAL_REWRITE_MODEL = "LOCAL_CHATBOT_ENABLE_LOCAL_REWRITE_MODEL"
ALLOW_LOCAL_REWRITE_MODEL_DOWNLOAD = "LOCAL_CHATBOT_ALLOW_MODEL_DOWNLOAD"
ENABLE_ATTRIBUTE_GRAPH_OVERRIDE = "LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE"
DISABLE_LORE_BACKUPS = "LOCAL_CHATBOT_DISABLE_LORE_BACKUPS"
MAIN_NAVIGATION_TABS = ["Characters", "Places", "Session Notes"]
LORE_BACKUP_IMPORT_SOURCE_KEY = "lore_backup_import_source"


def lore_backups_disabled() -> bool:
    return os.environ.get(DISABLE_LORE_BACKUPS, "").strip().lower() in {"1", "true", "yes", "on"}


st.set_page_config(page_title="Character Builder", page_icon=":material/forum:", layout="wide")
if not lore_backups_disabled():
    backup_lore_files()

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


def request_main_navigation_tab(tab_name: str) -> None:
    if tab_name not in MAIN_NAVIGATION_TABS:
        return
    st.session_state["main_navigation_tab_default"] = tab_name
    st.session_state["main_navigation_tab_revision"] = st.session_state.get("main_navigation_tab_revision", 0) + 1


def sync_main_navigation_tab(tab_key: str) -> None:
    selected = st.session_state.get(tab_key)
    if selected in MAIN_NAVIGATION_TABS:
        st.session_state["main_navigation_tab_default"] = selected


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
            label = f"{path.name} H{section.level}: {section.text}"
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
    return os.environ.get(ENABLE_CHARACTER_REWRITE) == "1"


def local_model_rewrites_enabled() -> bool:
    return os.environ.get(ENABLE_LOCAL_REWRITE_MODEL) == "1"


def local_model_downloads_enabled() -> bool:
    return os.environ.get(ALLOW_LOCAL_REWRITE_MODEL_DOWNLOAD) == "1"


def attribute_graph_override_enabled() -> bool:
    return os.environ.get(ENABLE_ATTRIBUTE_GRAPH_OVERRIDE) == "1"

def external_character_import_enabled() -> bool:
    return  False


def parse_list_field(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").replace(";", ",").split(",") if item.strip()]


def render_list_field(values: list[str] | None) -> str:
    return "\n".join(values or [])


def normalized_story_text(value: str) -> str:
    return " ".join(value.split())


def mark_combined_graph_dirty() -> None:
    st.session_state["combined_graph_revision"] = st.session_state.get("combined_graph_revision", 0) + 1


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
    graph = character_graph_or_regenerate(character)
    rewrite_client = local_rewrite_client_or_none()
    if rewrite_client:
        try:
            return build_graph_generated_summary(graph, profile, rewrite_client=rewrite_client)
        except LocalRewriteModelError as exc:
            st.warning(f"Model-backed summary failed; using deterministic graph rewrite. {exc}")
    return build_graph_generated_summary(graph, profile)


def character_graph_or_regenerate(character: Character):
    graph = load_graph(character.graph_path)
    if graph is None:
        regenerate_character_graph(character)
        graph = load_graph(character.graph_path)
    if graph is None:
        raise ValueError("No Character Graph Is Available. Regenerate The Graph First.")
    return graph


def graph_generated_backstory(character: Character, profile: CharacterProfile) -> str:
    graph = character_graph_or_regenerate(character)
    rewrite_client = local_rewrite_client_or_none()
    if rewrite_client:
        try:
            return build_graph_generated_backstory(graph, profile, rewrite_client=rewrite_client)
        except LocalRewriteModelError as exc:
            st.warning(f"Model-backed backstory failed; using deterministic graph rewrite. {exc}")
    return build_graph_generated_backstory(graph, profile)


def local_rewrite_client_or_none() -> LocalRewriteModelClient | None:
    if not local_model_rewrites_enabled():
        return None
    config = load_local_language_model_config(allow_download=local_model_downloads_enabled())
    lifecycle = LocalRewriteModelLifecycle(config)
    if not lifecycle.is_runtime_available():
        st.warning("llama CLI is not installed; using deterministic graph rewrite.")
        return None
    if not lifecycle.is_model_available() and not config.allow_download:
        st.warning("Local rewrite model is not downloaded; using deterministic graph rewrite.")
        return None
    return LocalRewriteModelClient(config=config, status_callback=local_model_status_callback())


def local_model_status_callback():
    status_message = st.empty()
    progress_message = st.empty()

    def update(message: str) -> None:
        download_match = re.search(r"Downloading local rewrite model:\s*(\d+)%", message)
        if download_match:
            percent = max(0, min(100, int(download_match.group(1))))
            status_message.info(f"Downloading local rewrite model: {percent}%")
            progress_message.progress(percent)
            return
        progress_message.empty()
        status_message.info(message)

    return update


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
    snapshots.append(
        {
            "backstory": read_text(character.backstory_path),
            "profile": read_text(character.profile_path) if character.profile_path.exists() else "",
        }
    )
    st.session_state[key] = snapshots[-20:]


def undo_character_changes(character: Character) -> None:
    key = f"character_undo_{character.name}"
    snapshots = st.session_state.get(key, [])
    if not snapshots:
        st.warning("No Character Changes To Undo.")
        return
    previous = snapshots.pop()
    if isinstance(previous, dict):
        character.backstory_path.write_text(previous.get("backstory", "").rstrip() + "\n", encoding="utf-8")
        profile_text = previous.get("profile", "")
        if profile_text:
            character.profile_path.parent.mkdir(parents=True, exist_ok=True)
            character.profile_path.write_text(profile_text.rstrip() + "\n", encoding="utf-8")
        else:
            character.profile_path.unlink(missing_ok=True)
    else:
        character.backstory_path.write_text(str(previous).rstrip() + "\n", encoding="utf-8")
    st.session_state[key] = snapshots
    regenerate_character_graph(character)
    mark_combined_graph_dirty()
    st.session_state[f"character_status_{character.name}"] = "Character Changes Undone."
    st.rerun()


def save_character_update(character: Character, updated: CharacterProfile) -> None:
    push_character_undo(character)
    write_character_profile(character, updated)
    mark_combined_graph_dirty()
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
    sync_place_editor_values(place, previous.rstrip())
    bump_place_editor_revision(place)
    mark_combined_graph_dirty()
    st.session_state[f"place_status_{place.name}"] = "Place Changes Undone."
    st.rerun()


def bump_place_editor_revision(place: Place) -> None:
    st.session_state[f"place_editor_revision_{place.name}"] = st.session_state.get(
        f"place_editor_revision_{place.name}",
        0,
    ) + 1


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
    mark_combined_graph_dirty()
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
                mark_combined_graph_dirty()
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
            mark_combined_graph_dirty()
            st.success("Attribute Graph Override Saved.")
            st.rerun()
        if clear_override:
            remove_character_connections(character)
            mark_combined_graph_dirty()
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


def render_combined_character_graph(active_main_tab: str = "Characters") -> None:
    characters = list_characters()
    places = list_places()
    graphs = load_lore_graphs()

    place_sources = [
        (lore_source_document_id(place.path), display_place_name(place), str(place.path), "source_document")
        for place in places
    ]
    source_label = os.environ.get("LOCAL_CHATBOT_KNOWLEDGE_GRAPH_SOURCE_LABEL", "Local Lore")
    with (st.expander(f"Combined Knowledge Graph", expanded=False)):
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
                mark_combined_graph_dirty()
                st.success("All Lore Graphs Regenerated.")
                st.rerun()

        if not graphs and not place_sources:
            st.info("Add Character Or Place Lore To See The Combined Graph.")
            return
        combined = build_combined_character_graph(
            graphs,
            place_sources,
            place_lore_relationships(places) + derived_lore_relationships(characters, places, graphs),
        )
        character_nodes = combined_main_tab_nodes(combined, characters, places)
        graph_revision = st.session_state.get("combined_graph_revision", 0)
        main_character_ids = {node.id for node in character_nodes if node.node_type == "character"}
        main_place_ids = {node.id for node in character_nodes if node.node_type == "place"}
        character_sheet_graphs = character_sheet_lore_graphs(graphs)
        render_knowledge_graph_tabs(
            combined=combined,
            character_sheet_combined=build_combined_character_graph(character_sheet_graphs),
            character_sheet_detail_rows=combined_attribute_rows(character_sheet_graphs),
            character_nodes=character_nodes,
            main_character_ids=main_character_ids,
            main_place_ids=main_place_ids,
            graph_revision=graph_revision,
            label_font_color=graph_edge_label_font_color(),
            active_main_tab=active_main_tab,
        )


def load_lore_graphs():
    graphs = []
    for path in lore_markdown_files():
        try:
            document = load_backstory(path, character_id=compact(path.stem))
            primary_name = session_note_source_name(path) if path_is_session_note(path) else None
            graphs.append(extract_character_graph(document, primary_name=primary_name))
        except (OSError, ValueError):
            continue
    return graphs


def character_sheet_lore_graphs(graphs):
    return [
        graph
        for graph in graphs
        if is_character_lore_path(Path(graph.primary_character.source_file))
    ]


def combined_main_tab_nodes(combined, characters, places):
    return graph_view_root_nodes(
        combined,
        [display_character_name(character) for character in characters],
        [display_place_name(place) for place in places],
    )


def derived_lore_relationships(characters, places, graphs) -> list[dict[str, str]]:
    graph_sources = {
        Path(graph.primary_character.source_file).resolve(): graph
        for graph in graphs
    }
    known_character_names = [display_character_name(character) for character in characters]
    known_place_names = known_knowledge_graph_place_names(places)
    relationships: list[dict[str, str]] = []
    for path in lore_markdown_files():
        if is_character_lore_path(path):
            continue
        graph = graph_sources.get(path.resolve())
        source_id = graph.primary_character.id if graph and not is_place_lore_path(path) else lore_source_document_id(path)
        source_name = combined_lore_source_name(path, graph)
        source_type = "source_document" if is_place_lore_path(path) else "character"
        try:
            text = read_text(path)
        except OSError:
            continue
        relationships.extend(
            derived_lore_entity_relationships(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                source_file=str(path),
                text=text,
                known_character_names=known_character_names,
                known_place_names=known_place_names,
            )
        )
    return relationships


def combined_lore_source_name(path: Path, graph) -> str:
    if graph is not None and path_is_session_note(path):
        return session_note_source_name(path)
    if graph is not None:
        return graph.primary_character.name
    return path.stem.replace("_", " ")


def known_knowledge_graph_place_names(places) -> list[str]:
    names: list[str] = []
    for place in places:
        for name in place_name_aliases(place):
            if name and name not in names:
                names.append(name)
    return names


def place_name_aliases(place) -> list[str]:
    display_name = display_place_name(place)
    aliases = [display_name, place.path.stem.replace("_", " ")]
    title = markdown_document_title(read_text(place.path))
    if title:
        aliases.append(title)
    for name in list(aliases):
        stripped = source_title_without_lore_suffix(name)
        if stripped and stripped not in aliases:
            aliases.append(stripped)
    return aliases


def source_title_without_lore_suffix(name: str) -> str:
    return re.sub(r"\s+Lore$", "", name.strip(), flags=re.IGNORECASE)


def lore_source_document_id(path: Path) -> str:
    return f"source_document__{compact(path.stem)}"


def is_character_lore_path(path: Path) -> bool:
    return "character_sheets" in path.parts


def is_place_lore_path(path: Path) -> bool:
    return "places" in path.parts


def path_is_session_note(path: Path) -> bool:
    normalized = str(path).replace("\\", "/").lower()
    try:
        path.resolve().relative_to(SESSION_NOTES_DIR.resolve())
        return True
    except ValueError:
        return "/session_notes/" in normalized or compact(path.stem) in {"sessionnote", "sessionnotes"}


def session_note_source_name(path: Path) -> str:
    name = path.stem.replace("_", " ")
    return name if name else "Session Notes"


def lore_markdown_files():
    paths: dict[Path, Path] = {}
    for directory in unique_lore_scan_dirs():
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            if (
                "TEMPLATE" not in path.name.upper()
                and not path.name.startswith(".")
                and not should_skip_lore_scan_path(path)
            ):
                paths[path.resolve()] = path
    return [paths[key] for key in sorted(paths, key=lambda item: str(item))]


def unique_lore_scan_dirs() -> list[Path]:
    directories: list[Path] = []
    for directory in [LORE_DIR, CHARACTERS_DIR, PLACES_DIR, SESSION_NOTES_DIR]:
        if directory not in directories:
            directories.append(directory)
    return directories


def should_skip_lore_scan_path(path: Path) -> bool:
    if not lore_backups_disabled():
        return False
    return any(part.lower() == "backup" for part in path.parts)


def place_lore_relationships(places) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    known_place_keys = {compact(place.name) for place in places}
    for place in places:
        text = read_text(place.path)
        source_id = lore_source_document_id(place.path)
        for line in place_connections_lines(text):
            if ":" in line:
                name, relationship = line.split(":", 1)
            else:
                name, relationship = line, "reference"
            target_name = name.strip().lstrip("-").strip()
            if not target_name:
                continue
            target_type = "place" if compact(target_name) in known_place_keys or looks_like_place_connection(target_name) else "character"
            relationships.append(
                {
                    "source_id": source_id,
                    "source_name": place.name,
                    "source_type": "source_document",
                    "source_file": str(place.path),
                    "target_id": compact(target_name),
                    "target_name": target_name,
                    "target_type": target_type,
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


def looks_like_place_connection(name: str) -> bool:
    lowered = name.strip().lower()
    place_suffixes = {
        "academy",
        "bastion",
        "cavern",
        "city",
        "college",
        "coast",
        "court",
        "fortress",
        "forest",
        "guild",
        "hall",
        "harbor",
        "keep",
        "kingdom",
        "library",
        "mage college",
        "monastery",
        "school",
        "sea",
        "shore",
        "temple",
        "tower",
        "tavern",
        "university",
        "village",
    }
    return any(lowered == suffix or lowered.endswith(f" {suffix}") for suffix in place_suffixes)


def connection_rows_for_character(combined, character_id: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for edge in combined.edges:
        source = combined.characters.get(edge.source)
        target = combined.characters.get(edge.target)
        if not source or not target:
            continue
        if compact(source.name) == character_id:
            for evidence in edge.evidence or [""]:
                rows.append(
                    {
                        "Source": "Character Sheet",
                        "Relationship": edge.relationship_label,
                        "Name": target.name,
                        "Evidence": clean_evidence_text(evidence),
                    }
                )
        elif compact(target.name) == character_id:
            for evidence in edge.evidence or [""]:
                rows.append(
                    {
                        "Source": "Place" if source.node_type == "place" else "Character Sheet",
                        "Relationship": edge.relationship_label,
                        "Name": source.name,
                        "Evidence": clean_evidence_text(evidence),
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
        name = st.text_input("Name", value=draft_profile.name, placeholder="Ms. Glorious", key=f"{key_prefix}_name")
        name_cols = st.columns(2)
        first_name = name_cols[0].text_input(
            "First Name",
            value=draft_profile.first_name,
            placeholder="Glorious",
            key=f"{key_prefix}_first_name",
        )
        family_name = name_cols[1].text_input(
            "Family Name",
            value=draft_profile.family_name,
            placeholder="Maximus",
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
            placeholder="A careful scholar who keeps notes about every strange place they visit...",
            height=160,
            key=f"{key_prefix}_backstory",
        )
        summary = st.text_area(
            "Summary",
            value=draft_profile.summary,
            placeholder="Ms. Glorious specializes in the study of the dark arts.",
            height=96,
            key=f"{key_prefix}_summary",
        )
        with st.expander("Optional Metadata", expanded=character_optional_metadata_present(draft_profile)):
            detail_cols = st.columns(3)
            drives = detail_cols[0].text_area(
                "Drives",
                value=render_list_field(draft_profile.drives),
                placeholder="Protect A Shared Home\nFollow A Longstanding Promise",
                height=96,
                key=f"{key_prefix}_drives",
            )
            alliances = detail_cols[1].text_area(
                "Alliances",
                value=render_list_field(draft_profile.alliances),
                placeholder="The Harbor Circle",
                height=96,
                key=f"{key_prefix}_alliances",
            )
            enemies = detail_cols[2].text_area(
                "Enemies",
                value=render_list_field(draft_profile.enemies),
                placeholder="The Hollow Council\nAlder Grin",
                height=96,
                key=f"{key_prefix}_enemies",
            )
            details = st.text_area(
                "Character Details",
                value=draft_profile.details,
                placeholder="Add any extra notes, traits, or background details here.",
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
                clear_character_creator_state(key_prefix)
                set_active_character(character)
                mark_combined_graph_dirty()
                st.success(f"Created {character.name}.")
                st.rerun()


def graph_edge_label_font_color() -> str:
    return "#cbd5e1"


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
        st.caption("Describe the place with a name and a short overview. You can add more detail later if you want to expand the lore.")
        name = st.text_input("Name", value=draft_profile.name, placeholder="Lantern House", key=f"{key_prefix}_name")
        markdown = st.text_area(
            "New Place Markdown",
            value=draft_place_markdown(draft_profile),
            placeholder="# Lantern House\n\nA welcoming inn where travelers share stories and quiet conversations.",
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
                clear_place_creator_state(key_prefix)
                set_active_place(place)
                request_main_navigation_tab("Places")
                mark_combined_graph_dirty()
                st.session_state[f"place_status_{place.name}"] = "Place Saved."
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
    place_panel_status = st.session_state.get("place_panel_status", "")
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
    place_message = st.session_state.get(f"place_status_{place.name}", "")
    if place_message:
        st.success(place_message)
    with st.expander("Edit Place", expanded=bool(place_message)):
        with st.form(f"edit_place_{place.name}"):
            original_title = markdown_document_title(markdown) or display_place_name(place)
            editor_revision = st.session_state.get(f"place_editor_revision_{place.name}", 0)
            if f"place_editor_body_{place.name}" not in st.session_state:
                sync_place_editor_values(place, markdown)
            title = st.text_input(
                "Name",
                value=original_title,
                key=f"place_title_{place.name}_{editor_revision}",
            )
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
                st.session_state.pop(f"place_status_{place.name}", None)
                st.session_state.pop("active_place", None)
                mark_combined_graph_dirty()
                st.session_state["place_panel_status"] = "Place Deleted."
                st.rerun()
            if save_requested:
                body = st.session_state.get(f"place_markdown_{place.name}_{editor_revision}", body)
                title = st.session_state.get(f"place_title_{place.name}_{editor_revision}", title)
                if not body.strip():
                    st.error("Add Place Markdown Before Saving.")
                    return
                push_place_undo(place)
                write_place_markdown(place, apply_place_title_update(markdown, body, title))
                sync_place_editor_values(place, read_place_markdown(place).strip())
                bump_place_editor_revision(place)
                mark_combined_graph_dirty()
                st.session_state[f"place_status_{place.name}"] = "Place Saved."
                st.rerun()


def sync_place_editor_values(place: Place, markdown: str) -> None:
    st.session_state[f"place_editor_body_{place.name}"] = markdown
    st.session_state[f"place_editor_title_{place.name}"] = markdown_document_title(markdown) or display_place_name(place)


def apply_place_title_update(original_markdown: str, updated_markdown: str, title: str) -> str:
    cleaned_title = title.strip()
    if not cleaned_title:
        return updated_markdown
    original_title = markdown_document_title(original_markdown)
    updated_title = markdown_document_title(updated_markdown)
    if updated_title and updated_title != original_title:
        return updated_markdown
    if updated_title == cleaned_title:
        return updated_markdown
    if updated_title:
        return replace_first_markdown_title(updated_markdown, cleaned_title)
    return f"# {cleaned_title}\n\n{updated_markdown.strip()}"


def replace_first_markdown_title(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("# "):
            lines[index] = f"# {title}"
            return "\n".join(lines)
    return markdown


def render_lore_import_tools() -> None:
    import_status = st.session_state.pop("lore_import_status", "")
    if import_status:
        st.success(import_status)

    with st.expander("Lore Import", expanded=False):
        backup_date = read_lore_backup_date()
        st.text_input(
            "Last Backup",
            value=format_backup_date(backup_date) if backup_date else "No Backup Created",
            disabled=True,
            key="last_lore_backup_date",
        )
        st.subheader("Bulk Lore Directory")
        source_dir = st.text_input(
            "Source Directory",
            value=str(TEST_FIXTURES_DIRECTORY),
            help="Choose a directory under world_building/import that contains character_sheets, places, and session_notes folders.",
            key="lore_directory_import_source",
        )
        overwrite_existing = st.checkbox(
            "Overwrite Existing Files",
            value=True,
            key="lore_directory_import_overwrite",
        )
        action_cols = st.columns(4)
        if action_cols[0].button("Import Testing Lore", icon=":material/folder_copy:", key="import_testing_lore"):
            try:
                summary = import_lore_directory(Path(source_dir), overwrite=overwrite_existing)
            except FileNotFoundError:
                st.error("Choose An Existing Lore Directory Before Importing.")
                return
            st.session_state["lore_import_status"] = (
                f"Imported {summary.total} Lore File{'s' if summary.total != 1 else ''} "
                f"({summary.characters} Characters, {summary.places} Places, {summary.session_notes} Session Notes)."
            )
            mark_combined_graph_dirty()
            st.rerun()
        if action_cols[1].button("Create Lore Backup", icon=":material/backup:", key="create_lore_backup"):
            summary = backup_lore_files(snapshot=True, backup_kind=BACKUP_KIND_SNAPSHOT)
            st.session_state["lore_import_status"] = (
                f"Created Backup For {summary.files} File{'s' if summary.files != 1 else ''}."
            )
            st.rerun()
        if action_cols[2].button("Import Lore Backup", icon=":material/restore_page:", key="import_lore_backup"):
            render_lore_backup_restore_dialog(overwrite_existing)
        if action_cols[3].button("Bulk Lore Removal", icon=":material/delete_forever:", key="bulk_lore_removal"):
            render_bulk_lore_removal_warning()


def format_backup_date(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


@st.dialog("Import Lore Backup")
def render_lore_backup_restore_dialog(overwrite_existing: bool) -> None:
    backup_options = list_lore_backups(WORLD_BUILDING_BACKUP_DIR)
    if not backup_options:
        st.warning("No Lore Backups Are Available.")
        if st.button("Close", icon=":material/close:", width="stretch"):
            st.rerun()
        return

    selected_backup = st.selectbox(
        "Backup",
        backup_options,
        format_func=lambda option: option.label,
        key="selected_lore_backup",
    )
    st.session_state[LORE_BACKUP_IMPORT_SOURCE_KEY] = str(selected_backup.path)
    action_cols = st.columns(2)
    if action_cols[0].button("Restore Selected Backup", icon=":material/restore_page:", width="stretch"):
        backup_source = Path(st.session_state[LORE_BACKUP_IMPORT_SOURCE_KEY])
        summary = restore_lore_backup(backup_source)
        st.session_state["lore_import_status"] = (
            f"Restored {summary.total} Backup File{'s' if summary.total != 1 else ''} "
            f"({summary.characters} Characters, {summary.places} Places, "
            f"{summary.session_notes} Session Notes, {summary.metadata} Metadata Files)."
        )
        mark_combined_graph_dirty()
        st.rerun()
    if action_cols[1].button("Cancel", icon=":material/close:", width="stretch"):
        st.rerun()


@st.dialog("Bulk Lore Removal")
def render_bulk_lore_removal_warning() -> None:
    st.warning(
        "This operation is destructive. Do you want to delete all local characters, places, and notes?"
    )
    st.write("This will clean the configured lore directory and generated lore data.")
    action_cols = st.columns(2)
    if action_cols[0].button("Yes, Delete Local Lore", icon=":material/delete_forever:", width="stretch"):
        backup_lore_files(snapshot=True)
        summary = clear_local_lore()
        st.session_state["lore_import_status"] = (
            f"Deleted {summary.total} Local Lore File{'s' if summary.total != 1 else ''} "
            f"({summary.characters} Characters, {summary.places} Places, {summary.session_notes} Session Notes)."
        )
        mark_combined_graph_dirty()
        for key in ("active_character", "active_place", "active_session_note"):
            st.session_state.pop(key, None)
        st.rerun()
    if action_cols[1].button("Cancel", icon=":material/close:", width="stretch"):
        st.rerun()


@st.dialog("Delete Session Note File?")
def render_delete_session_note_file_warning(path: Path, section_key: str) -> None:
    st.warning("This is the last section in this file. Do you want to delete the full session note file?")
    st.write(f"`{path.name}` will be removed.")
    action_cols = st.columns(2)
    if action_cols[0].button(
        "Delete Session Note File",
        icon=":material/delete_forever:",
        key=f"confirm_delete_last_section_file_{path.name}_{section_key}",
        width="stretch",
        ):
        push_session_notes_undo()
        delete_session_note(path)
        mark_combined_graph_dirty()
        st.session_state.pop(f"session_note_editor_revision_{path.name}", None)
        for key in (
            "active_session_note",
            "active_session_note_section",
            "active_session_note_editor",
            "pending_delete_session_section",
            "pending_delete_session_note_file",
        ):
            st.session_state.pop(key, None)
        st.session_state["session_notes_status"] = "Session Note Deleted."
        st.rerun()
    if action_cols[1].button(
        "Cancel",
        icon=":material/close:",
        key=f"cancel_delete_last_section_file_{path.name}_{section_key}",
        width="stretch",
    ):
        st.session_state.pop("pending_delete_session_note_file", None)
        st.session_state.pop("pending_delete_session_section", None)
        st.rerun()


@st.dialog("Select Searchable Headings")
def render_session_import_heading_dialog(
    notes: str,
    source_name: str,
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
            disabled=heading.kind == "structure",
            key=f"import_heading_{heading.key}",
        ):
            selected_heading_keys.add(heading.key)
    action_cols = st.columns(2)
    if action_cols[0].button("Save Selected Headings", icon=":material/check:", width="stretch"):
        request_main_navigation_tab("Session Notes")
        push_session_notes_undo()
        saved = import_markdown_text(
            notes,
            title=import_title,
            selected_heading_keys=selected_heading_keys,
            save_as_single_file=True,
        )
        st.session_state["session_notes_saved_count"] = len(saved)
        if saved:
            set_active_session_note(saved[0].path)
            set_active_session_note_section()
        mark_combined_graph_dirty()
        st.session_state["clear_session_notes_draft"] = True
        st.rerun()
    if action_cols[1].button("Cancel", icon=":material/close:", width="stretch"):
        request_main_navigation_tab("Session Notes")
        st.rerun()



def import_session_note():
    uploaded_file_state = st.session_state.get("markdown_import")
    import_expanded = st.session_state.get("session_notes_import_expanded", False) or uploaded_file_state is not None
    with st.expander(
            "Import Session Note",
            expanded=import_expanded,
    ):
        if st.session_state.pop("clear_session_notes_import", False):
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
        if st.button("Upload Session Note", icon=":material/upload_file:", key="upload_session_notes"):
            st.session_state["session_notes_import_expanded"] = True
            source_name = title.strip() or (uploaded_notes.name if uploaded_notes is not None else "")
            if uploaded_notes is None:
                st.error("Choose A Markdown Or Text File Before Uploading.")
                return
            try:
                notes = uploaded_notes.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                st.error("Import File Must Be UTF-8 Text.")
                return
            if not notes.strip():
                st.error("Import File Must Include Session Notes.")
                return
            request_main_navigation_tab("Session Notes")
            render_session_import_heading_dialog(
                notes,
                source_name,
            )
            return

def render_session_notes() -> None:
    st.title("Session Notes")
    saved_count = st.session_state.pop("session_notes_saved_count", 0)
    if saved_count:
        st.success(f"Saved {saved_count} Session Note File{'s' if saved_count != 1 else ''}.")
    session_notes_status = st.session_state.get("session_notes_status", "")
    if session_notes_status:
        st.success(session_notes_status)
    session_notes_error = st.session_state.pop("session_notes_error", "")
    if session_notes_error:
        st.error(session_notes_error)
    show_dates = True

    note_files = list_session_notes()
    if note_files:
        if any(normalize_session_note_file_headings(path) for path in note_files):
            note_files = list_session_notes()
        note_files = sorted(note_files, key=lambda path: path.name.casefold())
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


def render_session_note_editor(path, show_dates: bool = False, section_key: str = "") -> None:
    note_label = display_session_note_name(path, show_dates=False)
    note_date = read_session_note_date_text(path)
    note_title = read_session_note_title(path) if note_date else ""
    note_body = read_session_note_body(path) if note_date else read_session_note(path).strip()
    sections = markdown_sections(read_session_note(path))
    selected_section = next((section for section in sections if section.key == section_key), None)
    display_body = read_markdown_section(path, section_key) if section_key else note_body
    editor_state_key = f"{path.name}:{section_key or 'full'}"
    editor_is_open = not selected_section or st.session_state.get("active_session_note_editor") == editor_state_key
    is_first_title_section = bool(selected_section and selected_section.level == 1 and selected_section.start_line == 0)
    if markdown_document_title(note_body) != note_label:
        st.subheader(note_label)
    if selected_section:
        top_action_cols = st.columns(3)
        if selected_section.level == 1:
            if top_action_cols[0].button(
                "Hide Heading",
                icon=":material/visibility_off:",
                key=f"top_hide_heading_{path.name}_{section_key}",
            ):
                st.session_state["pending_hide_session_heading"] = {"path": path.name, "section": section_key}
        elif not is_first_title_section and top_action_cols[0].button(
            "Add Previous Section",
            icon=":material/vertical_align_top:",
            key=f"add_previous_section_{path.name}_{section_key}",
        ):
            push_session_notes_undo()
            _note, new_section_key = insert_markdown_section(path, section_key, "previous")
            set_active_session_note(path)
            set_active_session_note_section(new_section_key)
            st.session_state["active_session_note_editor"] = f"{path.name}:{new_section_key or 'full'}"
            st.session_state["session_notes_status"] = "Previous Section Added."
            st.rerun()
        if not is_first_title_section and top_action_cols[1].button(
            "Combine Section",
            icon=":material/call_merge:",
            key=f"combine_section_{path.name}_{section_key}",
        ):
            push_session_notes_undo()
            _note, parent_section_key = combine_markdown_section(path, section_key)
            set_active_session_note(path)
            set_active_session_note_section(parent_section_key)
            st.session_state["session_notes_status"] = "Section Combined."
            st.rerun()
        if top_action_cols[2].button(
            "Add Next Section",
            icon=":material/vertical_align_bottom:",
            key=f"top_add_next_section_{path.name}_{section_key}",
        ):
            push_session_notes_undo()
            _note, new_section_key = insert_markdown_section(path, section_key, "next")
            set_active_session_note(path)
            set_active_session_note_section(new_section_key)
            st.session_state["active_session_note_editor"] = f"{path.name}:{new_section_key or 'full'}"
            st.session_state["session_notes_status"] = "Next Section Added."
            st.rerun()
        pending_hide = st.session_state.get("pending_hide_session_heading", {})
        if pending_hide.get("path") == path.name and pending_hide.get("section") == section_key:
            promoted_section = next(iter(child_markdown_sections(read_session_note(path), section_key)), None)
            st.warning(f'Are you sure you want to hide "{selected_section.text}" heading')
            if promoted_section:
                st.write(
                    f'Hiding this heading will promote "{promoted_section.text}" heading top level heading for this document'
                )
            else:
                st.write("Hiding this heading will leave this document without a top level heading.")
            confirm_cols = st.columns(2)
            if confirm_cols[0].button(
                "Hide Heading",
                icon=":material/visibility_off:",
                key=f"confirm_hide_heading_{path.name}_{section_key}",
            ):
                push_session_notes_undo()
                hide_markdown_section_heading(path, section_key)
                set_active_session_note(path)
                set_active_session_note_section()
                st.session_state.pop("active_session_note_editor", None)
                st.session_state.pop("pending_hide_session_heading", None)
                mark_combined_graph_dirty()
                st.session_state["session_notes_status"] = "Heading Hidden."
                st.rerun()
            if confirm_cols[1].button(
                "Cancel",
                icon=":material/close:",
                key=f"cancel_hide_heading_{path.name}_{section_key}",
            ):
                st.session_state.pop("pending_hide_session_heading", None)
                st.rerun()
    if display_body:
        st.markdown(display_body)
    if selected_section:
        bottom_action_cols = st.columns(3)
        if bottom_action_cols[0].button(
            "Edit Section",
            icon=":material/edit:",
            key=f"edit_section_{path.name}_{section_key}",
        ):
            st.session_state["active_session_note_editor"] = editor_state_key
            st.rerun()
        if bottom_action_cols[1].button(
            "Add Next Section",
            icon=":material/vertical_align_bottom:",
            key=f"add_next_section_{path.name}_{section_key}",
        ):
            push_session_notes_undo()
            _note, new_section_key = insert_markdown_section(path, section_key, "next")
            set_active_session_note(path)
            set_active_session_note_section(new_section_key)
            st.session_state["active_session_note_editor"] = f"{path.name}:{new_section_key or 'full'}"
            mark_combined_graph_dirty()
            st.session_state["session_notes_status"] = "Next Section Added."
            st.rerun()
        if selected_section.level != 1 and bottom_action_cols[2].button(
            "Remove Section",
            icon=":material/delete:",
            key=f"remove_section_{path.name}_{section_key}",
        ):
            pending_key = (
                "pending_delete_session_note_file"
                if removing_markdown_section_removes_file(read_session_note(path), section_key)
                else "pending_delete_session_section"
            )
            st.session_state[pending_key] = {"path": path.name, "section": section_key}
        pending_file_delete = st.session_state.get("pending_delete_session_note_file", {})
        if pending_file_delete.get("path") == path.name and pending_file_delete.get("section") == section_key:
            render_delete_session_note_file_warning(path, section_key)
        pending_delete = st.session_state.get("pending_delete_session_section", {})
        if pending_delete.get("path") == path.name and pending_delete.get("section") == section_key:
            st.warning("Are you sure you would like to delete this section and all sub sections?")
            child_sections = child_markdown_sections(read_session_note(path), section_key)
            if child_sections:
                st.write("Subsections that will be deleted:")
                for child in child_sections:
                    st.write(f"- H{child.level}: {child.text}")

            confirm_cols = st.columns(2)
            if confirm_cols[0].button(
                "Delete Section",
                icon=":material/delete_forever:",
                key=f"confirm_remove_section_{path.name}_{section_key}",
            ):
                push_session_notes_undo()
                remove_markdown_section(path, section_key)
                set_active_session_note(path)
                set_active_session_note_section()
                st.session_state.pop("active_session_note_editor", None)
                st.session_state.pop("pending_delete_session_section", None)
                mark_combined_graph_dirty()
                st.session_state["session_notes_status"] = "Section Removed."
                st.rerun()
            if confirm_cols[1].button(
                "Cancel",
                icon=":material/close:",
                key=f"cancel_remove_section_{path.name}_{section_key}",
            ):
                st.session_state.pop("pending_delete_session_section", None)
                st.rerun()
    if editor_is_open:
        editor_revision = st.session_state.get(f"session_note_editor_revision_{path.name}", 0)
        section_token = section_key.replace(":", "_") if section_key else "full"
        with st.form(f"edit_session_note_{path.name}"):
            if note_date:
                session_date = st.text_input(
                    "Session Date",
                    value=note_date,
                    placeholder="Session date",
                    key=f"session_note_date_{path.name}_{editor_revision}",
                )
                title = st.text_input(
                    "Title",
                    value=note_title,
                    placeholder="Optional session heading",
                    key=f"session_note_title_{path.name}_{editor_revision}",
                )
            body = st.text_area(
                "Session Note",
                value=display_body,
                height=220,
                key=f"session_note_body_{path.name}_{section_token}_{editor_revision}",
            )
            action_cols = st.columns(3)
            save_requested = action_cols[0].form_submit_button("Save Session Note", icon=":material/save:")
            delete_requested = action_cols[1].form_submit_button(
                "Hide Heading"
                if selected_section and selected_section.level == 1
                else "Delete Section"
                if section_key
                else "Delete Session Note",
                icon=":material/visibility_off:" if selected_section and selected_section.level == 1 else ":material/delete_forever:",
            )
            undo_requested = action_cols[2].form_submit_button("Undo Changes", icon=":material/undo:")
            if undo_requested:
                undo_session_notes_changes()
            if delete_requested:
                if section_key:
                    if selected_section and selected_section.level == 1:
                        st.session_state["pending_hide_session_heading"] = {"path": path.name, "section": section_key}
                    elif removing_markdown_section_removes_file(read_session_note(path), section_key):
                        st.session_state["pending_delete_session_note_file"] = {"path": path.name, "section": section_key}
                    else:
                        push_session_notes_undo()
                        remove_markdown_section(path, section_key)
                        set_active_session_note(path)
                        set_active_session_note_section()
                        mark_combined_graph_dirty()
                        st.session_state["session_notes_status"] = "Section Removed."
                else:
                    push_session_notes_undo()
                    delete_session_note(path)
                    st.session_state.pop(f"session_note_editor_revision_{path.name}", None)
                    st.session_state.pop("active_session_note", None)
                    mark_combined_graph_dirty()
                    st.session_state["session_notes_status"] = "Session Note Deleted."
                st.rerun()
            if save_requested:
                if not body.strip():
                    st.error("Add Markdown Details Before Saving.")
                    return
                if section_key and not starts_with_searchable_markdown_heading(body):
                    st.session_state["session_notes_error"] = "Section Markdown Must Start With An H1, H2, Or H3 Heading."
                    st.session_state["active_session_note_editor"] = editor_state_key
                    st.rerun()
                push_session_notes_undo()
                if note_date:
                    write_session_note(path, body, title, session_date=session_date)
                    st.session_state["session_notes_status"] = "Session Note Saved."
                elif section_key:
                    write_markdown_section(path, section_key, body)
                    st.session_state["session_notes_status"] = "Session Note Saved."
                else:
                    write_lore_document(path, body)
                    st.session_state["session_notes_status"] = "Session Note Saved."
                mark_combined_graph_dirty()
                st.session_state[f"session_note_editor_revision_{path.name}"] = editor_revision + 1
                st.session_state.pop("active_session_note_editor", None)
                st.rerun()


def render_character_panel() -> None:
    st.title("Characters")
    character_panel_status = st.session_state.get("character_panel_status", "")
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

def render_character_editor(character: Character) -> None:
    profile = read_character_profile(character)
    with st.expander("Edit Character", expanded=bool(st.session_state.get(f"character_status_{character.name}", ""))):
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
                backstory_cols[0].caption(section_status_label("Character Backstory", profile))
                backstory = backstory_cols[0].text_area(
                    "Backstory",
                    value=profile.backstory,
                    height=180,
                )
                backstory_cols[1].caption("Original Character Backstory")
                backstory_cols[1].text_area(
                    "Original Backstory",
                    value=profile.original_backstory,
                    height=180,
                    disabled=True,
                )
            else:
                render_section_status("Character Backstory", profile)
                backstory = st.text_area("Backstory", value=profile.backstory, height=180)
            if has_distinct_original(profile.summary, profile.original_summary):
                summary_cols = st.columns(2)
                summary_cols[0].caption(section_status_label("Character Summary", profile))
                summary = summary_cols[0].text_area(
                    "Summary",
                    value=profile.summary,
                    height=96,
                )
                summary_cols[1].caption("Original Character Summary")
                summary_cols[1].text_area(
                    "Original Summary",
                    value=profile.original_summary,
                    height=96,
                    disabled=True,
                )
            else:
                render_section_status("Character Summary", profile)
                summary = st.text_area("Summary", value=profile.summary, height=96)
            with st.expander("Optional Metadata", expanded=character_optional_metadata_present(profile)):
                detail_cols = st.columns(3)
                drives = detail_cols[0].text_area("Drives", value=render_list_field(profile.drives), height=96)
                alliances = detail_cols[1].text_area("Alliances", value=render_list_field(profile.alliances), height=96)
                enemies = detail_cols[2].text_area("Enemies", value=render_list_field(profile.enemies), height=96)
                details_value = profile.details or default_details(profile)
                details = st.text_area("Character Details", value=details_value, height=120)
            action_cols = st.columns(5 if graph_rewrites_enabled() else 3)
            save_requested = action_cols[0].form_submit_button(
                "Save Character",
                icon=":material/save:",
                on_click=request_main_navigation_tab,
                args=("Characters",),
            )
            populate_summary = False
            repopulate_summary = False
            rewrite_backstory = False
            if graph_rewrites_enabled():
                repopulate_summary = action_cols[1].form_submit_button(
                    "Repopulate Summary",
                    icon=":material/sync:",
                    on_click=request_main_navigation_tab,
                    args=("Characters",),
                )
                rewrite_backstory = action_cols[2].form_submit_button(
                    "Rewrite Backstory",
                    icon=":material/edit_note:",
                    on_click=request_main_navigation_tab,
                    args=("Characters",),
                )
                delete_col = action_cols[3]
                undo_col = action_cols[4]
            else:
                delete_col = action_cols[1]
                undo_col = action_cols[2]
            delete_requested = delete_col.form_submit_button(
                "Delete Character",
                icon=":material/delete_forever:",
                on_click=request_main_navigation_tab,
                args=("Characters",),
            )
            undo_requested = undo_col.form_submit_button(
                "Undo Changes",
                icon=":material/undo:",
                on_click=request_main_navigation_tab,
                args=("Characters",),
            )
            if undo_requested:
                undo_character_changes(character)
            if delete_requested:
                delete_character_profile(character)
                st.session_state.pop(f"character_undo_{character.name}", None)
                st.session_state.pop("active_character", None)
                mark_combined_graph_dirty()
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
                        with st.spinner("Preparing graph-backed summary."):
                            next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                        updated_sections = remove_updated_section(updated_sections, "Character Summary")
                    elif repopulate_summary:
                        original_summary = profile.original_summary or profile.summary
                        with st.spinner("Preparing graph-backed summary."):
                            next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                        updated_sections = remove_updated_section(updated_sections, "Character Summary")
                    elif rewrite_backstory:
                        original_backstory = profile.original_backstory or profile.backstory
                        with st.spinner("Preparing graph-backed backstory."):
                            next_backstory = graph_generated_backstory(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Backstory")
                        updated_sections = remove_updated_section(updated_sections, "Character Backstory")
                except (RuntimeError, ValueError) as exc:
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


def section_status_label(section: str, profile: CharacterProfile) -> str:
    generated = {value.lower() for value in profile.auto_generated_sections or []}
    updated = {value.lower() for value in profile.updated_sections or []}
    if section.lower() in updated:
        return f"{section} (Updated)"
    if section.lower() in generated:
        return f"{section} (Generated)"
    return section


def render_section_status(section: str, profile: CharacterProfile) -> None:
    label = section_status_label(section, profile)
    if label != section:
        st.caption(label)


def render_memory_tools(character: Character) -> None:
    with st.expander("Backstory And Memory", expanded=False):
        st.markdown("**Backstory**")
        st.markdown(read_text(character.backstory_path))
        st.markdown("**Memory**")
        st.markdown(read_text(character.memory_path))


def character_optional_metadata_present(profile: CharacterProfile) -> bool:
    return any(
        [
            profile.drives,
            profile.alliances,
            profile.enemies,
            profile.details.strip(),
        ]
    )


def render_character_info(character: Character, model_config=None) -> None:
    st.subheader(display_character_name(character))
    character_message = st.session_state.get(f"character_status_{character.name}", "")
    if character_message:
        st.success(character_message)
    render_character_editor(character)
    render_relationship_graph(character)


st.title("Roleplaying Character Creator")
st.caption("Create Character Sheets And Explore Relationship Graphs From Local Lore.")

render_lore_import_tools()

main_navigation_default = st.session_state.get("main_navigation_tab_default", "Characters")
main_navigation_revision = st.session_state.get("main_navigation_tab_revision", 0)
main_navigation_key = f"main_navigation_tab_{main_navigation_revision}"
characters_tab, places_tab, session_notes_tab = st.tabs(
    MAIN_NAVIGATION_TABS,
    default=main_navigation_default,
    key=main_navigation_key,
    on_change=sync_main_navigation_tab,
    args=(main_navigation_key,),
)

with characters_tab:
    render_character_panel()
    active_character = get_active_character()
    if active_character is None:
        st.info("Create Or Open A Character To Edit Its Sheet.")

with places_tab:
    render_place_panel()

with session_notes_tab:
    import_session_note()
    render_session_notes()

active_main_navigation_tab = st.session_state.get(main_navigation_key, main_navigation_default)
render_combined_character_graph(active_main_navigation_tab)
