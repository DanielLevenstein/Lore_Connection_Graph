# Requirements

Build a local Python app for creating roleplaying character sheets, maintaining lore files, and viewing relationship graphs derived from those files.

## App Consistency
- Update button labels and headings to make all words start with an uppercase letter. 
- Support characters with first name only.
- Update the config directory so model configs are stored under config/model.
- Change the root level characters directory to world_building/lore/character_sheets
  - Support both character_name/BACKSTORY.md and character_name.md format
  - Add a stub folder for places in world_building/lore/places
- Move lore files to world_building/lore/character_sheets/*
- Support storing summary as a standalone section or under the character name. Keep track of where the data came from when saving character.
- Save generated characters to world_building/lore/character_sheets/character_name.md when the player chooses to save them.
  - make the world_building/lore folder the source of truth for what characters and places are currently available.

## Storage

- The source-of-truth file structure is `docs/` for committed project documentation, `world_building/` for local user-facing campaign documents, and `meta_data/` for local internal application data.
- Authored lore is stored in `world_building/lore`.
- Raw source imports are staged under `world_building/import`.
- Authored lore in `world_building/lore` is ignored by git so users can populate it with private campaign data.
- Available character sheets are sourced from `world_building/lore/character_sheets`.
- Available places are sourced from `world_building/lore/places`.
- Generated characters are stored in `world_building/lore/character_sheets` only after the player saves them.
- Runtime metadata, memory files, chat logs, generated graph JSON, and local model data are stored under `meta_data/`.
- No files in `world_building/` or `meta_data/` should be committed.

## Character Sheets

- Support flat character sheets at `world_building/lore/character_sheets/character_name.md`.
- Support folder character sheets at `world_building/lore/character_sheets/character_name/BACKSTORY.md`.
- Store runtime character metadata in `meta_data/character_metadata/character_name/PROFILE.json`.
- Store memory notes as markdown in `meta_data/character_metadata/character_name/MEMORY.md`.
- Store logs as raw text in `meta_data/character_metadata/character_name/chatlogs`.
- Preserve existing character sheet sections where possible when saving.
- Support first-name-only characters.

## Places

- Provide a place template and parsing rules.
- Allow players to create place lore files from the UI.
- Include places when building the combined knowledge graph.

## Models

- Model configs are stored in `config/model`.
- Each model config stores the model URL, size, download options when known, and a one-sentence description.
- The model can be switched without changing character or lore files.
- Use `https://huggingface.co/DavidAU/L3.1-Evil-Reasoning-Dark-Planet-Hermes-R1-Uncensored-8B` as the initial model option.

## Knowledge Graph

- Generate per-character graphs from character sheets.
- Hide the combined knowledge graph behind an environment variable until it is ready for normal use.
- Build combined graph data from all files under `world_building/lore`.
- Show characters, places, and relationships even when referenced entities do not have full character sheets.
- Generate summary and backstory text from graph data only when the player explicitly requests it.
