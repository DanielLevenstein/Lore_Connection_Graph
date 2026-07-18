# UI Issue Report

Date: 2026-07-14

## Summary

This report captures the current Streamlit UI issue state for the repository. The July 14 save-audit bugs have been fixed and covered by focused Streamlit/Playwright tests.

## Fixed On 2026-07-14

- `Character Saved.` now remains visible after saving, and the character editor stays expanded so Save/Undo/Delete buttons remain visible after rerun.
- `Place Saved.` now remains visible after creating or saving a place, and the place editor stays expanded after save.
- `Session Note Saved.` remains visible after saving session note edits.
- New places are selected and visible immediately after Create Place.
- New place Markdown titles are normalized to the submitted place name, preventing stale `# New Place` content and `New Place.md`-style UI confusion.
- The character creation Summary placeholder no longer shows a stray second period.
- Legacy model-harness runner/download scripts were removed; the random character script now uses the deterministic in-code generator.

## Verification

- `.venv/bin/python -m pytest tests/test_entity_file_saves.py tests/test_character_rewrite_model_lifecycle.py`
- `.venv/bin/python -m pytest tests/e2e/test_character_sheet_roundtrip_ui.py`

## Findings

### 1. UI test environment is not fully provisioned

- Playwright e2e tests now run in this local environment.

### 2. Test import path bug

- `tests/e2e/test_character_rewrites.py` originally failed because the repository root was not on `sys.path` during pytest discovery.
- `tests/conftest.py` has been added to insert the repo root into `sys.path` so e2e tests can import `character_graph` and other app modules.

### 3. Semantic report formatting mismatch

- `scripts/generate_semantic_improvement_report.py` contained score table labels that no longer matched assertions in the e2e test.
- The table labels were updated to `Post-transform story` and `Pre-transform backstory` to match current report expectations.

### 4. Streamlit UI state areas with high bug risk

The app contains many `st.expander`, `st.tabs`, and `st.session_state` interactions that are common sources of reload/rerun bugs:

- `st.expander("Add Session Note", expanded=st.session_state.get("session_notes_add_expanded", False))`
- `st.expander("Character Attribute Graph", expanded=False)` and related override logic
- `st.tabs([node.name for node in character_nodes] or ["Lore"])`
- `st.session_state` management for `active_character`, `active_place`, `active_session_note`, and section editors
- repeated `st.rerun()` calls after save/delete actions

These patterns should be the first focus of UI regression coverage because state can be lost on reload or when a rerun happens inside a selected tab.

## Observed UI issue opportunities

- incoming tab/expander state persistence may still be fragile on refresh and rerun outside the audited save flows
- explicit UI state is scattered across many session keys instead of a single source of truth

## Recommendations

- Keep the save-audit e2e coverage focused on visible confirmations plus file-write fallback indicators.
- Add focused Playwright tests for:
  - tab selection persistence after reload
  - expander expanded/collapsed persistence after reload
  - save behavior inside active tabs and expanders
  - session note section visibility after rerun and reload
- Review and simplify `st.session_state` initialization in `streamlit_app.py`.

## Next steps

- Continue prioritizing tab and expander state persistence in the Streamlit app.

## UI Save Audit (visible elements before / after Save)

**Characters**
- Before Save: Heading `Roleplaying Character Creator`; tab `Characters` (selected); heading `Characters`; `Existing Characters` combobox (e.g. Jory Ravenmark); `Open` / `chat Open Character` buttons; character heading (e.g. `Jory Ravenmark`); `Edit Character` expander; `Character Attribute Graph` expander; `New Character` / `Create Character` section; editor textboxes (`Name`, `First Name`, `Family Name`, `Level`, `Race`, `Class`, `Pronouns`, `Backstory`, `Summary`); editor buttons (`person_add Create Character`, `save Save Character`, `undo Undo Changes`, `delete_forever Delete Character`).
- After Save: transient confirmation `Character Saved.` (may be hidden or brief); tab `Characters` remains selected; character heading remains visible; editor buttons still present. Successful saves typically write a PROFILE.json under the app `meta_data/character_metadata/<name>/PROFILE.json`.
- Fixed: `Character Saved.` remains visible after Save and the editor buttons remain visible.

**Places**
- Before Save: tab `Places`; heading `Places`; `Create Place` expander with `Name` textbox and `Place Markdown` textbox; `add_location_alt Create Place` button; existing `Place Files` combobox.
- After Save: transient confirmation `Place Saved.`; created place heading visible (e.g. `Brindle Hall`); `save Save Place` and `delete_forever Delete Place` buttons available; place file appears under the `places` fixture directory when save completes.
- Fixed: created places appear immediately after `Create Place`, and stale `New Place` titles are replaced with the submitted place name.

**Session Notes**
- Before Save: tab `Session Notes`; heading `Session Notes`; `Session Note` combobox; `Open Session Note` button; editor fields (`Title`, `Session Note` textbox); `edit Edit Section` / `save Save Session Note` buttons.
- After Save: transient confirmation `Session Note Saved.`; selected session note heading visible (title); saved content displayed in the session notes panel; undo/delete buttons (`undo Undo Changes`, `delete_forever Delete Session Note`) remain available.

Please ensure that the following text fields are visible in the UI after clicking save `Character Saved.` / `Place Saved.` / `Session Note Saved.` 
They should be visible in plain text and not hidden by other UI elements.
Tests should assert both visible confirmation and fallback indicators (file writes, tab selection, presence of created headings) to reduce flakiness.

Status: fixed and covered by `tests/e2e/test_character_sheet_roundtrip_ui.py::test_ui_save_confirmations_are_visible`.
