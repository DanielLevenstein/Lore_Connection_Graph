# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Session Notes Import
We need the ability to import session notes about people, places, or things without having to follow a specific Markdown file format.

### Design 
For all imports without structured md headings do the following.
1) Identify the file title or file name and set it to H1 heading.
2) Extract all dates in the files and convert them to H2 `Month Year` headings.
3) Preserve existing Markdown heading levels, and convert inferred plain-text section headings other than the first to H3 headings.
4) Display a popup with a list of all extracted headings ask the user what headings they want searchable.
5) Convert deselected non-date H1-H3 headings to H4 headings so they stay in the content but do not appear in the UI.
6) Chat logs are converted to H5 headings with the format "##### Date - User"
7) When a chat-log heading appears immediately before a higher-level heading, move the chat-log heading below that higher-level heading to preserve section boundaries. Do not move ordinary H4/H5 headings.

### Date Detection Code
- Convert all dates in the section to H2 headings of format "Month Year".
- Convert inferred plain-text section headings to H3 headings while preserving all existing Markdown heading levels.
- Hide H4-H6 headings from the import selection dialog and section UI.
- Allow the user to select which of the discovered headings they would like to keep in the UI.

### Completed
- Converted freeform import date detection to selectable H2 `Month Year` headings without adding a synthetic Timeline heading.
- Preserved existing Markdown heading levels, including user-authored H2/H3 headings.
- Converted inferred plain-text section headings to selectable H3 headings and only reordered internally marked inferred headings below following month headings.
- Hid H4-H6 headings from the selection dialog and section UI.
- Demoted unchecked selectable H2/H3 headings to hidden H4 organization headings.
- Removed exact duplicate heading lines at every heading level while preserving the following content.
- Expanded single newlines to Markdown paragraph breaks during import preparation so text formatting survives txt-to-md conversion.
- Added screenshot: `docs/screenshots/import_session_notes_date_detection.png`.
- Updated screenshot: `docs/screenshots/session_notes_duplicate_headings.png`.
- Tested:
  - `../.venv/bin/python -m pytest tests/test_session_notes.py tests/test_entity_file_saves.py`
  - `../.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py::test_ui_imports_freeform_lore_markdown_without_requiring_dates`
  - `../.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py::test_ui_import_dialog_keeps_month_year_dates_and_hides_h4_headings`
  - `../.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py::test_ui_removes_duplicate_headings_on_session_notes_load`

## Section Rendering 

When Add Previous or Next Section buttons are clicked, the text area should open with a blank section for Markdown editing.
An auto-generated header for the new section should be created with one of the following forms.
- "Heading Value: (Previously)"
- "Heading Value: (Coming Next)"

- The heading level for the newly added section should match the heading level of the element it was generated from. 

- When the Remove Section button is clicked, a warning should be displayed saying, "Are you sure you would like to delete this section and all subsections?"
  - A list of all H1-H4 subsections of the chosen section should be displayed below that warning.
- When the combine section button is clicked, the old title is currently converted to level 4 or 5.

### References
docs/screenshots/Atlantia_Lore.png
docs/screenshots/Time_Turning.png
docs/screenshots/import_session_notes.png
docs/screenshots/session_note_section_controls.png
tests/fixtures/session_notes/Family_Tree.md
tests/fixtures/disabled_legacy_add_session_note_ui.py
tests/fixtures/places/Atlantia_Lore.md

### Testing
- `.venv/bin/python -m pytest tests/test_session_notes.py tests/test_entity_file_saves.py`
- `.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py tests/e2e/test_character_sheet_roundtrip_ui.py`

### Completed
- Added page-load/import normalization that removes repeated exact heading lines at any level while preserving their content.
- Added regression coverage for duplicate `2024/03/18 - Camryn` headings and existing-file page-load repair.
- Added screenshot: `docs/screenshots/session_notes_duplicate_headings.png`.
- Tested:
  - `../.venv/bin/python -m pytest tests/test_session_notes.py`
  - `../.venv/bin/python -m pytest tests/test_entity_file_saves.py`
  - `../.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py::test_ui_removes_duplicate_headings_on_session_notes_load`
- Full e2e suites still have unrelated existing failures:
  - `tests/e2e/test_session_notes_ui.py`: missing disabled legacy fixture, remove-section warning flow, external character-sheet import persistence.
  - `tests/e2e/test_character_sheet_roundtrip_ui.py`: session-note save-status assertion.


# Future UI Improvements
## Section Rendering 

- Update section selection in the UI to show "Filename.md H1: Heading Value"
- Add the following buttons at the top of each section
  - Add Previous Section
  - Add Previous Subsection
  - Combine Section
- Add the following buttons at the bottom of each section
  - Add Next Section
  - Add Next Subsection
  - Remove Section

- When the combine section button is clicked, the old titles heading level should be dropped down one level.
