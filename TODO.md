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
A backup date button has been added under the `Lore Import` section for your convenience.

Update README with these notes once the feature is implemented. 
