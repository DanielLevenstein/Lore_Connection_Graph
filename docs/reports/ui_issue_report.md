# UI Issue Report

Date: 2026-07-14

## Summary

This report captures the current Streamlit UI issue state for the repository. The July 14 save-audit bugs have been fixed and covered by focused Streamlit/Playwright tests.

# Fixed On 2026-07-14

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

## 1. Streamlit UI state areas with high bug risk

The app contains many `st.expander`, `st.tabs`, and `st.session_state` interactions that are common sources of reload/rerun bugs:

- `st.expander("Add Session Note", expanded=st.session_state.get("session_notes_add_expanded", False))`
- `st.expander("Character Attribute Graph", expanded=False)` and related override logic
- `st.tabs([node.name for node in character_nodes] or ["Lore"])`
- `st.session_state` management for `active_character`, `active_place`, `active_session_note`, and section editors
- repeated `st.rerun()` calls after save/delete actions

These patterns should be the first focus of UI regression coverage because state can be lost on reload or when a rerun happens inside a selected tab.

## 2. UI Save Audit (visible elements before / after Save)

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

# Fixed on 2026-07-18

- Changes made to the Optional Metadata section aren't undone when clicking the "Undo Changes" button.
- Restoring a previous version of lore should delete current lore files not present in back-up. 
- The Combined Knowledge Graph no longer renders a duplicate top-level heading above its expander.
- The Combined Knowledge Graph now includes a graph-node detail table below the chart, populated by the selected visible node and its incoming/outgoing evidence-backed edges.
- Session-note imports no longer project the session-note source into the graph view. Session notes are internal evidence sources only.
- The session-note graph projection was expanded from one-screen pruning to a 2-3 screen target for longer campaigns. The current direct graph trace keeps 28 internal nodes and 28 internal edges for evidence, while the graph view exposes only authored main characters and authored main places as roots.
- Combined Knowledge Graph tabs and graph root selectors now represent only authored main characters and authored main places. Selecting a root now highlights that node while the graph keeps all main characters together in one vertical party column.
- The graph DOT now uses stable layout groups: Family Names, Party/Main Characters, Secondary Characters, and Places.
- Connections outside the party are placed in the Secondary Characters and Places columns and ordered by evidence mention count.
- In column layout mode, visible relationship edges are non-constraining so they do not pull nodes out of the requested columns.
- A `Show Full Character Connection Graph` button restores the full non-session character connection graph view; the paired button returns to the party-centered graph.
- Old `.txt` session-note files imported through bulk lore import are converted to `.md`, so the Session Notes UI and Combined Knowledge Graph pick them up.
- UI lore file changes now mark the combined graph dirty after creates, edits, imports, restores, deletes, undo actions, and graph regenerations.
- The `Other Connections` table now shows each evidence item for a repeated connection as its own row.
- The Family Names column naturally renders empty when no family nodes exist, so no extra visibility checkbox is needed.
- Source files are no longer shown in the graph itself; source labels remain available in the lower `Extended Notes` detail/list section.
- Focused graph tracing now recognizes canonical session-note typo variants such as `Dizelvad`, `Typhin`, and `Typhen`, so Dizlevad no longer collapses to a single visible connection.
- Graph clarity metrics are recorded in markdown reports and tests only; the Combined Knowledge Graph UI does not display graph grades.
- Combined Knowledge Graph node detail evidence no longer exposes raw filesystem paths; node rows now show compact source labels such as `Source: Dizlevad.md`.

# Fixed on 2026-07-19

- The Combined Knowledge Graph now uses explicit `Single Character` and `Whole Graph` modes instead of a party/full toggle.
- The single-character graph shows only the connections associated with the selected graph node.
- Graph nodes are ordered by mention/evidence count within Family Names, Main Characters, Secondary Characters, and Places columns.
- Duplicate graph edges between the same two nodes are collapsed to the most prominent relationship label.
- Relationship/evidence tables now keep repeated evidence as separate rows instead of joining evidence into one cell.
- Evidence columns now strip Markdown bullet/list markers before display.
- Named session-note source nodes such as `Family Tree` are typed as `source_document` and appear in the Family Names column with a distinct graph shape instead of being promoted as secondary characters.
- Family-name nodes are labeled as `{Name} Family`, and extracted group names such as `Ignis Cult` appear in the Family Names column with a distinct group shape.

## Improvements made

### Knowledge Graph Improvements

- Captured a fresh screenshot of `world_building/import/Session_Notes.txt` behavior at `docs/screenshots/Knowledge_Graph_current_2026-07-18.png`.
- Added `reports/knowledge_graph_report.md` comparing the current session-note graph to `docs/screenshots/Knowledge_Graph.png`.
- Combined `docs/specs/KNOWLEDGE_GRAPH_DESIGN2.md` into `docs/specs/KNOWLEDGE_GRAPH_DESIGN.md` so the graph redesign guidance has a single source.
- Added `docs/specs/KNOWLEDGE_GRAPH_DESIGN3.md` to describe the longer-term session-note extraction strategy.
- Added a focused graph regression test that keeps false session-note character candidates out of the visible combined graph.
- Added direct graph tracing coverage for session-note entity extraction, authored-character prioritization, and vertical layout behavior for broad session-note graphs.
- Added committed-fixture graph layout coverage using the non-hidden Atlantia, Neal, Jory, and Orin fixtures.
- Added one-paragraph authored main-character stubs for Vivit, Typhon, Dizlevad, Mog, and Flicker so the graph can prioritize the recurring party.
- Added an opt-in Playwright screenshot capture path gated by `LOCAL_CHATBOT_E2E_LORE_FIXTURE_DIR` and `LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_SCREENSHOT`, so hidden/customer fixtures can be used without committing customer data.
- Added direct graph coverage that generates and validates character graphs for every character sheet in the default fixtures, or every hidden/customer character sheet when `LOCAL_CHATBOT_CHARACTER_GRAPH_TEST_LORE_DIR` is set.
- Added `docs/reports/knowledge_graph_fixed_issues_report.md` summarizing the graph issues fixed in this pass.

### Backup Improvements

- Expand the Optional Metadata section by default if any of the fields in it are filled out.
- Update backup functionality.
  - Restored snapshots should show up as "Restored {DATE_TIME}" in the dropdown
  - Before restoring a backup, add a new backup of the current state as is with the label "Snapshot {DATE_TIME}"
  - Add the newly restored backup into the dropdown as "Restored {DATE_TIME}" but place it above the newly created stapshot.
  - Manually created backups should use the "Snapshot {DATE_TIME}" format, while auto-generated backups should use the "Backup - {DATE_TIME}" format.

###  Test Cases Added
Make race and class fields official. 
- Test case **Mz. Glorious Backstory**:
   - Create a new character: "Mz. Glorious"
   - Enter the following backstory "Ms. Glorious is a glorious character who's vibrant personality is too powerful to be constrained by the required fields in their character sheet. "
   - Click the "Create Character" button
   - Error is displayed with the following text "Complete Name, Race, Class, And Backstory."
  
Infer markdown title from title in UI.
- Test case **Markdown Inn**
  - On the place tab, click the "Create Place" button.
  - For the place body type "This Inn is housed by non-technical people who don't understand how markdown titles work."
  - Click save
  - Result: Upon reloading the place, the Markdown title is added.
  - If the user later tries to update the title of an existing place in Markdown the changes are reverted. 

Allow the user to update titles of places and session notes through Markdown and through the UI. 
- Test case **Coming Next the Rapture Family**
  - On the session notes tab, scroll down to the last family name and open the associated session note
  - Click "Add Next Section"
  - The new section will be auto named The Lovington Family: (Coming Next)
  - Rename the section to "The Rapture Family" using Markdown and click save
  - validate that the section title is update. 
