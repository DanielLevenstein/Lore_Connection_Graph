from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from model_harness.chat import chat_completion, chat_session_key, clear_chat_memory, load_chat_memory, save_chat_memory
from model_harness.environment import data_dir
from model_harness.server import status


def chat_history_session_key(config) -> str:
    return f"chat_history_log_{config.name}"


def chat_history_log_path(config) -> object:
    history_key = chat_history_session_key(config)
    if history_key not in st.session_state:
        chatlog_dir = data_dir() / "chatlog"
        chatlog_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = chatlog_dir / f"{timestamp}.log"
        if path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = chatlog_dir / f"{timestamp}.log"
        path.write_text(
            f"Model: {config.name}\n"
            f"Model ID: {config.model_id}\n"
            f"API base URL: {config.api_base_url}\n"
            f"Started: {datetime.now().isoformat(timespec='seconds')}\n\n",
            encoding="utf-8",
        )
        st.session_state[history_key] = str(path)
    return Path(st.session_state[history_key])


def write_chat_history_message(config, role: str, content: str) -> None:
    path = chat_history_log_path(config)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {role.upper()}\n{content.strip()}\n\n")


def render_chat(active_model) -> None:
    if not active_model:
        st.info("Download and start a model to chat with it.")
        st.chat_input("Start a local model to enable chat", disabled=True)
        return

    server_status = status(active_model)
    ready = server_status.healthy
    messages_key = chat_session_key(active_model)
    if messages_key not in st.session_state:
        st.session_state[messages_key] = load_chat_memory(active_model)

    header_col, action_col = st.columns([1, 1])
    with header_col:
        st.subheader(active_model.name)
        st.caption(active_model.api_base_url)
    with action_col:
        if st.button("Clear chat", disabled=not st.session_state[messages_key]):
            st.session_state[messages_key] = []
            clear_chat_memory(active_model)
            st.session_state.pop(chat_history_session_key(active_model), None)
            st.rerun()

    if not ready:
        if server_status.endpoint_live:
            loaded = ", ".join(server_status.model_names) or "another model"
            st.warning(f"The local endpoint is serving {loaded}. Stop it or start {active_model.name} before chatting.")
        else:
            st.warning("Start the local model server before chatting.")

    for message in st.session_state[messages_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Message the local model", disabled=not ready)
    if not prompt:
        return

    st.session_state[messages_key].append({"role": "user", "content": prompt})
    save_chat_memory(active_model, st.session_state[messages_key])
    write_chat_history_message(active_model, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = chat_completion(active_model, st.session_state[messages_key], server_status)
            except (requests.RequestException, ValueError) as exc:
                st.error(f"Chat request failed: {exc}")
                write_chat_history_message(active_model, "assistant", f"Chat request failed: {exc}")
                return
            st.markdown(reply)
    st.session_state[messages_key].append({"role": "assistant", "content": reply})
    save_chat_memory(active_model, st.session_state[messages_key])
    write_chat_history_message(active_model, "assistant", reply)


def render_main(active_model) -> None:
    st.title("Local Hugging Face models")
    st.caption("Messages below are sent directly to local Hugging Face models.")

    st.divider()
    render_chat(active_model)
