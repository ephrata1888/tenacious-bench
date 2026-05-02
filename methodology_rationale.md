\# methodology\_rationale.md

\# One-page training data construction rationale

\# Author: Ephrata Wolde | TRP1 Week 11 | April 29, 2026



\## Path Declaration

Path B — ORPO preference-tuned judge (Hong et al., EMNLP 2024).



\## Why This Training Data Construction



\### Source selection — transcripts over synthetic generation



The five Tenacious discovery-call transcripts (transcript\_01 through transcript\_05)

are the primary source for chosen outputs, not LLM-generated rewrites.



This decision is grounded in LIMA (Zhou et al., NeurIPS 2023): 1,000 high-quality

examples from a curated human source outperform 10,000 synthetic examples on

downstream evaluation. The transcripts contain Arun's actual objection-handling

language — language that cannot be reliably reconstructed from a prompt because

it encodes specific Tenacious business constraints (the $\[PROJECT\_ACV\_MIN] POC floor,

the 3-hour Pacific overlap guarantee, the "architecture stays in-house" rule).



Evidence from Week 10: trace 485a3a8d shows the pipeline correctly grounding

the email in the DataStack AI Series B. But trace de389db2 shows the bench gate

correctly blocking — yet the agent still used soft fabrication language

("absolutely" + "we have the capacity") that the transcripts never use.

The transcripts are the ground truth for language, not just structure.



\### Preference leakage prevention



Per Li et al. (2025), the generator and judge must be different model families.

In this dataset:

\- Chosen outputs: human-authored (transcripts) — no model family

\- Rejected outputs: intentional failures matching probe patterns — no model family

\- Expansion pairs: template-generated (no LLM) for bench commitment

\- Judge for filtering: Qwen3-235b (Alibaba family) via scoring\_evaluator.py



No Anthropic model was used to generate data that a Qwen judge then grades.

No Qwen model was used to generate data that a Qwen judge then grades.



\### Why 112 pairs is sufficient



LIMA shows quality dominates quantity. Our 112 pairs have three properties

that make them high-quality:



1\. Chosen outputs are grounded in real Tenacious constraints — not prompt-generated

2\. Rejected outputs are maximally wrong — they violate bench gate AND banned phrases

&#x20;  simultaneously, creating a wide preference signal gap

3\. All 5 probe categories covered: bench commitment (P-009), tone drift (P-012,

&#x20;  P-013), objection handling (P-013, P-017), signal grounding (P-005),

&#x20;  abstention (P-005)



The score gap between chosen and rejected on scoring\_evaluator.py is

approximately 0.7-0.8 points (rejected scores \~0.1-0.2, chosen scores \~0.8-0.9).

Per Rafailov et al. (NeurIPS 2023), wide preference gaps produce stronger

gradient signal than narrow ones.



\### Training configuration rationale



Backbone: Qwen3.5 0.5B — smallest that fits T4 VRAM with ORPO overhead.

ORPO over DPO: reference-free, halves VRAM requirement, no separate reference

model pass (Hong et al., EMNLP 2024).

LoRA rank 16: standard for preference tuning on small backbones.

3 epochs: follows Prometheus 2 (Kim et al., 2024) recommendation for judge

training — more epochs risks memorizing rejected patterns.



\## Week 10 Trace Evidence



\- Trace 485a3a8d: correct grounding — chosen pattern

\- Trace de389db2: bench gate correct, soft fabrication language — rejected pattern  

\- Trace b475ca98: fallback tone scorer gave 5/5, LLM judge gave 3/5 — inconsistency

&#x20; failure that ORPO judge directly addresses

