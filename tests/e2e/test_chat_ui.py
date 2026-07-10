import os
import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_URL = "http://127.0.0.1:8511"


def wait_for_streamlit(url: str, process: subprocess.Popen, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"Streamlit exited before startup.\n{output}")
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    output = ""
    if process.stdout:
        try:
            output = process.stdout.read()
        except Exception:
            output = ""
    raise TimeoutError(f"Streamlit app did not start at {url}\n{output}")


@pytest.fixture(scope="module")
def streamlit_app():
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    process = subprocess.Popen(
        [
            str(ROOT_DIR / ".venv/bin/streamlit"),
            "run",
            "streamlit_app.py",
            "--server.port",
            "8511",
            "--server.headless",
            "true",
        ],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_streamlit(APP_URL, process)
        yield APP_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

