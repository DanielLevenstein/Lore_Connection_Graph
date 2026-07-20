# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If tests depend on deprecated or removed code, move the deprecated code to tests/e2e/deprecated_features.py

##  Change log
The changelog has been moved to the bottom of RELEASE_NOTES.md
Create a changelog for RELEASE_NOTES.md summarizing previous work. Then delete these entities from this TODO file. 

Use the following Markdown levels
H1 Branch 
H2 Date
H3 Feature Implementation
- Short description of what was changed. 


## Semantic Aware Model
- Install semantic informed model locally for character rewrites and knowledge graph summary sections.
- Ensure the model selected is able to extract people and place names from existing source data successfully.
- Select a second visual inspection model to validate the generated UI from each page against the requirements. 

## Task Management
- When a task is finished, add a Completed section to the TODO.md file. 
- When finishing a section, check TODO.md for the next task.

## Consistency Skill
- Use `$use-language-models-for-worldbuilding` for lore consistency checks before saving generated or rewritten character, place, session note, or knowledge graph summary content.
- Verify generated worldbuilding output preserves established names, places, relationships, chronology, and source-backed facts.

## Application Screenshots
- Add an application screenshot to docs/screenshots while testing code but do not commit these files. 
- After reviewing the work I will commit the files which are useful for demonstration or bug tracking purposes. 

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

### Notes for UI work

- The app uses many `st.session_state` keys to manage active character/place/session note selection and navigation tab persistence.
- When fixing UI state, prefer a single source of truth for active selections and tab state rather than scattering state across many keys.
- See `docs/reports/ui_issue_report.md` for current Streamlit tab/expander persistence risks and `docs/reports/environment_variable_feature_audit.md` for env var gating guidance.

### Environment Variable Removal Plan

- Created `docs/reports/environment_variable_feature_audit.md`.
- Added an ordered removal plan for all environment variables except `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES`, ranked from lowest to highest risk.
- For environmental variables used in testing come up with the shortest override list possible that allows the testing that needs to be done without creating a maintenance issue. 
