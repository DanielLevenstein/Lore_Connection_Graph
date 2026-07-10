# Character Rewrite Design

## Purpose

Character rewrites are an explicit, player-requested editing aid for improving a character summary or backstory. They must never silently replace authored prose. The saved character sheet must preserve both the original text and the rewritten text so the player can compare, undo, or manually merge the result.

## Current Status

The UI already exposes rewrite actions behind:

```text
LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES=1
```

The buttons are:

- `Populate Summary`
- `Repopulate Summary`
- `Rewrite Backstory`
- `Undo Changes`

`Undo Changes` remains available even when graph rewrite generation is disabled. The undo stack is recursive in the practical UI sense: each saved mutation pushes a snapshot, and repeated undo actions walk backward through prior snapshots.

## Model Recommendation

Use the configured local chat model exposed through the existing OpenAI-compatible local model server. Do not hard-code a specific remote model into the rewrite path.

Default recommendation:

- `qwen2.5-3b-instruct-gguf`
- Runner: `llama.cpp`
- Quantization: `Qwen2.5-3B-Instruct-Q4_K_M.gguf`
- Role: semantic-aware local rewrite model for summaries and compact backstory rewrites.

This is the best default for the current project because the repository already validates it as the selected runnable GGUF semantic model, it is small enough for local iteration, and it is instruction-tuned enough for constrained rewrite prompts. Larger 7B or 8B instruction models remain good future quality upgrades when latency and memory budgets allow them.

Recommended default model class:

- Instruction-tuned local model.
- 7B to 8B parameter range for interactive latency on local hardware.
- GGUF deployment through the existing harness when available.
- At least 8k context if the model and hardware support it.

Good candidates for this project are local instruction models in the Mistral, Llama, or Qwen families, selected through the existing model harness configuration. The app should ask the model for structured Markdown and then validate the output before it reaches the editor.

Fallback behavior:

- If no local model is configured or reachable, keep the current deterministic graph-derived draft helpers.
- The fallback should be labeled as derived from graph data, not presented as polished prose.
- The fallback summary builder should still use both authored profile fields and graph-derived facts so tests can validate the rewrite contract without requiring a running model server.

## Rewrite Context

Every rewrite request should combine authored prose and derived graph fields. The model input should include:

- Character name, first name, family name, race, class, level, pronouns.
- Current summary and current backstory.
- Preserved original summary or backstory when the current section is already auto-generated.
- Character details: drives, alliances, enemies, home/origin, gender, custom stat fields.
- Knowledge graph attributes, places, and relationships.
- Combined graph connections when available.
- Source evidence for graph facts.
- The requested operation: populate blank summary, repopulate summary, or rewrite backstory.

The prompt should clearly rank source authority:

1. Authored character sheet prose.
2. Explicit character stats and details.
3. Knowledge graph facts with evidence.
4. Inferred graph relationships.

When sources conflict, the model should preserve authored prose and avoid inventing a correction.

## Output Contract

Summary rewrite output:

- One concise paragraph.
- No Markdown heading.
- No table.
- Preserve the character's core facts.
- Mention only relationships or places supported by source context.

Backstory rewrite output:

- Markdown prose only.
- No top-level character sheet headings.
- Multiple paragraphs are allowed.
- Preserve existing canon unless the user edited the context first.
- Integrate graph-derived places and relationships only when evidence supports them.

The app should reject or warn on output that:

- Changes the character name.
- Drops required stat facts such as race or class when they were present.
- Contains a full character sheet instead of the requested section.
- Omits all source-backed relationships when the request was specifically graph-driven.

## Semantic Quality Gate

The first release gate uses a deterministic local semantic scorer rather than a live model judge. The scorer compares a candidate rewrite against a source context made from:

- Existing authored summary and backstory.
- Character stats and details.
- Graph attributes, relationships, places, and evidence.

The score combines:

- Hash-embedding cosine similarity to the source context.
- Required concept coverage for core facts such as race, class, drives, places, and supported relationships.
- Concision, because a summary should improve a bloated source by preserving facts in less space.

This gate is intentionally modest. It catches regressions where generated summaries ignore graph facts or simply copy the original backstory, while remaining fast and offline-friendly. A future model-backed evaluator can replace the hash embedder behind the same `candidate + source_context + required_terms -> score` shape.

## Save Semantics

When a rewrite is accepted:

- Mark the rewritten section heading with `(Auto Generated)`.
- Store the previous section text under `### Original Character Summary` or `### Original Character Backstory`.
- Preserve existing original text if the section was already auto-generated.
- Write both the Markdown sheet and `PROFILE.json`.
- Regenerate the character graph after save.

## Undo Semantics

Before any character save or rewrite mutation, push the current Markdown sheet into the session undo stack for that character.

Undo should:

- Restore the most recent snapshot.
- Pop only one snapshot per click.
- Regenerate the graph after restoring the sheet.
- Remain visible and usable whether or not `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES` is enabled.

Future durable undo can store snapshots under `data/lore/character_sheets/<character>/undo/`, but the current session stack is sufficient for the first implementation.

## UI Flow

The editor should show both versions when originals exist:

- Current or generated summary beside original summary.
- Current or generated backstory beside original backstory.

Rewrite buttons should appear only when `LOCAL_CHATBOT_ENABLE_GRAPH_REWRITES=1`. Save and undo should always remain available.

## Test Plan

Unit tests should cover:

- Legacy `Autogenerated` title parsing.
- Auto-generated section markers.
- Original section preservation.
- Rewrite save semantics.
- Repeated undo stack behavior through storage-independent helpers.
- Prompt/context construction once model-backed rewrites are implemented.

End-to-end tests should cover:

- Rewrite buttons hidden by default.
- Rewrite buttons visible when the environment variable is enabled.
- Saving a generated section displays both current and original text after rerun.
- Undo restores the previous Markdown sheet.
- A semantic-aware comparison where the graph-generated Orin Nightbloom summary scores higher than the original generated backstory.
- Legacy `Autogenerated` title markers are hidden from the character selector and heading.
