# Semantic Summary Improvement Report: Jory Ravenmark

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Evaluation: semantic similarity, sentence length fit, and sentence quality.

## Model Runtime

| Metric            | Value                                                |
| ----------------- | ---------------------------------------------------- |
| Model             | JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF           |
| Quantization      | Q4_K_M                                               |
| Prompt version    | character-rewrite-v7-local-qwen-1.5b-writing-quality |
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
| Prompt hash       | c83f5e9d0e140a00                                     |
| Prompt eval time  | 9683.40 ms                                           |
| Prompt tokens     | 437                                                  |
| Completion tokens | 242                                                  |
| Total tokens      | 679                                                  |

## Candidate

### Local Model Rewrite

Jory Ravenmark is a Human Barbarian haunted by her mother's loss at sea and her father’s loneliness from heavy drinking, leading her to blend nomadic hunter memories with a burning oath against tracking and facing a monstrous leviathan. Jory's parents' untimely deaths led her to adopt their legacy as she seeks justice through relentless pursuit of the beast that could have taken them both.

Jory Ravenmark is a Human Barbarian who has adopted her mother’s nomadic hunting lifestyle but has also developed a burning oath against tracking and facing what some believe is an inexplicably merciful leviathan. Her parents' untimely deaths drove Jory to adopt their legacy as she pursues justice through relentless pursuit of the beast that could have taken them both, blending her memories with her rage.

Jory Ravenmark, a Human Barbarian, seeks revenge against a monstrous Leviathan after losing her mother and father at sea, leading her to blend her nomadic hunting experiences with a burning oath. Her parents' untimely deaths drove Jory into adopting their legacy as she pursues justice through relentless pursuit of the beast that could have taken them both, blending her memories with her rage.

### Existing Summary

Haunted by the loss of her family and the inexplicable mercy shown by a monstrous leviathan, Jory Ravenmark blends her nomadic hunter-memories with a burning oath to track and face the beast.

### Source Backstory

Jory was a sailor and grew up with her family on a island watchtower. Her mother died at sea and her father was consumed by loneliness which drove him to drink heavily. When she was still but a child, a monster from the sea attacked the watchtower. Jory survived, but both her fathers were consumed by the beast and vanished without a trace. That night Jory decided to dedicate her life to tracking down the beast who killed her father.

She learned to read the open sea as her father once had before her. She greaved his passing terribly and would do anything in her power to bring him back, although she knew in her heart that that was not possible. She longed for the days they could sit together in front of the fire in peace, him siping his glass of wisky and her with her steaming cup of hot cooca.

Jory Ravenmark directed her grief to become a beacon of light to her community helping others who had lost love ones to the sea work on rebuilding their lives into something their ancestors would be proud of.

## Scores

| Candidate           | Status   | Summary Length Score | Overall | Similarity | Sentence Length Score | Sentence Quality |
| ------------------- | -------- | -------------------: | ------: | ---------: | --------------------: | ---------------: |
| Local model rewrite | Rejected | 31.25                | 56.48   | 71.64      | 50.67                 | 60.58            |
| Existing Summary    | Rejected | 100.00               | 44.21   | 72.24      | 48.00                 | 62.50            |
| Source Backstory    | Source   | 31.75                | 54.87   | 90.26      | 72.89                 | 84.26            |

## Sentence Lengths

![Sentence length distribution](semantic_summary_sentence_lengths.png)

## Result

The local model rewrite changes the writing quality score versus the original section by `0.0161`.
