# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Session Note Import Deduplication
Allow importing the same session note file again without creating a second file or duplicating existing sections. New imported sections should be appended when their section titles are not already present.

### H1 Heading Visibility
- For H1 headings, offer a non-destructive Hide Heading action instead of removing the section.
- Hiding an H1 heading converts the H1 line to an ignored H4 heading and keeps its content in the file.
- When hiding an H1 heading, promote the next non-H1 heading in that section to H1.

### Testing
- `../.venv/bin/python -m pytest tests/test_session_notes.py tests/e2e/test_session_notes_ui.py::test_ui_imports_uploaded_session_notes_as_one_markdown_file tests/e2e/test_session_notes_ui.py::test_ui_imports_freeform_lore_markdown_without_requiring_dates tests/e2e/test_session_notes_ui.py::test_ui_import_dialog_keeps_month_year_dates_and_hides_h4_headings tests/e2e/test_session_notes_ui.py::test_ui_reimporting_fixture_adds_only_new_section_titles tests/e2e/test_session_notes_ui.py::test_ui_reimporting_only_last_existing_section_preserves_prior_sections tests/e2e/test_session_notes_ui.py::test_ui_reimporting_hidden_session_notes_fixture_deduplicates_sections`
- `../.venv/bin/python -m pytest tests/test_session_notes.py tests/e2e/test_session_notes_ui.py::test_ui_hides_h1_heading_without_deleting_content`
- `../.venv/bin/python -m pytest tests/test_session_notes.py tests/e2e/test_session_notes_ui.py::test_ui_imports_uploaded_session_notes_as_one_markdown_file tests/e2e/test_session_notes_ui.py::test_ui_imports_freeform_lore_markdown_without_requiring_dates tests/e2e/test_session_notes_ui.py::test_ui_import_dialog_keeps_month_year_dates_and_hides_h4_headings tests/e2e/test_session_notes_ui.py::test_ui_reimporting_fixture_adds_only_new_section_titles tests/e2e/test_session_notes_ui.py::test_ui_reimporting_only_last_existing_section_preserves_prior_sections tests/e2e/test_session_notes_ui.py::test_ui_reimporting_hidden_session_notes_fixture_deduplicates_sections tests/e2e/test_session_notes_ui.py::test_ui_hides_h1_heading_without_deleting_content tests/e2e/test_session_notes_ui.py::test_ui_session_note_dropdown_sorts_files_alphabetically_preserving_heading_order`

### Completed
- Changed freeform lore/session-note imports to merge into the existing target file by section title.
- Added e2e coverage using `tests/fixtures/session_notes/Family_Tree.md` for appending only new section titles on reimport.
- Added e2e coverage proving partial reimports preserve earlier existing sections even when the import only contains the last existing section.
- Added e2e coverage using hidden `data/Session_Notes.txt` for unchanged duplicate reimports.
- Added H1 Hide Heading behavior before the section preview and regression coverage.
- Sorted session-note dropdown files alphabetically while preserving heading order within each markdown document.

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
