# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If test cases contradict manual changes, update the test case. 
- If tests depend on deprecated or removed code, move the deprecated code to tests/fixtures/deprecated_features.py

##  Change log
The changelog has been moved to the bottom of CHANGELOG.md
Create a changelog for CHANGELOG.md summarizing previous work. Then delete these entities from the TODO file. 

Use the following Markdown levels
H1 Branch 
H2 Date
H3 Feature Implementation
- Short description of what was changed. 

## Task Management
- When a task is finished, add a Completed section to the TODO.md file. 
- When finishing a section, check TODO.md for the next task.

## Consistency Skill
- Use `$use-language-models-for-worldbuilding` for lore consistency checks before saving generated or rewritten character, place, session note, or knowledge graph summary content.
- Verify generated worldbuilding output preserves established names, places, relationships, chronology, and source-backed facts.

## Automated Testing

- e2e tests for this project use playwright
- Install required Playwright browsers in the project venv with `.venv/bin/python -m playwright install chromium`
- Run the UI suite with `PYTHONPATH=. .venv/bin/python -m pytest -q tests/e2e --maxfail=1`
- When automated tests break, add a unique id to the button or table you are accessing.

## Repository Conventions

- Use `./run_streamlit.sh` to bootstrap the local `.venv` and start the Streamlit app.
- The source of truth is `world_building/lore`; files in `world_building/meta_data` are derived runtime data and should not be committed.
- `tests/e2e` fixtures start `streamlit_app.py` on `http://127.0.0.1:8512` and rely on environment overrides such as `LOCAL_CHATBOT_WORLD_BUILDING_DIR`, `LOCAL_CHATBOT_CHARACTERS_DIR`, `LOCAL_CHATBOT_SESSION_NOTES_DIR`, and `LOCAL_CHATBOT_LORE_DIR`.
- Hidden Streamlit feature flags are gated by environment variables in `streamlit_app.py`:  `LOCAL_CHATBOT_ENABLE_EXTERNAL_CHARACTER_IMPORT`, `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES`, `LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE`.
- UI changes must preserve accessible button/tab names and stable Playwright selectors; if Streamlit labels change, update the tests accordingly.
