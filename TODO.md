# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Semantic Aware Model
- Install semantic informed model locally for character rewrites and knowledge graph summary sections.
- Ensure the model selected is able to extract people and place names from existing source data successfully.
- Select a second visual inspection model to validate the generated UI from each page against the requirements. 

## Freeform Lore Markdown Import
We need the ability to import session notes about people, places or things without having to follow a specific Markdown file format.
I have written a document titled Atlanaia_Lore.md which fills in some of the missing details from the existing character sheets.
With our UI the way it's currently designed, this file is impossible to import anywhere. 
I could copy it into the summary section on the Places tab, but I feel forcing place information to match a specific schema detracts from the functionality of the app.

I could add dates to it and import it as a session note, but even then it only kind of fits. 
The solution for both problems is the same to let the Markdown files just exist as md files without trying to force them into a specific form. 

In fact, there is no structural reason for places and session notes not to share the exact same code behind the scenes. Let the schema drift as needed. 
If session dates exist, extract them but ask the user if they want to include any earth dates in their RP universe.

## 
