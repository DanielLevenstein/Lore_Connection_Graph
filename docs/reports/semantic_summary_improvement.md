# Semantic Summary Improvement Report: Jory Ravenmark

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Evaluation: semantic similarity, sentence length fit, and sentence quality.

## Model Runtime

| Metric            | Value                                                |
| ----------------- | ---------------------------------------------------- |
| Model             | Qwen/Qwen2.5-0.5B-Instruct-GGUF                      |
| Quantization      | Q4_K_M                                               |
| Prompt version    | character-rewrite-v7-local-qwen-0.5b-writing-quality |
| Max tokens        | 640                                                  |
| Temperature       | 0.75                                                 |
| Top P             | 0.85                                                 |
| Repeat penalty    | 1.15                                                 |
| Seed              | 2310                                                 |
| Context size      | 8192                                                 |
| Batch size        | 64                                                   |
| Threads           | 2                                                    |
| GPU layers        | 0                                                    |
| Device            | none                                                 |
| Timeout seconds   | 180                                                  |
| Prompt hash       | 059deadfda616978                                     |
| Prompt eval time  | 974.55 ms                                            |
| Prompt tokens     | 365                                                  |
| Completion tokens | 153                                                  |
| Total tokens      | 518                                                  |

## Candidate

### Model Rewrite

Jory Ravenmark is a Human Barbarian with strong feelings towards her nomadic hunter memories and a burning oath to track down and face the monstrous leviathan that has inexplicably shown mercy.

### Existing Summary

Haunted by the loss of her family and the inexplicable mercy shown by a monstrous leviathan, Jory Ravenmark blends her nomadic hunter-memories with a burning oath to track and face the beast.

### Source Backstory

Jory was a sailor and grew up with her family on a island watchtower. Her mother died at sea and her father was consumed by loneliness which drove him to drink heavily. When she was still but a child, a monster from the sea attacked the watchtower. Jory survived, but both her fathers were consumed by the beast and vanished without a trace. That night Jory decided to dedicate her life to tracking down the beast who killed her father.

She learned to read the open sea as her father once had before her. She greaved his passing terribly and would do anything in her power to bring him back, although she knew in her heart that that was not possible. She longed for the days they could sit together in front of the fire in peace, him siping his glass of wisky and her with her steaming cup of hot cooca.

Jory Ravenmark directed her grief to become a beacon of light to her community helping others who had lost love ones to the sea work on rebuilding their lives into something their ancestors would be proud of.

## Scores

| Candidate        | Status   | Overall | Summary Length Score | Similarity | Sentence Length Score | Sentence Quality |
| ---------------- | -------- | ------: | -------------------: | ---------: | --------------------: | ---------------: |
| Model Rewrite    | Accepted | 77.57   | 100.00               | 52.58      | 56.00                 | 70.83            |
| Existing Summary | Rejected | 52.78   | 100.00               | 72.24      | 48.00                 | 62.50            |
| Source Backstory | Source   | 63.44   | 31.75                | 90.26      | 72.89                 | 84.26            |

### Rejection Reasons

- Existing Summary: summary sentence too long; overall score below 70

## Sentence Lengths

![Sentence length distribution](semantic_summary_sentence_lengths.png)

## Result

The model rewrite changes the writing quality score versus the original section by `0.1413`.
