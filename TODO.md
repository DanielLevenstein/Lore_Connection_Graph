# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Lore Directory Move
Move the local lore source directory from `docs/lore` to `data/lore` so docs can stay focused on committed templates, specs, reports, and screenshots.

### Testing
- tests/test_lore_import.py 
- tests/test_entity_file_saves.py 
- tests/test_session_notes.py 
- tests/test_character_generation.py 
- tests/test_combined_character_graph.py 
- tests/e2e/test_session_notes_ui.py::test_ui_imports_lore_fixture_directory 
- tests/e2e/test_session_notes_ui.py::test_ui_bulk_lore_removal_confirms_before_cleaning_lore

### Completed
- Updated default lore paths to use `data/lore`, with `LOCAL_CHATBOT_LORE_DIR` as the preferred override and the legacy `LOCAL_CHATBOT_DOCS_LORE_DIR` still supported.
- Kept saved markdown lore human-readable under `data/lore` and moved runtime character metadata to `data/character_metadata`.
- Updated import/removal cleanup, path documentation, and tests for the new storage split.
- Moved local ignored lore from `docs/lore` to `data/lore`.
