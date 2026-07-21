# Multi-Character Rewrite Comparison

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
| Prompt hash       | 79b97ecf5c7fe657                                     |
| Prompt eval time  | 2860.18 ms                                           |
| Prompt tokens     | 724                                                  |
| Completion tokens | 321                                                  |
| Total tokens      | 1045                                                 |

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Candidate       | Status   | Overall | Summary Length Score | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | ------: | -------------------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Accepted | 81.77   | 100.00               | 58.16      | 74.00                 | 82.08            |
| Jory Ravenmark  | Accepted | 77.57   | 100.00               | 52.58      | 56.00                 | 70.83            |
| Neal Lovington  | Rejected | 52.81   | 100.00               | 68.03      | 93.33                 | 100.00           |

### Rejection Reasons

- Neal Lovington: overall score below 70

## Generated Backstory Scores

| Candidate       | Status   | Overall | Length Score | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | ------: | -----------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Rejected | 65.11   | 50.00        | 62.93      | 76.00                 | 86.88            |
| Jory Ravenmark  | Accepted | 80.78   | 50.00        | 63.44      | 66.00                 | 100.00           |
| Neal Lovington  | Rejected | 55.17   | 100.00       | 65.43      | 69.71                 | 100.00           |

### Rejection Reasons

- Orin Nightbloom: backstory paragraph count; length score below target; overall score below 70
- Neal Lovington: overall score below 70

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin Nightbloom, a Half-Orc Bard from the coastal mage college Sunstone Mage College, comes of age at this institution where he honed his talent and sense of exile. His drive to preserve is to stop younger relatives from repeating their worst choice while also breaking a curse that only worsens when ignored.

#### Generated Backstory

Orin Nightbloom, known for his talent and an exile sense, came of age at Sunstone Mage College. A place that sharpened both his gift and his isolation, it offered a chance to understand the curse that had been haunting his family. The loss of Orin's mother left him with only grief but also gave him reason to see the consequences of legacy and self-invention. Now, Orin carries his music forward as a form of defiance, trying to stop younger relatives from repeating their worst choice while turning inherited sorrow into something brave enough to protect the living.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

Jory Ravenmark is a Human Barbarian with strong feelings towards her nomadic hunter memories and a burning oath to track down and face the monstrous leviathan that has inexplicably shown mercy.

#### Generated Backstory

Jory Ravenmark is a human barbarian who grew up on a watchtower with her mother and father. Her mother died at sea when she was but a child, while her father was consumed by loneliness that drove him to drink heavily. Neal Lovington is Jory's favorite client, whose favorite customer is actually Ms. Ravenmark.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

Neal Lovington is a traveling performer working at the Lantern House in the seaside village of Ashton. He seeks entertainment to help manage his growing tensions with Mrs Nightbloom about the household's increasing drama and conflict. The character has been entertaining guests at the Lantern House for several years, which provides them with steady attendance.

#### Generated Backstory

Neal Lovington is a traveling performer who works in a local tavern. They have spent several years entertaining guests at the Lantern House, a welcoming pub with a lively stage and a steady flow of visitors.

One of their recurring patrons was Mr. Nightbloom, an old sailor carrying the grief of losing his mother. Their conversations often help him reflect on the old family curse that had shaped his life. But Neal's favorite patron is Ms. Ravenmark, who works at the shoreline lighthouse and carries a quiet loneliness that makes their talks feel unusually meaningful.
