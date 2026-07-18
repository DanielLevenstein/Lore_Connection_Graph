# UI Feedback Response

Date: 2026-07-18

## Bugs Found

- Changes made to the Optional Metadata section aren't undone when clicking the "Undo Changes" button.
- Restoring a previous version of lore should delete current lore files not present in back-up. 

###  Test Cases
Make race and class fields official. 
- Test case **Mz. Glorious Backstory**:
   - Create a new character: "Mz. Glorious"
   - Enter the following backstory "Ms. Glorious is a glorious character who's vibrant personality is too powerful to be constrained by the required fields in their character sheet. "
   - Click the "Create Character" button
   - Error is displayed with the following text "Complete Name, Race, Class, And Backstory."
  
Infer markdown title from title in UI.
- Test case **Markdown Inn**
  - On the place tab click the "Create Place" button.
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

## Suggested Improvements

- Expand the Optional Metadata section by default if any of the fields in it are filled out.
- Update backup functionality.
  - Restored snapshots should show up as "Restored {DATE_TIME}" in the dropdown
  - Before restoring a backup, add a new backup of the current state as is with the label "Snapshot {DATE_TIME}"
  - Add the newly restored backup into the dropdown as "Restored {DATE_TIME}" but place it above the newly created stapshot.
  - Manually created backups should use the "Snapshot {DATE_TIME}" format, while auto-generated backups should use the "Backup - {DATE_TIME}" format.

## Knowledge Graph Improvements

- Clean up wording for the evidence column in the Character Attributes Graph for Neal Lovington.

| Character Sheet | Item   | Value          | Evidence                                             |
|-----------------|--------|----------------|------------------------------------------------------|
| Jory Ravenmark  | Client | Neal Lovington | But Neals favorite client was actually Ms Ravenmark. |
