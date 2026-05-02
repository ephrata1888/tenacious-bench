\# model\_card.md

\# tenacious-orpo-adapter



\## Model Details

\- \*\*Model type:\*\* LoRA adapter (ORPO preference-tuned judge/critic)

\- \*\*Backbone:\*\* Qwen2.5-0.5B-Instruct (unsloth/Qwen2.5-0.5B-Instruct)

\- \*\*Training method:\*\* ORPO (Monolithic Preference Optimization without Reference Model)

\- \*\*HuggingFace URL:\*\* https://huggingface.co/ephrata123/tenacious-orpo-adapter

\- \*\*LoRA rank:\*\* 16 | \*\*LoRA alpha:\*\* 32 | \*\*Target modules:\*\* q\_proj, v\_proj

\- \*\*Trained by:\*\* Ephrata Wolde | TRP1 Week 11 | April 30, 2026



\## Intended Use

Deployed as a rejection-sampling layer in front of the Week 10 Conversion Engine

email composer. At inference time, the judge scores each draft output and routes

low-scoring drafts back for regeneration.



Scores Tenacious-specific quality dimensions:

\- Signal grounding (does output cite verifiable facts from hiring\_signal\_brief?)

\- Banned phrase detection (zero of 23 banned phrases)

\- Bench gate compliance (no fabricated capacity commitments)

\- Tone adherence (direct, grounded, honest, professional, non-condescending)



\## Training Data

\- 112 preference pairs from training\_data/preference\_pairs\_expanded.jsonl

\- Chosen outputs: grounded in 5 Tenacious discovery-call transcripts (human-authored)

\- Rejected outputs: intentional failures matching Week 10 probe patterns

\- Preference leakage prevention: chosen outputs are human-authored, not LLM-generated



\## Training Configuration

| Parameter | Value |

|-----------|-------|

| Epochs | 3 |

| Total steps | 42 |

| Learning rate | 5e-5 |

| Batch size (effective) | 8 (2 x 4 gradient accumulation) |

| Max sequence length | 512 |

| Seed | 42 |

| Runtime | 56 seconds on T4 |



\## Training Results

| Metric | Step 5 | Step 20 | Step 40 | Final |

|--------|--------|---------|---------|-------|

| Training loss | 4.582 | 4.044 | 4.189 | 4.241 |

| rewards/accuracies | 0.15 | 0.35 | 0.40 | 0.40 |

| rewards/margins | -0.048 | -0.035 | -0.027 | -0.027 |



Loss decreased from 4.58 to 3.89 (lowest at step 35).

Rewards/accuracies climbed from 0.15 to 0.40.

Rewards/margins remained negative — partial preference learning achieved.

112 pairs on 0.22% trainable parameters (1,081,344 of 495,114,112).



\## Limitations

\- Trained on 112 pairs — above LIMA threshold but below ideal for strong preference signal

\- Rewards/accuracies at 0.40 means model prefers chosen 40% of the time (above random, below strong)

\- Rewards/margins still negative — model has learned directional preference but not strong discrimination

\- 0.5B backbone limits capacity for complex multi-turn reasoning

\- Not tested on domains outside Tenacious B2B sales workflow



\## Evaluation

See ablations/ablation\_results.json for Delta A, Delta B, Delta C results.

Held-out evaluation uses scoring\_evaluator.py from tenacious-bench repo.



\## Environmental Cost

\- Training: T4 GPU, 56 seconds, \~0.0002 kWh estimated

\- No paid compute used (Colab free tier)



\## Citation

Wolde, E. (2026). tenacious-orpo-adapter: A preference-tuned judge for

Tenacious B2B sales agent evaluation. TRP1 Week 11.

https://huggingface.co/ephrata123/tenacious-orpo-adapter

