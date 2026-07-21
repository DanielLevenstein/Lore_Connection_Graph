Test-only variables:


| Variable                                       | Purpose                                                                             |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| `LOCAL_CHATBOT_E2E_LORE_FIXTURE_DIR`           | Points e2e graph tests at an alternate hidden/customer lore fixture directory.      |
| `LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_SCREENSHOT` | Saves an opt-in Combined Knowledge Graph screenshot during the screenshot e2e test. |
| `LOCAL_CHATBOT_E2E_KNOWLEDGE_GRAPH_NODE`       | Selects the graph node used by the screenshot e2e test. Defaults to`Dizlevad`.      |
| `LOCAL_CHATBOT_CHARACTER_GRAPH_TEST_LORE_DIR`  | Points direct character graph tests at an alternate lore directory.                 |

Directory Overrides:

| Variable                                  | Default                                       | Purpose                                                                               |
| ----------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------- |
| `LOCAL_CHATBOT_WORLD_BUILDING_DIR`        | `world_building`                              | Root directory for local campaign data, imports, backups, lore, and runtime metadata. |
| `LOCAL_CHATBOT_WORLD_BUILDING_IMPORT_DIR` | `$LOCAL_CHATBOT_WORLD_BUILDING_DIR/import`    | Raw markdown or text files staged for lore import.                                    |
| `LOCAL_CHATBOT_WORLD_BUILDING_BACKUP_DIR` | `$LOCAL_CHATBOT_WORLD_BUILDING_DIR/backup`    | Backup directory used by automatic and manual lore backups.                           |
| `LOCAL_CHATBOT_LORE_DIR`                  | `$LOCAL_CHATBOT_WORLD_BUILDING_DIR/lore`      | Root directory for canonical authored lore.                                           |
| `LOCAL_CHATBOT_CHARACTERS_DIR`            | `$LOCAL_CHATBOT_LORE_DIR/character_sheets`    | Authored character sheet markdown files.                                              |
| `LOCAL_CHATBOT_PLACES_DIR`                | `$LOCAL_CHATBOT_LORE_DIR/places`              | Authored place lore markdown files.                                                   |
| `LOCAL_CHATBOT_SESSION_NOTES_DIR`         | `$LOCAL_CHATBOT_LORE_DIR/session_notes`       | Authored or imported session note markdown files.                                     |
| `LOCAL_CHATBOT_META_DATA_DIR`             | `$LOCAL_CHATBOT_WORLD_BUILDING_DIR/meta_data` | Runtime metadata, character profiles, memories, and derived graph JSON.               |
| `LOCAL_CHATBOT_LORE_FIXTURES_DIR`         | `tests/fixtures`                              | Test fixture root used by the built-in lore import tools.                             |