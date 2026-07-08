import requests
import streamlit as st

from language_model_harness import configure_language_model_harness
from model_sidebar import render_sidebar

configure_language_model_harness()

from model_harness.chat import chat_completion
from model_harness.environment import ensure_base_dirs
from model_harness.server import status
from local_chatbot.storage import (
    Character,
    CharacterProfile,
    append_chatlog,
    create_character,
    list_characters,
    read_character_profile,
    read_text,
    start_chatlog,
    write_character_profile,
)


st.set_page_config(page_title="Local Roleplay Chatbot", page_icon=":material/forum:", layout="wide")
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


def build_character_messages(backstory: str, memory: str, history: list[dict[str, str]], user_text: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are roleplaying as the user's custom character. Stay in character, "
        "use the backstory and memory as ground truth, and keep replies conversational.\n\n"
        f"BACKSTORY:\n{backstory.strip()}\n\n"
        f"MEMORY:\n{memory.strip()}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_text})
    return messages

def render_character_creator(key_prefix: str = "new_character") -> None:
    with st.form(key_prefix, clear_on_submit=True):
        name = st.text_input("Name", placeholder="Mara Voss", key=f"{key_prefix}_name")
        pronouns = st.text_input("Pronouns", placeholder="she/her, he/him, they/them", key=f"{key_prefix}_pronouns")
        stat_cols = st.columns(3)
        level = stat_cols[0].text_input("Level", placeholder="3", key=f"{key_prefix}_level")
        race = stat_cols[1].text_input("Race", placeholder="Elf", key=f"{key_prefix}_race")
        character_class = stat_cols[2].text_input("Class", placeholder="Wizard", key=f"{key_prefix}_class")
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
        submitted = st.form_submit_button("Create character", icon=":material/person_add:")
        if submitted:
            if not all([name.strip(), pronouns.strip(), level.strip(), race.strip(), character_class.strip(), backstory.strip()]):
                st.error("Complete all character fields.")
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
            "Existing characters",
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
    with st.expander("Edit character", expanded=False):
        with st.form(f"edit_character_{character.name}"):
            st.text_input("Name", value=profile.name, disabled=True)
            pronouns = st.text_input("Pronouns", value=profile.pronouns)
            stat_cols = st.columns(3)
            level = stat_cols[0].text_input("Level", value=profile.level)
            race = stat_cols[1].text_input("Race", value=profile.race)
            character_class = stat_cols[2].text_input("Class", value=profile.character_class)
            backstory = st.text_area("Backstory", value=profile.backstory, height=180)
            summary = st.text_area("Summary", value=profile.summary, height=96)
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
                    origin=profile.origin,
                    gender=profile.gender,
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


def render_chat(character: Character, model_config) -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chatlog_path" not in st.session_state:
        st.session_state.chatlog_path = str(start_chatlog(character))

    st.subheader(character.name)
    render_character_editor(character)
    # render_memory_tools(character)
    model_status = status(model_config)
    if model_status.healthy:
        st.success(f"Model server ready at {model_config.api_base_url}")
    elif model_status.running:
        st.info(f"Model server process is running. Waiting for {model_config.api_base_url}.")
        st.chat_input(f"Message {character.name}", disabled=True)
        return
    else:
        st.warning("Model server is not running. Start the selected model from the sidebar before chatting.")
        st.chat_input(f"Message {character.name}", disabled=True)
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(f"Message {character.name}")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    append_chatlog(st.session_state.chatlog_path, "User", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    backstory = read_text(character.backstory_path)
    memory = read_text(character.memory_path)
    history = st.session_state.messages[:-1]
    messages = build_character_messages(backstory, memory, history, prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking locally..."):
            try:
                reply = chat_completion(model_config, messages, model_status)
            except (requests.RequestException, ValueError) as exc:
                reply = f"Local model error: {exc}"
                st.error(reply)
            else:
                st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    append_chatlog(st.session_state.chatlog_path, character.name, reply)


active_model = render_sidebar()

st.title("Local Huggingface Chatbot")
st.caption("Chat with local characters, backed by Markdown memory and raw text logs.")

render_character_panel()
st.divider()

active_character = get_active_character()
if not active_character:
    st.subheader("Chat")
    st.info("Create or open a character above to start chatting.")
elif not active_model:
    st.subheader(active_character.name)
    render_character_editor(active_character)
    # render_memory_tools(active_character)
    st.info("Download or select a model in the sidebar to enable chat replies.")
    st.chat_input(f"Message {active_character.name}", disabled=True)
else:
    render_chat(active_character, active_model)
