from dataclasses import dataclass
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = "Use only supplied character facts."
# TODO Delete this file

def normalized_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize incoming chat messages for rewrite workflows."""
    return [message for message in messages if message.get("content") != SYSTEM_PROMPT or message.get("role") == "system"]


def chat_completion(config: Any, messages: list[dict[str, str]]) -> Any:
    raise RuntimeError("External language-model use is disabled")


def append_chat_memory(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("External language-model use is disabled")


def clear_chat_memory(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("External language-model use is disabled")


def load_chat_memory(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("External language-model use is disabled")


def remember_and_chat(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("External language-model use is disabled")


def save_chat_memory(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("External language-model use is disabled")
