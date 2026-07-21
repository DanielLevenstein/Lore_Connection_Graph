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
- `generate_single_character_backstory_rewrite_report.py`
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

## Completed - v2.0.0 Release Notes - 2026-07-21 - feature/character_rewrite
- Added the `tag/v2.0.0` changelog entry and updated `RELEASE_NOTES.md` with character rewrite tuning, normalized reporting, generated-text save promotion, and supporting graph cleanup.
- Testing: `git diff --check`.

## Completed - Qwen 0.5B Report Rerun - 2026-07-21 - feature/character_rewrite
- Switched the local rewrite model defaults and advanced JSON config to `Qwen/Qwen2.5-0.5B-Instruct-GGUF` with the `Q4_K_M` artifact.
- Regenerated the single-character backstory report, single-character summary report, multi-character rewrite comparison, and sentence-length charts.
- Testing: `.venv/bin/python scripts/generate_single_character_backstory_rewrite_report.py`; `.venv/bin/python scripts/generate_single_character_summary_rewrite_report.py`; `.venv/bin/python scripts/generate_multi_character_rewrite_report.py`; `PYTHONPATH=. .venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_multi_character_rewrite_report.py tests/test_character_rewrite_model_lifecycle.py -q`.

### Character Rewrite Metadata Stabilization

- Centralized deterministic rewrite story signals so summary, backstory, prompt context, and required-term scoring use the same profile-plus-graph facts.
- Preserved JSON/metadata-backed origin, drives, alliances, enemies, motivations, custom stat fields, and source-backed places in rewrite scoring and generated prose.
- Filtered non-story attribute artifacts out of relationship prose so race, class, family placeholders, and place edges do not masquerade as character relationships.
- Regenerated `docs/reports/semantic_backstory_improvement.md` with model, existing generated, and original backstory scores.
- Testing: `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/e2e/test_character_rewrites.py`; `.venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_character_rewrite_model_lifecycle.py tests/test_character_graph.py tests/test_model_downloads.py tests/test_character_generation.py`.

## Completed - Reporting Interface Separation - 2026-07-21 - feature/character_rewrite
- Separated report candidate collection from rewrite evaluation data, added rejection reasons to summary and backstory score tables, and regenerated the single-character and multi-character reports.
- Testing: `.venv/bin/python -m py_compile scripts/generate_single_character_backstory_rewrite_report.py scripts/generate_single_character_summary_rewrite_report.py scripts/generate_multi_character_rewrite_report.py`; `PYTHONPATH=. .venv/bin/python -m pytest tests/test_semantic_improvement_report.py tests/test_multi_character_rewrite_report.py tests/test_model_rewrite_contract.py tests/test_character_rewrite_model_lifecycle.py -q`; `PYTHONPATH=. .venv/bin/python -m pytest tests/test_character_generation.py tests/test_character_graph.py tests/test_character_rewrite_model_lifecycle.py tests/test_combined_character_graph.py tests/test_entity_file_saves.py tests/test_graphviz_config.py tests/test_graphviz_rendering.py tests/test_lore_import.py tests/test_model_rewrite_contract.py tests/test_multi_character_rewrite_report.py tests/test_semantic_improvement_report.py tests/test_session_notes.py -q`.

## Completed - API Rewrite Contract Tests - 2026-07-21 - feature/character_rewrite
- Added API-level model-client tests for summary and backstory rewrites, including mode-specific prompt source context, summary candidate collapse, and backstory diagnostic stripping plus two-paragraph trimming.
- Testing: `.venv/bin/python -m pytest tests/test_model_rewrite_contract.py tests/test_character_rewrite_model_lifecycle.py -q`.

## Completed - Local Character Rewrite Worker - 2026-07-20 - feature/character_rewrite
- Added an app-managed `llama_cpp` worker path for optional model-backed character rewrites without a user-started model service.
- Kept deterministic graph rewrites as the default fallback and updated the semantic report script to use the real local model client by default.
- Testing: `.venv/bin/python -m pytest tests/test_character_generation.py tests/test_character_graph.py tests/test_character_rewrite_model_lifecycle.py tests/test_semantic_improvement_report.py tests/e2e/test_character_rewrites.py -q`.
