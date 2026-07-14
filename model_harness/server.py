from dataclasses import dataclass
from pathlib import Path

from .environment import data_dir
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


def log_path(config: ModelConfig) -> Path:
    return data_dir() / ".runtime" / f"{config.name}.log"


def status(config: ModelConfig) -> ServerStatus:
    return ServerStatus(
        pid=None,
        running=False,
        healthy=False,
        log_path=log_path(config),
        endpoint_live=False,
        model_names=(),
    )


def start_server(config: ModelConfig, wait_seconds: int = 0, option: dict | None = None) -> ServerStatus:
    require_codebase_owned_language_model()


def stop_server(config: ModelConfig) -> bool:
    return False


def runner_is_installed(config: ModelConfig) -> bool:
    return False
