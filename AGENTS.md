# Commit Working Changes
- Between each section in a TODO list commit working changes to create a stable checkpoint. 
- Do not commit changes until testing for each section is complete.
- If no testing section is present, add one to the TODO and commit it with the feature commit. 

## Semantic Aware Model
- Install semantic informed model locally for character rewrites and knowledge graph summary sections.
- Ensure the model selected is able to extract people and place names from existing source data successfully.
- Select a second visual inspection model to validate the generated UI from each page against the requirements. 

## Task Management
- When a task is finished, add a Completed section to the TODO.md file. 
- When finishing a section, check TODO.md for the next task.

## Consistency Skill
- Use `$use-language-models-for-worldbuilding` for lore consistency checks before saving generated or rewritten character, place, session note, or knowledge graph summary content.
- Verify generated worldbuilding output preserves established names, places, relationships, chronology, and source-backed facts.

## Application Screenshots
- Add an application screenshot to docs/screenshots while testing code but do not commit these files. 
- After reviewing the work I will commit the files which are useful for demonstration or bug tracking purposes. 

## Automated Testing

- e2e tests for this project use playwright
- When automated tests break, add a unique id to the button or table you are accessing.
