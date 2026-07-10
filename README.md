# Roleplaying Character Creator

A local Streamlit app for creating custom chat characters from short backstories and chatting with them through a local OpenAI-compatible model server.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Local Data Layout

```text
config/model_name.json
data/model_name
docs/lore/character_sheets/name/BACKSTORY.md
docs/lore/places/name/MEMORY.md
data/characters/name/chatlogs/DATETIME_CHAT.log
data/character_graph/name.graph.json
```

Everything under `data/` is ignored by git.

See [Character Association Graph Design](docs/design/character_association_graph.md) for the derived relationship graph used during chat prompt retrieval.
