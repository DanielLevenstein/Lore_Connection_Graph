import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from local_chatbot.storage import Character, Place, read_character_profile, read_place_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_URL = "http://127.0.0.1:8512"
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"


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


def markdown_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ")


@pytest.fixture()
def isolated_character_app(tmp_path):
    docs_lore_dir = tmp_path / "docs" / "lore"
    characters_dir = docs_lore_dir / "character_sheets"
    places_dir = docs_lore_dir / "places"
    session_notes_dir = docs_lore_dir / "session_notes"
    data_dir = tmp_path / "data"
    shutil.copytree(FIXTURE_CHARACTER_SHEETS_DIR, characters_dir)
    places_dir.mkdir(parents=True)
    session_notes_dir.mkdir(parents=True)
    data_dir.mkdir()

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH"] = "1"
    env["LOCAL_CHATBOT_DOCS_LORE_DIR"] = str(docs_lore_dir)
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(characters_dir)
    env["LOCAL_CHATBOT_PLACES_DIR"] = str(places_dir)
    env["LOCAL_CHATBOT_SESSION_NOTES_DIR"] = str(session_notes_dir)
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
        yield APP_URL, docs_lore_dir, characters_dir, places_dir, session_notes_dir, data_dir
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def select_character(page, character_label: str, index: int) -> None:
    if page.get_by_role("heading", name=character_label, exact=True).is_visible():
        return
    combobox = page.get_by_role("combobox", name="Existing Characters")
    combobox.scroll_into_view_if_needed()
    combobox.click()
    page.keyboard.press("Home")
    for _ in range(index):
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


def open_tab(page, name: str) -> None:
    page.get_by_role("tab", name=name, exact=True).click()


def expand_section(page, name: str) -> None:
    page.get_by_text(name, exact=True).first.click()


def ensure_character_editor_open(page) -> None:
    save_button = page.get_by_role("button", name="save Save Character")
    if not save_button.is_visible():
        page.get_by_text("Edit Character", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def ensure_place_editor_open(page) -> None:
    save_button = page.get_by_role("button", name="save Save Place")
    if not save_button.is_visible():
        page.get_by_text("Edit Place", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def ensure_session_notes_open(page) -> None:
    save_button = page.get_by_role("button", name="note_add Save Session Notes")
    if not save_button.is_visible():
        page.get_by_text("Capture Session Notes", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def ensure_session_note_editor_open(page) -> None:
    save_button = page.get_by_role("button", name="Save Session Note")
    if not save_button.is_visible():
        page.get_by_text("Edit Session Note", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def fill_textbox(page, name: str, value: str, index: int = 0) -> None:
    page.get_by_role("textbox", name=name, exact=True).nth(index).fill(value)


def test_ui_save_preserves_sheet_values_and_normalizes_details(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, data_dir = isolated_character_app
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


def test_ui_creates_loads_and_undoes_character_changes(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app
    character_path = characters_dir / "Della Moor.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        expand_section(page, "Create Character")
        fill_textbox(page, "Name", "Della Moor")
        fill_textbox(page, "First Name", "Della")
        fill_textbox(page, "Family Name", "Moor")
        fill_textbox(page, "Level", "5")
        fill_textbox(page, "Race", "Gnome")
        fill_textbox(page, "Class", "Rogue")
        fill_textbox(page, "Pronouns", "she/her")
        page.get_by_role("textbox", name="Backstory", exact=True).fill("Della maps locked doors beneath the old city.")
        page.get_by_role("textbox", name="Summary", exact=True).fill("Della is a careful scout.")
        page.get_by_role("button", name="person_add Create Character").click()
        expect(page.get_by_role("heading", name="Della Moor", exact=True)).to_be_visible(timeout=10000)

        ensure_character_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).first.fill("Della is a careful scout with brass lockpicks.")
        page.get_by_role("button", name="save Save Character").click()
        expect(page.get_by_text("Character Saved.")).to_be_visible(timeout=10000)

        ensure_character_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).first.fill("Della is a reckless scout tonight.")
        page.get_by_role("button", name="save Save Character").click()
        expect(page.get_by_text("Character Saved.")).to_be_visible(timeout=10000)

        ensure_character_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        expect(page.get_by_text("Character Changes Undone.")).to_be_visible(timeout=10000)
        ensure_character_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        expect(page.get_by_text("Character Changes Undone.")).to_be_visible(timeout=10000)
        browser.close()

    profile = read_character_profile(Character(name="Della Moor", path=character_path))
    assert profile.name == "Della Moor"
    assert profile.first_name == "Della"
    assert profile.family_name == "Moor"
    assert profile.level == "5"
    assert profile.race == "Gnome"
    assert profile.character_class == "Rogue"
    assert profile.pronouns == "she/her"
    assert profile.backstory == "Della maps locked doors beneath the old city."
    assert profile.summary == "Della is a careful scout."


def test_ui_creates_loads_and_undoes_place_changes(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, places_dir, _session_notes_dir, _data_dir = isolated_character_app
    place_path = places_dir / "Brindle Hall.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Places")
        expect(page.get_by_role("heading", name="Places")).to_be_visible(timeout=10000)
        expand_section(page, "Create Place")
        fill_textbox(page, "Name", "Brindle Hall")
        fill_textbox(page, "Type", "Guildhall")
        page.get_by_role("textbox", name="Summary", exact=True).fill("A narrow guildhall where maps are traded.")
        page.get_by_role("textbox", name="Place Details", exact=True).fill("Lanterns burn blue near the archives.")
        page.get_by_role("textbox", name="Place Connections", exact=True).fill("Della Moor: Stores maps")
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_role("heading", name="Brindle Hall", exact=True)).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Existing Places").click()
        page.get_by_role("option", name="Brindle Hall", exact=True).click()
        page.get_by_role("button", name="location_on Open Place").click()
        ensure_place_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).fill("A crowded guildhall where maps are traded.")
        page.get_by_role("button", name="save Save Place").click(force=True)
        expect(page.get_by_text("Place Saved.")).to_be_visible(timeout=10000)

        ensure_place_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).fill("A ruined guildhall after the fire.")
        page.get_by_role("button", name="save Save Place").click(force=True)
        expect(page.get_by_text("Place Saved.")).to_be_visible(timeout=10000)

        ensure_place_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        expect(page.get_by_text("Place Changes Undone.")).to_be_visible(timeout=10000)
        ensure_place_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        expect(page.get_by_text("Place Changes Undone.")).to_be_visible(timeout=10000)
        browser.close()

    profile = read_place_profile(Place(name="Brindle Hall", path=place_path))
    assert profile.name == "Brindle Hall"
    assert profile.place_type == "Guildhall"
    assert profile.summary == "A narrow guildhall where maps are traded."
    assert profile.details == "Lanterns burn blue near the archives."
    assert profile.connections == ["Della Moor: Stores maps"]


def test_ui_creates_loads_and_undoes_session_notes(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, session_notes_dir, _data_dir = isolated_character_app
    note_path = session_notes_dir / "2026-07-10_Session_Notes.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Session Notes", exact=True)).to_be_visible(timeout=10000)
        ensure_session_notes_open(page)
        page.get_by_role("textbox", name="Session Notes").fill("2026-07-10\nThe party found a silver key.")
        page.get_by_role("button", name="note_add Save Session Notes").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="2026-07-10 - Session Notes", exact=True)).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Existing Session Notes").click()
        page.get_by_role("option", name="2026-07-10 - Session Notes", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party found a silver key.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Title").fill("Silver Key")
        page.get_by_role("textbox", name="Session Note").fill("The party found a silver key and a brass map.")
        page.get_by_role("button", name="Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Saved.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="2026-07-10 - Silver Key", exact=True)).to_be_visible(timeout=10000)
        expect(page.locator("p").filter(has_text="The party found a silver key and a brass map.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note").fill("The party lost the key.")
        page.get_by_role("button", name="Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Saved.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Changes Undone.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Changes Undone.")).to_be_visible(timeout=10000)
        browser.close()

    assert note_path.exists()
    assert "# Session Notes - 2026-07-10 - Session Notes\n" in note_path.read_text(encoding="utf-8")
    assert "silver key" in note_path.read_text(encoding="utf-8")
    assert "brass map" not in note_path.read_text(encoding="utf-8")


def test_ui_creates_character_from_combined_graph_and_loads_it(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app
    original_files = {path.name for path in characters_dir.glob("*.md")}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        page.get_by_text("Combined Knowledge Graph", exact=True).last.click()
        page.get_by_role("button", name="Create Character File").click()
        expect(page.get_by_text("Draft Character")).to_be_visible(timeout=10000)
        page.get_by_role("textbox", name="Race", exact=True).first.fill("Human")
        page.get_by_role("textbox", name="Class", exact=True).first.fill("Commoner")
        page.get_by_role("button", name="person_add Create Character", exact=True).click()

        deadline = time.monotonic() + 10
        created_files = []
        while time.monotonic() < deadline:
            created_files = [path for path in characters_dir.glob("*.md") if path.name not in original_files]
            if created_files:
                break
            time.sleep(0.1)
        assert created_files
        created_title = markdown_title(created_files[0])
        select_character(page, created_title, 0)
        expect(page.get_by_role("heading", name=created_title, exact=True)).to_be_visible(timeout=10000)
        browser.close()
