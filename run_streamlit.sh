#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
USE_STRUCTURED_GRAPH_FIXTURE=0

if [[ "${1:-}" == "--structured-graph-fixture" ]]; then
  USE_STRUCTURED_GRAPH_FIXTURE=1
  shift
fi

cd "$SCRIPT_DIR"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ "$USE_STRUCTURED_GRAPH_FIXTURE" == "1" ]]; then
  FIXTURE_WORLD_BUILDING_DIR="$SCRIPT_DIR/.tmp/structured_graph_fixture/world_building"
  FIXTURE_LORE_DIR="$FIXTURE_WORLD_BUILDING_DIR/lore"
  rm -rf "$FIXTURE_WORLD_BUILDING_DIR"
  mkdir -p "$FIXTURE_LORE_DIR/character_sheets" "$FIXTURE_LORE_DIR/places" "$FIXTURE_LORE_DIR/session_notes"
  cp "$SCRIPT_DIR"/tests/fixtures/character_sheets/*.md "$FIXTURE_LORE_DIR/character_sheets/"

  export LOCAL_CHATBOT_WORLD_BUILDING_DIR="$FIXTURE_WORLD_BUILDING_DIR"
  export LOCAL_CHATBOT_LORE_DIR="$FIXTURE_LORE_DIR"
  export LOCAL_CHATBOT_CHARACTERS_DIR="$FIXTURE_LORE_DIR/character_sheets"
  export LOCAL_CHATBOT_PLACES_DIR="$FIXTURE_LORE_DIR/places"
  export LOCAL_CHATBOT_SESSION_NOTES_DIR="$FIXTURE_LORE_DIR/session_notes"
  export LOCAL_CHATBOT_META_DATA_DIR="$FIXTURE_WORLD_BUILDING_DIR/meta_data"
  export LOCAL_CHATBOT_KNOWLEDGE_GRAPH_SOURCE_LABEL="Screenshot Fixture"
fi

echo "Starting Streamlit app..."
exec streamlit run streamlit_app.py "$@"
