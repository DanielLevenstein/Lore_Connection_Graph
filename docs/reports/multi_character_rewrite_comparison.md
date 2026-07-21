# Multi-Character Rewrite Comparison

## Model Runtime

| Metric            | Value                                      |
| ----------------- | ------------------------------------------ |
| Model             | JustineF/Qwen2.5-1.5B-Instruct-Q4_K_M-GGUF |
| Quantization      | Q4_K_M                                     |
| Prompt version    | character-rewrite-v6-local-qwen-1.5b       |
| Max tokens        | 640                                        |
| Temperature       | 0.75                                       |
| Top P             | 0.85                                       |
| Repeat penalty    | 1.15                                       |
| Seed              | 2310                                       |
| Context size      | 8192                                       |
| Batch size        | 64                                         |
| Threads           | 2                                          |
| GPU layers        | 0                                          |
| Device            | none                                       |
| Timeout seconds   | 180                                        |
| Prompt hash       | 2086a00212f82a5f                           |
| Prompt eval time  | 9414.95 ms                                 |
| Prompt tokens     | 590                                        |
| Completion tokens | 249                                        |
| Total tokens      | 839                                        |

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Character       | Summary Length | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | -------------: | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom | 61             | 0.6033  | 0.6745     | 0.5000   | 0.7113           |
| Jory Ravenmark  | 68             | 0.6037  | 0.6103     | 0.4286   | 0.9861           |
| Neal Lovington  | 56             | 0.6664  | 0.5145     | 0.6364   | 1.0000           |

## Generated Backstory Scores

| Character       | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom | 0.5588  | 0.6393     | 0.3750   | 0.8317           |
| Jory Ravenmark  | 0.6956  | 0.7114     | 0.5714   | 0.9472           |
| Neal Lovington  | 0.7321  | 0.5002     | 0.8182   | 0.9444           |

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin Nightbloom is a Half-Orc Bard from Sunstone Mage College who seeks to stop his younger relative's worst choice and break a curse that worsens when ignored, all while preserving history by avoiding repeating past mistakes. His mother instilled in him the strength of lineage elders as he shoulders the responsibility of keeping their legacy alive at such an early age.

#### Generated Backstory

Orin Nightbloom was born into an orphan's legacy at Sunstone Mage College, where he honed his talents while grappling with a curse that shadows his family's history. His mother, revered as a powerful elven mage by all who knew her, instilled in him not just the strength to confront this curse but also the duty to prevent its worsening cycle.

Orin is driven both by necessity and desire: he seeks to stop a younger relative from repeating their worst choice through actions that embody resilience. His second drive propels him towards breaking the binding of his family's legacy, for in ignoring it, they only become worse off over time. Orin aims to avoid history’s repeating cycle and instead forge new paths—paths shaped by courage rather than regret.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

1. Jory Ravenmark is a Human Barbarian burdened by loss and mercy, dedicating her life to tracking and confronting a monstrous leviathan.
2. Jory's father died of loneliness after his wife's death at sea; this tragedy has driven him into alcoholism.  
3. Despite the tragic circumstances surrounding her parents' deaths, Jory dedicates herself to hunting down and avenging their violent demise by facing the beast that caused them.

#### Generated Backstory

Jory Ravenmark is a Human Barbarian who grew up on a watchtower island with her mother and father. Her mother died at sea, leaving their home devastated by grief as her father was consumed by loneliness which led him to drink heavily. One fateful night when Jory was young, the monster from the sea attacked the tower, saving her life but claiming both fathers' spirits in exchange for vengeance. This traumatizing event sealed Jory's place among barbarians who believe it is their duty to protect and honor those they care about at any cost.

Jory's relationship with Neal Lovington has always been significant; his favorite client was actually Ms. Ravenmark, an intriguing connection that hints at a dark side of the sea monster lore surrounding them both.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

Neal Lovington is an Elf Bard who entertains sailors on shore leave at Ashton's Lantern House. Their Mother lost her mother due to grief from visiting Mr Nightbloom as a patron of the tavern. Mrs. Nightbloom harbors unease about rising tensions in their household. Jory Ravenmark, a recurring client, has requested Neal's performances for several years.

#### Generated Backstory

Neal Lovington is an Elf Bard known for entertaining sailors on shore leave at a local tavern called Lantern House. Their primary drive has always been to provide entertainment and joy, but their enemy was Mrs. Nightbloom who grew uneasy about the growing tension within her household.

Their past includes spending several years at Lantern House, where they have become close friends with Jory Ravenmark due to his consistent patronage as a client listed in Neal's Character Stats table. Their mother passed away carrying grief after losing her job during an economic downturn that affected sailors' paychecks. This tragic event fueled their desire to connect with people and provide comfort through art.
