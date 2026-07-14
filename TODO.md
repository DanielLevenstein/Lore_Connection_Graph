# UI Bug Reports
- All files under the old legacy model harness can be safely deleted, I verified it locally.
- pull the latest changes from the main before writing code.
- Update `ui_issue_report.md` after UI bugs are fixed.

## UI Save Audit (visible elements before / after Save)

**Characters**
- Before Save: Heading `Roleplaying Character Creator`; tab `Characters` (selected); heading `Characters`; `Existing Characters` combobox (e.g. Jory Ravenmark); `Open` / `chat Open Character` buttons; character heading (e.g. `Jory Ravenmark`); `Edit Character` expander; `Character Attribute Graph` expander; `New Character` / `Create Character` section; editor textboxes (`Name`, `First Name`, `Family Name`, `Level`, `Race`, `Class`, `Pronouns`, `Backstory`, `Summary`); editor buttons (`person_add Create Character`, `save Save Character`, `undo Undo Changes`, `delete_forever Delete Character`).
- After Save: transient confirmation `Character Saved.` (may be hidden or brief); tab `Characters` remains selected; character heading remains visible; editor buttons still present. Successful saves typically write a PROFILE.json under the app `meta_data/character_metadata/<name>/PROFILE.json`.
- The `Character Saved` field not showing up after the save button is clicked is a bug and should be fixed. 
- The summary section on the character creation has two periods. 

**Places**
- Before Save: tab `Places`; heading `Places`; `Create Place` expander with `Name` textbox and `Place Markdown` textbox; `add_location_alt Create Place` button; existing `Place Files` combobox.
- After Save: transient confirmation `Place Saved.`; created place heading visible (e.g. `Brindle Hall`); `save Save Place` and `delete_forever Delete Place` buttons available;
- place file appears under the `places` fixture directory when save completes.
- Added new places aren't showing up in the UI after `Create Place` button is clicked
- When new places are created in the UI they are saved as `New Place.md`

**Session Notes**
- Before Save: tab `Session Notes`; heading `Session Notes`; `Session Note` combobox; `Open Session Note` button; editor fields (`Title`, `Session Note` textbox); `edit Edit Section` / `save Save Session Note` buttons.
- After Save: transient confirmation `Session Note Saved.`; selected session note heading visible (title); saved content displayed in the session notes panel; undo/delete buttons (`undo Undo Changes`, `delete_forever Delete Session Note`) remain available.

Please ensure that the following text fields are visible in the UI after clicking save `Character Saved.` / `Place Saved.` / `Session Note Saved.` 
They should be visible in plain text and not hidden by other UI elements.
Tests should assert both visible confirmation and fallback indicators (file writes, tab selection, presence of created headings) to reduce flakiness.

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

### Global Codex Skills

- Created global skills for LangGraph knowledge graphs, local model text transformations, Playwright e2e tests, Streamlit business logic separation, and language-model-assisted worldbuilding.
- Validated the new skill frontmatter and naming constraints.
- Added `AGENTS.md` guidance to use the worldbuilding skill for lore consistency checks.

### Rendering And Compiler Fixes

- Removed stale `language_model_harness.py` imports and switched tests/scripts to the existing `model_harness` defaults.
- Decoded literal escaped newlines during session note import, so imported headings and selected note labels render normally.
- Deleted obsolete `rendering_bug_*` screenshots after verification.
- Added `docs/screenshots/import_session_notes_escaped_newlines_fixed.png` to document the corrected import rendering.
- Testing: `.venv/bin/python -m pytest tests/test_session_notes.py tests/test_semantic_improvement_report.py tests/test_model_downloads.py tests/test_character_rewrite_model_lifecycle.py`; `.venv/bin/python -m pytest tests/e2e/test_session_notes_ui.py`.

### Environment Variable Removal Plan

- Created `docs/reports/environment_variable_feature_audit.md`.
- Added an ordered removal plan for all environment variables except `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES`, ranked from lowest to highest risk.
- Testing: report-only change; no runtime tests required beyond the focused validation already run for the pending code fixes.

### Hidden Knowledge Graph Release Hardening

- Replaced the Qwen-backed rewrite path with the in-code `deterministic-graph-rewrite` engine.
- Removed bundled external Qwen model configs from the release path.
- Hardened graph validation and save behavior so missing evidence, missing node references, and missing embeddings fail before graph JSON is written.
- Confirmed the same character knowledge graph can improve current character summary/backstory rewrites by feeding people, places, relationships, drives, and evidence into deterministic generated prose and the semantic improvement report.
- Disabled model-config-backed random character backstory generation for this release.
- Updated README, release notes, and rewrite design docs to reflect graph-backed generation instead of model downloads.
- Testing: run focused graph, rewrite, model-config, semantic-report, and character-generation tests before committing this section.

### Character Rewrite Metadata Stabilization

- Centralized deterministic rewrite story signals so summary, backstory, prompt context, and required-term scoring use the same profile-plus-graph facts.
- Preserved JSON/metadata-backed origin, drives, alliances, enemies, motivations, custom stat fields, and source-backed places in rewrite scoring and generated prose.
- Filtered non-story attribute artifacts out of relationship prose so race, class, family placeholders, and place edges do not masquerade as character relationships.
- Regenerated `docs/reports/semantic_backstory_improvement.md` with model, existing generated, and original backstory scores.
- Testing: `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/e2e/test_character_rewrites.py`; `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/test_character_graph.py tests/test_model_downloads.py tests/test_character_generation.py`.
