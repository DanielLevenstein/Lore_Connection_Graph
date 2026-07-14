#!/usr/bin/env python3
"""Start a local model server using a JSON config file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from model_harness.models import _read_config
from model_harness.server import start_server, status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="Path to a config/model/*.json model config")
    parser.add_argument("--wait", type=int, default=0, help="Seconds to wait for the health endpoint")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _read_config(Path(args.config))
    current = status(config)
    if current.running or current.healthy:
        print(f"{config.name} server already running; pid={current.pid}, healthy={current.healthy}")
        return
    started = start_server(config, wait_seconds=args.wait)
    print(f"Started {config.name}; pid={started.pid}, healthy={started.healthy}")
    print(f"Log: {started.log_path}")


if __name__ == "__main__":
    main()
