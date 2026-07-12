from pathlib import Path
from subprocess import CompletedProcess

import pytest

import local_chatbot.character_rewrites as rewrites
from model_harness.models import ModelConfig


def model_config() -> ModelConfig:
    return ModelConfig(
        name="qwen2.5-3b-instruct-gguf",
        model_id="test/model",
        model_url="https://example.test/test/model",
        api_base_url="",
        size="3B",
        download_size="1 GB",
        download_options=[{"filename": "model.gguf", "quant": "Q4_K_M"}],
        description="Test rewrite model",
        server={},
        config_path=Path("config/model/test.json"),
    )


def model_config_without_downloads() -> ModelConfig:
    config = model_config()
    return ModelConfig(
        name=config.name,
        model_id=config.model_id,
        model_url=config.model_url,
        api_base_url=config.api_base_url,
        size=config.size,
        download_size=config.download_size,
        download_options=[],
        description=config.description,
        server=config.server,
        config_path=config.config_path,
    )


def test_local_rewrite_client_invokes_downloaded_model_directly(monkeypatch):
    config = model_config()
    calls = []

    monkeypatch.setattr(rewrites, "rewrite_model_config", lambda: config)
    monkeypatch.setattr(rewrites, "selected_downloaded_option", lambda received: config.download_options[0])

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, stdout="Model rewrite.\n", stderr="")

    monkeypatch.setattr(rewrites.subprocess, "run", run)

    result = rewrites.local_rewrite_client(
        [
            {"role": "system", "content": "Use only supplied facts."},
            {"role": "user", "content": "Rewrite this backstory."},
        ]
    )

    assert result == "Model rewrite."
    command = calls[0][0]
    assert command[:5] == ["llama", "cli", "--log-disable", "--model", str(config.local_dir / "model.gguf")]
    assert "--device" in command
    assert command[command.index("--device") + 1] == "none"
    assert "--gpu-layers" in command
    assert command[command.index("--gpu-layers") + 1] == "0"
    assert "--single-turn" in command
    assert "--no-display-prompt" in command
    prompt = command[command.index("--prompt") + 1]
    assert "System:\nUse only supplied facts." in prompt
    assert "User:\nRewrite this backstory." in prompt
    assert calls[0][1]["timeout"] == 180


def test_local_rewrite_client_downloads_default_model_when_missing(monkeypatch, capsys):
    config = model_config()
    downloads = []

    monkeypatch.setattr(rewrites, "rewrite_model_config", lambda: config)
    monkeypatch.setattr(rewrites, "selected_downloaded_option", lambda received: None)
    monkeypatch.setattr(rewrites, "download_option", lambda received, option: downloads.append((received, option)))
    monkeypatch.setattr(
        rewrites.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 0, stdout="Model rewrite.\n", stderr=""),
    )

    assert rewrites.local_rewrite_client([{"role": "user", "content": "Rewrite."}]) == "Model rewrite."
    assert downloads == [(config, config.download_options[0])]
    status_output = capsys.readouterr().err
    assert "Downloading local model [#-------------------] model.gguf" in status_output
    assert "Ready local model [####################] model.gguf" in status_output


def test_local_rewrite_client_requires_downloadable_model(monkeypatch):
    monkeypatch.setattr(rewrites, "rewrite_model_config", model_config_without_downloads)
    monkeypatch.setattr(rewrites, "selected_downloaded_option", lambda received: None)

    with pytest.raises(RuntimeError, match="does not list downloadable GGUF options"):
        rewrites.local_rewrite_client([{"role": "user", "content": "Rewrite."}])


def test_local_rewrite_client_reports_cli_failure(monkeypatch):
    config = model_config()

    monkeypatch.setattr(rewrites, "rewrite_model_config", lambda: config)
    monkeypatch.setattr(rewrites, "selected_downloaded_option", lambda received: config.download_options[0])
    monkeypatch.setattr(
        rewrites.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 1, stdout="", stderr="bad model"),
    )

    with pytest.raises(RuntimeError, match="bad model"):
        rewrites.local_rewrite_client([{"role": "user", "content": "Rewrite."}])


def test_local_rewrite_client_strips_llama_loader_output(monkeypatch):
    config = model_config()
    stdout = """Loading model...


▄▄ ▄▄
██ ██
build      : b9890
model      : test/model
available commands:
  /exit or Ctrl+C     stop or exit

> User prompt

Jory Ravenmark is a Human Barbarian shaped by grief, sea-lore, and a vow to protect her community.

[ Prompt: 12.3 t/s | Generation: 4.5 t/s ]

Exiting...
"""

    monkeypatch.setattr(rewrites, "rewrite_model_config", lambda: config)
    monkeypatch.setattr(rewrites, "selected_downloaded_option", lambda received: config.download_options[0])
    monkeypatch.setattr(
        rewrites.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 0, stdout=stdout, stderr=""),
    )

    assert rewrites.local_rewrite_client([{"role": "user", "content": "Rewrite."}]) == (
        "Jory Ravenmark is a Human Barbarian shaped by grief, sea-lore, and a vow to protect her community."
    )
