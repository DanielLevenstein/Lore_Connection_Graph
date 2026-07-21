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
| Prompt hash       | 79c326b1f78320b0                                     |
| Prompt eval time  | 13000.44 ms                                          |
| Prompt tokens     | 725                                                  |
| Completion tokens | 228                                                  |
| Total tokens      | 953                                                  |

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Candidate       | Status   | Overall | Summary Length Score | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | ------: | -------------------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Rejected | 52.61   | 100.00               | 44.20      | 20.00                 | 5.71             |
| Jory Ravenmark  | Accepted | 88.98   | 100.00               | 78.05      | 48.00                 | 83.33            |
| Neal Lovington  | Accepted | 71.63   | 100.00               | 45.45      | 66.67                 | 98.61            |

### Rejection Reasons

- Orin Nightbloom: summary sentence too long; overall score below 70

## Generated Backstory Scores

| Candidate       | Status   | Overall | Length Score | Similarity | Sentence Length Score | Sentence Quality |
| --------------- | -------- | ------: | -----------: | ---------: | --------------------: | ---------------: |
| Orin Nightbloom | Accepted | 70.57   | 100.00       | 62.64      | 44.00                 | 50.39            |
| Jory Ravenmark  | Accepted | 71.39   | 100.00       | 82.48      | 41.00                 | 51.90            |
| Neal Lovington  | Accepted | 74.53   | 100.00       | 52.59      | 72.67                 | 96.53            |

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin Nightbloom, half-Orc Bard from Sunstone Mage College, seeks to prevent his younger relative's repetition of past mistakes and break a curse that worsens when ignored, driven by his desire to avoid repeating history at his college alma mater.

#### Generated Backstory

Orin Nightbloom, Half-Orc Bard, was raised at Sunstone Mage College, where his musical talent and sense of isolation intertwined to shape him into a figure of defiance against family history. The loss of Orin's Mother left an unspoken burden on her son; it fueled the desire within him to break a curse that only worsens when ignored—either by stopping a younger relative from repeating their worst choice or by preventing his own tragic fate being inherited.

Orin carries this music as a defiance, using it not just for pleasure but also as a weapon against history's cyclical nature. He aims to ensure the cycle of tragedy does not continue and hopes that through his art, he can turn grief into something meaningful enough to protect those still living in the shadow of past mistakes.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

Jory Ravenmark is a Human Barbarian haunted by the loss of her family and the inexplicable mercy shown by a monstrous leviathan that compelled her to seek revenge. She blends her nomadic hunter-memories with a burning oath to track and face the beast that tormented her childhood, driven by the memory of Neal Lovington's favorite client being actually Ms. Ravenmark.

#### Generated Backstory

Jory Ravenmark is a Human Barbarian who dedicated her life to hunting down monsters from the sea after losing both of her parents in a horrific attack on their island watchtower as a child. Her father's loneliness and alcoholism consumed him until he disappeared without a trace just before Jory was taken by the beast that killed them, driving her into a fierce dedication to tracking the creature responsible for her family’s demise.

Jory Ravenmark uses all aspects of sea life—her knowledge gleaned from watching her father as a child—to track down the monster. Her love for the open ocean is strong enough to make up for the grief she feels over losing both her parents, and though she knows in her heart that it's impossible for them to return, her resolve keeps pushing her forward.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

Neal Lovington is an Elf Bard who has been entertaining sailors on shore leave for many years at the Lantern House in Ashton's seaside village. They are driven by their passion to make others happy and have become a beloved figure among the locals. Mrs.

#### Generated Backstory

Neal Lovington is an Elf Bard who has spent several years entertaining guests at the Lantern House, a welcoming pub with a lively stage and steady traffic of visitors. They work tirelessly to entertain sailors on shore leave, providing them with some much-needed distraction from their duties.

Their favorite patron was Jory Ravenmark, a lighthouse keeper known for his quiet loneliness. Their conversations were often filled with meaning that resonated deeply with Orin Nightbloom's grief over losing his mother. Mrs. Nightbloom, the housekeeper and caretaker of Lantern House, harbored unease about growing tensions in their household.
