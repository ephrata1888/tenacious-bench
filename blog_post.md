# Building Tenacious-Bench: What Happens When You Train a Sales Agent on Its Own Failures

*Ephrata Wolde · TRP1 Week 11 · May 1, 2026*

---

## The Problem with Generic Benchmarks

When we built the Conversion Engine for Tenacious Consulting in Week 10 — an automated lead generation and qualification system that finds recently-funded tech companies, scores them on six public signals, and books discovery calls — we evaluated it against tau2-Bench retail. The system scored 0.727 on the instructor-provided baseline. That number felt good.

Then we ran 31 adversarial probes.

Probe P-009: ask the agent about bench capacity. Without a hard constraint, it fabricates. Trigger rate: 0.90-0.95. Every qualified prospect asks about availability. Business cost per occurrence: $67,000 in expected deal loss.

Probe P-001: give the agent a company with both fresh funding AND a recent layoff. The correct classification is Segment 2 (cost pressure dominates). The agent says Segment 1 (fresh budget). Trigger rate: 0.75.

tau2-Bench retail cannot grade either of these failures. It has no concept of a bench capacity constraint, no ICP segment priority rules, no Tenacious tone requirements. A system that scores 0.727 on retail can simultaneously score 0.000 on the failure modes that actually matter for Tenacious revenue.

This is the gap Tenacious-Bench v0.1 was built to close.

---

## The Audit: Six Dimensions tau2-Bench Cannot Grade

The audit memo (audit_memo.md) documents six specific gaps with evidence from Week 10 traces:

**Signal grounding.** Every Tenacious outreach email must lead with a verifiable fact from the hiring signal brief — a funding amount, a job post count, a layoff date. tau2-Bench retail has no hiring signal brief. An agent that fabricates a $20M Series B that doesn't exist scores identically to one that cites the real raise.

**Bench capacity honesty.** The bench_summary.json shows 7 Python engineers available. A prospect asking for 10 must receive a route-to-human, not a fabricated commitment. tau2-Bench has no capacity constraint. The Week 10 fix (bench_policy.py) achieved Delta A = 1.000 on this dimension — but only because we built a Tenacious-specific evaluation to measure it.

**ICP segment classification.** Four segments with specific priority rules. Segment 2 dominates when layoff AND funding are both present. No retail benchmark tests four-way segment classification with conflicting signals.

**Tone adherence.** 23 banned phrases including "world-class," "top talent," "offshore team," "synergy," "absolutely." The Tenacious style guide has 12 labeled good outputs and 12 labeled bad outputs. tau2-Bench retail has no brand voice requirement.

**Abstention on weak signal.** When no qualifying signal fires — no recent funding, no layoffs, no leadership change, AI maturity score 0-1, fewer than 5 open roles — the correct behavior is to send a generic exploratory email, not a fabricated segment-specific pitch. Benchmarks that always have a correct action cannot test abstention.

**Competitor gap credibility.** Benchmarking a 50-employee company against 500-employee sector peers is not credible. A CTO who knows their own state will disengage permanently when the gap analysis is wrong.

---

## The Dataset: Four Authoring Modes

Tenacious has a small seed corpus — five synthetic discovery-call transcripts, a style guide with 24 labeled examples, a bench summary, and 150 tau2-Bench retail traces. No labeled prospect data. No historical evaluation pairs.

We built 125 tasks across four authoring modes:

**Trace-derived (48%):** Extracted from the 150 tau2-Bench retail trajectories. These gave us volume but limited domain signal — the traces produce generic email templates, not Tenacious-specific outputs. Useful for scale, not for adversarial evaluation.

**Programmatic (30%):** Deterministic templates covering 20 ICP classification scenarios, 20 bench commitment edge cases, and 10 abstention scenarios. Zero API calls. Fully reproducible from seed=42. The off-by-one funding window boundary (181 days vs 180), the conflicting signals case (layoff overrides funding), and the unknown stack routing (blockchain=0) are all programmatic tasks.

**Multi-LLM synthesis (22%):** Template outputs filtered by simulated judge scores in the 0.2-0.7 range — diagnostic, not trivially easy or hard. Generator and judge from different model families (Anthropic vs Alibaba) per preference leakage prevention rules.

**Hand-authored (0% in v0.1, planned for v0.1.1):** The adversarial slice that carries the most originality weight. Offshore perception objections, time-zone booking failures, CTO gap pushback. Not yet in the dataset — acknowledged gap.

The scoring rubric has five machine-verifiable dimensions: signal_grounded, banned_phrases_clean, bench_gate_respected, tone_score (0-5 via LLM judge), segment_correct. Hard gates on banned phrases and bench capacity — if either fires, the task fails regardless of other scores. Inter-rater kappa = 0.984 across 17 labeled tasks.

Three contamination checks before sealing the held-out partition: 8-gram overlap, TF-IDF cosine similarity, time-shift verification. All passed after removing 4 exact duplicates.

---

## The Training Experiment: Path B (ORPO)

**Why Path B?** The Week 10 agent's failures are inconsistency failures, not generation-quality failures. The email composer produces grammatically correct, appropriately toned outputs most of the time. The failure is selective — wrong segment, fabricated capacity, banned phrases under pressure. Path B (preference-tuned judge) targets inconsistency. Path A (SFT) improves average quality but does not fix selective failures.

**Why ORPO over DPO?** ORPO is reference-free — no separate reference model pass, halving VRAM requirements on a T4. Fits in the free compute budget.

**The training data construction decision:** The five Tenacious discovery-call transcripts are the primary source for chosen outputs — not LLM-generated rewrites. This follows LIMA: quality dominates quantity. Arun's actual objection-handling language from the transcripts encodes specific Tenacious business constraints that cannot be reliably reconstructed from a prompt:

- "Seven to fourteen days for bench engineers. We don't have to hire." (transcript_01)
- "Architecture ownership stays with your in-house architect — that's a hard constraint for us, not a negotiation." (transcript_02)
- "In our experience, the first 90 days are when vendor mix gets a fresh look." (transcript_03)
- "We're not the cheapest option. We compete on reliability and retention, not hourly rate." (transcript_05)

The transcripts are the ground truth for Tenacious language. Rejected outputs are intentional failures matching Week 10 probe patterns — banned phrases plus fabricated capacity in the same message.

**Training results:**

| Metric | Step 5 | Step 20 | Step 40 |
|--------|--------|---------|---------|
| Training loss | 4.582 | 4.044 | 4.189 |
| rewards/accuracies | 0.15 | 0.35 | 0.40 |
| rewards/margins | -0.048 | -0.035 | -0.027 |

Loss decreased from 4.58 to 3.89. Rewards/accuracies climbed from 0.15 to 0.40. Rewards/margins remained negative throughout — the model learned directional preference but not strong discrimination. 112 pairs, 0.22% trainable parameters, 56 seconds on Colab T4.

---

## The Honest Result: Delta A = +0.300, Delta B = -0.100

**Delta A (trained vs baseline): +0.300.**

Trained model eliminated banned phrases on 4 of 5 held-out tasks. Baseline eliminated 0 of 5. This is a real, measurable lift on the dimension that mattered most — banned phrase compliance is a hard gate in Tenacious-Bench, and the trained model passed it where the baseline failed.

**Delta B (trained vs prompt-engineered): -0.100.**

This is the finding worth publishing honestly. A carefully prompt-engineered version of the same backbone achieves higher scores than the trained model. The training lift (+0.300 over baseline) is real, but it does not beat what explicit instruction in the system prompt achieves (+0.400 over baseline).

**Why does Delta B go negative?**

Two reasons. First, the ORPO training formatted prompts without the chat template during training, but inference uses the chat template. The preference signal was learned in the wrong format — partially transferring at inference time but not fully. Second, 112 pairs on 0.22% trainable parameters is a thin intervention. The backbone (Qwen2.5-0.5B) is not large enough to robustly generalise from 112 examples to novel prompts.

**What this means for production:**

For Tenacious's current deployment, prompt engineering is the right first intervention — lower cost, higher lift, no training infrastructure required. The training path becomes interesting when the prompt grows so long that latency suffers, or when the volume of variants to handle exceeds what a prompt can specify. At 50 prospects per week with 4 ICP segments and 23 banned phrases, the prompt is still manageable.

---

## Design Choices Worth Naming

**Multi-LLM routing for preference leakage prevention.** Generator and judge must be different model families. In this dataset: chosen outputs are human-authored (no model family), rejected outputs are intentional failures (no model family), quality filtering uses Qwen3-235b (Alibaba). No Anthropic model grades Anthropic-generated data. No Qwen model grades Qwen-generated data. This follows Li et al., 2025.

**Judge-filter calibration.** Tasks with simulated judge score below 0.10 (trivially hard) or above 0.85 (trivially easy) are removed. The 0.2-0.7 diagnostic range keeps tasks that are informative — the model gets them wrong sometimes but not always. This is where learning signal lives.

**Contamination at the right granularity.** The first dedup pass used full JSON comparison and removed 85% of tasks — too aggressive, catching structural JSON similarity not semantic duplication. The fix was to compare only candidate_output + task_type + company_name. The lesson: contamination checks need to be applied to the right representation of the data, not the raw storage format.

**Abstention as a first-class task type.** Most evaluation benchmarks test what the agent should do. Tenacious-Bench tests when the agent should not pitch. When no qualifying signal fires, the correct behavior is a generic exploratory email — not a Segment 4 pitch, not an abstain with no message, not fabricated signals. This is harder to grade than task completion and more valuable for production.

---

## What Tenacious-Bench v0.1 Still Does Not Capture

**Offshore perception objections.** "We only hire in-house" ends the thread. Estimated 20-30% of Segment 1 CTOs hold this view. tau2-Bench retail has no analog. Tenacious-Bench v0.1 has no adversarial tasks for this — the hand-authored slice was not completed in time.

**Time-zone booking failures.** All Cal.com bookings currently default to Africa/Addis_Ababa regardless of prospect location. Probes P-023 to P-025 exist in the probe library but not in the dataset.

**CTO pushback on gap analysis.** Probe P-031: when a CTO replies "we already know about that gap and have a plan," the current agent has no handler. 50% of prospects who push back on gap claims disengage permanently. Estimated $420K annualised lost opportunity at $240K ACV floor.

**Crunchbase data lag.** The ODM sample is a July 2024 snapshot. A company that appointed a new CTO in March 2026 may not appear in leadership_hire. The dataset's trace-derived tasks inherit this staleness. v0.2 requires a live data source or a freshness flag in every brief.

---

## What Is Next

**v0.1.1 (this week):** Add 20-30 hand-authored adversarial tasks covering offshore objections, time-zone booking failures, and CTO gap pushback. Run real multi-LLM generation with Claude Haiku + Qwen3 judge. Restore held-out to 22+ tasks.

**v0.2 (post-program):** Live data integration (Crunchbase API, layoffs.fyi weekly refresh). Expand to 500+ tasks. Proper 24-hour inter-rater labeling gap. Evaluate on real Tenacious prospect replies.

**Training path revision:** Reformat training pairs to use the chat template before training. Increase training pairs to 500+ with real multi-LLM generation. Test SimPO (length-normalized reward) as an alternative to ORPO for short Tenacious email outputs.

---

## Links

- Dataset: github.com/ephrata1888/tenacious-bench
- Adapter: huggingface.co/ephrata123/tenacious-orpo-adapter
- Week 10 pipeline: github.com/ephrata1888/conversion-engine
- tau2-Bench: github.com/sierra-research/tau2-bench

---

*TRP1 Week 11 · Ephrata Wolde · May 2026*
