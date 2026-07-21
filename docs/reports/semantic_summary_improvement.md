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
| Prompt hash       | a5a405072a612deb                                     |
| Prompt eval time  | 9867.50 ms                                           |
| Prompt tokens     | 599                                                  |
| Completion tokens | 63                                                   |
| Total tokens      | 662                                                  |

## Candidate

### Source Backstory

Jory was a sailor and grew up with her family on a island watchtower. Her mother died at sea and her father was consumed by loneliness which drove him to drink heavily. When she was still but a child, a monster from the sea attacked the watchtower. Jory survived, but both her fathers were consumed by the beast and vanished without a trace. That night Jory decided to dedicate her life to tracking down the beast who killed her father.

She learned to read the open sea as her father once had before her. She greaved his passing terribly and would do anything in her power to bring him back, although she knew in her heart that that was not possible. She longed for the days they could sit together in front of the fire in peace, him siping his glass of wisky and her with her steaming cup of hot cooca.

Jory Ravenmark directed her grief to become a beacon of light to her community helping others who had lost love ones to the sea work on rebuilding their lives into something their ancestors would be proud of.

### Local Model Rewrite

#### Initial Generation

Jory Ravenmark is a Human Barbarian haunted by the loss of her family and an inexplicable mercy shown by a monstrous leviathan that has driven her to blend nomadic hunter-memories with a burning oath to track and face the beast she seeks to vanquish. Her mother died at sea, while her father was consumed by loneliness which drove him to drink heavily; these traumatic losses have fueled her quest for vengeance against an entity she believes is responsible.

#### Retry Generation

Jory Ravenmark is a Human Barbarian haunted by the loss of her family and an inexplicable mercy shown by a monstrous leviathan that has driven her to blend nomadic hunter-memories with a burning oath to track and face the beast she seeks to vanquish, even in its monstrous form.

### Existing Summary

Haunted by the loss of her family and the inexplicable mercy shown by a monstrous leviathan, Jory Ravenmark blends her nomadic hunter-memories with a burning oath to track and face the beast.

## Scores

| Candidate                   | Status   | Overall | Summary Length Score | Similarity | Sentence Length Score | Sentence Quality | 
| --------------------------- | -------- | ------: | -------------------: | ---------: | --------------------: | ---------------: | 
| Source Backstory            | Source   | 54.87   | 31.75                | 90.26      | 72.89                 | 84.26            | 
| Local model rewrite initial | Rejected | 51.30   | 76.92                | 73.98      | 22.00                 | 30.60            | 
| Local model rewrite retry   | Rejected | 41.68   | 100.00               | 63.98      | 0.00                  | 0.00             | 
| Existing Summary            | Rejected | 44.21   | 100.00               | 72.24      | 48.00                 | 62.50            | 


## Sentence Lengths

![Sentence length distribution](semantic_summary_sentence_lengths.png)

## Result

The local model rewrite changes the writing quality score versus the original section by `-0.1319`.
