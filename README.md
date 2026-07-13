# Roleplaying Character Creator

A local Streamlit app for creating tabletop character sheets, organizing campaign lore, and visualizing relationships as knowledge graphs.

The app treats authored markdown in `data/lore` as the source of truth. Character sheets can be edited through the UI, places can be created as lore files, and derived graph JSON can be regenerated from the Markdown whenever needed.

`data/lore/` is intentionally ignored by git so each player can keep their own campaign data out of the repository. Templates and parsing rules are committed under `docs/`; test lore examples live under `tests/fixtures`.

## What It Does

- Create and edit character sheets with stats, backstory, summary, details, and character connections.
- Extracts session notes with date and session title info from either Markdown or raw text files.
- Build per-character knowledge graphs from character sheets.
- Use graph data to explicitly populate summaries or rewrite backstories when desired.

### Highlights

- Import session notes from raw text or markdown file.
- Extract the knowledge graph from the character backstory.
- Suggest wording updates for character summary and backstory to improve writing legibility.
- All your data is stored locally on your machine.
- The AI model will never overwrite human edits to your character files.
- Character creator does not enforce a specific character schema or stats system.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Project Screenshots

## Project Layout

```text
config/model/*.json                         Model configuration files
docs/CHARACTER_TEMPLATE.md                  Character sheet template
docs/PLACE_TEMPLATE.md                      Place lore template
data/lore/character_sheets/*.md             Authored character sheets
data/lore/character_sheets/*/BACKSTORY.md   Alternate character sheet format
data/lore/places/*.md                       Authored place lore
data/character_metadata/*/PROFILE.json   Runtime character metadata
data/character_metadata/*/MEMORY.md      Runtime memory notes
data/character_metadata/*/chatlogs/*.log Runtime play logs
data/character_graph/*.graph.json           Derived per-character graph JSON
```

Everything under `data/` is local runtime or generated output and should not be committed.
Everything under `data/lore/` is local authored campaign lore and should not be committed.

## Specs

- [Character Parsing Rules](docs/specs/CHARACTER_PARSING_RULES.md)
- [Place Parsing Rules](docs/specs/PLACE_PARSING_RULES.md)
- [Knowledge Graph Design](docs/specs/KNOWLEDGE_GRAPH_DESIGN.md)
- [Combined Knowledge Graph](docs/specs/COMBINED_KNOWLEDGE_GRAPH.md)
