import requests

from .models import ModelConfig


class LocalModelError(RuntimeError):
    """Raised when the local model server cannot complete a request."""


def build_messages(backstory: str, memory: str, history: list[dict[str, str]], user_text: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are roleplaying as the user's custom character. Stay in character, "
        "use the backstory and memory as ground truth, and keep replies conversational.\n\n"
        f"BACKSTORY:\n{backstory.strip()}\n\n"
        f"MEMORY:\n{memory.strip()}"
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_text})
    return messages


def chat_completion(
    config: ModelConfig,
    messages: list[dict[str, str]],
    temperature: float = 0.8,
    max_tokens: int = 512,
) -> str:
    endpoint = config.api_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        response = requests.post(endpoint, json=payload, timeout=120)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LocalModelError(f"Could not reach local model server at {endpoint}: {exc}") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LocalModelError("Local model server returned an unexpected response shape.") from exc
