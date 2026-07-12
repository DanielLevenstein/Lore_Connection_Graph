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

## Application Screenshots
- Add an application screenshot to docs/screenshots before committing code.
- Name the screenshot based on the UI page you are modifying.
- Compare the current version to the previous one before updating.

## Automated Testing

- e2e tests for this project use playwright
- When automated tests break, add a unique id to the button or table you are accessing.