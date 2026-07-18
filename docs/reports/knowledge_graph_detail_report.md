# Knowledge Graph Detail Report

Date: 2026-07-18

## Screenshots Compared

- Reference graph: `docs/screenshots/Knowledge_Graph.png`
- Session-note graph: `docs/screenshots/Knowledge_Graph_From_Session_Notes.png`

## Visual Comparison


| Area                    | `Knowledge_Graph.png`                                                                                                                                               | `Knowledge_Graph_From_Session_Notes.png`                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Screen fit              | Wide graph with many nodes; it uses the screen well but is near the limit of readability.                                                                           | Fits comfortably in one screen as a compact hub-and-spoke graph.                                                                      |
| Entity quality          | Mostly recognizable people, families, and places: Jory Ravenmark, Neal Lovington, Orin Nightbloom, Mrs Nightbloom, Sunstone Mage College, School, and family nodes. | Only shows`Session Notes`, `Pixie Kingdom`, `Forest`, and `Hall`. It avoids noisy false nodes, but loses nearly all named characters. |
| Relationship usefulness | Edges show game-meaningful relationship types such as Ally, Client, Enemy, Family, and Place.                                                                       | Every edge is`Place`, so the graph is clean but shallow.                                                                              |
| Noise                   | Some family placeholders and generic nodes remain, but most nodes are campaign-relevant.                                                                            | Very low visual noise after pruning. The cost is heavy under-selection.                                                               |
| Detail support          | The screenshot is graph-focused; details are visually encoded in edges.                                                                                             | Includes the new node selector and detail table below the graph, which helps review evidence but takes vertical space.                |

## Game Helpfulness Rating

I would find `Knowledge_Graph.png` more helpful in an actual game.

- `Knowledge_Graph.png`: **8/10**
- `Knowledge_Graph_From_Session_Notes.png`: **4/10**

The new session-note graph is much easier to read, and it satisfies the one-screen goal. However, at the table, the older graph is more useful because it includes named characters and relationship types that support recall, improvisation, and continuity. The session-note graph is currently a good visual size but not yet a good campaign memory graph.

## Character And Place Generation Code Review

The app treats characters and places as authored lore entities:

- `local_chatbot.storage.list_characters()` reads character Markdown files from `CHARACTERS_DIR`, either as `<name>.md` files or directories containing `BACKSTORY.md`.
- `local_chatbot.storage.create_character()` writes a character sheet and regenerates that character's graph JSON.
- `local_chatbot.character_generator.RandomCharacterGenerator` creates deterministic character profiles, then saves them through `create_generated_character()`.
- `local_chatbot.storage.list_places()` reads place Markdown files from `PLACES_DIR`.
- `local_chatbot.storage.create_place()` and `create_place_markdown()` write place Markdown files.

That means the combined graph should ideally promote entities that can become real character or place files. Session-note prose should not directly create dozens of visible graph nodes from capitalized fragments.

## Current Lore File Coverage

Current local lore files under `world_building/lore`:

- Character files: `0`
- Place files: `0`
- Session-note files: `2`

Strict file-based coverage is therefore not applicable:

- Characters from lore files shown on session-note graph: `0 / 0`
- Places from lore files shown on session-note graph: `0 / 0`

The useful coverage calculation has to come from named entities mentioned in `world_building/import/Session_Notes.txt`, because this checkout currently has session notes but no authored character or place files.

## Expected Session-Note Characters

Based on repeated named mentions and context in `Session_Notes.txt`, I would expect these characters or character-like entities to appear on a useful session-note-derived graph:

1. Vivit
2. Typhon / Typhen / Typhin
3. Ekkir
4. Delia
5. Morningstar
6. John Doctor
7. Tullia Damasa
8. Dhinras Buzish
9. Tharevon
10. Elphira
11. Crotheise
12. Dizlevad / Dizelvad
13. Sachill
14. Lychee
15. Cory
16. Bloodmane
17. Mog
18. Flicker
19. Trixie
20. Sauriv / Surriv
21. Mr. Light
22. Mr. Witch
23. Bosley the Beastly
24. Gribblesnot
25. Diana Cloppington
26. Snivol Darkfang
27. Varesska
28. Chieftain Zhekaris
29. Saraphen
30. Ignis
31. Yeenoghu
32. Kay Flaircackle

Current visible session-note graph character coverage:

- Expected characters shown: `0 / 32`
- Character coverage: **0.0%**

## Expected Session-Note Places

Based on named or recurring locations in `Session_Notes.txt`, I would expect these places or place-like entities to be considered for the graph:

1. Pinewilds
2. Forest of the Five Trees
3. Mentha
4. The Mystic Garden
5. Ore Else
6. Feywild
7. Feydark
8. Underdark
9. Dominaria
10. Dwarven town / Dwarven kingdom
11. Craigwood
12. Witchlight Carnival / Carnival
13. Pixie Kingdom
14. Hall of Illusions
15. Big Top
16. Feasting Orchard
17. Town Hall
18. Human city
19. Lizardmen tribe / canyons
20. Church locations
21. Plane of Fire

Current visible session-note graph place coverage:

- Expected places shown: `3 / 21`
- Shown places: `Pixie Kingdom`, `Forest`, `Hall`
- Place coverage: **14.3%**

`Forest` and `Hall` are only partial matches for richer names such as `Forest of the Five Trees`, `Town Hall`, or `Hall of Illusions`, so this 14.3% is generous. With strict name matching, only `Pixie Kingdom` is a clear match, which would be `1 / 21`, or **4.8%**.

## Overall Coverage

Using the practical session-note expected entity list:

- Expected characters: `32`
- Expected places: `21`
- Total expected entities: `53`
- Total visible expected entities: `3`
- Overall generous coverage: **5.7%**
- Overall strict coverage: **1.9%**

## Recommendation

Update the one-screen pruning to a 2-3 screen pruning as the imported game has been active for much longer than the one in the test fixtures.

Add code which will extract likely character names from session notes and places files then uses those extracted characters and places in the UI. Display characters from the character sheets prior to derived characters in the UI.

The next implementation pass should add a session-note-specific entity extraction and review pipeline that promotes known or validated characters and places into the graph.

The target graph should prioritize:

- The current party members and major NPCs.
- Named places where the party acted or learned information.
- High-value factions or threats only if the graph gains a faction node type.
- Relationship labels that say why an entity matters, not only that it was mentioned.
