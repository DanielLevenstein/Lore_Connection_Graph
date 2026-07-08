#!/usr/bin/env python3
"""Generate random local D&D-style characters."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from local_chatbot.character_generator import RandomCharacterGenerator
from local_chatbot.client import LocalModelError
from local_chatbot.models import ModelConfig, list_model_configs
from local_chatbot.server import status
from local_chatbot.storage import render_backstory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1, help="Number of characters to create")
    parser.add_argument("--seed", type=int, help="Optional random seed")
    parser.add_argument("--preview", action="store_true", help="Print generated profiles without writing files")
    parser.add_argument(
        "--model",
        help="Downloaded model config name to use. Defaults to the first downloaded model.",
    )
    return parser.parse_args()


def select_model_config(model_name: str | None) -> ModelConfig:
    configs = list_model_configs(downloaded_only=True)
    if model_name:
        match = next((config for config in configs if config.name == model_name), None)
        if match:
            return match
        names = ", ".join(config.name for config in configs) or "none"
        raise SystemExit(f"Downloaded model config not found: {model_name}. Downloaded configs: {names}")
    if not configs:
        raise SystemExit("No downloaded model configs found. Download a model first.")
    return configs[0]


def start_instructions(config: ModelConfig) -> str:
    command = [
        ".venv/bin/python",
        "scripts/start_model_server.py",
        str(config.config_path),
        "--wait",
        "30",
    ]
    return (
        "The selected model server is not ready.\n\n"
        "Start it from the app sidebar with the Start model button, or run:\n"
        f"  {shlex.join(command)}\n\n"
        f"Then retry this command after {config.api_base_url.rstrip('/')}/models responds."
    )


def require_ready_model(config: ModelConfig) -> None:
    model_status = status(config)
    if not model_status.healthy:
        raise SystemExit(start_instructions(config))


def main() -> None:
    args = parse_args()
    generator = RandomCharacterGenerator(seed=args.seed)
    model_config = select_model_config(args.model)
    require_ready_model(model_config)
    if args.preview:
        try:
            profiles = generator.generate_profiles(args.count, model_config)
        except (LocalModelError, ValueError) as exc:
            raise SystemExit(f"Could not generate model-backed characters: {exc}") from exc
        for index, profile in enumerate(profiles):
            if index:
                print("\n---\n")
            print(render_backstory(profile), end="")
        return

    try:
        characters = generator.create_characters(args.count, model_config)
    except (LocalModelError, ValueError) as exc:
        raise SystemExit(f"Could not generate model-backed characters: {exc}") from exc
    for character in characters:
        print(f"Created {character.path}")


if __name__ == "__main__":
    main()
