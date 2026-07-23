# Knowledge Graph Creation
Build a role-playing character sheet tracker which will pull in information from multiple data sources and display semantic connections between characters. 

## What It Does

- Create and edit character sheets with stats, backstory, summary, details, and character connections.
- Extracts session notes with date and session title info from either Markdown or raw text files.
- Build per-character knowledge graphs from character sheets.
- Use graph data to explicitly populate summaries or rewrite backstories when desired.

## Features

- Use a local language model to clean up character summaries and backstories
- Import session notes from external data sources extracting heading and date information
- Generate a knowledge graph from multiple data import sources and display information to users in clean readable format

### Highlights

- Import session notes from raw text or markdown file.
- Extract the knowledge graph from the character backstory.
- Suggest graph-backed wording updates for character summary and backstory to improve writing legibility.
- All your data is stored locally on your machine.
- Graph-backed rewrite helpers never overwrite human edits to your character files.
- Character creator does not enforce a specific character schema or stats system.

## Document Summary
Build a role-playing character sheet tracker which will pull in information from multiple data sources and display semantic connections between characters. The tool should include the use of local language models to clean up summaries and backstories before importing external session notes into knowledge graphs. Knowledge graph views are available for viewing character, place, and session notes.

Tech Stack - Streamlit, LangChain, Llama Cli, Graphviz