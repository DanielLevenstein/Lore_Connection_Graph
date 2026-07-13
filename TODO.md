# Character Rewrite And Lore Move Merge

This branch combines `feature/character_rewrite` and `feature/lore_move`.

## Character Rewrite Improvements

### Goals

- Generate character summaries and backstories from the character graph instead of deterministic fallback prose.
- Let missing character graphs be regenerated automatically before rewrite actions.
- Avoid requiring a long-running local API server for one-off rewrite generation.
- Show visible feedback when a local model artifact needs to be downloaded.
- Compare generated, existing, and original backstory sections in the semantic improvement report.

### Concerns To Resolve

- Direct `llama cli` output can include loader, banner, prompt, or performance text and must never be saved into character fields.
- First-run model downloads are slow, even with smaller quantized artifacts.
- Top-level Streamlit tab state needs careful handling, so validation errors do not move the user to another tab.
- The current rewrite path should be simplified and tested before merging back to main.

### Suggested Next Pass

- Isolate model invocation behind a small adapter with fixture-backed tests for CLI transcripts.
- Keep model download and generation status outside editable character fields.
- Re-evaluate the selected local model and quantization against output quality and download time.
- Add a focused Playwright test for Repopulate Summary with a missing graph and a mocked rewrite client.

### Testing

- Run focused unit tests for semantic reports, character rewrites, lore imports, and path behavior.
- Run Playwright e2e tests for the character rewrite and session note workflows.

## Session Note Import Deduplication

Allow importing the same session note file again without creating a second file or duplicating existing sections. New imported sections should be appended when their section titles are not already present.

### H1 Heading Visibility

- For H1 headings, offer a non-destructive Hide Heading action instead of removing the section.
- Hiding an H1 heading converts the H1 line to an ignored H4 heading and keeps its content in the file.
- When hiding an H1 heading, promote the next non-H1 heading in that section to H1.

## Lore Directory Move

The main flaw the lore move addresses is that the app was attempting to use the data directory for both internal application storage and the user-facing document store.

### Completed Proposal

Create root-level `docs` and `world_building` directories.

- Store specification and design docs in `docs`.
- Store lore, imports, backups, character graph data, and local model data in `world_building`.
- Use `world_building/import`, `world_building/lore`, and `world_building/meta_data` to separate raw imports, generated Markdown, and runtime metadata.
- On the session notes page, import UI should show the `world_building/import` directory as the base directory for Markdown imports.

### Backup Functionality

Backup lore files are stored in `world_building/backup` and are updated every time the app is loaded. Lore backups can be restored using the Lore Import functionality.

- Remove the existing backup button with a date timestamp.
- Add `Import Testing Lore`, `Create Lore Backup`, `Import Lore Backup`, and `Bulk Lore Removal` under `Lore Import`.
- Make sure the `Bulk Lore Removal` button quietly creates a backup before the wipe.

## Completed

### Backup Functionality

- Added `world_building/backup` as the local lore backup directory.
- Refresh backups whenever the Streamlit app loads.
- Include `world_building/meta_data` files in backups and backup restores.
- Removed the backup timestamp button.
- Added `Import Testing Lore`, `Create Lore Backup`, `Import Lore Backup`, and `Bulk Lore Removal` actions under `Lore Import`.
- Bulk lore removal creates a backup before wiping local lore.
- Documented backup behavior in README.

### Lore Directory Move

- Kept authored lore under `world_building/lore` and raw imports under `world_building/import`.
- Moved runtime metadata, graph data, and local model data under `world_building/meta_data`.
- Updated tests and documentation to use the nested metadata path.

### Merge Resolution

- Resolved merge conflicts between `feature/character_rewrite` and `feature/lore_move`.
- Preserved the `world_building` directory defaults while retaining fixture overrides for tests.
- Preserved the semantic improvement report comparison across model rewrite, existing generated section, and original section.

### Global Codex Skills

- Created global skills for LangGraph knowledge graphs, local model text transformations, Playwright e2e tests, Streamlit business logic separation, and language-model-assisted worldbuilding.
- Validated the new skill frontmatter and naming constraints.
