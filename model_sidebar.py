from collections import deque
import shlex
import subprocess
import sys

import streamlit as st

from model_harness.downloads import default_download_option, downloaded_options, selected_downloaded_option, status_for_option
from model_harness.environment import data_dir, ensure_base_dirs
from model_harness.models import list_model_configs, mark_model_downloaded
from model_harness.server import configured_command, log_path as server_log_path, required_runner_binary, runner_binary_path, runner_is_installed, start_server, status, stop_server


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
        st.info("No model configs found in config/.")
        render_model_config_generator()
        return None

    downloaded = list_model_configs(downloaded_only=True)
    selected = None
    if not downloaded:
        st.warning("No downloaded models found. Download or prepare a configured model to enable chat.")
    else:
        downloaded_names = [config.name for config in downloaded]
        if st.session_state.get("downloaded_model_select") not in downloaded_names:
            st.session_state["downloaded_model_select"] = downloaded_names[0]
        selected_name = st.selectbox(
            "Downloaded Model",
            downloaded_names,
            key="downloaded_model_select",
        )
        selected = next(config for config in downloaded if config.name == selected_name)
        st.caption(f"{selected.size} · download: {selected.download_size} · {selected.description}")
        # st.link_button("Hugging Face", selected.model_url)
        st.success(f"Local folder ready: data/{selected.name}")
        # render_server_controls(selected)
    render_model_config_generator()

    with st.expander("Model Configs", expanded=True):
        configured_names = [config.name for config in configs]
        configured_index = configured_names.index(selected.name) if selected and selected.name in configured_names else 0
        if st.session_state.get("configured_model_select") not in configured_names:
            st.session_state["configured_model_select"] = configured_names[configured_index]
        config_name = st.selectbox(
            "Configured Model",
            configured_names,
            index=configured_index,
            key="configured_model_select",
            format_func=lambda name: f"{name} {'(downloaded)' if next(c for c in configs if c.name == name).is_downloaded else '(not downloaded)'}",
        )
        config = next(item for item in configs if item.name == config_name)
        st.caption(f"{config.size} · download: {config.download_size} · {config.description}")
        render_download_controls(config)
    if not downloaded:
        return None
    return selected



def download_log_path(config) -> object:
    runtime_dir = data_dir() / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / f"{config.name}.download.log"

def config_log_path() -> object:
    runtime_dir = data_dir() / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / f"config.log"

def read_log_tail(path, max_lines: int = 8) -> str:
    if not path.exists():
        return "No log output yet."
    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        lines = deque(log_file, maxlen=max_lines)
    return "".join(lines).rstrip() or "No log output yet."


def render_tiny_log(label: str, path) -> None:
    st.caption(f"{label} tail: {path}")
    st.text_area(
        label,
        value=read_log_tail(path),
        height=96,
        disabled=True,
        key=f"log_{label}_{path}",
        label_visibility="collapsed",
    )


def render_download_controls(config) -> None:
    if not config.download_options:
        render_remote_model_controls(config)
        return

    local_options = downloaded_options(config)
    render_model_readiness_banner(config)
    st.markdown("**Downloaded Model Files**")
    try:
        if local_options:
            selected_local_option = render_selectable_artifact_table(
                config,
                local_options,
                key=f"start_choice_{config.name}",
            )
            selected_local_option = selected_local_option or selected_downloaded_option(config)
        else:
            selected_local_option = None
            render_empty_artifact_table(config)
        render_config_start_button(config, selected_local_option)
        render_all_model_files(config, local_options)

    except Exception:
        st.info("Model config is not present.")

def has_downloaded_preferred_quant(config, local_options: list[dict]) -> bool:
    preferred = default_download_option(config)
    if not preferred:
        return False
    preferred_quant = preferred.get("quant")
    return any(option.get("quant") == preferred_quant for option in local_options)


def render_all_model_files(config, local_options: list[dict]) -> None:
    variants_key = f"show_other_variants_{config.name}"
    hide_variants = has_downloaded_preferred_quant(config, local_options)
    if hide_variants:
        label = "Hide Variants" if st.session_state.get(variants_key) else "Other variants"
        if st.button(label, key=f"toggle_{variants_key}"):
            st.session_state[variants_key] = not st.session_state.get(variants_key, False)
            st.rerun()
        if not st.session_state.get(variants_key):
            return

    st.markdown("**All Model Files**")
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
        "Download Model",
        disabled=download_disabled,
        key=f"download_model_{config.name}",
    ):
        if selected_option:
            if download_model_file(config, selected_option):
                st.rerun()
    render_download_action_log(config, selected_option)

def render_remote_model_controls(config) -> None:
    render_model_readiness_banner(config)
    if config.is_downloaded:
        st.info(f"Local folder: data/{config.name}")
    else:
        st.caption("This config does not list individual model files. The server runner will use its own model cache.")
        if st.button("Download model", key=f"prepare_model_{config.name}"):
            mark_model_downloaded(config)
            st.success(f"Prepared local folder: data/{config.name}")
            st.rerun()
    render_config_start_button(config)


def render_model_config_generator() -> None:
    st.markdown("**Add Hugging Face Model**")
    default_model_url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
    stale_tinyllama_url = "https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    if st.session_state.get("model_url_field") == stale_tinyllama_url:
        st.session_state["model_url_field"] = default_model_url
    model_url = st.text_input("Model URL", default_model_url, key="model_url_field")
    replace_existing = st.checkbox("Replace existing config", key="replace_existing_config")
    col1, col2 = st.columns(2)
    with col1:
        generate_clicked = st.button("Generate Model Config")
    with col2:
        st.link_button("Open Model Page", model_url)
    if generate_clicked:
        if generate_model_config(model_url, overwrite=replace_existing):
            st.rerun()


def normalized_model_ref(value: str) -> str:
    return value.strip().removesuffix("/").removeprefix("https://huggingface.co/").removeprefix("http://huggingface.co/")


def config_for_model_url(model_url: str):
    model_ref = normalized_model_ref(model_url)
    for config in list_model_configs():
        if normalized_model_ref(config.model_url) == model_ref or normalized_model_ref(config.model_id) == model_ref:
            return config
    return None


def render_default_quant_download(model_url: str) -> None:
    config = config_for_model_url(model_url)
    if not config:
        st.button("Download Default Quantization", disabled=True, key="download_default_quantization_missing_config")
        st.caption("Generate a model config before downloading the default quantization.")
        return

    option = default_download_option(config)
    if not option:
        st.caption("This config does not list a default quantized model file.")
        return

    download_status = status_for_option(config, option)
    st.caption(f"Default quantization: {option['quant']} · {file_variant_label(option)} · {option['size']}")
    if download_status.exists:
        st.success(f"Default quantization is downloaded: {download_status.path}")
        return
    if download_status.partial_bytes:
        st.info(f"Default quantization has a partial download: {download_status.partial_bytes:,} bytes at {download_status.part_path}")

    if st.button("Download default quantization", key=f"download_default_quantization_{config.name}"):
        if download_model_file(config, option):
            st.rerun()


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
        height=min(38 * (len(rows) + 1), 360),
    )
    selected_rows = selection.selection.rows
    selected_index = selected_rows[0] if selected_rows else None
    return options[selected_index] if selected_index is not None else None


def render_empty_artifact_table(config) -> None:
    st.dataframe(
        [{"Quant": "", "Variant": "", "Size": "", "Status": ""}],
        hide_index=True,
        height=76,
        key="empty_downloaded_model_files",
    )
    st.caption("No downloaded model files yet.")
    render_default_quant_download(config.model_url)

def model_cell(value: str) -> str:
    return f'<div class="model-table-cell" title="{value}">{value}</div>'


def download_model_file(config, option) -> bool:
    log_path = download_log_path(config)
    command = [
        sys.executable,
        "scripts/download_model.py",
        str(config.config_path),
        "--filename",
        option["filename"],
    ]
    with st.spinner(f"Downloading {option['filename']}..."):
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n--- Running {shlex.join(command)} ---\n")
            log_file.flush()
            result = subprocess.run(
                command,
                cwd=config.config_path.parent.parent,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
    if result.returncode == 0:
        st.success(f"Downloaded {option['filename']}.")
        return True
    st.error(f"Could not download {option['filename']}. Log: {log_path}")
    render_tiny_log("Download log", log_path)
    return False


def generate_model_config(name="TinyLlama-1.1B-Chat-v1.0", overwrite: bool = False) -> bool:
    log_path = config_log_path()
    command = [
        sys.executable,
        "scripts/generate_model_config.py",
        str(name)
    ]
    if overwrite:
        command.append("--overwrite")
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n--- Running {shlex.join(command)} ---\n")
        log_file.flush()
        result = subprocess.run(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if result.returncode == 0:
        st.success(f"Generated model config. Log: {log_path}")
        return True
    latest_log = read_log_tail(log_path)
    if "already exists. Use --overwrite to replace it." in latest_log:
        st.warning("A config with this name already exists. Select the existing model, or enable Replace existing config and generate again.")
        render_tiny_log("Config log", log_path)
        return False
    st.error(f"Could not generate model config. Log: {log_path}")
    render_tiny_log("Config log", log_path)
    return False

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
    requires_local_file = bool(config.download_options)
    if requires_local_file and selected_option is None:
        selected_option = selected_downloaded_option(config)
    missing_download = selected_option is None if requires_local_file else not config.is_downloaded
    disabled = missing_download or not runner_installed or server_status.running or server_status.healthy
    try:
        start_col, stop_col = st.columns(2)
        with start_col:
            if st.button("Start Model", key=f"start_model_{config.name}", disabled=disabled):
                try:
                    started = start_server(config, wait_seconds=15, option=selected_option)
                except (OSError, ValueError) as exc:
                    with server_log_path(config).open("a", encoding="utf-8") as log_file:
                        log_file.write(f"--- Could not start model: {exc} ---\n")
                    st.error(f"Could not start model: {exc}")
                else:
                    st.success(f"Started model server with PID {started.pid}.")
                    st.rerun()
        with stop_col:
            stop_disabled = not (server_status.running or server_status.endpoint_live)
            if st.button("Stop Model", key=f"stop_model_{config.name}", disabled=stop_disabled):
                stopped = stop_server(config, include_endpoint=True)
                if stopped.endpoint_live:
                    st.warning("Stop signal sent, but the local endpoint is still responding.")
                else:
                    st.success("Stopped local model server.")
                st.rerun()
    except Exception as exc:
        st.error(f"Could not start model: {exc}")
    if not missing_download:
        st.caption(f"Start command: `{shlex.join(configured_command(config, selected_option))}`")
    render_runner_install_prompt(config)
    if missing_download and requires_local_file:
        st.caption("Select a downloaded model file before starting it.")
    elif missing_download:
        st.caption("Download or prepare this model before starting it.")
    if server_status.healthy:
        st.success("Model health is green. The local chat endpoint is ready.")
    elif server_status.endpoint_live:
        loaded = ", ".join(server_status.model_names) or "another model"
        st.warning(f"Local endpoint is already serving {loaded}. Stop it before starting this model.")
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
    elif config.download_options:
        st.warning("Model server is stopped. Select a downloaded file and click Start model.")
    else:
        st.warning("Model server is stopped. Download or prepare this model, then click Start model.")


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


def render_sidebar() -> object | None:
    with st.sidebar:
        st.header("Local setup")
        return render_model_panel()


if __name__ == "__main__":
    from model_main import render_main

    active_model = render_sidebar()
    render_main(active_model)
