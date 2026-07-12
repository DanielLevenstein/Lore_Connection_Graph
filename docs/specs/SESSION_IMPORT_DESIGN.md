# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Session Notes Import
We need the ability to import session notes about people, places, or things without having to follow a specific Markdown file format.

### Design 
For all imports without structured md headings do the following.
1) Identify the file title or file name and set it to H1 heading.
2) Extract all dates in the files and convert them to H2 headings.
3) Preserve existing Markdown heading levels, and convert inferred plain-text section headings other than the first to H3 headings.
4) Display a popup with a list of all extracted headings ask the user what headings they want searchable.
5) Convert deselected non-date headings back to plain text.

- Popup for selecting extracted headings should show a checkmark by all headings H1-H3 that is checked by default.
- Extracted md files should be saved as a single file, with selected headings exposed as openable UI dropdown sections.
- Date fields are always converted to H2 headings for the first iteration.

- Entity dropdown should use the following format dropdown text "file_name.md - Date - Heading"

### References
docs/screenshots/Atlantia_Lore.png
docs/screenshots/Time_Turning.png
docs/screenshots/import_session_notes.png
tests/fixtures/session_notes/Family_Tree.md
tests/fixtures/places/Atlantia_Lore.md

### Testing
- `.venv/bin/python -m pytest tests/test_session_notes.py tests/test_entity_file_saves.py`
- `.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py tests/e2e/test_character_sheet_roundtrip_ui.py`
