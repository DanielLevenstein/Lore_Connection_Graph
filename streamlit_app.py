import requests
import streamlit as st

from character_graph.combined_graph import (
    build_combined_character_graph,
    combined_relationship_dot,
    combined_relationship_rows,
)
from character_graph.graph_view import (
    evidence_rows,
)
from character_graph.prompt_context import build_prompt_context
from character_graph.retrieval import retrieve_relevant_context
from character_graph.storage import load_graph
from language_model_harness import configure_language_model_harness

configure_language_model_harness()

from model_harness.environment import ensure_base_dirs
from local_chatbot.storage import (
    Character,
    CharacterProfile,
    PlaceProfile,
    append_chatlog,
    character_family_name,
    character_first_name,
    create_character,
    create_place,
    default_details,
    list_places,
    list_characters,
    read_character_profile,
    read_text,
    regenerate_character_graph,
    start_chatlog,
    write_character_profile,
)


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


def display_character_name(character: Character) -> str:
    profile = read_character_profile(character)
    return (profile.name or character.name).replace("_", " ")


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


def graph_generated_summary(character: Character, profile: CharacterProfile) -> str:
    graph = load_graph(character.graph_path)
    if graph is None:
        raise ValueError("No Character Graph Is Available. Regenerate The Graph First.")
    primary = graph.characters.get(graph.primary_character.id)
    traits = ", ".join(primary.traits[:3]) if primary and primary.traits else ""
    motivations = ", ".join(primary.motivations[:2]) if primary and primary.motivations else ""
    places = ", ".join(place.name for place in list(graph.places.values())[:2])
    relationships = [
        graph.characters[edge.target].name
        for edge in graph.relationships
        if edge.target in graph.characters and edge.target != graph.primary_character.id
    ][:2]
    pieces = [f"{profile.first_name or character_first_name(profile.name) or profile.name}"]
    descriptor = " is"
    if traits:
        descriptor += f" {traits}"
    role = " ".join(value for value in [profile.race, profile.character_class] if value).strip()
    if role:
        descriptor += f" a {role}"
    pieces.append(descriptor)
    if places:
        pieces.append(f" tied to {places}")
    if relationships:
        pieces.append(f" and connected to {', '.join(relationships)}")
    if motivations:
        pieces.append(f", driven to {motivations}")
    return "".join(pieces).strip() + "."


def graph_generated_backstory(character: Character, profile: CharacterProfile) -> str:
    graph = load_graph(character.graph_path)
    if graph is None:
        raise ValueError("No Character Graph Is Available. Regenerate The Graph First.")
    name = profile.first_name or character_first_name(profile.name) or profile.name
    places = [place.name for place in graph.places.values()]
    relationships = [
        graph.characters[edge.target].name
        for edge in graph.relationships
        if edge.target in graph.characters and edge.target != graph.primary_character.id
    ]
    attributes = [attribute.value for attribute in graph.attributes.values() if attribute.value]
    first = f"{name} carries a history shaped by {', '.join(attributes[:3]) or 'unsettled origins'}."
    second = (
        f"Their path keeps crossing {', '.join(relationships[:3])}."
        if relationships
        else "Their closest relationships are still waiting to be written."
    )
    third = (
        f"Places such as {', '.join(places[:3])} keep pulling the story back into motion."
        if places
        else "The places that matter most to them have not yet been named."
    )
    return "\n\n".join([first, second, third])


def mark_auto_generated(profile: CharacterProfile, section: str) -> list[str]:
    sections = list(profile.auto_generated_sections or [])
    if section not in sections:
        sections.append(section)
    return sections


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

        evidence = evidence_rows(graph)

        if not evidence:
            st.info("No Character Graph Attributes Were Extracted From This Backstory.")
            return

        attributes_tab = st.tabs(["Attributes"])[0]
        with attributes_tab:
            st.table(evidence, hide_index=True, width="stretch")


def render_combined_character_graph() -> None:
    graphs = []
    for character in list_characters():
        try:
            graph = load_graph(character.graph_path)
        except (OSError, ValueError):
            graph = None
        if graph is not None:
            graphs.append(graph)

    with st.expander("Combined Character Graph", expanded=False):
        if len(graphs) < 2:
            st.info("Add At Least Two Character Graphs To See Combined Connections.")
            return
        combined = build_combined_character_graph(graphs)
        rows = combined_relationship_rows(combined)
        if not rows:
            st.info("No Cross-Character Connections Were Found Yet.")
            return
        st.graphviz_chart(combined_relationship_dot(combined), width="stretch")
        st.table(rows, hide_index=True, width="stretch")


def render_character_creator(key_prefix: str = "new_character") -> None:
    with st.form(key_prefix, clear_on_submit=True):
        name = st.text_input("Name", placeholder="Mara Voss", key=f"{key_prefix}_name")
        name_cols = st.columns(2)
        first_name = name_cols[0].text_input("First Name", placeholder="Mara", key=f"{key_prefix}_first_name")
        family_name = name_cols[1].text_input("Family Name", placeholder="Voss", key=f"{key_prefix}_family_name")
        stat_cols = st.columns(4)
        level = stat_cols[0].text_input("Level", placeholder="3", key=f"{key_prefix}_level")
        race = stat_cols[1].text_input("Race", placeholder="Elf", key=f"{key_prefix}_race")
        character_class = stat_cols[2].text_input("Class", placeholder="Wizard", key=f"{key_prefix}_class")
        pronouns = stat_cols[3].text_input("Pronouns", placeholder="she/her", key=f"{key_prefix}_pronouns")

        backstory = st.text_area(
            "Backstory",
            placeholder="A terse archivist from a vanished city who tests every lock twice...",
            height=160,
            key=f"{key_prefix}_backstory",
        )
        summary = st.text_area(
            "Summary",
            placeholder="Mara is a wary archivist whose courage looks like preparation.",
            height=96,
            key=f"{key_prefix}_summary",
        )
        with st.expander("Optional Metadata", expanded=False):
            detail_cols = st.columns(3)
            drives = detail_cols[0].text_area(
                "Drives",
                placeholder="Restore Family Name\nProtect Old Friends",
                height=96,
                key=f"{key_prefix}_drives",
            )
            alliances = detail_cols[1].text_area(
                "Alliances",
                placeholder="Silver Cartographers\nMara Voss",
                height=96,
                key=f"{key_prefix}_alliances",
            )
            enemies = detail_cols[2].text_area(
                "Enemies",
                placeholder="The Ash Court\nTorvak",
                height=96,
                key=f"{key_prefix}_enemies",
            )
            details = st.text_area(
                "Character Details",
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
                set_active_character(character)
                st.success(f"Created {character.name}.")
                st.rerun()


def render_place_creator() -> None:
    st.title("Add Place")
    places = list_places()
    if places:
        st.caption(f"{len(places)} Place Files Available.")
    with st.expander("Create Place", expanded=False):
        with st.form("new_place", clear_on_submit=True):
            name = st.text_input("Name", placeholder="Royal Tittles", key="place_name")
            place_type = st.text_input("Type", placeholder="Tavern", key="place_type")
            summary = st.text_area(
                "Summary",
                placeholder="A dockside tavern where private bargains sound like songs.",
                height=96,
                key="place_summary",
            )
            details = st.text_area("Place Details", height=120, key="place_details")
            connections = st.text_area(
                "Place Connections",
                placeholder="Neal Lovington: Performs Here",
                height=96,
                key="place_connections",
            )
            submitted = st.form_submit_button("Create Place", icon=":material/add_location_alt:")
            if submitted:
                if not all([name.strip(), place_type.strip(), summary.strip()]):
                    st.error("Complete Name, Type, And Summary.")
                    return
                try:
                    create_place(
                        PlaceProfile(
                            name=name.strip(),
                            place_type=place_type.strip(),
                            summary=summary.strip(),
                            details=details.strip(),
                            connections=parse_list_field(connections),
                        )
                    )
                except FileExistsError:
                    st.error("A Place With That Name Already Exists.")
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Created {name.strip()}.")
                    st.rerun()


def render_character_panel() -> None:
    st.subheader("Characters")
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
    # When a character is opened show it here before the create character section.
    if "active_character" in st.session_state:
        character = get_active_character()
        if character:
            render_character_info(character)

    st.title("Add Character")
    with st.expander("Create Character", expanded=not characters):
        render_character_creator("main_new_character")


def render_character_editor(character: Character) -> None:
    profile = read_character_profile(character)
    with st.expander("Edit Character", expanded=False):
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
            backstory = st.text_area("Backstory", value=profile.backstory, height=180)
            summary = st.text_area("Summary", value=profile.summary, height=96)
            with st.expander("Optional Metadata", expanded=False):
                detail_cols = st.columns(3)
                drives = detail_cols[0].text_area("Drives", value=render_list_field(profile.drives), height=96)
                alliances = detail_cols[1].text_area("Alliances", value=render_list_field(profile.alliances), height=96)
                enemies = detail_cols[2].text_area("Enemies", value=render_list_field(profile.enemies), height=96)
                details_value = profile.details or default_details(profile)
                details = st.text_area("Character Details", value=details_value, height=120)
            action_cols = st.columns(4)
            save_requested = action_cols[0].form_submit_button("Save Character", icon=":material/save:")
            populate_summary = action_cols[1].form_submit_button("Populate Summary", icon=":material/auto_awesome:")
            repopulate_summary = action_cols[2].form_submit_button("Repopulate Summary", icon=":material/sync:")
            rewrite_backstory = action_cols[3].form_submit_button("Rewrite Backstory", icon=":material/edit_note:")
            if save_requested or populate_summary or repopulate_summary or rewrite_backstory:
                submitted_details = details.strip()
                if not profile.details.strip() and submitted_details == default_details(profile).strip():
                    submitted_details = ""
                next_summary = summary.strip()
                next_backstory = backstory.strip()
                auto_generated_sections = list(profile.auto_generated_sections or [])
                try:
                    if populate_summary and not next_summary:
                        next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                    elif repopulate_summary:
                        next_summary = graph_generated_summary(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Summary")
                    elif rewrite_backstory:
                        next_backstory = graph_generated_backstory(character, profile)
                        auto_generated_sections = mark_auto_generated(profile, "Character Backstory")
                except ValueError as exc:
                    st.error(str(exc))
                    return
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
                )
                write_character_profile(character, updated)
                st.success("Character Saved.")
                st.rerun()


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

# active_model = render_sidebar()

st.title("Roleplaying Character Creator")
st.caption("Create Character Sheets And Explore Relationship Graphs From Local Lore.")

render_character_panel()
render_place_creator()
active_character = get_active_character()
if active_character is None:
    st.info("Create Or Open A Character To Edit Its Sheet.")
