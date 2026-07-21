# Multi-Character Rewrite Comparison

## Rewrite Engine

- Rewrite engine: `local-language-model-llama-cli`
- Candidates: source material, generated summary, and generated backstory.
- Orin Nightbloom uses the generation 1 auto-generated backstory as source material.

## Generated Summary Scores

| Character       | Summary Length | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | -------------: | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom |             49 | 0.6329  | 0.6774     | 0.5000   | 0.8542           |
| Jory Ravenmark  |             66 | 0.6356  | 0.6241     | 0.5714   | 0.8000           |
| Neal Lovington  |             56 | 0.6809  | 0.5557     | 0.6364   | 1.0000           |

## Generated Backstory Scores

| Character       | Overall | Similarity | Coverage | Sentence Quality |
| --------------- | ------: | ---------: | -------: | ---------------: |
| Orin Nightbloom | 0.7277  | 0.7259     | 0.7500   | 0.6807           |
| Jory Ravenmark  | 0.6213  | 0.7907     | 0.4286   | 0.7583           |
| Neal Lovington  | 0.5521  | 0.5662     | 0.4545   | 0.7467           |

## Character Outputs

### Orin Nightbloom

Source material: generation 1 auto-generated backstory

#### Generated Summary

Orin is a Half-Orc Bard from Sunstone Mage College, driven to stop a younger relative from repeating a life-ending mistake and break a curse that only worsens when ignored. His mother instilled a sense of duty to her legacy, making him brave in the face of his future challenges.

#### Generated Backstory

Orin Nightbloom, a Half-Orc Bard, emerged from Sunstone Mage College, a crucible where his talents were honed but his sense of exile sharpened by the weight of his family's legacy. His mother's sacrifice, a revered elven mage, instilled in him the duty to break the curses that shadowed his family's history. Orin's drives are rooted in two core desires: to stop a younger relative from repeating their worst choice and to break a curse that only worsens when ignored, to avoid the painful cycle of history repeating itself. His connection to Sunstone Mage College is tangible, a testament to the institution's impact on Orin's character.

### Jory Ravenmark

Source material: current character backstory

#### Generated Summary

- Jory Ravenmark, a Human Barbarian, seeks to honor her mother and father's memory by tracking and facing the monstrous leviathan that left them bereft.
- Jory's mother died at sea, and her father's loneliness led to his alcoholism, creating a bond between his and Jory.
- Jory's relationship with Neal Lovington, her favorite client, is actually with her father, a stark contrast to her quest.

#### Generated Backstory

Jory Ravenmark, a Human Barbarian, was born into a tragic sea-faring family. Her mother, a sailor, tragically died at sea, leaving her father, consumed by loneliness and alcohol, to raise her and their infant sibling alone on the island watchtower. When Jory was just a child, a monstrous sea beast attacked the tower, but Jory managed to survive. Her fathers, now consumed by the beast's rampage, vanished without a trace that night, leaving Jory to fend for herself and her infant sibling.

### Neal Lovington

Source material: current character backstory

#### Generated Summary

- Neal Lovington, Elf Bard, entertains sailors with their lively performances at the Lantern House.
- Neal is an enemy of Mrs. Nightbloom.
- Neal's mother, Orin Nightbloom, was a sailor who lost his mother.
- Jory Ravenmark is one of Neal's clients.
- The Lantern House, a welcoming pub, has hosted Neal for several years.

#### Generated Backstory

Neal Lovington, an Elf Bard, has a deep connection with Jory Ravenmark, a sailor who often visits the Lantern House to share his stories and tales. This patron's presence brings a sense of comfort and familiarity to Neal, who has spent several years entertaining guests at the tavern. Mrs. Nightbloom's unease about the growing tension in the household has no effect on Neal, who remains focused on his performance and the pleasure it brings to the tavern's patrons. The Lantern House, with its welcoming atmosphere and lively stage, is where Neal has found his true calling, and it is here that he has made a name for himself as a performer.
