# Character Rewrite Improvements

Initial changes for this branch are on feature/character_rewrite
This branch preserves the experimental character rewrite work for later review.

## Goals

- Generate character summaries and backstories from the character graph instead of deterministic fallback prose.
- Let missing character graphs be regenerated automatically before rewrite actions.
- Avoid requiring a long-running local API server for one-off rewrite generation.
- Show visible feedback when a local model artifact needs to be downloaded.
- Compare generated, existing, and original backstory sections in the semantic improvement report.

## Concerns To Resolve

- Direct `llama cli` output can include loader, banner, prompt, or performance text and must never be saved into character fields.
- First-run model downloads are slow, even with smaller quantized artifacts.
- Top-level Streamlit tab state needs careful handling, so validation errors do not move the user to another tab.
- The current rewrite path should be simplified and tested before merging back to main.

## Suggested Next Pass

- Isolate model invocation behind a small adapter with fixture-backed tests for CLI transcripts.
- Keep model download and generation status outside editable character fields.
- Re-evaluate the selected local model and quantization against output quality and download time.
- Add a focused Playwright test for Repopulate Summary with a missing graph and a mocked rewrite client.
