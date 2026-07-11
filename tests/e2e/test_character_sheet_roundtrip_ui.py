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
    save_button = page.get_by_role("button", name="save Save Character").first
    if not save_button.is_visible():
        page.get_by_text("Edit Character", exact=True).click()
        save_button = page.get_by_role("button", name="save Save Character").first
    expect(save_button).to_be_visible(timeout=10000)
    save_button = page.get_by_role("button", name="save Save Character").first
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
        page.get_by_text("Add Session Note", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def ensure_session_note_editor_open(page) -> None:
    save_button = page.get_by_role("button", name="save Save Session Note")
    if not save_button.is_visible():
        page.get_by_text("Edit Session Note", exact=True).click()
    expect(save_button).to_be_visible(timeout=10000)


def fill_textbox(page, name: str, value: str, index: int = 0) -> None:
    page.get_by_role("textbox", name=name, exact=True).nth(index).fill(value)


def click_form_button_by_save_button(page, save_button_name: str, target_button_name: str) -> None:
    form = page.locator("form").filter(has=page.get_by_role("button", name=save_button_name)).first
    button = form.get_by_role("button", name=target_button_name)
    if button.count():
        button.click(force=True)
        return
    page.get_by_role("button", name=target_button_name).first.click(force=True)


def click_place_undo_button(page) -> None:
    click_form_button_by_save_button(page, "save Save Place", "undo Undo Changes")


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


def test_ui_hides_legacy_autogenerated_marker_from_character_name(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app
    legacy_path = characters_dir / "Legacy_Hero.md"
    legacy_path.write_text(
        """# Legacy Hero - Autogenerated

## Character Stats

| Name | Race | Class |
| ---- | ---- | ----- |
| Legacy Hero | Human | Bard |

## Character Backstory

Legacy Hero is a test character.

## Character Summary

Legacy Hero is a legacy generated character.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        page.get_by_role("combobox", name="Existing Characters").click()
        page.get_by_role("option", name="Legacy Hero", exact=True).click()
        page.get_by_role("button", name="Open Character").click()
        expect(page.get_by_role("heading", name="Legacy Hero", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_text("Legacy Hero - Autogenerated")).not_to_be_visible()
        browser.close()


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
        page.get_by_role("button", name="save Save Character").first.click(force=True)
        expect(page.get_by_text("Character Saved.")).to_be_visible(timeout=10000)

        ensure_character_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").first.click()
        expect(page.get_by_text("Character Changes Undone.")).to_be_visible(timeout=10000)
        ensure_character_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").first.click()
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
        page.get_by_role("textbox", name="Place Markdown", exact=True).fill(
            "# Brindle Hall\n\nA narrow guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives."
        )
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_role("heading", name="Brindle Hall", exact=True).last).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Notes", exact=True)).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Place Files").click()
        page.get_by_role("option", name="Brindle Hall (Brindle Hall.md)", exact=True).click()
        page.get_by_role("button", name="location_on Open Place").click()
        ensure_place_editor_open(page)
        page.get_by_role("textbox", name="Place Markdown", exact=True).fill(
            "# Brindle Hall\n\nA crowded guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives."
        )
        page.get_by_role("button", name="save Save Place").click(force=True)
        expect(page.get_by_text("Place Saved.")).to_be_visible(timeout=10000)

        ensure_place_editor_open(page)
        page.get_by_role("textbox", name="Place Markdown", exact=True).fill("# Brindle Hall\n\nA ruined guildhall after the fire.")
        page.get_by_role("button", name="save Save Place").click(force=True)
        expect(page.get_by_text("Place Saved.")).to_be_visible(timeout=10000)

        ensure_place_editor_open(page)
        click_place_undo_button(page)
        expect(page.get_by_text("Place Changes Undone.")).to_be_visible(timeout=10000)
        ensure_place_editor_open(page)
        expect(page.get_by_role("textbox", name="Place Markdown", exact=True)).to_have_value(
            "# Brindle Hall\n\nA crowded guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives.",
            timeout=10000,
        )
        click_place_undo_button(page)
        expect(page.get_by_text("Place Changes Undone.")).to_be_visible(timeout=10000)
        ensure_place_editor_open(page)
        expect(page.get_by_role("textbox", name="Place Markdown", exact=True)).to_have_value(
            "# Brindle Hall\n\nA narrow guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives.",
            timeout=10000,
        )
        browser.close()

    text = place_path.read_text(encoding="utf-8")
    assert text.startswith("# Brindle Hall")
    assert "A narrow guildhall where maps are traded." in text
    assert "## Notes" in text


def test_ui_creates_loads_and_undoes_session_notes(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, session_notes_dir, _data_dir = isolated_character_app
    note_path = session_notes_dir / "2026-07-10_Session_Notes.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        ensure_session_notes_open(page)
        page.get_by_role("textbox", name="Session Notes").fill("2026-07-10\nThe party found a silver key.")
        page.get_by_role("button", name="note_add Save Session Notes").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Session Notes (2026-07-10_Session_Notes.md)", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party found a silver key.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Title").fill("Silver Key")
        expect(page.get_by_role("textbox", name="Title")).to_have_value("Silver Key", timeout=10000)
        page.wait_for_timeout(300)
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note").fill("The party found a silver key and a brass map.")
        page.get_by_role("button", name="Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Saved.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Silver Key", exact=True)).to_be_visible(timeout=10000)
        expect(page.locator("p").filter(has_text="The party found a silver key and a brass map.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note").fill("The party lost the key.")
        page.get_by_role("button", name="Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Saved.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").last.click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Changes Undone.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").last.click()
        open_tab(page, "Session Notes")
        expect(page.get_by_text("Session Note Changes Undone.")).to_be_visible(timeout=10000)
        browser.close()

    assert note_path.exists()
    assert "# Session Notes - 2026-07-10 - Session Notes\n" in note_path.read_text(encoding="utf-8")
    assert "silver key" in note_path.read_text(encoding="utf-8")
    assert "brass map" not in note_path.read_text(encoding="utf-8")


def test_create_validation_preserves_entered_fields(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        expand_section(page, "Create Character")
        fill_textbox(page, "Name", "Keeps Draft")
        fill_textbox(page, "Race", "Human")
        fill_textbox(page, "Class", "Bard")
        page.get_by_role("button", name="person_add Create Character").click()
        expect(page.get_by_text("Complete Name, Race, Class, And Backstory.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Name", exact=True).first).to_have_value("Keeps Draft")
        expect(page.get_by_role("textbox", name="Race", exact=True).first).to_have_value("Human")
        expect(page.get_by_role("textbox", name="Class", exact=True).first).to_have_value("Bard")

        open_tab(page, "Places")
        expand_section(page, "Create Place")
        fill_textbox(page, "Name", "Draft Hall")
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_text("Complete Name And Place Markdown.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Name", exact=True).first).to_have_value("Draft Hall")

        open_tab(page, "Session Notes")
        ensure_session_notes_open(page)
        page.get_by_role("textbox", name="Title").fill("Draft Session")
        page.get_by_role("button", name="note_add Save Session Notes").click()
        expect(page.get_by_text("Add Session Notes Before Saving.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Title")).to_have_value("Draft Session")
        browser.close()


def test_ui_deletes_character_place_and_session_note_files(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, places_dir, session_notes_dir, _data_dir = isolated_character_app
    character_path = characters_dir / "Delete Me.md"
    place_path = places_dir / "Delete Hall.md"
    note_path = session_notes_dir / "2026-07-10_Session_Notes.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        expand_section(page, "Create Character")
        fill_textbox(page, "Name", "Delete Me")
        fill_textbox(page, "First Name", "Delete")
        fill_textbox(page, "Family Name", "Me")
        fill_textbox(page, "Level", "1")
        fill_textbox(page, "Race", "Human")
        fill_textbox(page, "Class", "Commoner")
        fill_textbox(page, "Pronouns", "they/them")
        page.get_by_role("textbox", name="Backstory", exact=True).fill("A temporary character for deletion.")
        page.get_by_role("textbox", name="Summary", exact=True).fill("Temporary.")
        page.get_by_role("button", name="person_add Create Character").click()
        expect(page.get_by_role("heading", name="Delete Me", exact=True)).to_be_visible(timeout=10000)
        ensure_character_editor_open(page)
        page.get_by_role("button", name="delete_forever Delete Character").click()
        expect(page.get_by_text("Character Deleted.")).to_be_visible(timeout=10000)

        open_tab(page, "Places")
        expand_section(page, "Create Place")
        fill_textbox(page, "Name", "Delete Hall")
        page.get_by_role("textbox", name="Place Markdown", exact=True).fill("# Delete Hall\n\nA temporary place for deletion.")
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_role("heading", name="Delete Hall", exact=True).last).to_be_visible(timeout=10000)
        ensure_place_editor_open(page)
        page.get_by_role("button", name="delete_forever Delete Place").click()
        expect(page.get_by_text("Place Deleted.")).to_be_visible(timeout=10000)

        open_tab(page, "Session Notes")
        ensure_session_notes_open(page)
        page.get_by_role("textbox", name="Session Notes").fill("2026-07-10\nA temporary note for deletion.")
        page.get_by_role("button", name="note_add Save Session Notes").click()
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="delete_forever Delete Session Note").click()
        expect(page.get_by_text("Session Note Deleted.")).to_be_visible(timeout=10000)
        browser.close()

    assert not character_path.exists()
    assert not place_path.exists()
    assert not note_path.exists()


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
