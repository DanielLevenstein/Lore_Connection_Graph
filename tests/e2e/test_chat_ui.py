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


def test_real_model_chat_returns_valid_response(streamlit_app):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(streamlit_app, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Bubble Gum")).to_be_visible(timeout=10000)
        expect(page.get_by_text("Model server ready", exact=False)).to_be_visible(timeout=15000)
        chat_input = page.get_by_placeholder("Message Bubble Gum")
        expect(chat_input).to_be_visible()

        prompt = "Miss Bubble Gum, what is your name?"
        chat_input.fill(prompt)
        chat_input.press("Enter")

        expect(page.get_by_text(prompt)).to_be_visible(timeout=10000)
        expect(page.get_by_text("AttributeError")).not_to_be_visible()
        expect(page.get_by_text("Local model error")).not_to_be_visible(timeout=30000)
        page.wait_for_function(
            """
            () => {
              const text = document.body.innerText;
              const prompt = "Miss Bubble Gum, what is your name?";
              const promptIndex = text.indexOf(prompt);
              if (promptIndex < 0) return false;
              const afterPrompt = text.slice(promptIndex + prompt.length);
              return !afterPrompt.includes("Thinking locally...")
                && !afterPrompt.includes("Local model error")
                && afterPrompt.trim().length > 80;
            }
            """,
            timeout=60000,
        )
        browser.close()
