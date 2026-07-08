import subprocess
import shlex
import sys

import streamlit as st

from local_chatbot.client import LocalModelError, build_messages, chat_completion
from local_chatbot.downloads import downloaded_options, status_for_option
from local_chatbot.models import list_model_configs, mark_model_downloaded
from local_chatbot.paths import DATA_DIR, ensure_base_dirs
from local_chatbot.server import configured_command, log_path as server_log_path, required_runner_binary, runner_binary_path, runner_is_installed, start_server, status, stop_server
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


def file_variant_label(option: dict) -> str:
    filename = option["filename"].removesuffix(".gguf")
    quant = str(option["quant"])
    for token in (f"-D_AU-{quant}", f"-D_AU-{quant.lower()}", f"-{quant}", f"-{quant.lower()}"):
        filename = filename.replace(token, "")
    parts = [part for part in filename.split("-") if part.lower() in {"max", "cpu"}]
    return "-".join(parts) if parts else "standard"


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


def render_model_panel() -> object | None:
    configs = list_model_configs()
    if not configs:
        st.error("No model configs found in config/.")
        return None

    downloaded = list_model_configs(downloaded_only=True)
    if not downloaded:
        st.warning("No downloaded models found. Mark a configured model as downloaded to enable chat.")
    else:
        selected_name = st.selectbox("Downloaded model", [config.name for config in downloaded])
        selected = next(config for config in downloaded if config.name == selected_name)
        st.caption(f"{selected.size} · Download: {selected.download_size} · {selected.description}")
        # st.link_button("Hugging Face", selected.model_url)
        st.success(f"Local folder ready: data/{selected.name}")
        # render_server_controls(selected)

    with st.expander("Model configs", expanded=True):
        config_name = st.selectbox(
            "Configured model",
            [config.name for config in configs],
            format_func=lambda name: f"{name} {'(downloaded)' if next(c for c in configs if c.name == name).is_downloaded else '(not downloaded)'}",
        )
        config = next(item for item in configs if item.name == config_name)
        st.caption(f"{config.size} · Download: {config.download_size} · {config.description}")
        render_download_controls(config)
        st.link_button("Open model page", config.model_url)
        if config.is_downloaded:
            st.info(f"Local folder: data/{config.name}")
        elif not config.download_options and st.button("Create local folder", icon=":material/create_new_folder:"):
            mark_model_downloaded(config)
            st.rerun()

    if not downloaded:
        return None
    return selected


def download_log_path(config) -> object:
    runtime_dir = DATA_DIR / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / f"{config.name}.download.log"


def read_log_tail(path, max_lines: int = 8) -> str:
    if not path.exists():
        return "No log output yet."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:]) or "No log output yet."


def render_tiny_log(label: str, path) -> None:
    st.caption(f"{label}: {path}")
    st.text_area(
        label,
        value=read_log_tail(path),
        height=96,
        disabled=True,
        label_visibility="collapsed",
    )


def render_download_controls(config) -> None:
    if not config.download_options:
        return

    local_options = downloaded_options(config)
    render_model_readiness_banner(config)
    st.markdown("**Downloaded model files**")
    if local_options:
        selected_local_option = render_selectable_artifact_table(
            config,
            local_options,
            key=f"start_choice_{config.name}",
        )
    else:
        selected_local_option = None
        render_empty_artifact_table()
    render_config_start_button(config, selected_local_option)


    st.markdown("**All model files**")
    selected_option = render_selectable_artifact_table(
        config,
        config.download_options,
        key=f"download_choice_{config.name}",
    )
    selected_status = status_for_option(config, selected_option) if selected_option else None

    if selected_option and selected_status:
        if selected_status.exists:
            st.success(f"Selected file is already downloaded: {selected_status.path}")
        elif selected_status.partial_bytes:
            st.info(f"Selected file has a partial download: {selected_status.partial_bytes:,} bytes at {selected_status.part_path}")
        else:
            st.caption(f"Selected: {selected_option['quant']} · {file_variant_label(selected_option)} · {selected_option['size']} · {selected_option['filename']}")
    else:
        st.caption("Select a row in the table to enable download.")

    download_disabled = selected_option is None
    if st.button(
        "Download model",
        icon=":material/download:",
        disabled=download_disabled,
        key=f"download_model_{config.name}",
    ):
        if selected_option:
            start_model_download(config, selected_option)
    render_download_action_log(config, selected_option)




def render_selectable_artifact_table(config, options: list[dict], key: str) -> dict | None:
    rows = []
    for option in options:
        download_status = status_for_option(config, option)
        status_label = "Local" if download_status.exists else "Partial" if download_status.partial_bytes else "Remote"
        rows.append(
            {
                "Quant": option["quant"],
                "Variant": file_variant_label(option),
                "Size": option["size"],
                "Status": status_label,
            }
        )

    selection = st.dataframe(
        rows,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
        width="stretch",
        height=min(38 * (len(rows) + 1), 360),
    )
    selected_rows = selection.selection.rows
    selected_index = selected_rows[0] if selected_rows else None
    return options[selected_index] if selected_index is not None else None


def render_empty_artifact_table() -> None:
    st.dataframe(
        [{"Quant": "", "Variant": "", "Size": "", "Status": ""}],
        hide_index=True,
        width="stretch",
        height=76,
    )
    st.caption("No downloaded model files yet.")


def model_cell(value: str) -> str:
    return f'<div class="model-table-cell" title="{value}">{value}</div>'


def start_model_download(config, option) -> None:
    log_path = download_log_path(config)
    command = [
        sys.executable,
        "scripts/download_model.py",
        str(config.config_path),
        "--filename",
        option["filename"],
    ]
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n--- Running {shlex.join(command)} ---\n")
        log_file.flush()
        subprocess.Popen(
            command,
            cwd=config.config_path.parent.parent,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
    )
    st.info(f"Download started for {option['filename']}. Log: {log_path}")


def render_download_action_log(config, selected_option: dict | None) -> None:
    if selected_option:
        command = [
            sys.executable,
            "scripts/download_model.py",
            str(config.config_path),
            "--filename",
            selected_option["filename"],
        ]
        st.caption(f"Download command: `{shlex.join(command)}`")
    render_tiny_log("Download log", download_log_path(config))


def render_config_start_button(config, selected_option: dict | None = None) -> None:
    server_status = status(config)
    runner_installed = runner_is_installed(config)
    disabled = selected_option is None or not runner_installed or server_status.running or server_status.healthy
    if selected_option:
        st.caption(f"Start command: `{shlex.join(configured_command(config, selected_option))}`")
    if st.button("Start model", icon=":material/play_arrow:", disabled=disabled):
        try:
            started = start_server(config, wait_seconds=15, option=selected_option)
        except (OSError, ValueError) as exc:
            with server_log_path(config).open("a", encoding="utf-8") as log_file:
                log_file.write(f"--- Could not start model: {exc} ---\n")
            st.error(f"Could not start model: {exc}")
        else:
            st.success(f"Started model server with PID {started.pid}.")
            st.rerun()
    render_runner_install_prompt(config)
    if selected_option is None:
        st.caption("Select a downloaded model file before starting it.")
    if server_status.healthy:
        st.success("Model health is green. The local chat endpoint is ready.")
    elif server_status.running:
        st.info("Model process is running. Waiting for health to become green.")
    else:
        st.caption("Model server is stopped.")
    render_tiny_log("Model server log", server_log_path(config))


def render_model_readiness_banner(config) -> None:
    server_status = status(config)
    log_path = server_log_path(config)
    if server_status.healthy:
        append_log_once(log_path, "--- Health check green: model server is ready ---")
        st.success(f"Model loaded and ready at {config.api_base_url}. You can chat now.")
    elif server_status.running:
        st.info("Model process is running. Loading can take a little while; waiting for health to turn green.")
    else:
        st.warning("Model server is stopped. Select a downloaded file and click Start model.")


def append_log_once(path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if line not in current:
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")


def render_runner_install_prompt(config) -> None:
    binary = required_runner_binary(config)
    if not binary:
        return
    if runner_binary_path(config):
        return
    runner = config.server.get("runner", binary) if config.server else binary
    st.warning(f"`{binary}` was not found on PATH. Install {runner} locally before starting this model.")
    if binary == "llama":
        st.code("brew install llama.cpp", language="bash")
        st.caption("After installing, restart the Streamlit app so it can see the updated PATH.")

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
    messages = build_messages(backstory, memory, history, prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking locally..."):
            try:
                reply = chat_completion(model_config, messages)
            except LocalModelError as exc:
                reply = f"Local model error: {exc}"
                st.error(reply)
            else:
                st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    append_chatlog(st.session_state.chatlog_path, character.name, reply)


with st.sidebar:
    st.header("Local Setup")
    active_model = render_model_panel()

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
