# Roleplaying Character Creator

A local Streamlit app for creating tabletop character sheets, organizing campaign lore, and visualizing relationships as knowledge graphs.

The app treats authored markdown in `world_building/lore` as the source of truth. Character sheets can be edited through the UI, places can be created as lore files, and derived graph JSON can be regenerated from the Markdown whenever needed.

- `world_building/` is intentionally ignored by git so each player can keep their own campaign data
- Generated runtime files are stored in `world_building/meta_data` while user-readable application docs are stored in `world_building/lore`
- Templates, specifications, and parsing rules are committed under `docs/`
- test lore examples live under `tests/fixtures`.

Backup lore files are stored in `world_building/backup` and are updated everytime the app is loaded.
A manual backup button has been added in the `Lore Import` Section for your convenience.

## What It Does

- Create and edit character sheets with stats, backstory, summary, details, and character connections.
- Extracts session notes with date and session title info from either Markdown or raw text files.
- Build per-character knowledge graphs from character sheets.
- Use graph data to explicitly populate summaries or rewrite backstories when desired.

### Highlights

- Import session notes from raw text or markdown file.
- Extract the knowledge graph from the character backstory.
- Suggest graph-backed wording updates for character summary and backstory to improve writing legibility.
- All your data is stored locally on your machine.
- Graph-backed rewrite helpers never overwrite human edits to your character files.
- Character creator does not enforce a specific character schema or stats system.

## Setup

The easiest way to run the app is:

```bash
./run_streamlit.sh
```

This helper script creates a local `.venv` environment if needed, installs the dependencies from `requirements.txt`, and starts the Streamlit app.

If you prefer to manage the environment manually, use:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Project Screenshots

## Storage Source Of Truth

The repository uses committed project docs plus one ignored local workspace root:

- Only files under `world_building/lore` are treated as canonical authored campaign lore.
- Files under `world_building/import` are raw inputs and can be re-imported or reorganized.
- Files under `world_building/backup` are auto generated backups of lore and metadata which can be used for restoring old campaign notes and derived local state.
- Files under `world_building/meta_data` are derived or runtime data and can be rebuilt or regenerated from the lore.

## Project Layout

```text
docs/CHARACTER_TEMPLATE.md                  Character sheet template
docs/PLACE_TEMPLATE.md                      Place lore template
world_building/import/                      Raw markdown/text import staging area
world_building/lore/character_sheets/*.md   Authored character sheets
world_building/lore/character_sheets/*/BACKSTORY.md
                                            Alternate character sheet format
world_building/lore/places/*.md             Authored place lore
world_building/backup/                      Latest local Markdown backup
world_building/meta_data/character_metadata/*/PROFILE.json
                                            Runtime character metadata
world_building/meta_data/character_metadata/*/MEMORY.md
                                            Runtime memory notes
world_building/meta_data/character_graph/*.graph.json
                                            Derived per-character graph JSON
```

Everything under `world_building/` is local campaign material, runtime data, or generated output and should not be committed.

## Specs

- [Character Parsing Rules](docs/specs/CHARACTER_PARSING_RULES.md)
- [Place Parsing Rules](docs/specs/PLACE_PARSING_RULES.md)
- [Knowledge Graph Design](docs/specs/KNOWLEDGE_GRAPH_DESIGN.md)
- [Combined Knowledge Graph](docs/specs/COMBINED_KNOWLEDGE_GRAPH.md)
