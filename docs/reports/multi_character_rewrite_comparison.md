# Multi-Character Rewrite Comparison

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Character       | Summary Length | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | -------------: | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom | 36             | 0.5075  | 0.5526     | 0.6250   | 0.1643           |
| Jory Ravenmark  | 15             | 0.2170  | 0.0485     | 0.0000   | 1.0000           |
| Neal Lovington  | 71             | 0.7595  | 0.5637     | 0.8182   | 0.9700           |

## Generated Backstory Scores

| Character       | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom | 0.6437  | 0.7828     | 0.5000   | 0.7238           |
| Jory Ravenmark  | 0.6222  | 0.7624     | 0.4286   | 0.8125           |
| Neal Lovington  | 0.5542  | 0.4924     | 0.4545   | 0.8867           |

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin Nightbloom, a Half-Orc Bard from Sunstone Mage College, seeks to prevent a younger relative from repeating the same disastrous choices their mother made, while also working to break a curse that only worsens when ignored.

#### Generated Backstory

Orin Nightbloom, a Half-Orc Bard, was born into the shadow of his mother's legacy. Raised at Sunstone Mage College, a place that sharpened both his talent and his sense of exile, Orin had to confront the weight of his family's curse. The loss of his mother, a revered elven mage, left Orin with a responsibility to understand the shadowing curse that plagued his family. He wanted to break the curse that only worsened when ignored, knowing that by doing so, he would be stopping a younger relative from repeating the same disastrous choices.

Orin's career as a bard was not just a passion but a way to live out his mother's legacy, a duty that he took on with the strength of a lineage elder, instilled in him by his mother, a revered elven mage. His drive was to break the curse, to prevent the cycle of mistakes that his mother's story had foreshadowed. Through his music, he aimed to avoid repeating history, to prevent a younger relative from falling into the same path of ruin.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

_No acceptable generated candidate was produced. local model rewrite returned an unusable rewrite: truncated ending._

#### Generated Backstory

Jory Ravenmark, a Human Barbarian, was born into the tumultuous world of the sea and the watchtower that served as her home. Her mother, who vanished at sea, and her father, consumed by loneliness, left a void that she sought to fill with adventure and survival. The monster from the sea that attacked the watchtower, consuming both her parents, was a turning point that shaped her destiny. This event was the catalyst for Jory's journey, driving her to become the fearless Barbarian she is today.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

- Neal Lovington, an Elf Bard, works at the Lantern House in Ashton, entertaining sailors on shore leave.
- Mrs. Nightbloom, upset about growing tension at the household, fears for her son's wellbeing.
- Neal has a long-standing client relationship with Jory Ravenmark and a connection to Orin Nightbloom through grief.
- The Lantern House, known for its stage and welcoming atmosphere, has hosted Neal and his fellow performers for years.

#### Generated Backstory

Neal Lovington, an Elf Bard, has dedicated their life to entertaining sailors on shore leave. This passion stems from their interaction with Mr. Nightbloom, a sailor burdened by the grief of losing his mother. The tavern's Lantern House has been their haven since they first began performing, where they weave tales of adventure and magic into the lives of those who seek solace. Despite the growing unease in the household, Neal remains steadfast in their mission, knowing that their art can lift spirits and bring a smile to those who are weary.
