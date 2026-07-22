import os
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from language_model.storage import Character, read_character_profile
from tests.e2e.test_character_sheet_roundtrip_ui import (
    APP_URL,
    ROOT_DIR,
    seed_lore_fixture,
    select_character,
    streamlit_executable,
    wait_for_streamlit,
)


@pytest.fixture()
def graph_rewrite_app(tmp_path):
    process, app_state = launch_graph_rewrite_app(
        tmp_path,
        extra_env={
            "LOCAL_CHATBOT_MODEL_CACHE_DIR": str(tmp_path / "missing_models"),
            "PATH": "/usr/bin:/bin",
        },
    )
    try:
        yield app_state
    finally:
        stop_streamlit(process)


def launch_graph_rewrite_app(tmp_path, extra_env: dict[str, str] | None = None):
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
    env["LOCAL_CHATBOT_WORLD_BUILDING_DIR"] = str(world_building_dir)
    env["LOCAL_CHATBOT_LORE_DIR"] = str(docs_lore_dir)
    env["LOCAL_CHATBOT_CHARACTERS_DIR"] = str(characters_dir)
    env["LOCAL_CHATBOT_PLACES_DIR"] = str(places_dir)
    env["LOCAL_CHATBOT_SESSION_NOTES_DIR"] = str(session_notes_dir)
    env["LOCAL_CHATBOT_META_DATA_DIR"] = str(meta_data_dir)
    env.update(extra_env or {})
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
    wait_for_streamlit(APP_URL, process)
    return process, (APP_URL, characters_dir, meta_data_dir)


def stop_streamlit(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def test_rewrite_backstory_button_is_hidden_without_model_runtime(graph_rewrite_app):
    app_url, characters_dir, _data_dir = graph_rewrite_app
    character_file = characters_dir / "Orin_Nightbloom.md"
    original_profile = read_character_profile(Character(name=character_file.stem, path=character_file))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(app_url, wait_until="networkidle")
        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        select_character(page, "Orin Nightbloom", 0)

        if not page.get_by_role("heading", name="Edit Character").is_visible():
            page.get_by_text("Edit Character", exact=True).click()
        expect(page.get_by_role("button", name="edit_note Rewrite Backstory")).to_have_count(0)
        expect(page.get_by_role("heading", name="Edit Character")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Backstory", exact=True)).to_be_visible(timeout=10000)
        profile = read_character_profile(Character(name=character_file.stem, path=character_file))

        assert profile.backstory == original_profile.backstory
        assert profile.original_backstory == original_profile.original_backstory
        browser.close()


def test_repopulate_summary_button_is_hidden_without_model_runtime(graph_rewrite_app):
    app_url, characters_dir, _data_dir = graph_rewrite_app
    character_file = characters_dir / "Orin_Nightbloom.md"
    original_profile = read_character_profile(Character(name=character_file.stem, path=character_file))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(app_url, wait_until="networkidle")
        expect(page.get_by_role("heading", name="Characters")).to_be_visible(timeout=10000)
        select_character(page, "Orin Nightbloom", 0)

        if not page.get_by_role("heading", name="Edit Character").is_visible():
            page.get_by_text("Edit Character", exact=True).click()
        expect(page.get_by_role("button", name="sync Repopulate Summary")).to_have_count(0)
        expect(page.get_by_role("heading", name="Edit Character")).to_be_visible(timeout=10000)
        expect(page.get_by_role("textbox", name="Summary", exact=True)).to_be_visible(timeout=10000)
        profile = read_character_profile(Character(name=character_file.stem, path=character_file))

        assert profile.summary == original_profile.summary
        assert profile.original_summary == original_profile.original_summary
        browser.close()
