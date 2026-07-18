# Environment Variable And Feature Deletion Audit

Date: 2026-07-13

## Scope

This report answers two questions:

- Which environment variables are actually used anywhere in the test suite?
- Which feature gates or legacy surfaces look like deletion candidates before continuing character rewrite work?

Commands used:

```bash
rg -n "os\.environ|monkeypatch\.(setenv|delenv)|env\[|LOCAL_CHATBOT_|STREAMLIT_BROWSER" tests -g '*.py'
rg -n "os\.environ\.get|os\.environ\[|os\.environ\.setdefault|LOCAL_CHATBOT_|STREAMLIT_BROWSER" character_graph local_chatbot scripts streamlit_app.py tests -g '*.py'
.venv/bin/python -m vulture character_graph local_chatbot scripts streamlit_app.py tests --min-confidence 60
```

## Variables Used In Tests

| Variable | Test Usage | App/Code Usage | Notes |
| --- | --- | --- | --- |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Set to `false` in all Streamlit e2e app fixtures. | Streamlit runtime setting, not app code. | Keep in tests only. |
| `LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH` | Set to `1` in `tests/e2e/test_character_sheet_roundtrip_ui.py`. | Read in `streamlit_app.py` to hide/show Combined Knowledge Graph. | This is a feature gate currently used by e2e tests. |
| `LOCAL_CHATBOT_ENABLE_EXTERNAL_CHARACTER_IMPORT` | Set to `1` in `tests/e2e/test_session_notes_ui.py`. | Read in `streamlit_app.py` to hide/show external character sheet import. | This is a feature gate currently used by e2e tests. |
| `LOCAL_CHATBOT_WORLD_BUILDING_DIR` | Set in character and session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated tests and local sandboxing. |
| `LOCAL_CHATBOT_WORLD_BUILDING_IMPORT_DIR` | Set in session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated import fixtures. |
| `LOCAL_CHATBOT_LORE_DIR` | Set in character and session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated lore fixtures. |
| `LOCAL_CHATBOT_CHARACTERS_DIR` | Set in character and session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated character fixtures. |
| `LOCAL_CHATBOT_PLACES_DIR` | Set in character and session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated place fixtures. |
| `LOCAL_CHATBOT_SESSION_NOTES_DIR` | Set in character and session note e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep for isolated session note fixtures. |
| `LOCAL_CHATBOT_META_DATA_DIR` | Set in character e2e fixtures. | Read in `local_chatbot/paths.py`. | Keep while tests need isolated metadata writes for save-audit fallback assertions. |

## Variables Read By Code But Not Exercised In Tests

| Variable | Code Usage | Current Test Coverage | Deletion/Collapse Recommendation |
| --- | --- | --- | --- |
| `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES` | Read in `streamlit_app.py` by `graph_rewrites_enabled()`. | No test sets it. Rewrite behavior is unit-tested below the UI. | Candidate to remove as a gate once rewrite functionality is stable. Prefer one working app with buttons present when a character graph/model path is available. |
| `LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE` | Read in `streamlit_app.py` by `attribute_graph_override_enabled()`. | No test sets it. | Strong deletion candidate. It is described as an internal maintenance feature and is exactly the kind of hidden alternate UI path that increases app variants. |
| `LOCAL_CHATBOT_DATA_DIR` | Read in `local_chatbot/paths.py`; also used as a fallback for `LOCAL_CHATBOT_META_DATA_DIR`. | No current test sets it. | Candidate to collapse into `LOCAL_CHATBOT_WORLD_BUILDING_DIR` plus fixed `meta_data` subdir. User note says backward compatibility is not required. |
| `LOCAL_CHATBOT_META_DATA_DIR` | Read in `local_chatbot/paths.py`. | Character e2e tests set it. | Candidate to remove after replacing test setup with a direct path-configuration mechanism. Keep metadata under `world_building/meta_data` by default. |
| `LOCAL_CHATBOT_WORLD_BUILDING_BACKUP_DIR` | Read in `local_chatbot/paths.py`. | No current test sets it. | Candidate to remove unless custom backup location is a real user requirement. Default `world_building/backup` is simpler. |
| `LOCAL_CHATBOT_DOCS_LORE_DIR` | Read as fallback in `local_chatbot/paths.py`. | No current test sets it. | Delete. This is backwards-compatibility with the old docs/lore layout, and backwards compatibility is not required. |
| `LOCAL_CHATBOT_LORE_FIXTURES_DIR` | Read into `LORE_FIXTURES_DIR`, which vulture reports unused. | No current test sets it. | Delete along with `LORE_FIXTURES_DIR`. |

## Proposed Feature Deletions

## Removal Order By Risk

Keep `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES` for now. It gates a real feature that is not ready to be enabled by default.

Remove the remaining environment variables in this order:

1. `LOCAL_CHATBOT_LORE_FIXTURES_DIR`
   - Risk: very low.
   - Reason: read into `LORE_FIXTURES_DIR`, which is unused by app code and tests.

2. `LOCAL_CHATBOT_DOCS_LORE_DIR`
   - Risk: very low.
   - Reason: old `docs/lore` compatibility fallback. The lore move made `world_building/lore` the source of truth, and backwards compatibility is not required.

3. `LOCAL_CHATBOT_DATA_DIR`
   - Risk: low.
   - Reason: old generic data root. It overlaps with `world_building/meta_data`, which is the desired storage location after the lore move.

4. `LOCAL_CHATBOT_META_DATA_DIR`
   - Risk: low.
   - Reason: separate metadata-root override. Keeping metadata under `world_building/meta_data` simplifies the app and test mental model.

5. `LOCAL_CHATBOT_WORLD_BUILDING_BACKUP_DIR`
   - Risk: low to medium.
   - Reason: backup location override is not tested. Removing it standardizes backups under `world_building/backup`.

6. `LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE`
   - Risk: medium.
   - Reason: hidden alternate UI path with no test coverage. Removing it reduces app variants, but it touches Streamlit UI and character connection write paths.

7. `LOCAL_CHATBOT_ENABLE_EXTERNAL_CHARACTER_IMPORT`
   - Risk: medium.
   - Reason: tested feature gate. Remove the variable by making external character import part of the normal app rather than deleting the feature.

8. `LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH`
   - Risk: medium to high.
   - Reason: tested feature gate around the combined graph. Remove the variable by making the combined knowledge graph normal app behavior, not by deleting the graph.

9. Directory isolation variables used by e2e fixtures:
   - `LOCAL_CHATBOT_WORLD_BUILDING_DIR`
   - `LOCAL_CHATBOT_WORLD_BUILDING_IMPORT_DIR`
   - `LOCAL_CHATBOT_LORE_DIR`
   - `LOCAL_CHATBOT_CHARACTERS_DIR`
   - `LOCAL_CHATBOT_PLACES_DIR`
   - `LOCAL_CHATBOT_SESSION_NOTES_DIR`
   - Risk: high.
   - Reason: tests currently rely on these to isolate filesystem state. Remove only after replacing test setup with a direct path-configuration mechanism.

10. Legacy model harness scripts and variables:
    - Status: removed from this repository.
    - Deleted scripts: `scripts/download_model.py`, `scripts/start_model_server.py`, and `scripts/rebuild_download_manifests.py`.
    - Reason: external language-model downloads and server startup are no longer part of the release path.

### 1. Delete Attribute Graph Override UI

Why:

- Hidden behind `LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE`.
- No tests exercise the environment variable.
- It creates a second way to edit graph-derived character connection data.
- The app already supports writing visible `Character Connections` rows through normal combined graph actions.

Likely removal area:

- `streamlit_app.py`: `ENABLE_ATTRIBUTE_GRAPH_OVERRIDE`, `attribute_graph_override_enabled()`, and `render_attribute_graph_override_editor()`.
- `local_chatbot.storage.write_character_connections(..., manual_override=False)`: remove the unused `manual_override` parameter.

### 2. Collapse Legacy Lore/Data Path Overrides

Why:

- User direction: maintain the lore move structure, but no backwards compatibility required.
- `LOCAL_CHATBOT_DOCS_LORE_DIR`, `LOCAL_CHATBOT_DATA_DIR`, and `LOCAL_CHATBOT_META_DATA_DIR` preserve older layout flexibility.
- Tests now isolate via `LOCAL_CHATBOT_WORLD_BUILDING_DIR`, `LOCAL_CHATBOT_LORE_DIR`, and specific lore subdirectory vars.

Proposed target:

- Keep `LOCAL_CHATBOT_WORLD_BUILDING_DIR` for test isolation.
- Keep `LOCAL_CHATBOT_LORE_DIR`, `LOCAL_CHATBOT_CHARACTERS_DIR`, `LOCAL_CHATBOT_PLACES_DIR`, `LOCAL_CHATBOT_SESSION_NOTES_DIR`, and `LOCAL_CHATBOT_WORLD_BUILDING_IMPORT_DIR` while tests still use them.
- Delete `LOCAL_CHATBOT_DOCS_LORE_DIR`, `LOCAL_CHATBOT_DATA_DIR`, `LOCAL_CHATBOT_META_DATA_DIR`, `LOCAL_CHATBOT_LORE_FIXTURES_DIR`.

### 3. Decide Whether Combined Knowledge Graph Should Stay Gated

Why:

- `LOCAL_CHATBOT_ENABLE_COMBINED_GRAPH` is actively used in e2e tests.
- The user’s current direction says the new global knowledge graph needs processing information from all sections.
- If this is now core functionality, a hidden environment gate creates two app variants.

Recommendation:

- Do not delete the combined graph feature.
- Consider deleting the gate and making the combined graph normal app behavior after current rendering issues are settled.

### 4. Decide Whether Rewrite Buttons Should Stay Gated

Why:

- `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES` is read by app code but not set in tests.
- Character rewrite functionality is the active target feature.
- Hiding the UI behind an env var makes it easier for tests and users to miss regressions.

Recommendation:

- Do not delete rewrite functionality.
- Consider deleting the gate and making the buttons visible with clear disabled/error states when graph/model prerequisites are missing.

### 5. Delete Dead Chat UI Remnants

Why:

- Vulture reports these Streamlit functions as unused: `build_character_messages`, `generate_fallback_reply`, `graph_context_for_prompt`, `render_memory_tools`.
- `render_character_info()` currently renders the editor and relationship graph, not a chat UI.
- `local_chatbot.client.build_messages`, `write_memory`, `append_memory`, and `append_chatlog` are also not referenced.

Recommendation:

- If chat is no longer part of the single working app, delete the dead chat/memory helpers and associated session-state setup.
- If chat should return later, reintroduce it as part of the one app after the current rewrite/graph workflows are stable.

### 6. Delete Direct `llama cli` Rewrite Path Unless Explicitly Needed

Why:

- The direct CLI rewrite path is only referenced by tests in the current working tree.
- The design doc says rewrites should use the configured local OpenAI-compatible model server.
- The user specifically noted running the language model outside the app caused consistency issues.

Recommendation:

- Prefer the app’s single local model path.
- Deleted the Qwen-backed rewrite client path in favor of `deterministic-graph-rewrite`; keep future model work out of the release path unless the model is a codebase-owned, redistributable dependency.

## Lower-Confidence Cleanup Candidates

These are unused by vulture, but are small enough that deletion should follow nearby code inspection:

- `character_graph.extraction.character_last_name`
- `character_graph.graph_view.visible_relationship_count`
- `local_chatbot.character_rewrites.graph_drive_values`
- `local_chatbot.character_rewrites.attribute_value`
- `local_chatbot.session_notes.lore_document_path`
- `local_chatbot.session_notes.has_session_note_date`
- `local_chatbot.storage.create_stub_character`
- `local_chatbot.storage.read_backstory_template`
- legacy model harness runner/download scripts were removed on 2026-07-14

## Suggested Next Step

Start with deletions that reduce app variants rather than deleting small helpers first:

1. Remove Attribute Graph Override UI and its env var.
2. Remove old path compatibility variables for `docs/lore`, `data`, and separate metadata roots.
3. Decide whether Combined Knowledge Graph and Graph Rewrite controls should be normal app features instead of env-gated features.
