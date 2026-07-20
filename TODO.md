# Change log
The changelog has been moved to the bottom of RELEASE_NOTES.md

# Graph Improvements
- Move knowledge graph code into a helper module called graphviz_rendering.py
- Split graph rendering into four tabs [Characters Graph, Place Graph, Session Note Graph, Full Graph]

## Characters Graph
Views [Single Character, Character Data Only (formerly Party View)]
Column 0: Family Names
Column 1: Main Characters
Column 2: Secondary Characters & places

## Places Graph
Views [Place Lore]
Column 1: Source Documents 
Column 2: Place Names 
Column 3: Character Connections

## Session Notes
Views [Month Selection]
Column 1: Date
Column 2: Characters
Column 3: Places

### Structured Knowledge View
- Lock down the current knowledge graph view under the name "Structured Knowledge View"
- Refactor the code base so new knowledge views can be created without breaking the existing view.
- Use the UI code that was formally used to display the full knowledge graph to test this out.
