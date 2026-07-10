import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from local_chatbot.storage import Character, read_character_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_URL = "http://127.0.0.1:8512"


def streamlit_executable() -> Path:
    project_venv = ROOT_DIR / ".venv/bin/streamlit"
    workspace_venv = ROOT_DIR.parent / ".venv/bin/streamlit"
    if project_venv.exists():
        return project_venv
    return workspace_venv


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
    output = process.stdout.read() if process.stdout else ""
    raise TimeoutError(f"Streamlit app did not start at {url}\n{output}")


def markdown_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ")


@pytest.fixture()
def isolated_character_app(tmp_path):
    characters_dir = tmp_path / "docs" / "lore" / "character_sheets"
    data_dir = tmp_path / "data"
    shutil.copytree(ROOT_DIR / "docs" / "lore" / "character_sheets", characters_dir)
    data_dir.mkdir()

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(characters_dir)
    env["LOCAL_CHATBOT_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        [
            str(streamlit_executable()),
            "run",
            "streamlit_app.py",
            "--server.port",
            "8512",
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
        yield APP_URL, characters_dir, data_dir
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def select_character(page, character_label: str, index: int) -> None:
    if index > 0:
        page.get_by_role("combobox", name="Existing Characters").click()
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
    page.get_by_role("button", name="Open Character").click()
    expect(page.get_by_role("heading", name=character_label, exact=True)).to_be_visible(timeout=10000)


def wait_for_profile_write(data_dir: Path, character_file: Path, timeout: int = 10) -> None:
    profile_path = data_dir / "lore" / "character_sheets" / character_file.stem / "PROFILE.json"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if profile_path.exists():
            return
        time.sleep(0.1)
    raise AssertionError(f"UI save did not write {profile_path}")


def save_open_character(page, data_dir: Path, character_file: Path) -> None:
    save_button = page.get_by_role("button", name="save Save Character")
    if not save_button.is_visible():
        page.get_by_text("Edit Character", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)
    save_button.scroll_into_view_if_needed()
    save_button.click(force=True)
    wait_for_profile_write(data_dir, character_file)


def test_ui_save_preserves_sheet_values_and_normalizes_details(isolated_character_app):
    app_url, characters_dir, data_dir = isolated_character_app
    character_files = sorted(path for path in characters_dir.glob("*.md") if path.name != "TEMPLATE.md")
    labels = {path.name: markdown_title(path) for path in character_files}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        for index, path in enumerate(character_files):
            select_character(page, labels[path.name], index)
            save_open_character(page, data_dir, path)

        browser.close()

    for path in character_files:
        text = path.read_text(encoding="utf-8")
        profile = read_character_profile(Character(name=path.stem, path=path))
        assert profile.race
        assert profile.character_class
        if path.name == "Neal_Lovington.md":
            assert "| Mx. Lovington |" in text
            assert "Favorite Color: Pink" in text
