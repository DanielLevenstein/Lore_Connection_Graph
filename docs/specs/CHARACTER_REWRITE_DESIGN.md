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

## Rewrite Engine

Use a small local model through a narrow adapter, with the deterministic graph rewrite engine retained as the fallback and test oracle. The previous LangChain/LangGraph rewrite path underperformed the earlier graph-backed prose path, so the next implementation should remove that extra orchestration layer and call one local inference backend directly.

Release behavior:

- Preferred model: `Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M`.
- Preferred runner: app-managed Python worker process using `llama_cpp` bindings installed by `pip install -r requirements.txt`.
- Fallback engine: `deterministic-graph-rewrite`.
- Inputs: authored character profile fields plus knowledge graph characters, places, attributes, relationships, and evidence.
- Role: generate compact summaries and backstory drafts from source-backed graph facts.

The selected model is intentionally the smallest practical instruction-tuned candidate for this workflow. The official Qwen GGUF model card lists Qwen2.5 0.5B Instruct as an instruction-tuned GGUF model with `Q4_K_M` support. That keeps download size and RAM requirements low while preserving enough instruction-following behavior for short source-grounded rewrites.

This model must be treated as optional runtime data, not committed repository content. The app should report missing artifact/download status visibly and keep the current character fields unchanged until a clean candidate is produced and accepted.

The deterministic fallback remains important because it is offline, fixture-testable, and available to every user who has the codebase. Unit tests should inject fake rewrite clients and noisy model-output fixtures rather than invoking a real downloaded model.

The model rewrite output should be labeled as graph-backed generated text and should still preserve original sections for review before acceptance.

References:

- Qwen model card: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF>
- llama-cpp-python package: <https://github.com/abetlen/llama-cpp-python>

## Rewrite Context

Every rewrite request should combine authored prose and derived graph fields. The rewrite context should include:

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

When sources conflict, the rewrite should preserve authored prose and avoid inventing a correction.

## Local Model Adapter

Model invocation should live behind a small adapter with this behavioral contract:

- Accept structured chat messages from `rewrite_prompt`.
- Ensure the configured model artifact is present, downloading it only through the approved model-download path.
- Surface download and generation status to Streamlit without mixing status text into editable character fields.
- Run inference through an app-managed worker that initializes `llama_cpp.Llama`.
- Return only the model's candidate prose to the rewrite pipeline.
- Raise a clear `RuntimeError` when the Python runtime dependency, model artifact, runner initialization, or output contract fails.

The adapter must not expose LangChain, LangGraph, raw `llama_cpp` runtime details, or download implementation details to the Streamlit form handler. Streamlit should call the same high-level `graph_generated_summary` and `graph_generated_backstory` functions with a configured local rewrite client.

The first implementation should prefer explicit configuration constants over broad settings machinery:

- Model id: `Qwen/Qwen2.5-0.5B-Instruct-GGUF`.
- Quantization: `Q4_K_M`.
- Prompt version: `character-rewrite-v2-local-qwen-0.5b`.
- Output mode: summary or backstory.
- Max generated tokens: short bounded values appropriate to each mode.
- Temperature: low, deterministic prose generation.
- Context window, batch size, and thread count: conservative defaults chosen to avoid container memory spikes.

If the selected 0.5B model fails semantic gates on the fixture set after prompt cleanup, the next design review should evaluate `Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M`. The implementation should not silently promote to a larger model.

## Service-Free Model Execution

The character rewrite feature must run without requiring the user to start, monitor, or stop an external model service. The Streamlit app should own the entire one-shot execution lifecycle for each rewrite request.

### Runner options:

1. App-managed Python worker process using `llama_cpp`.
2. In-process `llama_cpp` generation inside Streamlit.
3. LangChain/LangGraph orchestration around a local model.
4. Direct `llama cli` subprocess.

The preferred implementation is option 1. It keeps the dependency model simple because `llama-cpp-python` is installed from `requirements.txt`, but it avoids loading GGUF weights into the long-running Streamlit process. The app starts the worker for a rewrite request, sends structured JSON input, receives structured JSON output, and then lets the worker exit. This is not an external service because the user never starts, stops, monitors, or configures a background model server.

Option 2 is simpler but riskier for Docker and Streamlit reruns because the app process can retain model memory after generation. 
Option 3 is rejected for this pass because the previous LangChain/LangGraph rewrite version performed worse than the earlier graph-backed path while adding orchestration complexity that the app does not need. A direct `llama cli` subprocess is also not a preferred fallback because it adds an external CLI dependency that `pip install -r requirements.txt` does not provide.
Option 4 is rejected because it would require the user to install a separate dependency and would we would have to manage the session starting and stopping code.

### Execution model:

- Build the prompt and model invocation arguments in the Streamlit app process.
- Check whether the configured GGUF artifact is available in the local model cache.
- If the artifact is missing, display a Streamlit status area that explains the first-run download and streams coarse progress when available.
- Start a short-lived project Python worker process for the rewrite request.
- Send the worker a JSON payload containing model path, model settings, prompt version, output mode, and chat messages.
- In the worker, lazily initialize `llama_cpp.Llama` from the local GGUF path.
- Generate through `create_chat_completion` or the closest stable chat-completion API exposed by the installed binding.
- Use explicit arguments: bounded context, bounded generation tokens, low temperature, conservative batch size, and conservative thread count.
- Return structured JSON containing either candidate text plus metadata or a typed error.
- Treat the returned candidate text as untrusted model output until it passes cleanup and validation.
- Return the cleaned candidate to the rewrite pipeline, or raise a user-visible error while leaving character fields unchanged.

This is an app-owned worker adapter, not a server adapter. The implementation should not call `llama serve`, should not require an OpenAI-compatible localhost endpoint, and should not ask the user to install or manage anything beyond the project Python requirements and the model artifact.

### Runtime and lifecycle rules:

- Add `llama-cpp-python` to `requirements.txt` during implementation and pin it tightly enough to keep local and Docker installs reproducible.
- Use a per-model lock so two rewrite clicks cannot download or initialize the same model artifact at the same time.
- Disable or ignore duplicate rewrite submissions while a generation is in progress for the active character.
- Do not load the GGUF model in the Streamlit process for the default path.
- Kill the worker on timeout or cancellation.
- Do not read candidate prose from worker stderr. Worker stderr is diagnostics only.
- Use conservative memory settings first: small context window, small batch size, no memory locking by default, and no GPU offload unless explicitly added later.
- Do not persist partial output from interrupted, failed, or timed-out generation.
- Record non-sensitive metadata for accepted rewrites: model id, quantization, prompt version, source hash, and generation timestamp.

The app needs readiness checks that can distinguish "Python binding missing", "model artifact not downloaded yet", "worker failed to start", "model failed to initialize", and "generation failed." Add a small model-lifecycle helper whose public contract is limited to `is_runtime_available`, `is_model_available`, `ensure_model_available`, and `generate`.

### Docker safety rules:

- Do not load the model at app import time.
- Prefer the short-lived worker process so model memory is released when generation ends.
- Keep model-backed rewrite tests fake-client based by default so CI and Docker smoke tests do not load GGUF weights.
- Add one opt-in integration test for local machines that have the model artifact and enough memory.
- If `llama_cpp` install or initialization fails in Docker, the app should continue to run with deterministic graph rewrites and show model-backed rewrites as unavailable.

## Attribute Graph Overrides

The Character Attribute Graph override is an internal maintenance feature. It must stay hidden in the shipped UI because visible override controls imply the normal attribute table needs manual repair.

Override controls are only shown when this environment variable is set:

```text
LOCAL_CHATBOT_ENABLE_ATTRIBUTE_GRAPH_OVERRIDE=1
```

The display/control rule is:

- If a character sheet has a populated `## Character Connections` table, the Streamlit Attribute Graph table shows those rows so the user can control what they see.
- If the table is absent or empty, the Streamlit Attribute Graph table shows autogenerated extraction rows.
- The full generated graph remains available for character backstory rewrites so graph-derived context is not lost when a user cleans up the visible table.

When enabled for maintenance, the Streamlit Attribute Graph editor writes the visible table back to the markdown sheet. Clearing the override removes the `Character Connections` section so the visible table returns to autogenerated rows.

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

Raw model output must be sanitized before persistence. The cleaner should strip or reject:

- Loader and download text if it leaks through the backend.
- llama.cpp diagnostics if they leak through the backend.
- Prompt echoes or chat-template fragments.
- Token timing and performance summaries.
- Markdown fences around an otherwise valid section.
- Labels such as `Summary:` or `Backstory:`.
- Empty or truncated fragments.

No raw backend diagnostic line may be saved into `Character Summary`, `Character Backstory`, `PROFILE.json`, or the semantic report candidate sections.

## Semantic Quality Gate

The release gate uses a deterministic local semantic scorer rather than a live model judge. The scorer compares a candidate rewrite against a source context made from:

- Existing authored summary and backstory.
- Character stats and details.
- Graph attributes, relationships, places, and evidence.

The score combines:

- Hash-embedding cosine similarity to the source context.
- Required concept coverage for core facts such as race, class, drives, places, and supported relationships.
- Concision, because a summary should improve a bloated source by preserving facts in less space.

This gate is intentionally modest. It catches regressions where generated summaries ignore graph facts, simply copy the original backstory, or lose the profile-plus-graph signals that made the deterministic rewrite score well. A future model-backed evaluator can replace the hash embedder behind the same `candidate + source_context + required_terms -> score` shape.

The semantic improvement report should compare:

- Local model rewrite candidate.
- Existing generated section.
- Original authored backstory.

The model-backed path should remain disabled for save if the model candidate does not beat the original authored section and does not preserve required terms. The UI may still display the failure reason, but it should keep the existing sheet unchanged.

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

Future durable undo can store snapshots under `world_building/lore/character_sheets/<character>/undo/`, but the current session stack is sufficient for the first implementation.

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
- Rewrite/context construction for graph-backed summaries and backstories.
- Local model adapter lifecycle with missing Python binding, missing artifact, available artifact, failed initialization, failed generation, and empty output.
- Model output cleanup for leaked diagnostics, prompt echoes, performance lines, Markdown fences, and valid prose.
- Semantic report formatting for local model, existing generated, and original backstory candidates.

End-to-end tests should cover:

- Rewrite buttons hidden by default.
- Rewrite buttons visible when the environment variable is enabled.
- Saving a generated section displays both current and original text after rerun.
- Undo restores the previous Markdown sheet.
- A semantic-aware comparison where the graph-generated Orin Nightbloom summary scores higher than the original generated backstory.
- Legacy `Autogenerated` title markers are hidden from the character selector and heading.
- Visible status when a model artifact must be downloaded before the first rewrite.
