#!/usr/bin/env python3
"""Create per-artifact download manifests for already-downloaded model files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from local_chatbot.downloads import downloaded_options, manifest_path, write_download_manifest, write_downloads_index
from local_chatbot.models import _read_config, list_model_configs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configs", nargs="*", help="Optional config JSON paths. Defaults to all configs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = [_read_config(Path(path)) for path in args.configs] if args.configs else list_model_configs()
    for config in configs:
        options = downloaded_options(config)
        if not options:
            print(f"No downloaded artifacts for {config.name}")
            continue
        for option in options:
            write_download_manifest(config, option)
            print(f"Wrote {manifest_path(config, option)}")
        write_downloads_index(config)


if __name__ == "__main__":
    main()
