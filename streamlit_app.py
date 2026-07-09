import requests
import streamlit as st

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
    append_chatlog,
    create_character,
    default_details,
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


def render_relationship_graph(character: Character) -> None:
    with st.expander("Character Attribute Graph", expanded=False):
        graph = None
        try:
            graph = load_graph(character.graph_path)
        except (OSError, ValueError) as exc:
            st.warning(f"Could not load relationship graph: {exc}")

        toolbar_cols = st.columns([1, 3])
        if toolbar_cols[0].button("Regenerate", icon=":material/sync:", key=f"regen_graph_{character.name}"):
            try:
                regenerate_character_graph(character)
            except (OSError, ValueError) as exc:
                st.error(f"Could not regenerate graph: {exc}")
            else:
                st.success("Relationship graph regenerated.")
                st.rerun()

        if graph is None:
            toolbar_cols[1].caption("No graph JSON found yet. Regenerate it from the current backstory.")
            return

        evidence = evidence_rows(graph)

        if not evidence:
            st.info("No character graph attributes were extracted from this backstory.")
            return

        attributes_tab = st.tabs(["Attributes"])[0]
        with attributes_tab:
            st.table(evidence, hide_index=True, width="stretch")

def render_character_creator(key_prefix: str = "new_character") -> None:
    with st.form(key_prefix, clear_on_submit=True):
        name = st.text_input("Name", placeholder="Mara Voss", key=f"{key_prefix}_name")
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
        with st.expander("Optional metadata", expanded=False):
            detail_cols = st.columns(3)
            drives = detail_cols[0].text_area(
                "Drives",
                placeholder="Restore family name\nProtect old friends",
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
                "Character details",
                placeholder="Add any freeform character sheet fields here.",
                height=120,
                key=f"{key_prefix}_details",
            )

        submitted = st.form_submit_button("Create character", icon=":material/person_add:")
        if submitted:
            if not all([name.strip(), race.strip(), character_class.strip(), backstory.strip()]):
                st.error("Complete name, race, class, and backstory.")
                return
            try:
                profile = CharacterProfile(
                    name=name.strip(),
                    pronouns=pronouns.strip(),
                    level=level.strip(),
                    race=race.strip(),
                    character_class=character_class.strip(),
                    backstory=backstory.strip(),
                    summary=summary.strip(),
                    motivations=[],
                    drives=parse_list_field(drives),
                    alliances=parse_list_field(alliances),
                    enemies=parse_list_field(enemies),
                    details=details.strip(),
                )
                character = create_character(profile)
            except FileExistsError:
                st.error("A character with that name already exists.")
            except ValueError as exc:
                st.error(str(exc))
            else:
                set_active_character(character)
                st.success(f"Created {character.name}.")
                st.rerun()


def render_character_panel() -> None:
    st.subheader("Characters")
    characters = list_characters()
    if characters:
        names = [character.name for character in characters]
        current = st.session_state.get("active_character", names[0])
        selected_character_name = st.selectbox(
            "Existing Characters",
            names,
            index=names.index(current) if current in names else 0,
            key="main_existing_character",
        )
        selected_character = next(character for character in characters if character.name == selected_character_name)
        if st.button("Open character", icon=":material/chat:", key="main_open_character"):
            set_active_character(selected_character)
            st.rerun()
        if "active_character" not in st.session_state:
            set_active_character(selected_character)
    else:
        st.info("Create your first character to begin.")

    with st.expander("Create character", expanded=not characters):
        render_character_creator("main_new_character")


def render_character_editor(character: Character) -> None:
    profile = read_character_profile(character)
    with st.expander("Edit Character", expanded=False):
        with st.form(f"edit_character_{character.name}"):
            st.text_input("Name", value=profile.name, disabled=True)
            stat_cols = st.columns(2)
            race = stat_cols[0].text_input("Race", value=profile.race)
            character_class = stat_cols[1].text_input("Class", value=profile.character_class)
            backstory = st.text_area("Backstory", value=profile.backstory, height=180)
            summary = st.text_area("Summary", value=profile.summary, height=96)
            with st.expander("Optional metadata", expanded=False):
                optional_cols = st.columns(2)
                level = optional_cols[0].text_input("Level", value=profile.level)
                pronouns = optional_cols[1].text_input("Pronouns", value=profile.pronouns)
                detail_cols = st.columns(3)
                drives = detail_cols[0].text_area("Drives", value=render_list_field(profile.drives), height=96)
                alliances = detail_cols[1].text_area("Alliances", value=render_list_field(profile.alliances), height=96)
                enemies = detail_cols[2].text_area("Enemies", value=render_list_field(profile.enemies), height=96)
                details_value = profile.details or default_details(profile)
                details = st.text_area("Character details", value=details_value, height=120)
            if st.form_submit_button("Save character", icon=":material/save:"):
                updated = CharacterProfile(
                    name=profile.name,
                    pronouns=pronouns.strip(),
                    level=level.strip(),
                    race=race.strip(),
                    character_class=character_class.strip(),
                    backstory=backstory.strip(),
                    summary=summary.strip(),
                    motivations=profile.motivations,
                    drives=parse_list_field(drives),
                    alliances=parse_list_field(alliances),
                    enemies=parse_list_field(enemies),
                    origin=profile.origin,
                    gender=profile.gender,
                    details=details.strip(),
                )
                write_character_profile(character, updated)
                st.success("Character saved.")
                st.rerun()


def render_memory_tools(character: Character) -> None:
    with st.expander("Backstory and memory", expanded=False):
        st.markdown("**Backstory**")
        st.markdown(read_text(character.backstory_path))
        st.markdown("**Memory**")
        st.markdown(read_text(character.memory_path))


def render_character_info(character: Character, model_config=None) -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatlog_path" not in st.session_state:
        st.session_state.chatlog_path = str(start_chatlog(character))

    st.subheader(character.name)
    render_character_editor(character)
    render_relationship_graph(character)

# active_model = render_sidebar()

st.title("Local Huggingface Chatbot")
st.caption("Chat with local characters, backed by Markdown memory and raw text logs.")

render_character_panel()
active_character = get_active_character()
if active_character is None:
    st.info("Create or open a character to edit its sheet.")
else:
    render_character_info(active_character)
