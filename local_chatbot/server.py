import os
import signal
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .downloads import local_model_path, selected_downloaded_option
from .models import ModelConfig
from .paths import DATA_DIR, ensure_base_dirs


@dataclass(frozen=True)
class ServerStatus:
    pid: int | None
    running: bool
    healthy: bool
    log_path: Path


def runtime_dir() -> Path:
    ensure_base_dirs()
    path = DATA_DIR / ".runtime"
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


def server_is_healthy(config: ModelConfig) -> bool:
    try:
        response = requests.get(health_url(config), timeout=2)
    except requests.RequestException:
        return False
    return response.status_code == 200


def status(config: ModelConfig) -> ServerStatus:
    pid = read_pid(config)
    running = process_is_running(pid)
    healthy = server_is_healthy(config)
    if not running and pid_path(config).exists() and not healthy:
        pid_path(config).unlink(missing_ok=True)
        pid = None
    return ServerStatus(pid=pid, running=running, healthy=healthy, log_path=log_path(config))


def start_server(config: ModelConfig, wait_seconds: int = 0, option: dict | None = None) -> ServerStatus:
    current = status(config)
    if current.running or current.healthy:
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
        cwd=DATA_DIR,
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


def stop_server(config: ModelConfig) -> ServerStatus:
    pid = read_pid(config)
    if pid and process_is_running(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
    pid_path(config).unlink(missing_ok=True)
    return status(config)
