## App Consistency
- Do not modify a character sheet. If user saves changes to an existing character sheet only update changed sections
  - Default Stats are ["Name", "Level", "Race", "Class", "Pronouns"]
  - Default sections headings are ["Character Name", "Character Stats", "Character Details", "Character Summary", "Character Connections"]
    - If heading titles or stats column are changed, add an alies field in the JSON document indicating what they have been changed to. 
    - Wrote a unit test which takes the existing 3 characters md files and validates that they can be loaded in the UI and saved back without modifying untouched sections. 
  - Support reading knowledge graph fields from the table appended to the button of a character sheet like in Orin Nightblooms character sheet.
- Update the edit character UI to match the UI for the new character UI.
- Do not render _ character when displaying the name in the UI. 
- Add dedicated fields for the first name and family name in the JSON doc for each character. 
- Create a section of the character specs JSON which stores the fields present in the character stats table in a normalized format. 

Example character sheets have been added to the root level characters directory.