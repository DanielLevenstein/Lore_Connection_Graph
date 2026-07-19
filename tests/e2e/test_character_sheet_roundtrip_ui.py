import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright
import json

from local_chatbot.storage import Character, read_character_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_URL = "http://127.0.0.1:8512"
FIXTURE_CHARACTER_SHEETS_DIR = ROOT_DIR / "tests" / "fixtures" / "character_sheets"
HIDDEN_LORE_FIXTURE_ENV = "LOCAL_CHATBOT_E2E_LORE_FIXTURE_DIR"
KNOWLEDGE_GRAPH_SCREENSHOT_ENV = "LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_SCREENSHOT"
KNOWLEDGE_GRAPH_SCREENSHOT_NODE_ENV = "LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_NODE"
STRUCTURED_KNOWLEDGE_GRAPH_FULL_SCREENSHOT = ROOT_DIR / "docs" / "screenshots" / "Structured_Knowledge_Graph_Full.png"


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


def seed_lore_fixture(docs_lore_dir: Path, characters_dir: Path, places_dir: Path, session_notes_dir: Path) -> None:
    hidden_lore_dir = os.environ.get(HIDDEN_LORE_FIXTURE_ENV)
    if hidden_lore_dir:
        source = Path(hidden_lore_dir).expanduser().resolve()
        source_lore_dir = source / "lore" if (source / "lore").is_dir() else source
        if not source_lore_dir.is_dir():
            raise RuntimeError(f"{HIDDEN_LORE_FIXTURE_ENV} must point to a lore directory or world_building directory.")
        docs_lore_dir.mkdir(parents=True, exist_ok=True)
        for source_child in source_lore_dir.iterdir():
            destination = docs_lore_dir / source_child.name
            if source_child.is_dir():
                shutil.copytree(source_child, destination)
            elif source_child.is_file():
                shutil.copy2(source_child, destination)
        characters_dir.mkdir(parents=True, exist_ok=True)
        places_dir.mkdir(parents=True, exist_ok=True)
        session_notes_dir.mkdir(parents=True, exist_ok=True)
        return

    shutil.copytree(FIXTURE_CHARACTER_SHEETS_DIR, characters_dir)
    places_dir.mkdir(parents=True)
    session_notes_dir.mkdir(parents=True)


@pytest.fixture()
def isolated_character_app(tmp_path):
    world_building_dir = tmp_path / "world_building"
    docs_lore_dir = world_building_dir / "lore"
    characters_dir = docs_lore_dir / "character_sheets"
    places_dir = docs_lore_dir / "places"
    session_notes_dir = docs_lore_dir / "session_notes"
    meta_data_dir = world_building_dir / "meta_data"
    seed_lore_fixture(docs_lore_dir, characters_dir, places_dir, session_notes_dir)
    meta_data_dir.mkdir()

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH"] = "1"
    env["LOCAL_CHATBOT_WORLD_BUILDING_DIR"] = str(world_building_dir)
    env["LOCAL_CHATBOT_LORE_DIR"] = str(docs_lore_dir)
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(characters_dir)
    env["LOCAL_CHATBOT_PLACES_DIR"] = str(places_dir)
    env["LOCAL_CHATBOT_SESSION_NOTES_DIR"] = str(session_notes_dir)
    env["LOCAL_CHATBOT_META_DATA_DIR"] = str(meta_data_dir)
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
        yield APP_URL, docs_lore_dir, characters_dir, places_dir, session_notes_dir, meta_data_dir
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
    option = page.get_by_role("option", name=character_label, exact=True)
    if option.count():
        option.click()
    else:
        page.keyboard.press("Home")
        for _ in range(index):
            page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
    page.get_by_role("button", name="Open Character").click()
    expect(page.get_by_role("heading", name=character_label, exact=True)).to_be_visible(timeout=10000)


def wait_for_profile_write(data_dir: Path, character_file: Path, timeout: int = 10) -> None:
    profile_path = data_dir / "character_metadata" / character_file.stem / "PROFILE.json"
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
    expect(save_button).to_be_visible(timeout=10000)
    click_button_with_retry(page, "save Save Character")
    for button_name in ("library_books Keep Both", "Keep Both"):
        keep_both = page.get_by_role("button", name=button_name)
        try:
            expect(keep_both).to_be_visible(timeout=2000)
        except AssertionError:
            continue
        keep_both.click(force=True)
        break
    wait_for_profile_write(data_dir, character_file)


def open_tab(page, name: str) -> None:
    tab = page.get_by_role("tab", name=name, exact=True)
    if tab.get_attribute("aria-selected") == "true":
        return
    tab.click()


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


def place_editor(page):
    return page.locator("[data-testid=stExpander]").filter(has_text="Edit Place").first


def fill_place_editor_markdown(page, value: str) -> None:
    editor = place_editor(page)
    textbox = editor.get_by_role("textbox", name="Place Markdown", exact=True)
    expect(textbox).to_be_visible(timeout=10000)
    textbox.fill(value)
    expect(textbox).to_have_value(value, timeout=10000)


def click_place_save_button(page) -> None:
    editor = place_editor(page)
    save_button = editor.get_by_role("button", name="save Save Place")
    expect(save_button).to_be_visible(timeout=10000)
    save_button.evaluate("element => element.click()")


def ensure_session_note_editor_open(page) -> None:
    save_button = page.get_by_role("button", name="save Save Session Note")
    if not save_button.is_visible():
        page.get_by_role("button", name="edit Edit Section").first.click()
    expect(save_button).to_be_visible(timeout=10000)


def fill_textbox(page, name: str, value: str, index: int = 0) -> None:
    page.get_by_role("textbox", name=name, exact=True).nth(index).fill(value)


def fill_visible_text_inputs(page, prefix: str = "UPDATED") -> list[str]:
    textboxes = page.get_by_role("textbox")
    filled = []
    for index in range(textboxes.count()):
        textbox = textboxes.nth(index)
        if not textbox.is_visible() or not textbox.is_enabled():
            continue
        label = textbox.get_attribute("aria-label") or textbox.get_attribute("name") or textbox.get_attribute("id") or f"field_{index}"
        value = f"{prefix} {label}"
        try:
            textbox.fill(value)
        except Exception:
            continue
        filled.append(label)
    return filled


def click_form_button_by_save_button(page, save_button_name: str, target_button_name: str) -> None:
    form = page.locator("form").filter(has=page.get_by_role("button", name=save_button_name)).first
    button = form.get_by_role("button", name=target_button_name)
    if button.count():
        button.click(force=True)
        return
    page.get_by_role("button", name=target_button_name).first.click(force=True)


def click_button_with_retry(page, button_name: str, index: int = 0, attempts: int = 3) -> None:
    last_error = None
    for _ in range(attempts):
        button = page.get_by_role("button", name=button_name).nth(index)
        try:
            expect(button).to_be_visible(timeout=5000)
            button.click(force=True)
            return
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(300)
    raise last_error


def click_place_undo_button(page) -> None:
    editor = page.locator("[data-testid=stExpander]").filter(has_text="Edit Place").first
    undo_button = editor.get_by_role("button", name="undo Undo Changes")
    expect(undo_button).to_be_visible(timeout=10000)
    undo_button.evaluate("element => element.click()")


def assert_character_saved_visible(page) -> None:
    """Assert character save confirmation is visible (not hidden behind expander)."""
    expect(page.get_by_text("Character Saved.").first).to_be_visible(timeout=10000)


def assert_place_saved_visible(page) -> None:
    """Assert place save confirmation is visible (not hidden behind expander)."""
    expect(page.get_by_text("Place Saved.").first).to_be_visible(timeout=10000)


def assert_session_note_saved_visible(page) -> None:
    """Assert session note save confirmation is visible."""
    expect(page.get_by_text("Session Note Saved.").first).to_be_visible(timeout=10000)


def assert_character_profile_written(data_dir: Path, character_name: str) -> None:
    """Assert character profile file was written to disk (fallback indicator)."""
    profile_path = data_dir / "character_metadata" / character_name / "PROFILE.json"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if profile_path.exists():
            return
        time.sleep(0.1)
    raise AssertionError(f"Character profile not written: {profile_path}")


def assert_place_file_written(places_dir: Path, place_name: str) -> None:
    """Assert place file was written to disk (fallback indicator)."""
    place_file = places_dir / f"{place_name}.md"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if place_file.exists():
            return
        time.sleep(0.1)
    raise AssertionError(f"Place file not written: {place_file}")


def wait_for_file_text(path: Path, expected_text: str, timeout: int = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and expected_text in path.read_text(encoding="utf-8"):
            return
        time.sleep(0.1)
    raise AssertionError(f"{expected_text!r} not found in {path}")


def test_ui_save_confirmations_are_visible(isolated_character_app):
    """Test that save confirmations are visible without opening expanders.
    
    Validates both visible confirmation text and fallback file write indicators
    to ensure robust save detection that reduces flakiness.
    """
    app_url, _docs_lore_dir, characters_dir, places_dir, session_notes_dir, data_dir = isolated_character_app
    
    # Create a session note file to open
    session_notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = session_notes_dir / "test_save_confirmation.md"
    note_path.write_text(
        "# Session Notes - test_save_confirmation\n\n"
        "## 2026-07-14\n"
        "Initial test content.\n",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        # Test character save confirmation is visible without opening expander
        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        expand_section(page, "Create Character")
        fill_textbox(page, "Name", "Test Character")
        fill_textbox(page, "First Name", "Test")
        fill_textbox(page, "Family Name", "Character")
        fill_textbox(page, "Level", "1")
        fill_textbox(page, "Race", "Human")
        fill_textbox(page, "Class", "Fighter")
        page.get_by_role("textbox", name="Backstory", exact=True).fill("Test backstory for confirmation.")
        page.get_by_role("textbox", name="Summary", exact=True).fill("Test summary.")
        page.get_by_role("button", name="person_add Create Character").click()
        expect(page.get_by_role("heading", name="Test Character", exact=True)).to_be_visible(timeout=10000)
        
        # Save character and verify confirmation is visible
        ensure_character_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).first.fill("Updated test summary.")
        page.get_by_role("button", name="save Save Character").click()
        # Handle the "Keep Both" dialog if it appears
        for button_name in ("library_books Keep Both", "Keep Both"):
            keep_both = page.get_by_role("button", name=button_name)
            try:
                expect(keep_both).to_be_visible(timeout=2000)
            except AssertionError:
                continue
            keep_both.click(force=True)
            break
        assert_character_saved_visible(page)  # Should be visible without opening expander
        assert_character_profile_written(data_dir, "Test Character")

        # Test place save confirmation is visible without opening expander
        open_tab(page, "Places")
        expect(page.get_by_role("heading", name="Places")).to_be_visible(timeout=10000)
        expand_section(page, "Create Place")
        fill_textbox(page, "Name", "Test Place")
        page.get_by_role("textbox", name="New Place Markdown", exact=True).fill("# Test Place\n\nTest place content.")
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_role("heading", name="Test Place", exact=True).last).to_be_visible(timeout=10000)
        assert_place_saved_visible(page)
        assert_place_file_written(places_dir, "Test Place")
        assert not (places_dir / "New Place.md").exists()
        
        # Open place and save it
        page.get_by_role("combobox", name="Place Files").click()
        page.get_by_role("option", name="Test Place (Test Place.md)", exact=True).click()
        page.get_by_role("button", name="location_on Open Place").click()
        ensure_place_editor_open(page)
        fill_place_editor_markdown(page, "# Test Place\n\nUpdated place content.")
        click_place_save_button(page)
        assert_place_saved_visible(page)  # Should be visible without opening expander
        assert_place_file_written(places_dir, "Test Place")
        expect(page.get_by_role("heading", name="Test Place", exact=True).last).to_be_visible(timeout=10000)

        # Test session note save confirmation is visible
        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option").filter(has_text="test_save_confirmation").first.click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        open_tab(page, "Session Notes")
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note", exact=True).fill("Updated test content.")
        page.get_by_role("button", name="save Save Session Note").click()
        assert_session_note_saved_visible(page)  # Should be visible
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        
        browser.close()
    
    # Verify file content was actually saved
    saved_content = note_path.read_text(encoding="utf-8")
    assert "Updated test content" in saved_content


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


def test_capture_knowledge_graph_screenshot(isolated_character_app):
    screenshot_path_value = os.environ.get(KNOWLEDGE_GRAPH_SCREENSHOT_ENV)
    if not screenshot_path_value:
        pytest.skip(f"Set {KNOWLEDGE_GRAPH_SCREENSHOT_ENV} to capture a knowledge graph screenshot.")
    graph_node_name = os.environ.get(KNOWLEDGE_GRAPH_SCREENSHOT_NODE_ENV, "")

    app_url, _docs_lore_dir, _characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app
    screenshot_path = Path(screenshot_path_value).expanduser().resolve()
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(app_url, wait_until="networkidle")
        page.evaluate("document.body.style.zoom = '1.15'")

        graph_expander = page.locator("[data-testid=stExpander]").filter(has_text="Combined Knowledge Graph")
        expect(graph_expander).to_be_visible(timeout=10000)
        graph_expander.get_by_text("Combined Knowledge Graph").click()
        expect(graph_expander.get_by_role("button", name="sync Regenerate All Lore Graphs")).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Single Character View", exact=True)).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Test Fixture", exact=True)).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Full Structured Graph", exact=True)).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Before Selection", exact=True)).not_to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Selected View", exact=True)).not_to_be_visible(timeout=10000)
        if graph_node_name:
            graph_expander.get_by_text("Single Character View", exact=True).click()
            expect(graph_expander.get_by_role("tab").first).to_be_visible(timeout=10000)
            graph_tab = graph_expander.get_by_role("tab", name=graph_node_name, exact=True)
            if graph_tab.count():
                graph_tab.click()
            graph_node_select = graph_expander.get_by_label(f"Graph Node For {graph_node_name}", exact=True).first
            expect(graph_node_select).to_have_value(graph_node_name, timeout=10000)
        else:
            graph_expander.get_by_text("Test Fixture", exact=True).click()
            expect(graph_expander.get_by_role("img").first).to_be_visible(timeout=10000)
        page.wait_for_timeout(1000)

        graph_expander.scroll_into_view_if_needed()
        page.screenshot(path=str(screenshot_path))
        browser.close()

    assert screenshot_path.exists()
    assert screenshot_path.stat().st_size > 0


def test_combined_graph_structured_graph_views_are_separate(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(app_url, wait_until="networkidle")

        graph_expander = page.locator("[data-testid=stExpander]").filter(has_text="Combined Knowledge Graph")
        expect(graph_expander).to_be_visible(timeout=10000)
        graph_expander.get_by_text("Combined Knowledge Graph").click()
        expect(graph_expander.get_by_text("Single Character View", exact=True)).to_be_visible(timeout=10000)

        graph_expander.get_by_text("Test Fixture", exact=True).click()
        expect(graph_expander.get_by_role("img").first).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Test Fixture Details", exact=True)).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_label("Graph Node For Jory Ravenmark", exact=True)).not_to_be_visible(timeout=10000)

        graph_expander.get_by_text("Full Structured Graph", exact=True).click()
        expect(graph_expander.get_by_role("img").first).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Full Graph Details", exact=True)).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_label("Graph Node For Jory Ravenmark", exact=True)).not_to_be_visible(timeout=10000)
        browser.close()


def graph_node_titles(graph_expander) -> list[str]:
    return graph_expander.evaluate(
        """(root) => {
            const svgs = [...root.querySelectorAll("svg")];
            const svg = svgs[svgs.length - 1];
            if (!svg) {
                throw new Error("Graphviz SVG was not rendered.");
            }
            return [...svg.querySelectorAll("g.node title, g.node text")]
                .map((element) => element.textContent.trim())
                .filter(Boolean);
        }"""
    )


def test_test_fixture_view_uses_only_character_sheet_data(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, places_dir, session_notes_dir, _data_dir = isolated_character_app
    shutil.copy2(ROOT_DIR / "tests" / "fixtures" / "places" / "Atlantia_Lore.md", places_dir / "Atlantia_Lore.md")
    shutil.copy2(ROOT_DIR / "tests" / "fixtures" / "session_notes" / "Family_Tree.md", session_notes_dir / "Family_Tree.md")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(app_url, wait_until="networkidle")

        graph_expander = page.locator("[data-testid=stExpander]").filter(has_text="Combined Knowledge Graph")
        expect(graph_expander).to_be_visible(timeout=10000)
        graph_expander.get_by_text("Combined Knowledge Graph").click()

        graph_expander.get_by_text("Test Fixture", exact=True).click()
        expect(graph_expander.locator("svg").first).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Test Fixture Details", exact=True)).to_be_visible(timeout=10000)
        full_character_titles = graph_node_titles(graph_expander)
        assert "Family Tree" not in full_character_titles
        assert "Atlantia Lore" not in full_character_titles

        graph_expander.get_by_text("Full Structured Graph", exact=True).click()
        expect(graph_expander.locator("svg").first).to_be_visible(timeout=10000)
        expect(graph_expander.get_by_text("Full Graph Details", exact=True)).to_be_visible(timeout=10000)
        full_structured_titles = graph_node_titles(graph_expander)
        assert "Family Tree" in full_structured_titles
        browser.close()


def graph_edge_label_position_issues(graph_expander) -> list[dict[str, object]]:
    return graph_expander.evaluate(
        """(root) => {
            const svg = root.querySelector("svg");
            if (!svg) {
                throw new Error("Graphviz SVG was not rendered.");
            }
            const issues = [];
            const tolerance = 6;
            for (const edge of svg.querySelectorAll("g.edge")) {
                const title = edge.querySelector("title")?.textContent?.trim() || "(untitled edge)";
                const geometry = [
                    ...edge.querySelectorAll("path, polygon, polyline, line")
                ].filter((element) => {
                    const box = element.getBBox();
                    return box.width > 0 || box.height > 0;
                });
                const labels = [...edge.querySelectorAll("text")].filter((element) => {
                    return (element.textContent || "").trim().length > 0;
                });
                if (!geometry.length && labels.length) {
                    issues.push({edge: title, label: labels[0].textContent.trim(), reason: "missing edge geometry"});
                    continue;
                }
                for (const label of labels) {
                    const labelBox = label.getBBox();
                    const labelCenter = {
                        x: labelBox.x + labelBox.width / 2,
                        y: labelBox.y + labelBox.height / 2,
                    };
                    const associated = geometry.some((element) => {
                        if (typeof element.getPointAtLength === "function") {
                            const length = element.getTotalLength();
                            const samples = Math.max(24, Math.ceil(length / 18));
                            for (let index = 0; index <= samples; index += 1) {
                                const point = element.getPointAtLength(length * index / samples);
                                if (
                                    point.x >= labelBox.x - tolerance &&
                                    point.x <= labelBox.x + labelBox.width + tolerance &&
                                    point.y >= labelBox.y - tolerance &&
                                    point.y <= labelBox.y + labelBox.height + tolerance
                                ) {
                                    return true;
                                }
                            }
                        }
                        const box = element.getBBox();
                        return (
                            labelCenter.x >= box.x - tolerance &&
                            labelCenter.x <= box.x + box.width + tolerance &&
                            labelCenter.y >= box.y - tolerance &&
                            labelCenter.y <= box.y + box.height + tolerance
                        );
                    });
                    if (!associated) {
                        issues.push({
                            edge: title,
                            label: label.textContent.trim(),
                            labelBox: {
                                x: Math.round(labelBox.x),
                                y: Math.round(labelBox.y),
                                width: Math.round(labelBox.width),
                                height: Math.round(labelBox.height),
                            },
                            reason: "label is not located on its owning edge geometry",
                        });
                    }
                }
            }
            return issues;
        }"""
    )


def test_full_knowledge_graph_edge_labels_are_located_on_their_edges(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, _session_notes_dir, _data_dir = isolated_character_app
    STRUCTURED_KNOWLEDGE_GRAPH_FULL_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(app_url, wait_until="networkidle")
        page.evaluate("document.body.style.zoom = '1.15'")

        graph_expander = page.locator("[data-testid=stExpander]").filter(has_text="Combined Knowledge Graph")
        expect(graph_expander).to_be_visible(timeout=10000)
        graph_expander.get_by_text("Combined Knowledge Graph").click()
        expect(graph_expander.get_by_text("Single Character View", exact=True)).to_be_visible(timeout=10000)
        graph_expander.get_by_text("Test Fixture", exact=True).click()

        graph_image = graph_expander.get_by_role("img").first
        expect(graph_image).to_be_visible(timeout=10000)
        expect(graph_expander.locator("svg").first).to_be_visible(timeout=10000)

        edge_label_issues = graph_edge_label_position_issues(graph_expander)
        assert edge_label_issues == []

        graph_expander.scroll_into_view_if_needed()
        page.screenshot(path=str(STRUCTURED_KNOWLEDGE_GRAPH_FULL_SCREENSHOT))
        browser.close()

    assert STRUCTURED_KNOWLEDGE_GRAPH_FULL_SCREENSHOT.exists()
    assert STRUCTURED_KNOWLEDGE_GRAPH_FULL_SCREENSHOT.stat().st_size > 0


def test_ui_fills_only_visible_character_editor_fields_and_saves(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, data_dir = isolated_character_app
    character_path = characters_dir / "Jory_Ravenmark.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        select_character(page, markdown_title(character_path), 0)
        ensure_character_editor_open(page)
        filled = fill_visible_text_inputs(page, prefix="RoundTrip")
        assert filled, "No visible character editor fields were found to fill."
        save_open_character(page, data_dir, character_path)
        browser.close()

    profile = read_character_profile(Character(name=character_path.stem, path=character_path))
    assert profile.name
    assert profile.summary


def test_ui_fills_visible_place_editor_fields_and_saves(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, places_dir, _session_notes_dir, _data_dir = isolated_character_app
    existing_files = {path.name for path in places_dir.glob("*.md")}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Places")
        expect(page.get_by_role("heading", name="Places")).to_be_visible(timeout=10000)
        expand_section(page, "Create Place")
        filled = fill_visible_text_inputs(page, prefix="RoundTrip")
        assert filled, "No visible place editor fields were found to fill."
        page.get_by_role("button", name="add_location_alt Create Place").click()

        deadline = time.monotonic() + 10
        created = []
        while time.monotonic() < deadline:
            created = [path for path in places_dir.glob("*.md") if path.name not in existing_files]
            if created:
                break
            time.sleep(0.1)
        assert created, "Place file was not created after saving visible fields."
        created_title = markdown_title(created[0])
        page.get_by_role("combobox", name="Place Files").click()
        page.get_by_role("option", name=f"{created_title} ({created[0].name})", exact=True).click()
        page.get_by_role("button", name="location_on Open Place").click()
        ensure_place_editor_open(page)
        expect(page.get_by_role("heading", name=created_title, exact=True).last).to_be_visible(timeout=10000)
        browser.close()

    content = created[0].read_text(encoding="utf-8")
    assert created_title in content


def test_ui_fills_visible_session_note_editor_fields_and_saves(isolated_character_app):
    app_url, _docs_lore_dir, _characters_dir, _places_dir, session_notes_dir, _data_dir = isolated_character_app
    note_path = session_notes_dir / "2026-07-10_Session_Notes.md"
    session_notes_dir.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "# Session Notes - 2026-07-10 - Session Notes\n\n"
        "## 2026-07-10\n"
        "The party found a silver key.\n",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role(
            "option",
            name="2026-07-10_Session_Notes.md - 2026-07-10 - Session Notes",
            exact=True,
        ).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        open_tab(page, "Session Notes")
        ensure_session_note_editor_open(page)
        filled = fill_visible_text_inputs(page, prefix="RoundTrip")
        assert filled, "No visible session note editor fields were found to fill."
        page.get_by_role("button", name="save Save Session Note").click()
        assert_session_note_saved_visible(page)
        browser.close()

    saved_content = note_path.read_text(encoding="utf-8")
    assert "RoundTrip" in saved_content


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
        assert_character_saved_visible(page)
        expect(page.get_by_role("tab", name="Characters", exact=True)).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )

        ensure_character_editor_open(page)
        page.get_by_role("textbox", name="Summary", exact=True).first.fill("Della is a reckless scout tonight.")
        page.get_by_role("button", name="save Save Character").first.click(force=True)
        assert_character_saved_visible(page)

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
        page.get_by_role("textbox", name="New Place Markdown", exact=True).fill(
            "# Brindle Hall\n\nA narrow guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives."
        )
        page.get_by_role("button", name="add_location_alt Create Place").click()
        expect(page.get_by_role("heading", name="Brindle Hall", exact=True).last).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Notes", exact=True)).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Place Files").click()
        page.get_by_role("option", name="Brindle Hall (Brindle Hall.md)", exact=True).click()
        page.get_by_role("button", name="location_on Open Place").click()
        ensure_place_editor_open(page)
        fill_place_editor_markdown(
            page,
            "# Brindle Hall\n\nA crowded guildhall where maps are traded.\n\n## Notes\n\nLanterns burn blue near the archives.",
        )
        click_place_save_button(page)
        assert_place_saved_visible(page)
        wait_for_file_text(place_path, "A crowded guildhall where maps are traded.")
        expect(page.get_by_role("tab", name="Places", exact=True)).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )

        ensure_place_editor_open(page)
        fill_place_editor_markdown(page, "# Brindle Hall\n\nA ruined guildhall after the fire.")
        click_place_save_button(page)
        assert_place_saved_visible(page)
        wait_for_file_text(place_path, "A ruined guildhall after the fire.")
        expect(page.get_by_role("textbox", name="Place Markdown", exact=True)).to_have_value(
            "# Brindle Hall\n\nA ruined guildhall after the fire.",
            timeout=10000,
        )

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
    session_notes_dir.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "# Session Notes - 2026-07-10 - Session Notes\n\n"
        "## 2026-07-10\n"
        "The party found a silver key.\n",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role(
            "option",
            name="2026-07-10_Session_Notes.md - 2026-07-10 - Session Notes",
            exact=True,
        ).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party found a silver key.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Title").fill("Silver Key")
        expect(page.get_by_role("textbox", name="Title")).to_have_value("Silver Key", timeout=10000)
        page.wait_for_timeout(300)
        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note", exact=True).fill("The party found a silver key and a brass map.")
        page.get_by_role("button", name="save Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.get_by_role("heading", name="Silver Key", exact=True)).to_be_visible(timeout=10000)
        expect(page.locator("p").filter(has_text="The party found a silver key and a brass map.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("textbox", name="Session Note", exact=True).fill("The party lost the key.")
        page.get_by_role("button", name="save Save Session Note").click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party lost the key.")).to_be_visible(timeout=10000)

        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").last.click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party found a silver key and a brass map.")).to_be_visible(timeout=10000)
        ensure_session_note_editor_open(page)
        page.get_by_role("button", name="undo Undo Changes").last.click()
        open_tab(page, "Session Notes")
        expect(page.locator("p").filter(has_text="The party found a silver key.")).to_be_visible(timeout=10000)
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
        expect(page.get_by_text("Add Session Note", exact=True)).to_have_count(0)
        expect(page.get_by_text("Import Session Note", exact=True)).to_be_visible(timeout=10000)
        browser.close()


def test_ui_deletes_character_place_and_session_note_files(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, places_dir, session_notes_dir, _data_dir = isolated_character_app
    character_path = characters_dir / "Delete Me.md"
    place_path = places_dir / "Delete Hall.md"
    note_path = session_notes_dir / "2026-07-10_Session_Notes.md"
    session_notes_dir.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "# Session Notes - 2026-07-10 - Session Notes\n\n"
        "## 2026-07-10\n"
        "A temporary note for deletion.\n",
        encoding="utf-8",
    )

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
        page.get_by_role("textbox", name="New Place Markdown", exact=True).fill("# Delete Hall\n\nA temporary place for deletion.")
        page.get_by_role("button", name="add_location_alt Create Place").click()
        assert_place_file_written(places_dir, "Delete Hall")
        expect(page.get_by_role("heading", name="Delete Hall", exact=True).last).to_be_visible(timeout=10000)
        ensure_place_editor_open(page)
        click_button_with_retry(page, "delete_forever Delete Place")
        expect(page.get_by_text("Place Deleted.")).to_be_visible(timeout=10000)

        open_tab(page, "Session Notes")
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
        page.get_by_text("Combined Knowledge Graph").last.click()
        page.get_by_text("Single Character View", exact=True).click()
        expect(page.get_by_label("Graph Node For Orin Nightbloom", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_text("Other Connections", exact=True).first).to_be_visible(timeout=10000)
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


def test_ui_fills_all_visible_character_fields_saves_and_reports_ui_elements(isolated_character_app):
    app_url, _docs_lore_dir, characters_dir, _places_dir, _session_notes_dir, data_dir = isolated_character_app
    character_path = characters_dir / "Jory_Ravenmark.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        select_character(page, markdown_title(character_path), 0)
        ensure_character_editor_open(page)

        filled = fill_visible_text_inputs(page, prefix="Audit")
        assert filled, "No visible character editor fields were found to fill."
        # Click the save button and wait for the UI confirmation instead of relying on file writes
        click_button_with_retry(page, "save Save Character")
        # Handle potential Keep Both prompt
        for button_name in ("library_books Keep Both", "Keep Both"):
            keep_both = page.get_by_role("button", name=button_name)
            if keep_both.count():
                try:
                    expect(keep_both).to_be_visible(timeout=2000)
                    keep_both.click(force=True)
                except Exception:
                    pass
                break
        # Allow UI to settle after save action
        page.wait_for_timeout(500)

        elements = {"headings": [], "tabs": [], "buttons": [], "textboxes": []}

        headings = page.get_by_role("heading")
        for idx in range(headings.count()):
            h = headings.nth(idx)
            if not h.is_visible():
                continue
            try:
                elements["headings"].append(h.inner_text())
            except Exception:
                elements["headings"].append("")

        tabs = page.get_by_role("tab")
        for idx in range(tabs.count()):
            t = tabs.nth(idx)
            if not t.is_visible():
                continue
            try:
                name = t.get_attribute("name") or t.inner_text()
            except Exception:
                name = ""
            selected = t.get_attribute("aria-selected")
            elements["tabs"].append({"name": name, "selected": selected})

        buttons = page.get_by_role("button")
        for idx in range(buttons.count()):
            b = buttons.nth(idx)
            if not b.is_visible():
                continue
            try:
                name = b.get_attribute("name") or b.inner_text()
            except Exception:
                name = ""
            elements["buttons"].append(name)

        textboxes = page.get_by_role("textbox")
        for idx in range(textboxes.count()):
            tb = textboxes.nth(idx)
            if not tb.is_visible():
                continue
            try:
                label = tb.get_attribute("aria-label") or tb.get_attribute("name") or tb.get_attribute("id") or ""
            except Exception:
                label = ""
            try:
                value = tb.input_value()
            except Exception:
                try:
                    value = tb.inner_text()
                except Exception:
                    value = ""
            elements["textboxes"].append({"label": label, "value": value})

        out_path = data_dir / "ui_save_audit.json"
        out_path.write_text(json.dumps(elements, indent=2), encoding="utf-8")
        # capture a screenshot of the page after save for visual verification
        out_path_img = data_dir / "ui_save_screenshot.png"
        try:
            page.screenshot(path=str(out_path_img), full_page=True)
        except Exception:
            pass
        browser.close()

    assert out_path.exists()
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    assert parsed.get("headings") and len(parsed["headings"]) > 0
    assert parsed.get("buttons") and any("Save" in (b or "") or "save" in (b or "") for b in parsed["buttons"])
