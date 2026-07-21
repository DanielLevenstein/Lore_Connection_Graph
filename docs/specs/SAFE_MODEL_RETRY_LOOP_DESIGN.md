# Safe Model Retry Loop Design

## Purpose

The local rewrite model can produce malformed prose, repeated alternatives, prompt echoes, empty output, or runtime failures. The retry loop should improve the candidate before it reaches scoring, reports, or the user interface. It must never turn backend errors into candidate text and must never require reports to understand model failure internals.

## Retry Prompts
In retry prompts, do not include raw backend errors, stack traces, stderr, or validator strings. Use neutral repair instructions that describe the desired output shape.

## Design Goals

- Retry model generation when the candidate violates the requested output contract.
- Keep reports focused on candidate text and score tables.
- Keep user-facing UI focused on editable prose, status, and safe failure messages.
- Store diagnostics in structured metadata for tests and debugging only.
- Preserve authored character fields unless the user explicitly accepts a candidate.
- Make retry behavior testable with fake clients without invoking the local model.

## Non-Goals

- Do not add a report-level rejection framework.
- Do not display raw exception messages, stack traces, stderr, prompts, or validator details in reports.
- Do not append error text to candidate prose.
- Do not save failed attempts to character sheets.
- Do not use retry attempts as hidden scoring rows.

## Output Contract

The retry loop operates on a structured result, not a raw string-or-error mix.

```python
@dataclass(frozen=True)
class RewriteAttempt:
    attempt_number: int
    prompt_version: str
    raw_text: str
    cleaned_text: str
    metadata: dict[str, object]
    validation_issues: tuple[str, ...]


@dataclass(frozen=True)
class RewriteResult:
    text: str
    attempts: tuple[RewriteAttempt, ...]
    metadata: dict[str, object]
```

Only `RewriteResult.text` is allowed to flow into report candidate sections, Streamlit editable fields, and semantic scoring.

`RewriteAttempt.raw_text`, `validation_issues`, exception messages, stderr, and retry metadata are diagnostics. They may be used by unit tests, logs, or a developer-only debug artifact, but not by generated reports or normal UI.

## Retry Flow

1. Build the base prompt from the requested rewrite kind.
2. Call the rewrite client.
3. Capture raw stdout and runtime metadata.
4. Clean the raw output.
5. Normalize the candidate for the rewrite kind.
6. Validate the normalized candidate against the output contract.
7. If valid, return `RewriteResult(text=cleaned_text, attempts=...)`.
8. If invalid and attempts remain, build a narrower retry prompt using only issue categories, not raw exception text.
9. If all attempts fail, return the best cleaned candidate if one exists.
10. If no cleaned candidate exists, raise a typed generation failure for the caller to handle outside reporting.

The fallback rule matters: a flawed prose candidate is usually still useful for tuning and scoring. Empty output, prompt-only output, or diagnostics-only output are not useful candidates.

## Validation Levels

Validation should classify output contract issues without deciding report acceptance.

Hard failures:

- Empty cleaned output.
- Prompt echo or full character sheet output.
- Backend diagnostics only.
- Output contains obvious runtime/error text.

Retryable quality issues:

- Multiple summary alternatives.
- More than one paragraph for a summary.
- Summary outside the 30-60 word target.
- Repeated sentence.
- Repetitive wording.
- Truncated ending.
- Markdown headings or labels.

Report acceptance remains score-based. Retry validation is only used to produce a better candidate before scoring.

## Summary Retry Prompt

For summary retries, the prompt should be narrow and explicit:

```text
Rewrite the previous candidate as exactly one character summary paragraph.
Use 30 to 60 words.
Use one to three complete sentences.
Do not provide alternatives, drafts, headings, labels, analysis, or Markdown.
Preserve only source-backed facts from the original prompt.
Return only the final summary prose.
```

Do not include raw validator text such as `repetitive wording` in the user-visible candidate. Internally, the retry prompt may refer to issue categories in neutral wording, such as "avoid repeated phrases."

## Backstory Retry Prompt

For backstory retries:

```text
Rewrite the previous candidate as exactly two concise prose paragraphs.
Preserve source-backed names, places, relationships, and drives.
Avoid repeated sentences and repeated phrases.
Do not include headings, labels, analysis, or Markdown fences.
Return only the final backstory prose.
```

## Diagnostics Boundary

Allowed diagnostic destinations:

- Unit test assertions.
- Developer-only logs.
- Structured attempt metadata.
- Optional local debug files under a clearly named developer path.

Forbidden diagnostic destinations:

- `docs/reports/*.md` candidate sections.
- Report score tables.
- Streamlit editable summary/backstory fields.
- Saved character sheets.
- User-facing markdown bodies.
- Semantic scoring input.

The report layer should receive plain candidate strings and scoring objects only. It should not know whether a candidate was produced on the first attempt or fifth attempt.

## UI Behavior

The UI may show coarse status:

- "Generating summary..."
- "Retrying summary..."
- "Could not produce a usable summary. Existing text was not changed."

The UI must not show:

- Raw model stderr.
- Python exception strings.
- Prompt text.
- Validator internals.
- Rejected candidate attempts unless the user explicitly opens a developer debug view.

If every retry fails with no cleaned candidate, the editable text must remain unchanged.

## Report Behavior

Reports should:

- Show the final candidate text.
- Score the final candidate text.
- Include model runtime metadata already intended for report readers.
- Keep `Overall` as the acceptance source.

Reports should not:

- Show retry attempts.
- Show model errors.
- Mark candidates rejected because an earlier attempt failed.
- Include raw validation issue text.

## Testing Strategy

Fast unit tests should use fake rewrite clients:

- First attempt returns three summary alternatives, second attempt returns one 30-60 word summary.
- First attempt returns a prompt echo, second attempt returns valid prose.
- All attempts return diagnostics-only output and no candidate text reaches scoring.
- Retry metadata captures issue categories while report output omits them.
- Summary report scores the final summary text, not retry diagnostics or source backstory.
- Streamlit handler leaves saved character fields unchanged when no candidate is available.

Report tests should assert absence, not presence, of diagnostics:

- No `## Model Error`.
- No `ERROR:`.
- No raw validator issue strings.
- No prompt echo text.

Integration tests with the real local model should remain opt-in because they depend on the downloaded GGUF artifact and local runtime performance.

## Open Questions

- Whether to expose a developer-only retry trace file for tuning sessions.
- Whether retries should reuse the full original prompt or a compact repair prompt.
- Whether the max retry count should differ between summary and backstory.
- Whether score-based acceptance should consider retry count as a metadata signal without changing the visible score.
