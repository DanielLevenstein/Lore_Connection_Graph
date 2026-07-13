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

## Lore Directory Move
The main flaw the lore move is we are attempting to use the data directory for both the internal application storage and the userfacing document store.

### Previous solution
Move the local lore source directory from `docs/lore` to `data/lore` so docs can stay focused on committed templates, specs, reports, and screenshots.

### New proposal
Create 3 root levels data directories [docs, world_building, meta_data]
- Store specification and design docs in docs
- Store lore folder in world_building
- Store character graph and local model in meta_data

Add two subdirectories to the world_building directory [import, lore] 
- this will separate raw import files from generated Markdown and provides a path to create an export directory later if we want a way of extracting info from the system.
- On the session notes page import UI should show the world_building directory as the base directory for md imports.

### Backup Functionality
Backup lore files are stored in `world_building/backup` and are updated everytime the app is loaded.
Lore backups can be restored using the Lore Import functionality. 

- Remove the existing backup button with a date timestamp
- Add the following buttons under the `Lore Import` heading
[Import Testing Lore, Create Lore Backup, Import Lore Backup, Bulk Lore Removal]
- Make sure the `Bulk Lore Removal` button quietly creates a backup before the wipe. 

### Testing
- Add focused tests for lore backup copying, timestamp recording, Lore Import UI visibility, and backup creation before bulk removal.

## Completed

### Backup Functionality
- Added `world_building/backup` as the local lore backup directory.
- Refresh backups whenever the Streamlit app loads.
- Removed the backup timestamp button.
- Added `Import Testing Lore`, `Create Lore Backup`, `Import Lore Backup`, and `Bulk Lore Removal` actions under `Lore Import`.
- Bulk lore removal creates a backup before wiping local lore.
- Documented backup behavior in README.
