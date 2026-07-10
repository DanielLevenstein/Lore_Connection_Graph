import os
import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_URL = "http://127.0.0.1:8513"


def streamlit_executable() -> Path:
    workspace_venv = ROOT_DIR.parent / ".venv/bin/streamlit"
    project_venv = ROOT_DIR / ".venv/bin/streamlit"
    if workspace_venv.exists():
        return workspace_venv
    return project_venv


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


@pytest.fixture()
def isolated_session_notes_app(tmp_path):
    docs_lore_dir = tmp_path / "docs" / "lore"
    data_dir = tmp_path / "data"
    docs_lore_dir.mkdir(parents=True)
    data_dir.mkdir()

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["LOCAL_CHATBOT_DOCS_LORE_DIR"] = str(docs_lore_dir)
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(docs_lore_dir / "character_sheets")
    env["LOCAL_CHATBOT_PLACES_DIR"] = str(docs_lore_dir / "places")
    env["LOCAL_CHATBOT_SESSION_NOTES_DIR"] = str(docs_lore_dir / "session_notes")
    env["LOCAL_CHATBOT_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        [
            str(streamlit_executable()),
            "run",
            "streamlit_app.py",
            "--server.port",
            "8513",
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
        yield APP_URL, docs_lore_dir
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def test_ui_saves_dated_session_notes(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        expect(page.get_by_role("heading", name="Session Notes", exact=True)).to_be_visible(timeout=10000)
        page.get_by_text("Capture Session Notes", exact=True).click()
        page.get_by_role("textbox", name="Session Notes").fill(
            "2026-07-10\n"
            "The party found a silver key.\n\n"
            "2026-07-11\n"
            "The party opened the lighthouse door."
        )
        page.get_by_role("button", name="note_add Save Session Notes").click()
        expect(page.get_by_text("Saved 2 Session Note Files.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="2026-07-10 - Session Notes", exact=True)).to_be_visible(timeout=10000)
        browser.close()

    first = notes_dir / "2026-07-10_Session_Notes.md"
    second = notes_dir / "2026-07-11_Session_Notes.md"
    assert first.exists()
    assert second.exists()
    assert "silver key" in first.read_text(encoding="utf-8")
    assert "lighthouse door" in second.read_text(encoding="utf-8")


def test_ui_imports_discord_session_notes_with_markdown_and_date_field(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    import_file = docs_lore_dir / "discord_import.md"
    import_file.write_text(
        """Sean [OOZE], Server Tag: OOZEOOZE — 7/10/26, 11:36 PMFriday, July 10, 2026 at 11:36 PM
Session 12:

## Scene Notes

- Found a **silver key**
- Met `Jory`

| Clue | Status |
| ---- | ------ |
| Door | Open |

Session 13:

## Second Scene

- Preserved in the same note
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_text("Import Session Notes", exact=True).first.click()
        page.locator("input[type=file]").set_input_files(str(import_file))
        page.get_by_label("Split Session Headings Into Separate Notes").uncheck(force=True)
        page.get_by_role("button", name="upload_file Import Session Notes").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="2026-07-10 - Sessions 12-13", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Scene Notes", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Second Scene", exact=True)).to_be_visible(timeout=10000)
        page.get_by_text("Edit Session Note", exact=True).click()
        expect(page.get_by_role("textbox", name="Date")).to_have_value("2026-07-10", timeout=10000)
        browser.close()

    imported = notes_dir / "2026-07-10_Sessions_12_13.md"
    assert imported.exists()
    text = imported.read_text(encoding="utf-8")
    assert "## Scene Notes" in text
    assert "## Second Scene" in text
    assert "- Found a **silver key**" in text
    assert "| Clue | Status |" in text
