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
    world_building_dir = tmp_path / "world_building"
    docs_lore_dir = world_building_dir / "lore"
    import_dir = world_building_dir / "import"
    meta_data_dir = tmp_path / "meta_data"
    docs_lore_dir.mkdir(parents=True)
    import_dir.mkdir(parents=True)
    meta_data_dir.mkdir()

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["LOCAL_CHATBOT_WORLD_BUILDING_DIR"] = str(world_building_dir)
    env["LOCAL_CHATBOT_WORLD_BUILDING_IMPORT_DIR"] = str(import_dir)
    env["LOCAL_CHATBOT_LORE_DIR"] = str(docs_lore_dir)
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(docs_lore_dir / "character_sheets")
    env["LOCAL_CHATBOT_PLACES_DIR"] = str(docs_lore_dir / "places")
    env["LOCAL_CHATBOT_SESSION_NOTES_DIR"] = str(docs_lore_dir / "session_notes")
    env["LOCAL_CHATBOT_META_DATA_DIR"] = str(meta_data_dir)
    env["LOCAL_CHATBOT_ENABLE_EXTERNAL_CHARACTER_IMPORT"] = "1"
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


def import_session_note_file(page, path: Path, imported_file_name: str = "") -> None:
    page.get_by_role("tab", name="Session Notes", exact=True).click()
    upload_button = page.get_by_role("button", name="upload_file Upload Session Note")
    if not upload_button.is_visible():
        page.get_by_text("Import Session Note", exact=True).last.click()
    expect(upload_button).to_be_visible(timeout=10000)
    file_input = page.get_by_label("File", exact=True).locator("input[type=file]")
    file_input.set_input_files([])
    file_input.set_input_files(str(path))
    if imported_file_name:
        page.get_by_role("textbox", name="Imported File Name").fill(imported_file_name)
    upload_button.click()
    expect(page.get_by_role("heading", name="Select Searchable Headings")).to_be_visible(timeout=10000)
    page.get_by_role("button", name="check Save Selected Headings").click()
    expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)


def test_ui_removes_broken_add_session_note_path(isolated_session_notes_app):
    app_url, _docs_lore_dir = isolated_session_notes_app
    app_source = (ROOT_DIR / "streamlit_app.py").read_text(encoding="utf-8")
    disabled_fixture = (ROOT_DIR / "tests" / "fixtures" / "disabled_legacy_add_session_note_ui.py").read_text(encoding="utf-8")

    assert "save_new_session_notes" not in app_source
    assert "save_new_session_notes" in disabled_fixture

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        expect(page.get_by_role("heading", name="Session Notes", exact=True).last).to_be_visible(timeout=10000)
        expect(page.get_by_text("Add Session Note", exact=True)).to_have_count(0)
        expect(page.get_by_text("Import Session Note", exact=True)).to_be_visible(timeout=10000)
        browser.close()


def test_ui_imports_uploaded_session_notes_as_one_markdown_file(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    import_file = docs_lore_dir / "discord_import.md"
    import_file.write_text(
        """John [OOZE], Server Tag: OOZEOOZE — 7/10/26, 11:36 PMFriday, July 10, 2026 at 11:36 PM
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
        page.get_by_text("Import Session Note", exact=True).last.click()
        expect(page.get_by_role("button", name="upload_file Upload Session Note")).to_be_visible(timeout=10000)
        page.get_by_label("File", exact=True).locator("input[type=file]").set_input_files(str(import_file))
        page.get_by_role("button", name="upload_file Upload Session Note").click()
        expect(page.get_by_role("heading", name="Select Searchable Headings")).to_be_visible(timeout=10000)
        page.get_by_role("button", name="check Save Selected Headings").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("tab", name="Session Notes", exact=True)).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )
        expect(page.get_by_role("heading", name="discord import", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Scene Notes", exact=True)).to_be_visible(timeout=10000)
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="discord_import.md H2: Scene Notes", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("heading", name="Scene Notes", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Second Scene", exact=True)).to_have_count(0)
        page.get_by_role("button", name="edit Edit Section").click()
        expect(page.get_by_role("textbox", name="Session Note")).to_contain_text("Found a **silver key**")
        expect(page.get_by_role("textbox", name="Session Note")).not_to_contain_text("Second Scene")
        browser.close()

    imported = notes_dir / "discord_import.md"
    assert imported.exists()
    assert not list(notes_dir.glob("2026-07-10*.md"))
    text = imported.read_text(encoding="utf-8")
    assert "## Scene Notes" in text
    assert "- Found a **silver key**" in text
    assert "| Clue | Status |" in text
    assert "## Second Scene" in text


def test_ui_imports_freeform_lore_markdown_without_requiring_dates(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    import_file = ROOT_DIR / "tests" / "fixtures" / "places" / "Atlantia_Lore.md"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_text("Import Session Note", exact=True).click()
        page.get_by_label("File", exact=True).locator("input[type=file]").set_input_files(str(import_file))
        page.get_by_role("textbox", name="Imported File Name").fill("Imported Atlantia.md")
        page.get_by_role("button", name="upload_file Upload Session Note").click()
        expect(page.get_by_role("heading", name="Select Searchable Headings")).to_be_visible(timeout=10000)
        expect(page.get_by_label("H1 Atlantia Lore")).to_be_checked(timeout=10000)
        expect(page.get_by_label("H2 The Watch Tower")).to_be_checked(timeout=10000)
        page.get_by_role("button", name="check Save Selected Headings").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("tab", name="Session Notes", exact=True)).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )
        expect(page.get_by_role("heading", name="Atlantia Lore", exact=True)).to_have_count(1)
        expect(page.get_by_role("heading", name="Town Overview", exact=True)).to_be_visible(timeout=10000)
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Imported_Atlantia.md H2: The Harbor", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("heading", name="The Harbor", exact=True)).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="The Watch Tower", exact=True)).to_have_count(0)
        page.get_by_role("button", name="edit Edit Section").click()
        expect(page.get_by_role("textbox", name="Session Note")).to_contain_text("The harbor is the town's busiest edge")
        expect(page.get_by_role("textbox", name="Session Note")).not_to_contain_text("Sunstone Mage College")
        browser.close()

    imported = notes_dir / "Imported_Atlantia.md"
    assert imported.exists()
    text = imported.read_text(encoding="utf-8")
    assert text.startswith("# Atlantia Lore")
    assert "## The Harbor" in text
    assert "## The Watch Tower" in text


def test_ui_reimporting_fixture_adds_only_new_section_titles(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    import_file = docs_lore_dir / "Family_Tree.md"
    fixture_text = (ROOT_DIR / "tests" / "fixtures" / "session_notes" / "Family_Tree.md").read_text(encoding="utf-8")
    import_file.write_text(fixture_text, encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        import_session_note_file(page, import_file, imported_file_name="Family_Tree.md")
        import_file.write_text(
            fixture_text
            + "\n\n## The Ravenmark Family\n\nChanged duplicate section text should not be added.\n"
            + "\n## The New Family\n\nThis new family section should be appended.\n",
            encoding="utf-8",
        )
        import_session_note_file(page, import_file, imported_file_name="Family_Tree.md")

        browser.close()

    imported = notes_dir / "Family_Tree.md"
    assert imported.exists()
    assert not (notes_dir / "Family_Tree_2.md").exists()
    text = imported.read_text(encoding="utf-8")
    assert text.count("## The Ravenmark Family") == 1
    assert "Changed duplicate section text should not be added." not in text
    assert "## The New Family\n\nThis new family section should be appended." in text


def test_ui_reimporting_only_last_existing_section_preserves_prior_sections(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    import_file = docs_lore_dir / "Family_Tree.md"
    fixture_text = (ROOT_DIR / "tests" / "fixtures" / "session_notes" / "Family_Tree.md").read_text(encoding="utf-8")
    import_file.write_text(fixture_text, encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        import_session_note_file(page, import_file, imported_file_name="Family_Tree.md")
        import_file.write_text(
            """# Family Tree

## The Lovington Family

Copied last section text should not replace the original or remove prior sections.
""",
            encoding="utf-8",
        )
        import_session_note_file(page, import_file, imported_file_name="Family_Tree.md")

        browser.close()

    imported = notes_dir / "Family_Tree.md"
    text = imported.read_text(encoding="utf-8")
    assert not (notes_dir / "Family_Tree_2.md").exists()
    assert "## The Nighbloom Family" in text
    assert "Mrs. Judeth Nightbloom is a teacher at Sunstone Mage College." in text
    assert "## The Ravenmark Family" in text
    assert "Judeth's cousin Mary Ravenmark died at sea at a young age" in text
    assert "## The Lovington Family" in text
    assert "Copied last section text should not replace the original" not in text


def test_ui_reimporting_hidden_session_notes_fixture_deduplicates_sections(isolated_session_notes_app):
    hidden_fixture = ROOT_DIR / "data" / "Session_Notes.txt"
    if not hidden_fixture.exists():
        pytest.skip("Hidden Session_Notes.txt fixture is not available.")

    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        import_session_note_file(page, hidden_fixture, imported_file_name="Session_Notes.txt")
        imported = notes_dir / "Session_Notes.md"
        first_text = imported.read_text(encoding="utf-8")

        import_session_note_file(page, hidden_fixture, imported_file_name="Session_Notes.txt")

        browser.close()

    assert imported.exists()
    assert not (notes_dir / "Session_Notes_2.md").exists()
    assert imported.read_text(encoding="utf-8") == first_text


def test_ui_import_dialog_keeps_month_year_dates_and_hides_h4_headings(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    import_file = docs_lore_dir / "dated_import.md"
    import_file.write_text(
        """### 2024/03/18 - Camryn
The next morning they meet with the towns mayor and assistant.

### 2024/03/18 - Camryn
The group follows the directions and arrive at a hut.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_text("Import Session Note", exact=True).click()
        upload_button = page.get_by_role("button", name="upload_file Upload Session Note")
        expect(upload_button).to_be_visible(timeout=10000)
        page.get_by_label("File", exact=True).locator("input[type=file]").set_input_files(str(import_file))
        upload_button.click(force=True)
        expect(page.get_by_role("heading", name="Select Searchable Headings")).to_be_visible(timeout=10000)
        expect(page.get_by_label("H2 March 2024")).to_be_checked(timeout=10000)
        expect(page.get_by_label("H3 2024/03/18 - Camryn")).to_be_checked(timeout=10000)
        expect(page.get_by_label("H4 2024/03/18 - Camryn")).to_have_count(0)
        page.get_by_role("button", name="check Save Selected Headings").click()
        expect(page.get_by_text("Saved 1 Session Note File.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="March 2024", exact=True)).to_be_visible(timeout=10000)
        browser.close()

    imported = notes_dir / "dated_import.md"
    text = imported.read_text(encoding="utf-8")
    assert "## March 2024" in text
    assert text.count("### 2024/03/18 - Camryn") == 1
    assert "The group follows the directions and arrive at a hut." in text


def test_ui_hides_h1_heading_without_deleting_content(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "Hide_Heading.md"
    note_path.write_text(
        """# Family Tree

Introductory family notes.

## The Ravenmark Family

Ravenmark details.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Hide_Heading.md H1: Family Tree", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("button", name="visibility_off Hide Heading")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="delete Remove Section")).to_have_count(0)

        page.get_by_role("button", name="visibility_off Hide Heading").click()
        expect(page.get_by_text('Are you sure you want to hide "Family Tree" heading')).to_be_visible(timeout=10000)
        expect(
            page.get_by_text(
                'Hiding this heading will promote "The Ravenmark Family" heading top level heading for this document'
            )
        ).to_be_visible(timeout=10000)
        page.get_by_role("button", name="visibility_off Hide Heading").last.click()
        expect(page.get_by_text("Heading Hidden.")).to_be_visible(timeout=10000)

        page.get_by_role("combobox", name="Session Note").click()
        expect(page.get_by_role("option", name="Hide_Heading.md H1: Family Tree", exact=True)).to_have_count(0)
        page.get_by_role("option", name="Hide_Heading.md H1: The Ravenmark Family", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("heading", name="The Ravenmark Family", exact=True)).to_be_visible(timeout=10000)
        browser.close()

    text = note_path.read_text(encoding="utf-8")
    assert text.startswith("#### Family Tree\n\nIntroductory family notes.")
    assert "# The Ravenmark Family\n\nRavenmark details." in text


def test_ui_session_note_dropdown_sorts_files_alphabetically_preserving_heading_order(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Zoo.md").write_text(
        """# Zoo Root

## Zebra

Zebra details.

## Aardvark

Aardvark details.
""",
        encoding="utf-8",
    )
    (notes_dir / "Alpha.md").write_text(
        """# Alpha Root

## Beta

Beta details.

## Alpha Child

Alpha child details.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_role("combobox", name="Session Note").click()
        options = page.get_by_role("option").all_inner_texts()
        browser.close()

    alpha_root = options.index("Alpha.md H1: Alpha Root")
    alpha_beta = options.index("Alpha.md H2: Beta")
    alpha_child = options.index("Alpha.md H2: Alpha Child")
    zoo_root = options.index("Zoo.md H1: Zoo Root")
    zoo_zebra = options.index("Zoo.md H2: Zebra")
    zoo_aardvark = options.index("Zoo.md H2: Aardvark")

    assert alpha_root < zoo_root
    assert alpha_root < alpha_beta < alpha_child
    assert zoo_root < zoo_zebra < zoo_aardvark


def test_ui_section_controls_add_and_confirm_remove(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "Section_Test.md"
    note_path.write_text(
        """# Section Test

## Harbor Trouble
The party found a sealed brass door.

### Locked Door
The lock has silver runes.

#### 2026/07/10 - Keeper
This chat metadata should be listed before deletion.

## Lighthouse Door
The party opened the lighthouse door.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Section_Test.md H1: Section Test", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("button", name="vertical_align_top Add Previous Section")).to_have_count(0)
        expect(page.get_by_role("button", name="call_merge Combine Section")).to_have_count(0)

        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Section_Test.md H2: Harbor Trouble", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        expect(page.get_by_role("button", name="vertical_align_bottom Add Next Section")).to_have_count(2, timeout=10000)
        expect(page.get_by_role("button", name="edit Edit Section")).to_be_visible(timeout=10000)
        expect(page.get_by_role("button", name="delete Remove Section")).to_be_visible(timeout=10000)

        page.get_by_role("button", name="delete Remove Section").click()
        expect(page.get_by_text("Are you sure you would like to delete this section and all sub sections?")).to_be_visible(timeout=10000)
        expect(page.get_by_text("H3: Locked Door")).to_be_visible(timeout=10000)
        expect(page.get_by_text("H4: 2026/07/10 - Keeper")).to_be_visible(timeout=10000)
        page.get_by_role("button", name="close Cancel").click()

        page.get_by_role("button", name="vertical_align_bottom Add Next Section").last.click()
        expect(page.get_by_text("Next Section Added.")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Session Note")).to_have_value("## Harbor Trouble: (Coming Next)", timeout=10000)
        page.get_by_role("textbox", name="Session Note").fill("Follow-up notes without a heading.")
        page.get_by_role("button", name="save Save Session Note").click()
        expect(page.get_by_text("Section Markdown Must Start With An H1, H2, Or H3 Heading.")).to_be_visible(timeout=10000)
        page.get_by_role("textbox", name="Session Note").fill("## Harbor Trouble: (Coming Next)\n\nFollow-up notes.")
        page.get_by_role("button", name="save Save Session Note").click()
        expect(page.get_by_text("Session Note Saved.")).to_be_visible(timeout=10000)

        browser.close()

    text = note_path.read_text(encoding="utf-8")
    assert "## Harbor Trouble: (Coming Next)\n\nFollow-up notes." in text
    assert "### Locked Door\nThe lock has silver runes." in text


def test_ui_last_section_removal_prompts_for_file_delete(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "Single_Section.md"
    note_path.write_text(
        """# Single Section

Only one searchable section exists.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        page.get_by_role("combobox", name="Session Note").click()
        page.get_by_role("option", name="Single_Section.md H1: Single Section", exact=True).click()
        page.get_by_role("button", name="event_note Open Session Note").click()
        page.get_by_role("button", name="delete Remove Section").click()
        expect(page.get_by_text("This is the last section in this file. Do you want to delete the full session note file?")).to_be_visible(timeout=10000)
        expect(page.get_by_test_id("stDialog").get_by_text("Single_Section.md")).to_be_visible(timeout=10000)

        page.get_by_role("button", name="close Cancel").click()
        expect(page.get_by_text("This is the last section in this file. Do you want to delete the full session note file?")).not_to_be_visible(timeout=10000)
        assert note_path.exists()

        page.get_by_role("button", name="delete Remove Section").click()
        page.get_by_role("button", name="delete_forever Delete Session Note File").click()
        expect(page.get_by_text("Session Note Deleted.")).to_be_visible(timeout=10000)

        browser.close()

    assert not note_path.exists()


def test_ui_removes_duplicate_headings_on_session_notes_load(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    notes_dir = docs_lore_dir / "session_notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "Duplicate_Headings.md"
    note_path.write_text(
        """# Duplicate Headings

### 2024/03/18 - Camryn
The next morning they meet with the towns mayor and assistant.

### 2024/03/18 - Camryn
The group follows the directions and arrive at a hut.
""",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Session Notes", exact=True).click()
        expect(page.get_by_role("heading", name="Duplicate Headings", exact=True)).to_be_visible(timeout=10000)
        browser.close()

    text = note_path.read_text(encoding="utf-8")
    assert "### 2024/03/18 - Camryn\nThe next morning" in text
    assert "### 2024/03/18 - Camryn\nThe group follows" not in text
    assert "The group follows the directions and arrive at a hut." in text


def test_ui_imports_lore_fixture_directory(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    import_dir = docs_lore_dir.parent / "import"
    characters_dir = docs_lore_dir / "character_sheets"
    places_dir = docs_lore_dir / "places"
    notes_dir = docs_lore_dir / "session_notes"
    fixture_dir = ROOT_DIR / "tests" / "fixtures"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_text("Lore Import", exact=True).first.click()
        lore_import = page.locator("[data-testid=stExpander]").filter(has_text="Lore Import").first
        source_directory = page.get_by_role("textbox", name="Source Directory")
        expect(source_directory).to_have_value(str(import_dir), timeout=10000)
        expect(lore_import.get_by_label("Character Sheet File")).to_have_count(0)
        source_directory.fill(str(fixture_dir))
        page.get_by_role("button", name="folder_copy Import Lore Directory").click()
        expect(page.get_by_text("Imported 6 Lore Files")).to_be_visible(timeout=10000)
        browser.close()

    assert (characters_dir / "Jory_Ravenmark.md").exists()
    assert (places_dir / "Atlantia_Lore.md").exists()
    assert (notes_dir / "Family_Tree.md").exists()
    assert (notes_dir / "Time_Turning.md").exists()

def test_ui_bulk_lore_removal_confirms_before_cleaning_lore(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    character_metadata_dir = docs_lore_dir.parent.parent / "meta_data" / "character_metadata"
    characters_dir = docs_lore_dir / "character_sheets"
    places_dir = docs_lore_dir / "places"
    notes_dir = docs_lore_dir / "session_notes"
    fixture_dir = ROOT_DIR / "tests" / "fixtures"
    generated_draft = character_metadata_dir / "Draft" / "PROFILE.json"
    generated_draft.parent.mkdir(parents=True)
    generated_draft.write_text("{}", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_text("Lore Import", exact=True).first.click()
        page.get_by_role("textbox", name="Source Directory").fill(str(fixture_dir))
        page.get_by_role("button", name="folder_copy Import Lore Directory").click()
        expect(page.get_by_text("Imported 6 Lore Files")).to_be_visible(timeout=10000)
        page.get_by_text("Lore Import", exact=True).first.click()
        page.get_by_role("button", name="delete_forever Bulk Lore Removal").click()
        expect(page.get_by_text("This operation is destructive.")).to_be_visible(timeout=10000)
        expect(page.get_by_text("delete all local characters, places, and notes")).to_be_visible(timeout=10000)
        page.get_by_role("button", name="delete_forever Yes, Delete Local Lore").click()
        expect(page.get_by_text("Deleted 6 Local Lore Files")).to_be_visible(timeout=10000)
        browser.close()

    assert not (characters_dir / "Jory_Ravenmark.md").exists()
    assert not (places_dir / "Atlantia_Lore.md").exists()
    assert not (notes_dir / "Family_Tree.md").exists()
    assert not (notes_dir / "Time_Turning.md").exists()
    assert not generated_draft.exists()

def test_ui_imports_external_character_sheet(isolated_session_notes_app):
    app_url, docs_lore_dir = isolated_session_notes_app
    characters_dir = docs_lore_dir / "character_sheets"
    external_sheet = docs_lore_dir / "external_sheet.pdf"
    external_sheet.write_bytes(b"%PDF-1.4\nexternal character sheet\n")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.goto(app_url, wait_until="networkidle")

        page.get_by_role("tab", name="Characters", exact=True).click()
        page.get_by_text("Import External Character Sheet", exact=True).first.click()
        page.get_by_label("Character Sheet File").locator("input[type=file]").set_input_files(str(external_sheet))
        expect(page.get_by_text("external_sheet.pdf")).to_be_visible(timeout=10000)
        import_sheet_button = page.get_by_role("button", name="upload_file Import Character Sheet")
        expect(import_sheet_button).to_be_visible(timeout=10000)
        import_sheet_button.click(force=True)
        expect(page.get_by_role("tab", name="Characters", exact=True)).to_have_attribute(
            "aria-selected",
            "true",
            timeout=10000,
        )
        browser.close()

    assert (characters_dir / "external" / "external_sheet.pdf").read_bytes() == b"%PDF-1.4\nexternal character sheet\n"
