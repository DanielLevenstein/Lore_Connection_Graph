# Knowledge Graph Views
- Move knowledge graph code into a helper module called graphviz_rendering.py
- Split graph rendering into four tabs [Characters Graph, Place Graph, Session Note Graph, Full Graph]

Specs Update
1) When the top level tab is Characters only display the ["Single Character", "Party View"]
2) When the top level tab is "Places" display ["Place Lore", "Party View"]
3) When the top level tab is "Session Notes" display ["Place Lore", "Party View"]

Also remove all non-place or character nodes from the place graph, If no character connections exist, just don't show any. 

## Characters Graph
Views [Single Character, Party View]
Column 0: Family Names
Column 1: Main Characters
Column 2: Secondary Characters & places

## Places Graph
Views [Place Lore, Party View]

Column 0: Source Documents & Place Names
Column 1: Markdown Heading 1
Column 2: Markdown Heading 2
Column 3: Markdown Heading 3 
Column 4: Character Connections

Sort all connections within each column by the number of connections with the edges with the most connections displayed first.
Display all graph connections as a straight line and enforce that columns are maintained.
Table of connections should only show edges with character connections

## Session Notes Graph
Views [Place Lore, Party View]

Column 0: Source Documents & Group Names
Column 1: Markdown Heading 1
Column 2: Markdown Heading 2
Column 3: Markdown Heading 3
Column 4: Character Connections & Places
Sort all connections within each column by the number of connections with the edges with the most connections displayed first.
Display all graph connections as a straight line and enforce that columns are maintained.
Table of connections should only show edges with character connections

# Node Deduplication
Views [Character Deduplication, Place Deduplication, Node Removal]
Freeform graph with all headings and source documents hidden.

UI Design isn't completed yet
