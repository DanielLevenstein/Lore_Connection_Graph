from pathlib import Path

from .environment import data_dir
from .policy import require_codebase_owned_language_model


SYSTEM_PROMPT = (
    "You are a local chat assistant. Use the full conversation history, "
    "including earlier user and assistant messages, when answering."
)


def chat_url(config) -> str:
    return config.api_base_url.rstrip("/") + "/chat/completions"


def chat_session_key(config) -> str:
    return f"chat_messages_{config.name}"


def chat_memory_path(config) -> Path:
    return data_dir() / "chat_memory" / f"{config.name}.json"


def normalized_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    has_system_prompt = any(
        message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and bool(message["content"].strip())
        for message in messages
    )
    normalized = [] if has_system_prompt else [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role in {"system", "user", "assistant"} and isinstance(content, str) and content.strip():
            normalized.append({"role": role, "content": content})
    return normalized


def load_chat_memory(config) -> list[dict[str, str]]:
    return []


def save_chat_memory(config, messages: list[dict[str, str]]) -> None:
    chat_memory_path(config).parent.mkdir(parents=True, exist_ok=True)
    chat_memory_path(config).write_text("[]\n", encoding="utf-8")


def append_chat_memory(config, role: str, content: str) -> list[dict[str, str]]:
    require_codebase_owned_language_model()


def clear_chat_memory(config) -> None:
    chat_memory_path(config).unlink(missing_ok=True)


def chat_completion(config, messages: list[dict[str, str]], server_status=None) -> str:
    require_codebase_owned_language_model()


def remember_and_chat(config, prompt: str, server_status=None) -> str:
    require_codebase_owned_language_model()
