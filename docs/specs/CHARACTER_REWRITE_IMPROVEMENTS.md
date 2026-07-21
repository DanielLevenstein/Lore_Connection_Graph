# Character Rewrite Improvements

Initial changes for this branch are on `feature/character_rewrite`.
This branch preserves the experimental character rewrite work for review, but the next pass should replace the underperforming LangChain/LangGraph rewrite path with the smallest practical local model adapter.

## Design Decision

Use `JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF` as the current local model candidate for character summary and backstory rewrites.

Reasons:

- Qwen2.5 0.5B is the most promising candidate after fixing Qwen chat-template parsing and removing generated ellipses from prompt context.
- SmolLM2 135M and 360M were faster, but both stopped mid-sentence or repeated prose on the Orin fixture.
- TinyLlama produced real prose, but copied fact-line wording and repeated itself.
- It can run through an app-managed `llama cli` subprocess, avoiding a long-running local API server.
- It preserves the existing injected `RewriteClient` testing shape, so unit tests can use fake clients and transcript fixtures.
- It keeps the deterministic graph rewrite as the fallback and regression oracle.

Implementation should not reintroduce LangChain, LangGraph, a user-managed local service, or `llama-cpp-python` for this narrow rewrite operation. The rewrite path only needs prompt construction, local artifact readiness, app-owned CLI inference, output cleanup, validation, semantic scoring, and save/undo semantics.

Rejected option: LangChain/LangGraph orchestration around the rewrite model. It performed worse than the earlier local rewrite path and adds unnecessary layers for a single prompt-in, prose-out operation.

## Goals

- Generate character summaries and backstories from a selected local model using authored prose plus compact graph-extracted story segments.
- Let missing character graphs be regenerated automatically before rewrite actions.
- Avoid requiring a long-running local API server or any user-started external service for one-off rewrite generation.
- Show visible feedback when a local model artifact needs to be downloaded.
- Compare generated, existing, and original backstory sections in the semantic improvement report.
- Preserve deterministic fallback generation for offline behavior and tests.
- Keep failed or low-quality candidates out of saved character fields.

## Concerns To Resolve

- Raw local-model output can include loader, banner, prompt, diagnostic, or performance text and must never be saved into character fields.
- `llama cli` can leak diagnostics, prompt echoes, or partial completions and those must never be saved into character fields.
- First-run model downloads are slow, even with smaller quantized artifacts.
- `llama-cpp-python` caused Python process crashes during validation, so the implementation should use `llama cli` instead.
- Top-level Streamlit tab state needs careful handling, so validation errors do not move the user to another tab.
- The current rewrite path should be simplified and tested before merging back to main.
- The semantic report currently describes `LangGraph Rewrite` even when the actual engine is `deterministic-graph-rewrite`; labels should reflect the local model candidate, existing generated section, and original section.
- The selected Qwen 0.5B model may still fail canon preservation; semantic and required-term gates must be allowed to reject it without damaging authored lore.
- Long prompts make the local CLI path too slow. The model prompt should provide the graph segments associated with the character instead of dumping every graph node and the full character sheet.

## Required Implementation Pass

1. Add a local rewrite model adapter.

   - Configure `JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF` in code and in the advanced JSON config file, not in editable UI fields.
   - Document `llama cli` installation in README.
   - Use an app-managed short-lived `llama cli` process for generation.
   - Do not call `llama serve`, require a localhost API endpoint, or leave background inference processes running.
   - Keep runner/download/status details outside Streamlit form state and character prose.
   - Preserve the current fake-client injection point for tests.

2. Own the service-free execution lifecycle.

   - Add a model lifecycle helper with `is_runtime_available`, `is_model_available`, `ensure_model_available`, and `generate` responsibilities.
   - Show first-run download/readiness status from the app.
   - Use a per-model lock so duplicate clicks cannot start overlapping downloads, model loads, or generations.
   - Load the GGUF model only inside the short-lived CLI process, never at app import time or in the Streamlit process.
   - Kill the CLI process on timeout or cancellation.
   - Treat CLI stderr as diagnostics and timing metadata only.
   - Use conservative CLI settings: bounded context, bounded output tokens, small batch size, limited thread count, no KV/op offload, and no GPU layers by default.
   - Never persist partial output from failed, cancelled, timed-out, or interrupted generation.

3. Harden transcript cleanup.

   - Strip leaked diagnostics, loader text, prompt echo, chat-template, timing, and Markdown-fence text.
   - Reject empty, truncated, full-sheet, or diagnostic-only output.
   - Add fixture-backed unit tests with realistic noisy local-model outputs.

4. Stabilize semantic acceptance.

   - Build required terms from the same profile-plus-graph story signals used for prompt context.
   - Build model prompts from compact graph segments: identity, origin, places, drives, alliances, enemies, traits, relationships, and short evidence.
   - Truncate authored profile sections before prompt construction so prompt-eval time remains bounded.
   - Score local model, existing generated, and original backstory candidates in `generate_semantic_improvement_report.py`.
   - Block save when a model candidate fails required-term coverage or does not improve on the original section.
   - Keep deterministic rewrite available as a fallback candidate and test oracle.

5. Update Streamlit feedback.

   - Show a visible status/spinner when the model artifact is missing or downloading.
   - Keep the active top-level `Characters` tab stable on validation errors.
   - Display model failure reasons without changing editable summary/backstory text.

6. Test the simplified path.

   - `generate_semantic_improvement_report.py`
   - `tests/test_character_rewrite_model_lifecycle.py`
   - `tests/test_semantic_improvement_report.py`
   - Focused e2e coverage for missing graph regeneration and mocked rewrite-client behavior.
   - Unit coverage for missing CLI, missing artifact, download failure, CLI start failure, timeout/interruption, leaked diagnostics cleanup, timing metadata parsing, and duplicate generation locking.
   - Opt-in integration coverage for machines with a downloaded model artifact; default tests must not load GGUF weights.

## Model Escalation Rule

If `JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF` cannot beat the original Orin backstory while preserving required terms after graph-segment prompt fixes, stop and document the failure. The next comparison candidates are TinyLlama and a larger Qwen model, but promotion to a different model should happen in a separate design update rather than silently inside implementation.
