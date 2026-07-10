## App Consistency
- Update button labels and headings to make all words start with an uppercase letter. 
- Support characters with first name only.
- Update the config directory so model configs are stored under config/model.
- Change the root level characters directory to docs/lore/character_sheets
  - Support both character_name/BACKSTORY.md and character_name.md format
  - Add a stub folder for places in docs/lore/places
- Move lore files in the data directory to data/lore/character_sheets/*
- Support storing summary as a standalone section or under the character name. Keep track of where the data came from when saving character.
- Save auto-generated characters to data/lore/character_sheets/character_name.md by default and let the player move them to the main characters folder manually.
  - make the docs/lore folder the source of truth for what characters and places are currently available. 

## App Improvements

- Create a PLACE_TEMPLATE.md file and PLACE_PARSING_RULES.md file
  - Create an editor in the UI allowing the player to create places.
- Support generation of backstory and summary text from the knowledge graph but only when the user specifically requests it.
  - For auto-generated sections write Auto Generated next to the section title.
- UI buttons ["Populate Summary" , "Repopulate Summary" , "Rewrite Backstory"]

## Documentation
- Rewrite the README.md file to match the current app design. Focus description on character creation and relationship graphing and remove references to chatbot.
- Review REQUIREMENTS.md and existing specification files for consistency.
- Write a specification file for COMBINED_KNOWLEDGE_GRAPH before modifying existing code. 

## Combined knowledge graph
- Hide the combined knowledge graph in the UI behind an environmental variable.
  - parse all files in the doc/lore folder when generating the knowledge graph. 
  - Show all places and relationships in a combined graph even if they do not have full character sheets associated with them.
  - Update the knowledge graph UI so that each tab shows the graph for a different character, avoiding the need to manually load character files for the graph to populate.
- Support the ability to create new place and character files from secondary characters. 
- Add the ability to add the Character Connections section to the bottom of an existing character sheet. 
  - Generated Character Connections section should place character information sourced from other character sheets and places first.

