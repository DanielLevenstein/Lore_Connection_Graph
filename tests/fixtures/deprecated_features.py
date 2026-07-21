"""
DISABLED TEST FIXTURE ONLY: legacy Add Session Note UI.

This code is intentionally not imported by the app or test suite. It preserves
the removed Streamlit UI path for regression context: saving directly through
save_session_notes(notes) date-splits and normalizes Markdown before the section
editor sees it, which can break section boundaries.
"""


def legacy_add_session_note_ui_reference(
    st,
    save_session_notes,
    push_session_notes_undo,
    set_active_session_note,
    set_active_session_note_section,
):
    """Reference-only copy of the removed UI. Do not call this fixture."""
    with st.expander("Add Session Note", expanded=st.session_state.get("session_notes_add_expanded", False)):
        if st.session_state.pop("clear_session_notes_draft", False):
            st.session_state["new_session_notes"] = ""
        notes = st.text_area(
            "New Session Notes",
            height=180,
            key="new_session_notes",
        )
        if st.button("Save Session Notes", icon=":material/note_add:", key="save_new_session_notes"):
            st.session_state["session_notes_add_expanded"] = True
            if not notes.strip():
                st.error("Add Session Notes Before Saving.")
                return
            push_session_notes_undo()
            saved = save_session_notes(notes)
            st.session_state["session_notes_saved_count"] = len(saved)
            if saved:
                set_active_session_note(saved[0].path)
                set_active_session_note_section()
            st.session_state["clear_session_notes_draft"] = True
            st.session_state["main_navigation_tab"] = "Session Notes"
            st.rerun()
