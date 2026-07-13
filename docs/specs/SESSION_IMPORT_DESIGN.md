# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Session Notes Import
We need the ability to import session notes about people, places, or things without having to follow a specific Markdown file format.

### Design 
For all imports without structured md headings do the following.
1) Identify the file title or file name and set it to H1 heading.
2) Extract all dates in the files and convert them to H2 headings (Not Implemented)
3) Preserve existing Markdown heading levels and convert inferred plain-text section headings other than the first to H3 headings.
4) Display a popup with a list of all extracted headings ask the user what headings they want searchable.
5) Convert deselected non-date headings back to plain text.
6) Chat logs are converted to H5 headings with the format "##### Date - User"
7) When a chat-log heading appears immediately before a higher-level heading, move the chat-log heading below that higher-level heading to preserve section boundaries. Do not move ordinary H4/H5 headings.


## Section Rendering Buttons

- Update section selection in the UI to show "Filename.md H1: Heading Value"
- Add the following buttons at the top of each section
  - Add Previous Section
  - Combine Section
- Add the following buttons at the bottom of each section
  - Add Next Section
  - Remove Section

When Add Previous or Next Section buttons are clicked, the text area should open with a blank section for Markdown editing.
An auto-generated header for the new section should be created with one of the following forms.
- "Heading Value: (Previously)"
- "Heading Value: (Coming Next)"

- When the Remove Section button is clicked, a warning should be displayed saying, "Are you sure you would like to delete this section and all subsections?"
  - A list of all H1-H4 subsections of the chosen section should be displayed below that warning.
- When the combine section button is clicked, the old title should be converted to an H5 heading (`##### Value`) so it stays visible without becoming a selectable section.
- Section editor saves should prevent added or edited sections that do not start with an H1, H2, or H3 heading.
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
