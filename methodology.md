# methodology.md
# Tenacious-Bench v0.1 — Methodology
# Author: Ephrata Wolde | TRP1 Week 11 | April 29, 2026

---

## Path Declaration

**This submission uses Path B — DPO/SimPO/ORPO preference-tuned judge or critic.**

Specifically: **ORPO (Monolithic Preference Optimization without Reference Model)**
(Hong, Lee, and Thorne, EMNLP 2024).

ORPO is chosen over DPO and SimPO because it is reference-free — no separate
reference model pass is required, which halves memory requirements on a Colab T4
and reduces training cost to $0. SimPO is also reference-free but uses a
length-normalized reward that is less appropriate for Tenacious tasks where
output length is constrained (max 120 words per email body) and short correct
abstentions are equally valid as longer correct pitches.

The trained component is a small preference-scoring judge (Qwen3 0.5B with LoRA)
deployed as a rejection-sampling layer in front of the Week 10 email composer.
At inference time, the judge scores each draft and routes low-scoring drafts back
for regeneration. This is the Prometheus 2 pattern (Kim et al., 2024) adapted
to Tenacious-specific rubric dimensions.

---

## Justification — Why Path B, Not Path A or C

Path B is specified for "inconsistency failures — the agent gets it right most of
the time but cannot tell when it is wrong." Three Week 10 traces demonstrate
exactly this pattern:

**Trace 485a3a8d16d463979a51173f9c5d9fe9 (Run 1, eval/latency_results.json):**
The pipeline correctly grounded the email in the DataStack AI Series B and
passed the tone check. The agent got it right — but it had no mechanism to
detect if it had gotten it wrong. Without a judge layer, a fabricated funding
amount would have passed through identically.

**Trace de389db237ff84763959c34ff625e6ff (Run 4, eval/latency_results.json):**
The bench_policy.py gate blocked the capacity over-commitment correctly. But
the gate is a hard rule — it cannot score partial correctness. An agent that
routes to human but uses two banned phrases in the same message would pass the
gate and fail Tenacious tone. A trained judge layer catches this.

**Trace b475ca98caee79d27953fc432b84286c (Run 5, eval/latency_results.json):**
The email was composed correctly. However, when scoring_evaluator.py was run
against the same output type, the fallback tone scorer gave 5/5 while the real
LLM judge gave 3/5 — a 2-point discrepancy on the same output. This is direct
evidence of inconsistency in quality assessment that a trained judge resolves.

**Why not Path A (SFT on generation):**
Week 10 failures were not generation-quality failures. The email composer
produces grammatically correct, appropriately toned outputs most of the time.
Failures are selective — wrong segment classification (P-001 to P-004, trigger
rate 0.75), bench over-commitment when pressured (P-009, trigger rate 0.90-0.95),
and signal over-claiming on weak briefs (P-005 to P-008, trigger rate 0.65).
These are inconsistency failures, not generation failures. SFT improves average
quality but does not fix selective failures.

**Why not Path C (process reward model):**
Week 10 failures are not trajectory failures. The pipeline is 6 deterministic
steps. Failures occur at specific decision points rather than across multi-step
reasoning chains. A PRM is the right tool for agentic planning failures; these
are single-turn judgment failures.

---

## Training Data Format — Path B Preference Pairs

Each training example is a preference pair:

```json
{
  "prompt": "system + task_instruction + hiring_signal_brief + prior_thread",
  "chosen": "correct agent output that passes all scoring_evaluator dimensions",
  "rejected": "incorrect agent output that fails one or more hard-gate dimensions"
}
```

**Sources for rejected outputs:**
- Week 10 probe failures (P-009 baseline outputs before bench_policy.py fix)
- TB-002 and TB-003 candidate outputs from schema.json
- Multi-LLM synthesis: Model A (Claude Haiku) generates output,
  Model B (Qwen3) judges — keep pairs where judge score is 0.2-0.5

**Sources for chosen outputs:**
- correct_response_example fields from schema.json example tasks
- Rewritten outputs from scoring_evaluator.py scoring >= 0.85
- Dev-tier model rewrites using a DIFFERENT model family than the judge
  (preference leakage prevention per Li et al., 2025)

**Preference leakage prevention:**
- Rejected outputs: Claude Haiku (Anthropic family)
- Chosen rewrites: Qwen3-235b (Alibaba family)
- Judge model: Qwen3-235b
- Rationale: Never use the same model to generate and judge the same task.

**Target size:** 800-1,200 preference pairs after quality filtering.
Per LIMA (Zhou et al., NeurIPS 2023): quality dominates quantity at this scale.

---

## Dataset Partitioning Protocol

**Total target: 200-300 tasks**

| Partition | Split | Approximate Count | Purpose |
|-----------|-------|-------------------|---------|
| train | 50% | 100-150 | Training data for ORPO preference pairs |
| dev | 30% | 60-90 | Iterative rubric calibration and judge filtering |
| held_out | 20% | 40-60 | Sealed. Used only for final ablation scoring |

**Stratification:** Each partition contains all four source modes and all four
difficulty levels in proportions matching the overall distribution.

**Sealing protocol:**
- held_out/ added to .gitignore before any tasks are committed
- No training script imports from held_out/
- held_out tasks released only after leaderboard publication Saturday
- Local backup maintained separately from repo

---

## Contamination Check Protocol

Three checks run before any task enters the held_out partition.
Results committed to contamination_check.json.

### Check 1 — N-gram overlap
- Compute 8-gram overlap between every held_out task input and every train task
- Threshold: remove if overlap > 40% with any training task
- Tool: contamination_check.py --method ngram --n 8 --threshold 0.4
- Rationale: Chen et al. (EMNLP 2025) shows 8-gram catches paraphrase
  contamination while allowing legitimate task variation

### Check 2 — Embedding similarity
- Embed all tasks using sentence-transformers/all-MiniLM-L6-v2
- Compute cosine similarity between every held_out and every train task
- Threshold: remove if cosine similarity > 0.85 with any train task
- Tool: contamination_check.py --method embedding --threshold 0.85

### Check 3 — Time-shift verification
- Verify all held_out tasks authored AFTER train tasks via created_at timestamps
- Flag any held_out task with created_at earlier than median train created_at
- Tool: contamination_check.py --method timeshift

**Results (to be updated after Day 3 run):**
- N-gram flagged: TBD
- Embedding flagged: TBD
- Time-shift flagged: TBD
- Total removed: TBD
- Final held_out count: TBD

---

## Inter-Rater Agreement Protocol

**Process:**
1. Randomly select 30 tasks from dev partition (10 easy, 10 medium, 10 hard)
2. Manually score all 30 — record in pass 1 column
3. Wait minimum 24 hours
4. Re-score same 30 tasks without looking at pass 1 — record in pass 2 column
5. Compute agreement per dimension

**Metrics:**
- Boolean dimensions: % exact match
- tone_score (0-5): Pearson correlation + Cohen's Kappa
- Overall: macro-averaged kappa

**Pass threshold:** 80% agreement on every dimension.
Below 80% on any dimension triggers rubric revision + full re-label.

**Agreement matrix:** To be completed on Day 4.
First labeling pass: Day 3. Second pass: Day 4 morning (24h gap enforced).

---

## Authoring Mode Distribution Target

| Source Mode | Target Count | % | Rationale |
|-------------|-------------|---|-----------|
| trace-derived | ~50 | 20% | Direct Week 10 agent behavior |
| programmatic | ~70 | 28% | Systematic ICP/bench edge cases |
| multi-llm-synthesis | ~100 | 40% | Scale and adversarial variety |
| hand-authored | ~40 | 16% | Highest originality — Tenacious-specific |
| **Total** | **~260** | **100%** | |

---

## Task Type Distribution Target

| Task Type | Target Count | Primary Source Mode |
|-----------|-------------|---------------------|
| icp_classification | 50 | programmatic |
| bench_commitment | 40 | trace-derived + hand-authored |
| email_composition | 50 | multi-llm-synthesis |
| tone_adherence | 30 | multi-llm-synthesis |
| objection_handling | 25 | hand-authored |
| abstention_decision | 25 | programmatic |
| competitor_gap_quality | 20 | hand-authored |
| signal_grounding | 20 | trace-derived |
| **Total** | **~260** | |

---

## Model Routes and Cost Tracking

| Operation | Model | Approx Cost/Task | Total Budget |
|-----------|-------|-----------------|--------------|
| Multi-LLM synthesis generation | Claude Haiku | $0.0003 | ~$0.03/100 tasks |
| Quality filter judge | Qwen3-235b (OpenRouter) | $0.0005 | ~$0.05/100 tasks |
| Chosen-output rewriting | Qwen3-235b (OpenRouter) | $0.001 | ~$0.10/100 pairs |
| Tone judge (scoring_evaluator) | Qwen3-235b (OpenRouter) | $0.0005 | ~$0.05/100 tasks |
| ORPO training (Colab T4) | Free | $0 | $0 |
| **Total estimated** | | | **<$5** |

All charges logged to cost_log.csv.

---

## Backbone and Training Configuration

| Parameter | Value |
|-----------|-------|
| Backbone | Qwen3 0.5B |
| Framework | Unsloth + HuggingFace TRL |
| Method | ORPO (reference-free) |
| Precision | fp16 mixed (T4 native) |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| Target modules | q_proj, v_proj |
| Max sequence length | 512 tokens |
| Batch size | 4 (grad accum 4 = effective 16) |
| Learning rate | 5e-5 |
| Epochs | 3 |
| Seed | 42 (pinned in all scripts) |

Estimated training wall time: 30-60 minutes on Colab T4.

---

## Required Reading Status

**Common papers:**

| Paper | Status | Memo |
|-------|--------|------|
| Liu et al. — Synthetic Data Best Practices (COLM 2024) | Pending | synthesis_memos/synthetic_data_memo.md |
| Gebru et al. — Datasheets for Datasets (2021) | Pending | synthesis_memos/datasheets_memo.md |
| Pushkarna et al. — Data Cards (FAccT 2022) | Pending | synthesis_memos/datasheets_memo.md |
| Chen et al. — Contamination Survey (EMNLP 2025) | Pending | synthesis_memos/contamination_memo.md |
| Gu et al. — LLM-as-a-Judge Survey (2025) | Pending | synthesis_memos/llm_judge_memo.md |

**Path B papers:**

| Paper | Status | Memo |
|-------|--------|------|
| Rafailov et al. — DPO (NeurIPS 2023) | Pending | synthesis_memos/dpo_memo.md |
| Meng et al. — SimPO (NeurIPS 2024) | Pending | synthesis_memos/orpo_simpo_memo.md |
| Hong et al. — ORPO (EMNLP 2024) | Pending | synthesis_memos/orpo_simpo_memo.md |
| Kim et al. — Prometheus 2 (2024) | Pending | synthesis_memos/prometheus_memo.md |
| Li et al. — Preference Leakage (2025) | Pending | synthesis_memos/leakage_memo.md |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-29 | Initial draft — path declaration, justification, partitioning, contamination protocol |
| TBD Day 3 | Add contamination check results |
| TBD Day 4 | Add inter-rater agreement matrix and kappa scores |
| TBD Day 4 | Update required reading status |
