# Character Association Graph Design

## Purpose

The Character Association Graph is a derived index built from each character's human-authored `BACKSTORY.md`. Its config defines three broad connection buckets: relationships, attributes, and places. The extractor only auto-populates facts the markdown can be expected to provide reliably: the character name, race, and class.

The markdown backstory in `world_building/lore/character_sheets` remains the canonical source of truth. The graph JSON in `world_building/meta_data/character_graph` is regenerated derived data and can be discarded or rebuilt when the backstory changes.

## Current Scope

The current implementation is an MVP with an offline, dependency-light pipeline:

- Load one markdown backstory for a selected character.
- Extract the primary character name from the markdown H1.
- Extract Race and Class from the Character Stats markdown table.
- Infer Family from the last token in the full character name.
- Generate grounded summaries for those attribute nodes.
- Store nodes, edges, metadata, and deterministic local embeddings in JSON.
- Retrieve relevant attribute context by exact value, fuzzy value match, and embedding similarity.
- Expose retrieved context for UI tools and optional prompt construction.

The implementation does not yet call a local language model for extraction, does not use Pydantic, and does not require sentence-transformers, FAISS, or Chroma. Those remain future upgrades.

## Redesign Direction

The current graph should evolve into two related but separate knowledge stores:

- Entity-specific graphs keep character-local attributes, motivations, evidence, and rewrite context.
- The combined campaign graph shows only global Character and Place nodes that are useful for navigation and relationship review.

The redesign does not need to preserve old generated graph JSON. Authored lore remains the source of truth, and derived graph files may be rebuilt after parser or schema changes.

### Character Connections Override

Character sheets may include a manually authored `Character Connections` table. When present, this table overrides generated character-connection rows for the visible graph and rewrite context. This allows users to correct extraction mistakes without hand-editing derived JSON.

Recommended normalized fields:

- `id`
- `edge_type`
- `edge_item`
- `edge_value`
- `edge_description`
- `edge_source`

Attribute values should use readable names in UI tables, not underscore-heavy identifiers. IDs may still use compact normalized forms such as `mr_smith` or `john_adams_father` when part of a name is unknown.

### Session Note And Place Attributes

Session notes and places should gain entity-specific attribute sections instead of being forced through character-sheet assumptions. Extracted attributes must include an attribute type, source evidence, and a context-aware shortened description when raw evidence is too long for a review table.

### Combined Graph Requirements

The combined campaign graph must stay stricter than entity-specific graphs:

- Forbid self-referencing graph nodes.
- Hide nodes that have no connections.
- Remove duplicate edges from the chart.
- Show only true people, places, and explicitly meaningful family nodes.
- Do not combine unrelated mother, father, or parent placeholders across characters.
- Keep details removed from the chart available in a table below the graph.
- Provide a node-focused detail table so a selected graph node can be reviewed without visually tracing every edge.

### Redesign Testing

Validation should cover both data shape and visual fidelity:

- Every combined graph node is a Character, Place, or approved Family node.
- Duplicate edges are not shown.
- Attribute values do not display raw `_` separators.
- Attribute value and description fields are separate and have reasonable maximum lengths.
- Session-note imports are scanned for duplicate or low-confidence attribute generation.
- Generated graph screenshots are visually reviewed for nodes that are not real entities.

## Module Layout

```text
character_graph/
  __init__.py
  config.py
  embeddings.py
  extraction.py
  ingest.py
  prompt_context.py
  retrieval.py
  schema.py
  storage.py
  validation.py
  graph_view.py
```

### `ingest.py`

`load_backstory(source_file, character_id=None)` reads a markdown file and returns a `BackstoryDocument` containing:

- `character_id`
- `source_file`
- `raw_text`
- `source_hash`
- `schema_version`

The source hash is a SHA-256 hash of the raw markdown and is used by validation to detect stale generated graphs.

### `config.py`

`config/character_graph.json` defines the valid graph connection types. The config is intentionally ontology-shaped instead of extractor-shaped: it contains three root-level lists named `relationships`, `attributes`, and `places`.

Current config shape:

```json
{
  "schema_version": "0.2.0",
  "relationships": ["family", "drive", "alliance", "enemy"],
  "attributes": ["race", "class", "pronouns"],
  "places": ["home", "family", "enemies", "allies"]
}
```

The extractor currently auto-populates only `family`, `race`, and `class` when those connection types are enabled in the config. Other configured types are valid for future extraction or manual graph editing, but they are not assumed to exist in markdown. The config loader rejects malformed config files, missing root lists, and duplicate connection types.

### `schema.py`

The graph uses dataclasses rather than Pydantic to avoid adding runtime dependencies.

Top-level schema:

```json
{
  "schema_version": "0.2.0",
  "primary_character": {},
  "characters": {},
  "attributes": {},
  "relationships": [],
  "embeddings": {},
  "metadata": {}
}
```

Important dataclasses:

- `CharacterGraph`
- `PrimaryCharacterRef`
- `CharacterNode`
- `AttributeNode`
- `RelationshipEdge`
- `EmbeddingRecord`
- `Alignment`
- `GraphMetadata`

`CharacterGraph.to_dict()` and `CharacterGraph.from_dict()` provide JSON round-tripping.

`characters` stores actual character nodes. `attributes` stores stable values such as family name, race, and class. `CharacterGraph.from_dict()` migrates older `0.1.0` graph JSON by moving non-primary legacy nodes from `characters` into `attributes`.

### `extraction.py`

`extract_character_graph(document, primary_name=None)` builds a full graph from a `BackstoryDocument`.

The extractor currently uses:

- Markdown H1 heading as the primary character name when available.
- The full primary character name to infer `Family` from the final name token.
- The `Character Stats` markdown table to extract `Race` and `Class`.
- Simple motivation patterns such as `wants to`, `seeks to`, and `goal is to`.
- A small trait vocabulary for lightweight trait extraction.
- Metadata summaries that identify the source evidence for each attribute.

Only connection types declared in `config/character_graph.json` are valid. The default config includes:

- `family`
- `race`
- `class`
- `pronouns`
- `drive`
- `alliance`
- `enemy`

Only `family`, `race`, and `class` are generated automatically from markdown today. Generated metadata edges use `sentiment="metadata"`, `trust_level=1.0`, `conflict_level=0.0`, and `emotional_weight=0.3`.

### `embeddings.py`

The MVP uses `HashingEmbedder`, a deterministic local hashing vectorizer. It tokenizes text, hashes tokens into a fixed-size vector, and normalizes the result.

This is not a substitute for a sentence transformer model, but it gives the retrieval path a stable offline semantic-overlap signal and keeps tests fast. A future `SentenceTransformerEmbedder` can be added behind the same `embed(text) -> list[float]` shape.

### `storage.py`

`save_graph(graph, path)` writes pretty JSON with UTF-8 encoding.

`load_graph(path)` returns a `CharacterGraph` or `None` when no graph file exists.

### `retrieval.py`

`retrieve_relevant_context(graph, message, limit=3, min_score=0.18)` returns `RetrievedCharacterContext` records.

Scoring combines:

- Exact case-insensitive name or alias match.
- Fuzzy match using `difflib.SequenceMatcher`.
- Cosine similarity between the user message vector and stored character embedding vector.

The primary character is excluded from retrieval so prompt context focuses on attribute nodes.

### `prompt_context.py`

`build_prompt_context(retrieved)` formats retrieved characters and relationship edges into a compact prompt section:

```text
Relevant character attribute context:

Elf:
Arlen Voss's race is Elf. Evidence: Race is listed as Elf in the Character Stats table.

Relationship metadata:
- Relationship: Race
- Evidence: Race is listed as Elf in the Character Stats table.
```

### `validation.py`

`validate_graph(graph, expected_source_hash=None)` returns warning strings for:

- Schema version mismatch.
- Missing primary character node.
- Character or attribute nodes with no summary.
- Relationship sources or targets missing from both `characters` and `attributes`.
- Relationships with no evidence.
- Source hash mismatch.

### `graph_view.py`

`graph_view.py` contains Streamlit-independent helpers for the simple relationship UI:

- `relationship_rows(graph)` builds relationship table rows.
- `attribute_rows(graph)` builds attribute table rows.
- `relationship_dot(graph)` builds a Graphviz DOT string for a compact left-to-right relationship diagram.

Keeping these helpers outside `streamlit_app.py` makes the display formatting testable without importing the Streamlit app.

## Storage Integration

Storage follows the project-wide source-of-truth split: `docs/` holds committed specifications and templates, `world_building/lore` holds editable campaign Markdown, `world_building/import` holds raw source imports, and `world_building/meta_data` holds derived/runtime application data.

Authored character markdown files live under:

```text
world_building/lore/character_sheets/<name>/BACKSTORY.md
```
or 

```text
world_building/lore/character_sheets/Character_Name.md
```

Generated draft character sheets live under:

```text
world_building/lore/character_sheets/Character_Name.md
```

Graph JSON now lives under:

```text
world_building/meta_data/character_graph/<name>.graph.json
```

`language_model.paths` defines `CHARACTER_GRAPHS_DIR` and creates it in `ensure_base_dirs()`.

`language_model.storage.Character.graph_path` points at the derived graph file.

`write_character_profile(character, profile)` now writes `PROFILE.json`, writes `BACKSTORY.md`, then calls `regenerate_character_graph(character)`.

`regenerate_character_graph(character)`:

1. Loads the character's `BACKSTORY.md`.
2. Extracts a `CharacterGraph`.
3. Saves the graph JSON to `character.graph_path`.

## Prompt Context Integration

`graph_context_for_prompt(character, prompt)` can format relevant graph facts for any future prompt workflow. The current character-building UI uses graph data only when the player explicitly requests generated summary or backstory text.

Context flow:

1. A user action or prompt supplies text.
2. The app loads `character.graph_path` if it exists.
3. Retrieval finds generated attributes relevant to the message.
4. Prompt context is formatted with summaries and relationship metadata.
5. The caller may include the context in an explicit generation request.

If the graph is missing or malformed, normal sheet editing continues without graph context.

## Streamlit Relationship UI

The app renders a `Character attribute graph` expander for the active character. It is shown both when a model is available and when the user is only editing or inspecting the character.

The UI includes:

- A `Regenerate` button that rebuilds graph JSON from the current `BACKSTORY.md`.
- Metrics for character count, relationship count, and attribute count.
- A `Graph` tab with a simple Graphviz relationship diagram.
- A `Relationships` tab with character, relationship, value, and evidence.
- An `Attributes` tab with attribute roles, aliases, and summaries.

If no graph JSON exists yet, the UI prompts the user to regenerate it. If graph loading fails, the error is displayed in the expander while normal chat remains usable.

## Example Graph Shape

```json
{
  "schema_version": "0.2.0",
  "primary_character": {
    "id": "arlen_voss",
    "name": "Arlen Voss",
    "source_file": "world_building/lore/character_sheets/Arlen Voss/BACKSTORY.md"
  },
  "characters": {
    "arlen_voss": {
      "name": "Arlen Voss",
      "aliases": [],
      "role": "primary character",
      "summary": "Arlen is guarded, strategic, and loyal once trust is earned.",
      "motivations": [
        "restore his family name and avoid becoming like his father"
      ],
      "traits": [
        "guarded",
        "loyal",
        "strategic"
      ],
      "alignment": {
        "moral_alignment": "unknown",
        "faction_alignment": [],
        "loyalty_targets": [],
        "opposition_targets": []
      },
      "source_spans": []
    }
  },
  "attributes": {
    "family_voss": {
      "value": "Voss",
      "aliases": [],
      "attribute_type": "Family",
      "summary": "Arlen Voss's family is Voss. Evidence: Voss is inferred as the family name from the full character name Arlen Voss.",
      "source_spans": [
        "Voss is inferred as the family name from the full character name Arlen Voss."
      ]
    },
    "race_elf": {
      "value": "Elf",
      "aliases": [],
      "attribute_type": "Race",
      "summary": "Arlen Voss's race is Elf. Evidence: Race is listed as Elf in the Character Stats table.",
      "source_spans": [
        "Race is listed as Elf in the Character Stats table."
      ]
    }
  },
  "relationships": [
    {
      "source": "arlen_voss",
      "target": "family_voss",
      "relationship_type": "family",
      "relationship_label": "Family",
      "sentiment": "metadata",
      "trust_level": 1.0,
      "conflict_level": 0.0,
      "emotional_weight": 0.3,
      "evidence": [
        "Voss is inferred as the family name from the full character name Arlen Voss."
      ]
    },
    {
      "source": "arlen_voss",
      "target": "race_elf",
      "relationship_type": "race",
      "relationship_label": "Race",
      "sentiment": "metadata",
      "trust_level": 1.0,
      "conflict_level": 0.0,
      "emotional_weight": 0.3,
      "evidence": [
        "Race is listed as Elf in the Character Stats table."
      ]
    }
  ],
  "embeddings": {
    "race_elf": {
      "node_id": "race_elf",
      "embedding_text": "Elf Race Arlen Voss's race is Elf...",
      "embedding_ref": "local_hash:race_elf",
      "vector": []
    }
  },
  "metadata": {
    "snapshot_date": "2026-07-08T16:27:00",
    "backup_date": "2026-07-08T16:27:00",
    "source_hash": "..."
  }
}
```

## Testing

The MVP is covered by `tests/test_character_graph.py`.

Covered behavior:

- Backstory loading and source hashing.
- Config loading and validation for relationships, attributes, and places.
- Family, Race, and Class relationship extraction.
- Evidence preservation.
- Embedding record creation.
- JSON storage round-trip.
- Legacy `0.1.0` graph migration into separate attributes.
- Retrieval and prompt context formatting.
- Validation warnings for missing relationship targets.
- Relationship table rows, character table rows, and Graphviz DOT generation.

Run the focused tests:

```bash
.venv/bin/python -m pytest tests/test_character_graph.py tests/test_character_generation.py
```

## Known Limitations

- Family is inferred from the final token in the full character name, which may not fit every naming convention.
- Only name, Race, and Class are assumed to exist in markdown.
- Social relationships from prose are intentionally ignored.
- Trait and motivation extraction are lightweight heuristics.
- The hashing embedder only approximates semantic overlap.
- Existing graph files are regenerated on profile save, not continuously watched.
- There is no manual graph editor.
- Graph visualization is intentionally simple and limited to chart-backed metadata relationship types.

## Upgrade Path

The current module boundaries are intended to support these upgrades without changing the chat integration:

- Add a local LLM structured extractor in `extraction.py` if broader social relationships are reintroduced.
- Add a sentence-transformer-backed embedder in `embeddings.py`.
- Store vectors in FAISS or Chroma instead of JSON.
- Add faction and organization nodes.
- Add timeline and relationship-change events.
- Add a manual correction UI.
- Add graph export formats such as Mermaid, GraphML, or NetworkX.
