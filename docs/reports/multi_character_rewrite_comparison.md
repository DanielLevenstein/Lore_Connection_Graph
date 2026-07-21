# Multi-Character Rewrite Comparison

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
| Prompt hash       | 9f1d57257b232b81                                     |
| Prompt eval time  | 12666.18 ms                                          |
| Prompt tokens     | 665                                                  |
| Completion tokens | 269                                                  |
| Total tokens      | 934                                                  |

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Character       | Status   | Summary Length Score | Overall | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | -------------------: | ------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Rejected | 100.00               | 61.87   | 66.05      | 66.00                 | 81.25            |
| Jory Ravenmark  | Rejected | 0.00                 | 56.48   | 71.64      | 50.67                 | 60.58            |
| Neal Lovington  | Accepted | 100.00               | 71.56   | 56.18      | 84.00                 | 95.83            |

## Generated Backstory Scores

| Character       | Status   | Overall | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | ------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Accepted | 74.24   | 64.73      | 75.20                 | 89.17            |
| Jory Ravenmark  | Rejected | 68.36   | 69.16      | 86.00                 | 92.22            |
| Neal Lovington  | Rejected | 68.46   | 61.95      | 58.29                 | 90.71            |

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin Nightbloom is a Half-Orc Bard who came to the Sunstone Mage College with hopes of avoiding his younger relative's worst choice and breaking their curse that worsens when ignored. His mother instilled in him an unwavering drive to preserve history by preventing repetition, even if it means facing origninal mistakes through the strength of lineage.

#### Generated Backstory

Orin Nightbloom is a Half-Orc Bard who came to light at Sunstone Mage College. His life was shaped by the tension between his inherited legacy and his personal quest for self-discovery. The loss of Orin's Mother left him with an unwavering resolve: stop a younger relative from repeating their worst choice, which in turn would break a curse that only worsens when ignored.

Orin seeks to avoid repeating history while striving to be remembered as brave through the strength and resilience he brings to his community. With skills honed at Sunstone Mage College, Orin aims not just for mastery but also to honor his mother's legacy by breaking cycles of despair rather than perpetuating them.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

Jory Ravenmark is a Human Barbarian haunted by her mother's loss at sea and her father’s loneliness from heavy drinking, leading her to blend nomadic hunter memories with a burning oath against tracking and facing a monstrous leviathan. Jory's parents' untimely deaths led her to adopt their legacy as she seeks justice through relentless pursuit of the beast that could have taken them both.

Jory Ravenmark is a Human Barbarian who has adopted her mother’s nomadic hunting lifestyle but has also developed a burning oath against tracking and facing what some believe is an inexplicably merciful leviathan. Her parents' untimely deaths drove Jory to adopt their legacy as she pursues justice through relentless pursuit of the beast that could have taken them both, blending her memories with her rage.

Jory Ravenmark, a Human Barbarian, seeks revenge against a monstrous Leviathan after losing her mother and father at sea, leading her to blend her nomadic hunting experiences with a burning oath. Her parents' untimely deaths drove Jory into adopting their legacy as she pursues justice through relentless pursuit of the beast that could have taken them both, blending her memories with her rage.

#### Generated Backstory

Jory Ravenmark is a Human Barbarian who grew up with her mother and father on a watchtower island. Her mother died at sea, leaving both Jory's father to become consumed by loneliness after drinking heavily. When she was still young, a monstrous creature from the ocean attacked their home, but Jory managed to survive despite losing both of her fathers in that night.

Jory has an important relationship with her Mother who passed away and Father who became consumed by alcoholism. Their deaths drove them into darkness, leading Jory on this path as she grew older. Despite these challenges, Jory was raised by a skilled shipwright named Neal Lovington, who took pity on the young orphaned girl.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

Neal Lovington is an Elf Bard who entertains sailors with performances on shore leave at the Lantern House in Ashton's seaside village. Mrs Nightbloom harbors unease about growing household tensions, while Jory Ravenmark remains a Client of theirs at the pub where they've spent many years entertaining guests.

#### Generated Backstory

Neal Lovington is an Elf Bard who has spent several years entertaining guests at the Lantern House in a tavern filled with lively stage performances and steady flow of visitors. Their most notable patron was Mr. Nightbloom, a sailor carrying grief from losing his mother. The characters often discussed how Jory Ravenmark's clientship could help ease some of their burdens.

Neal Lovington has driven to entertain sailors on shore leave by using their talents as an Elf Bard and entertaining them with performances that capture the spirit of sea voyages. Mrs. Nightbloom, feeling uneasy about growing tension in the household, sought out Neal for his skillful storytelling and comedic relief to help ease her worries.
