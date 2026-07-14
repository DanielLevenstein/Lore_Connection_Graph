---
name: streamlit-ui-testing
description: "Use when adding or updating Streamlit UI regression tests for tab and expander state persistence, especially across page reloads and reruns. Triggers: streamlit, UI test, tabs, expander, reload, rerun, session_state, Playwright, e2e."
---

# Streamlit UI Testing

This skill is a focused workflow for Streamlit UI regression coverage. It helps you validate that all Streamlit code paths are exercised, with special emphasis on tab selection, expander open/closed state, and page reload behavior.

## When to use

- You are writing or updating Playwright/Streamlit UI tests.
- You need to verify Streamlit tab selection survives reloads or intentional reruns.
- You need to verify `st.expander` open/closed state behaves correctly after page refresh.
- You are debugging Streamlit session state or rerun bugs.
- Your UI changes involve conditional rendering inside tabs or expanders.

## Workflow

1. Identify the Streamlit entry point.
   - Prefer `streamlit_app.py` if present.
   - If ambiguous, locate the file that imports `streamlit as st` and contains `st.tabs`, `st.expander`, or `st.session_state`.

2. Scan the app for interactive state paths.
   - Find `st.tabs(...)`, `st.expander(...)`, `st.session_state[...]`, and `st.rerun()`.
   - Note any dynamic keys, default expanded values, and conditional branches inside those containers.

3. Add or extend tests to cover each path.
   - Click each tab and verify its content appears.
   - Open and close every expander you can reach.
   - Assert visible content for both the expanded and collapsed states.
   - Reload the page with `page.reload()` and verify the expected UI state.
   - Validate whether state should persist or intentionally reset.

4. Verify state persistence and reload behavior.
   - For stateful tabs: select a tab, reload, and assert the same tab is still selected if intended.
   - For expanders: expand a section, reload, and assert the section remains open if state should persist.
   - Confirm hidden content behind tabs/expanders still renders after reload when its parent becomes active.

5. Validate all conditional branches.
   - Trigger alternate app paths by using different tab combinations, expander states, and button actions.
   - Ensure no branch is only reachable by manual interaction that is skipped by current test coverage.
   - Check both open and collapsed variants of UI sections.

6. Use stable selectors.
   - Prefer `page.get_by_role(..., name=...)` and `page.get_by_text(..., exact=True)`.
   - Avoid selectors that depend on transient CSS or ordering unless ordering is part of the behavior.
   - Use element names and button labels from the app UI.

## Important checks

- `st.session_state` keys are initialized before read.
- `st.rerun()` is used intentionally and does not discard the desired tab/expander state.
- `st.tabs` and `st.expander` state is not lost silently on refresh.
- Conditional rendering inside tabs/expanders is executed in the reload path.
- UI labels and buttons remain stable enough to test reliably.

## Example test patterns

- Select a tab, reload, and assert the selected pane remains active if that behavior is expected.
- Expand a section, reload, and assert the section remains expanded if state is persisted.
- Click a button inside a tab/expander, reload, and confirm the content still matches the selected state.
- Force a rerun with an action and verify whether the page resets or preserves state.

## Notes

Most of the manual Streamlit bugs in this repo are in tabs and expanders because state can be lost during reruns or refreshes. This skill focuses on adding coverage for those paths first.
