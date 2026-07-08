import json
from pathlib import Path

import requests

from .environment import data_dir
from .server import status


SYSTEM_PROMPT = (
    "You are a local chat assistant. Use the full conversation history, "
    "including earlier user and assistant messages, when answering."
)


def chat_url(config) -> str:
    return config.api_base_url.rstrip("/") + "/chat/completions"


def chat_session_key(config) -> str:
    return f"chat_messages_{config.name}"


def chat_memory_path(config) -> Path:
    memory_dir = data_dir() / "chat_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir / f"{config.name}.json"


def valid_chat_message(message) -> bool:
    return (
        isinstance(message, dict)
        and message.get("role") in {"user", "assistant"}
        and isinstance(message.get("content"), str)
        and bool(message["content"].strip())
    )


def load_chat_memory(config) -> list[dict[str, str]]:
    path = chat_memory_path(config)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    return [
        {"role": message["role"], "content": message["content"].strip()}
        for message in payload
        if valid_chat_message(message)
    ]


def save_chat_memory(config, messages: list[dict[str, str]]) -> None:
    path = chat_memory_path(config)
    remembered = [message for message in messages if valid_chat_message(message)]
    path.write_text(json.dumps(remembered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_chat_memory(config, role: str, content: str) -> list[dict[str, str]]:
    messages = load_chat_memory(config)
    messages.append({"role": role, "content": content})
    save_chat_memory(config, messages)
    return messages


def clear_chat_memory(config) -> None:
    chat_memory_path(config).unlink(missing_ok=True)


def served_model_id(config, server_status=None) -> str:
    server_status = server_status or status(config)
    if server_status.model_names:
        return server_status.model_names[0]
    return config.model_id


def normalized_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role in {"system", "user", "assistant"} and isinstance(content, str) and content.strip():
            normalized.append({"role": role, "content": content})
    return normalized


def write_chat_request_log(config, payload: dict) -> None:
    runtime_dir = data_dir() / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "model": payload["model"],
        "message_count": len(payload["messages"]),
        "roles": [message["role"] for message in payload["messages"]],
        "messages": payload["messages"],
    }
    with (runtime_dir / f"{config.name}.chat.log").open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def chat_completion(config, messages: list[dict[str, str]], server_status=None) -> str:
    outbound_messages = normalized_chat_messages(messages)
    payload = {
        "model": served_model_id(config, server_status),
        "messages": outbound_messages,
        "temperature": 0.7,
        "max_tokens": 512,
    }
    write_chat_request_log(config, payload)
    response = requests.post(chat_url(config), json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("The model returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("The model returned an empty response.")
    return content.strip()


def remember_and_chat(config, prompt: str, server_status=None) -> str:
    messages = append_chat_memory(config, "user", prompt)
    reply = chat_completion(config, messages, server_status)
    append_chat_memory(config, "assistant", reply)
    return reply
