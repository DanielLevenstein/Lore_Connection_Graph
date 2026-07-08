#!/usr/bin/env python3
"""Download one model artifact described by a JSON config file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from language_model_harness import configure_language_model_harness

configure_language_model_harness()

from model_harness.downloads import default_download_option, download_option, option_by_filename
from model_harness.models import _read_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="Path to a config/*.json model config")
    parser.add_argument("--filename", help="Exact artifact filename to download")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _read_config(Path(args.config))
    if not config.download_options:
        raise SystemExit(f"{config.name} does not list downloadable artifact options.")

    option = option_by_filename(config, args.filename) if args.filename else default_download_option(config)
    if not option:
        raise SystemExit("Could not find a matching download option.")

    print(f"Downloading {option['filename']} to {config.local_dir}")
    path = download_option(config, option)
    print(f"Downloaded {path}")


if __name__ == "__main__":
    main()
