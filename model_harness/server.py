import os
import signal
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from .downloads import local_model_path, selected_downloaded_option
from .environment import data_dir, ensure_base_dirs
from .models import ModelConfig
from .policy import require_codebase_owned_language_model


@dataclass(frozen=True)
class ServerStatus:
    pid: int | None
    running: bool
    healthy: bool
    log_path: Path
    endpoint_live: bool = False
    model_names: tuple[str, ...] = ()


def runtime_dir() -> Path:
    ensure_base_dirs()
    path = data_dir() / ".runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def pid_path(config: ModelConfig) -> Path:
    return runtime_dir() / f"{config.name}.pid"


def log_path(config: ModelConfig) -> Path:
    return runtime_dir() / f"{config.name}.server.log"


def configured_command(config: ModelConfig, option: dict | None = None) -> list[str]:
    command = config.server.get("command") if config.server else None
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError(f"{config.name} does not have a valid server.command list in its JSON config.")

    option = option or selected_downloaded_option(config)
    if option and config.server.get("runner") == "llama.cpp":
        port = "8000"
        if "--port" in command:
            port_index = command.index("--port") + 1
            if port_index < len(command):
                port = command[port_index]
        return [
            "llama",
            "serve",
            "-m",
            str(local_model_path(config, option)),
            "--host",
            "127.0.0.1",
            "--port",
            port,
        ]
    return command


def required_runner_binary(config: ModelConfig) -> str | None:
    try:
        command = configured_command(config)
    except ValueError:
        return None
    return command[0] if command else None


def runner_binary_path(config: ModelConfig) -> str | None:
    binary = required_runner_binary(config)
    return shutil.which(binary) if binary else None


def runner_is_installed(config: ModelConfig) -> bool:
    return runner_binary_path(config) is not None


def health_url(config: ModelConfig) -> str:
    if config.server and isinstance(config.server.get("health_url"), str):
        return config.server["health_url"]
    return config.api_base_url.rstrip("/") + "/models"


def health_port(config: ModelConfig) -> int | None:
    parsed = urlparse(health_url(config))
    if parsed.port:
        return parsed.port
    if parsed.scheme == "http":
        return 80
    if parsed.scheme == "https":
        return 443
    return None


def read_pid(config: ModelConfig) -> int | None:
    path = pid_path(config)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def process_is_running(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def listening_pids(config: ModelConfig) -> tuple[int, ...]:
    port = health_port(config)
    if port is None or not shutil.which("lsof"):
        return ()
    result = subprocess.run(
        ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        return ()
    pids = []
    for line in result.stdout.splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            pass
    return tuple(dict.fromkeys(pids))


def server_is_healthy(config: ModelConfig) -> bool:
    endpoint_live, model_names = server_models(config)
    if not endpoint_live:
        return False
    expected = expected_model_tokens(config)
    if not expected:
        return True
    return any(model_matches(token, model_name) for token in expected for model_name in model_names)


def server_models(config: ModelConfig) -> tuple[bool, tuple[str, ...]]:
    try:
        response = requests.get(health_url(config), timeout=2)
    except requests.RequestException:
        return False, ()
    if response.status_code != 200:
        return False, ()
    try:
        payload = response.json()
    except ValueError:
        return True, ()

    names = []
    for item in payload.get("data", []):
        if isinstance(item, dict):
            names.extend(str(item[key]) for key in ("id", "model", "name") if item.get(key))
    for item in payload.get("models", []):
        if isinstance(item, dict):
            names.extend(str(item[key]) for key in ("id", "model", "name") if item.get(key))
    return True, tuple(dict.fromkeys(names))


def expected_model_tokens(config: ModelConfig, option: dict | None = None) -> tuple[str, ...]:
    option = option or selected_downloaded_option(config)
    if option:
        path = local_model_path(config, option)
        return (str(path), path.name)
    tokens = [config.model_id]
    command = config.server.get("command") if config.server else None
    if isinstance(command, list):
        tokens.extend(part for part in command if "/" in part and not part.startswith("http"))
    return tuple(dict.fromkeys(tokens))


def model_matches(expected: str, actual: str) -> bool:
    expected = expected.strip()
    actual = actual.strip()
    return bool(expected and actual and (expected == actual or expected in actual or actual in expected))


def status(config: ModelConfig) -> ServerStatus:
    pid = read_pid(config)
    running = process_is_running(pid)
    endpoint_live, model_names = server_models(config)
    expected = expected_model_tokens(config)
    healthy = endpoint_live and (
        not expected or any(model_matches(token, model_name) for token in expected for model_name in model_names)
    )
    if not running and pid_path(config).exists() and not healthy:
        pid_path(config).unlink(missing_ok=True)
        pid = None
    return ServerStatus(
        pid=pid,
        running=running,
        healthy=healthy,
        log_path=log_path(config),
        endpoint_live=endpoint_live,
        model_names=model_names,
    )


def start_server(config: ModelConfig, wait_seconds: int = 0, option: dict | None = None) -> ServerStatus:
    require_codebase_owned_language_model()
    current = status(config)
    if current.healthy:
        return current
    if current.endpoint_live:
        loaded = ", ".join(current.model_names) or "an unknown model"
        raise ValueError(f"{health_url(config)} is already serving a different model: {loaded}")
    if current.running:
        return current

    command = configured_command(config, option)
    if not shutil.which(command[0]):
        raise FileNotFoundError(
            f"{command[0]} is not installed or is not available on PATH."
        )
    runtime_log = log_path(config)
    runtime_log.parent.mkdir(parents=True, exist_ok=True)
    log_file = runtime_log.open("a", encoding="utf-8")
    log_file.write(f"\n--- Starting {' '.join(command)} ---\n")
    log_file.flush()

    process = subprocess.Popen(
        command,
        cwd=data_dir(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pid_path(config).write_text(str(process.pid), encoding="utf-8")

    deadline = time.monotonic() + wait_seconds
    while wait_seconds > 0 and time.monotonic() < deadline:
        if server_is_healthy(config):
            break
        time.sleep(1)
    current = status(config)
    with runtime_log.open("a", encoding="utf-8") as status_log:
        if current.healthy:
            status_log.write("--- Health check green: model server is ready ---\n")
        elif current.running:
            status_log.write("--- Model process is running; health check is not green yet ---\n")
        else:
            status_log.write("--- Model process exited before health check became green ---\n")
    return current


def stop_server(config: ModelConfig, include_endpoint: bool = False) -> ServerStatus:
    pid = read_pid(config)
    if pid and process_is_running(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
    if include_endpoint:
        for endpoint_pid in listening_pids(config):
            if endpoint_pid != pid and process_is_running(endpoint_pid):
                os.kill(endpoint_pid, signal.SIGTERM)
        time.sleep(1)
    pid_path(config).unlink(missing_ok=True)
    return status(config)
