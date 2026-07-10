# Roleplaying Character Creator

A local Streamlit app for creating tabletop character sheets, organizing campaign lore, and visualizing relationships as knowledge graphs.

The app treats authored markdown in `docs/lore` as the source of truth. Character sheets can be edited through the UI, places can be created as lore files, and derived graph JSON can be regenerated from the markdown whenever needed.

`docs/lore/` is intentionally ignored by git so each player can keep their own campaign data out of the repository. Templates and parsing rules are committed under `docs/`; test lore examples live under `tests/fixtures`.

## What It Does

- Create and edit character sheets with stats, backstory, summary, details, and character connections.
- Support both `docs/lore/character_sheets/Name.md` and `docs/lore/character_sheets/Name/BACKSTORY.md`.
- Create place lore files in `docs/lore/places`.
- Build per-character knowledge graphs from character sheets.
- Use graph data to explicitly populate summaries or rewrite backstories when the player clicks a generation button.
- Keep generated drafts and runtime metadata under ignored `data/` folders.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Project Layout

```text
config/model/*.json                         Model configuration files
docs/CHARACTER_TEMPLATE.md                  Character sheet template
docs/PLACE_TEMPLATE.md                      Place lore template
docs/lore/character_sheets/*.md             Authored character sheets
docs/lore/character_sheets/*/BACKSTORY.md   Alternate character sheet format
docs/lore/places/*.md                       Authored place lore
data/lore/character_sheets/*.md             Generated character drafts
data/lore/character_sheets/*/PROFILE.json   Runtime character metadata
data/lore/character_sheets/*/MEMORY.md      Runtime memory notes
data/lore/character_sheets/*/chatlogs/*.log Runtime play logs
data/character_graph/*.graph.json           Derived per-character graph JSON
```

Everything under `data/` is local runtime or generated output and should not be committed.
Everything under `docs/lore/` is local authored campaign lore and should not be committed.

## Specs

- [Character Parsing Rules](docs/specs/CHARACTER_PARSING_RULES.md)
- [Place Parsing Rules](docs/specs/PLACE_PARSING_RULES.md)
- [Knowledge Graph Design](docs/specs/KNOWLEDGE_GRAPH_DESIGN.md)
- [Combined Knowledge Graph](docs/specs/COMBINED_KNOWLEDGE_GRAPH.md)
