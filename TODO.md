# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Session Notes Import
We need the ability to import session notes about people, places, or things without having to follow a specific Markdown file format.

### Design 
For all imports without structured md headings do the following.
1) Identify the file title or file name and set it to the H1 heading.
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

## Completed
- Session note imports now review extracted searchable headings in a popup before saving uploaded Markdown.
- Uploaded Markdown is normalized into H1 title, H2 dates, and H3 section headings, with unselected non-date headings restored to plain text.
- Existing Markdown headings are preserved at their original levels unless the user unchecks them during import.
- Session note dropdowns expose checked H1-H3 import headings as virtual sections while preserving the original single Markdown file.
- Uploaded session imports save as one Markdown file in `docs/lore/session_notes` instead of splitting into date-named files.
- Session note dropdown labels now use `file_name.md - Date - Heading`.
- Removed unstable import controls for hiding dates, detected-date behavior, and split-session behavior.
- Discord author export lines are rewritten as H4 metadata (`Username - Date`) without making them searchable headings yet.
- Add and import session note flows continue through the same save path, with editable campaign/session dates preserved.
- Updated `docs/screenshots/import_session_notes.png` for the import heading-selection UI.
- Testing completed:
  - `.venv/bin/python -m pytest tests/test_session_notes.py tests/test_entity_file_saves.py`
  - `.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py tests/e2e/test_character_sheet_roundtrip_ui.py`

## Bugs Found
- When transitioning from separating session notes by heading to separating them by heading, the default ordering of the files got messed up.
- The Import Session Note and Add session note UI should be combined, so there is a single code path for testing purposes then we test the shit out of that one path.
- There are two date values present in the app import date and session date. If the session date is present, we should default to ordering by it, otherwise we should order it by import date. 
  - We need to make the session date field editable so that if a game chooses to set up a date system that doesn't match real world dates, the system will still work.
