import subprocess
import shlex
import sys

import streamlit as st

from local_chatbot.downloads import downloaded_options, status_for_option
from local_chatbot.models import list_model_configs, mark_model_downloaded
from local_chatbot.paths import DATA_DIR, ensure_base_dirs
from local_chatbot.server import configured_command, log_path as server_log_path, required_runner_binary, runner_binary_path, runner_is_installed, start_server, status, stop_server


ensure_base_dirs()

def file_variant_label(option: dict) -> str:
    filename = option["filename"].removesuffix(".gguf")
    quant = str(option["quant"])
    for token in (f"-D_AU-{quant}", f"-D_AU-{quant.lower()}", f"-{quant}", f"-{quant.lower()}"):
        filename = filename.replace(token, "")
    parts = [part for part in filename.split("-") if part.lower() in {"max", "cpu"}]
    return "-".join(parts) if parts else "standard"

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

with st.sidebar:
    st.header("Local Setup")
    active_model = render_model_panel()

st.title("Local Huggingface Chatbot")
st.caption("Chat with local characters, backed by Markdown memory and raw text logs.")

st.divider()
