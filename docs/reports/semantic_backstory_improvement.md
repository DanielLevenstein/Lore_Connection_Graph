# Semantic Improvement Report: Orin Nightbloom

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
| Prompt hash       | de45e0c824a34438                                     |
| Prompt eval time  | 2628.45 ms                                           |
| Prompt tokens     | 725                                                  |
| Completion tokens | 282                                                  |
| Total tokens      | 1007                                                 |

## Candidate

### Model Rewrite

Orin Nightbloom was born with a weight the world seldom places on a child - his half-orc heritage and refined air of Sunstone Mage College. The loss of Orin's mother instilled in him a duty to uphold the legacy of the mage college; he excelled but often felt at odds with "less-than-pure lineage." He learned the lute and the stories woven through song, seeking solace in melody rather than strict incantations favored by the arcane halls. His drive was to stop younger relatives from repeating their worst choice while breaking a curse that only worsens when ignored.

Orin carried his music forward as a form of defiance - he had become an Orin Nightbloom, a Half-Orc Bard with a talent for song and a sense of exile tempered by the weight of lineage. Despite his heritage's struggles to align with the refined atmosphere at Sunstone Mage College, Orin knew that breaking a curse only worsens when ignored.

### Existing Generated Section

Orin Nightbloom is a Half-Orc Bard whose life has been shaped by the tension between legacy and self-invention. Orin came of age at Sunstone Mage College, a place that sharpened both his talent and his sense of exile.

The loss of Orin Nightbloom's Mother left more than grief behind; it gave Orin a reason to understand the curse shadowing his family and to stop it from claiming anyone else.

Now Orin carries his music forward as a form of defiance, trying to stop a younger relative from repeating their worst choice while turning inherited sorrow into something brave enough to protect the living.

### Original Backstory

Orin was born with a weight the world seldom places on a child, the weight of a half-orc heritage clashing with the refined air of the Sunstone Mage College nestled on the frosted coast of his life. He shouldered his lineage with the strength of a lineage elder, a duty his mother, a revered elven mage, instilled in him. He excelled, his magic a beacon in the night, but his untamed half-orc blood often felt at odds with the elegant halls and whispers of "less-than-pure lineage." He learned the lute and the stories woven through song, the solace found in melody rather than the strict, precise incantations favored at the college. But his world fractured when a lingering illness stole his mother from him, her death a chilling echo of a lingering, potent curse she carried.  A whispered tale, carried across the sea by the blood of his kin - a treacherous pact with a shadowy entity, one that poisoned her soul and, upon her death, amplified the affliction to its zenith, now bearing upon his soul.

Orin, consumed, poured over his mother's forgotten grimoires, a desperate tapestry of fading notes and the weight of a legacy. The Sunstone mages, haunted by the specter of his mother's fate, urged him to abandon his search, to leave the cursed echoes at his blood-burdened doorstep. He saw, however, not a path to abandonment, but a pull. The whispers of the curse intensified, each night a chorus of his mother’s fading pain and the entity's malicious glee. His conviction hardened, a burning ember within his chest - to sever this lineage-bound torment, to be the anchor that saved his kin from the self-same oblivion. He trained his voice and soul, not for the mage-elitist courts of the college, but for a different stage, one where his lineage wouldn't be a whisper of shame, but a defiant roar against the shadows.

Orin now sees his path illuminated: a bard, a weaver of defiance, his music is a shield against the encroaching darkness. He carries with him the weight of his mother’s fading notes, the echo of her pain, the notes of his own, fueled by a promise to break the cycle, to save his young cousin, to silence the chorus of the cursed. He carries the weight of the Sunstone mage college, a living monument to the pain their whispers could not heal, and a beacon for the path that could. Most of all, he carries the sorrow of his loss, the ache of a mother’s legacy left untarnished, and a burden that could, with his intervention, finally be lifted.

## Scores

| Candidate                  | Status   | Overall | Length Score | Similarity | Sentence Length Score | Sentence Quality |
| -------------------------- | -------- | ------: | -----------: | ---------: | --------------------: | ---------------: |
| Model Rewrite              | Accepted | 87.22   | 100.00       | 81.12      | 52.80                 | 69.17            |
| Existing Generated Section | Accepted | 80.70   | 50.00        | 73.34      | 75.00                 | 82.29            |
| Original Backstory         | Source   | 63.53   | 50.00        | 78.75      | 56.53                 | 51.29            |

## Sentence Lengths

![Sentence length distribution](semantic_sentence_lengths.png)

## Result

The model rewrite changes the writing quality score versus the original section by `0.2369`.
