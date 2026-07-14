# UI Issue Report

Date: 2026-07-14

## Summary

This report captures the current Streamlit UI issue state for the repository. Two categories of problems were found:

- test infrastructure and regression validation issues that block UI bug discovery
- UI state and feature-risk areas in `streamlit_app.py` that are known to be fragile

## Findings

### 1. UI test environment is not fully provisioned

- The Playwright browser binary is missing in the dev container.
- Running the Playwright-based e2e tests fails with `BrowserType.launch: Executable doesn't exist`.
- Until `playwright install chromium` is run, the Streamlit UI regression suite cannot execute end-to-end.

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

- incoming tab/expander state persistence may be fragile on refresh and rerun
- explicit UI state is scattered across many session keys instead of a single source of truth
- the current end-to-end test harness is unable to verify these behaviors until Playwright is installed

## Recommendations

- Install Playwright browsers in the dev environment:
  - `source .venv/bin/activate`
  - `playwright install chromium`
- Re-run the e2e suite after installation:
  - `PYTHONPATH=. pytest -q tests/e2e --maxfail=1`
- Add focused Playwright tests for:
  - tab selection persistence after reload
  - expander expanded/collapsed persistence after reload
  - save behavior inside active tabs and expanders
  - session note section visibility after rerun and reload
- Review and simplify `st.session_state` initialization in `streamlit_app.py`.

## Next steps

- Confirm Playwright browser installation and rerun the full `tests/e2e` suite.
- Add a screenshot-based regression test or manual capture once Playwright is working.
- Prioritize bug fixes around tab and expander state persistence in the Streamlit app.

## UI Save Audit (visible elements before / after Save)

**Characters**
- Before Save: Heading `Roleplaying Character Creator`; tab `Characters` (selected); heading `Characters`; `Existing Characters` combobox (e.g. Jory Ravenmark); `Open` / `chat Open Character` buttons; character heading (e.g. `Jory Ravenmark`); `Edit Character` expander; `Character Attribute Graph` expander; `New Character` / `Create Character` section; editor textboxes (`Name`, `First Name`, `Family Name`, `Level`, `Race`, `Class`, `Pronouns`, `Backstory`, `Summary`); editor buttons (`person_add Create Character`, `save Save Character`, `undo Undo Changes`, `delete_forever Delete Character`).
- After Save: transient confirmation `Character Saved.` (may be hidden or brief); tab `Characters` remains selected; character heading remains visible; editor buttons still present. Successful saves typically write a PROFILE.json under the app `meta_data/character_metadata/<name>/PROFILE.json`.

**Places**
- Before Save: tab `Places`; heading `Places`; `Create Place` expander with `Name` textbox and `Place Markdown` textbox; `add_location_alt Create Place` button; existing `Place Files` combobox.
- After Save: transient confirmation `Place Saved.`; created place heading visible (e.g. `Brindle Hall`); `save Save Place` and `delete_forever Delete Place` buttons available; place file appears under the `places` fixture directory when save completes.

**Session Notes**
- Before Save: tab `Session Notes`; heading `Session Notes`; `Session Note` combobox; `Open Session Note` button; editor fields (`Title`, `Session Note` textbox); `edit Edit Section` / `save Save Session Note` buttons.
- After Save: transient confirmation `Session Note Saved.`; selected session note heading visible (title); saved content displayed in the session notes panel; undo/delete buttons (`undo Undo Changes`, `delete_forever Delete Session Note`) remain available.

Note: confirmation messages such as `Character Saved.` / `Place Saved.` / `Session Note Saved.` can be transient or rendered hidden in some UI states. Tests should assert both visible confirmation and fallback indicators (file writes, tab selection, presence of created headings) to reduce flakiness.
