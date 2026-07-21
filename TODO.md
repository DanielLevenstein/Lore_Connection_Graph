# TODO
## Switch Branch
- Switch to feature/character_rewrite and merge the latest changes from features/knowledge_graph2
- Update the TODO file on feature/character_rewrite branch with this file.
- Update CHARACTER_REWRITE_DESIGN.md and CHARACTER_REWRITE_IMPROVEMENTS.md designs prior to updating code.

## Character Rewrite Improvements

Character rewrite version implemented with LangChain performed worse than an initial version.
Identify the smallest local model which can be used for the rewrite and use existing.
Current branch has a backstory rewrite function, but it's disabled because of low similarity scores in `semantic_backstory_improvement.md`

### Testing
- `generate_semantic_improvement_report.py`
- `test_character_rewrite_model_lifecycle.py` 
- `test_semantic_improvement_report.py`

### Goals

- Generate character summaries and backstories from a selected model using both original prose and knowledge extracted from graph.
- Avoid requiring a long-running local API server for one-off rewrite generation.
- Show visible feedback when a local model artifact needs to be downloaded.
- Compare generated, existing, and original backstory sections in the semantic improvement report.

### Concerns To Resolve

- Direct `llama cli` output can include loader, banner, prompt, or performance text and must never be saved into character fields.
- First-run model downloads are slow, even with smaller quantized artifacts.
- Top-level Streamlit tab state needs careful handling, so validation errors do not move the user to another tab.
- The current rewrite path should be simplified and tested before merging back to main.

### Character Rewrite Metadata Stabilization

- Centralized deterministic rewrite story signals so summary, backstory, prompt context, and required-term scoring use the same profile-plus-graph facts.
- Preserved JSON/metadata-backed origin, drives, alliances, enemies, motivations, custom stat fields, and source-backed places in rewrite scoring and generated prose.
- Filtered non-story attribute artifacts out of relationship prose so race, class, family placeholders, and place edges do not masquerade as character relationships.
- Regenerated `docs/reports/semantic_backstory_improvement.md` with model, existing generated, and original backstory scores.
- Testing: `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/e2e/test_character_rewrites.py`; `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/test_character_graph.py tests/test_model_downloads.py tests/test_character_generation.py`.

