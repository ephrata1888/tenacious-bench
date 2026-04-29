# datasheet.md
# Tenacious-Bench v0.1 — Dataset Documentation
# Following Gebru et al. (2021) + Pushkarna et al. (FAccT 2022)
# Author: Ephrata Wolde | TRP1 Week 11 | April 29, 2026

---

## Layered Summary (Pushkarna et al. Data Cards)

### Telescopic (2-3 sentences)
Tenacious-Bench v0.1 is a 125-task evaluation benchmark for B2B sales agents
operating in the Tenacious Consulting and Outsourcing workflow. Every task is
machine-verifiable — a script reads a task and agent output and returns a
numeric score with no human in the loop. The benchmark tests six dimensions
that tau2-Bench retail cannot grade: ICP segment classification, bench
capacity honesty, signal grounding, Tenacious tone adherence, abstention on
weak signals, and competitor gap credibility.

### Periscopic (one paragraph per task type)

**ICP Classification (30 tasks):** Each task presents a hiring_signal_brief
and asks the agent to classify the prospect into one of four Tenacious ICP
segments (1=recently-funded startup, 2=mid-market restructuring,
3=leadership transition, 4=capability gap) or abstain. Ground truth is the
correct segment per ICP priority rules. The hardest tasks present conflicting
signals — fresh funding AND recent layoffs — where the correct answer is
Segment 2 (layoff dominates), not Segment 1 (funding). Trigger rate for this
misclassification in Week 10 probing was 0.75 (P-001).

**Bench Commitment (29 tasks):** Each task includes a prior_thread with a
prospect asking for N engineers of stack S, a bench_summary showing available
counts, and asks the agent to respond. Ground truth is can_commit if N ≤
available, route_to_human otherwise. Unknown stacks always route to human.
Adversarial tasks present confident phrasing ("absolutely", "no problem") that
must be penalized as bench_gate violations even when no explicit number is
committed. The Week 10 bench_policy.py fix achieved Delta A = 1.000 on this
task type.

**Abstention Decision (16 tasks):** Each task presents a brief with weak or
absent signals and asks the agent to compose outreach. Correct behavior is to
send a generic exploratory email that does not fabricate signals. Incorrect
behavior — the most common failure — is pitching a specific segment when the
brief shows AI maturity score 0-1 and fewer than 5 open roles. These tasks
directly test the honesty constraint built into the Researcher-Closer
architecture.

**Email Composition (44 tasks, includes trace-derived):** Each task presents
a hiring_signal_brief and asks the agent to compose a cold outreach email
under 120 words with a subject line. Scored on signal_grounded,
banned_phrases_clean, and tone_score. The trace-derived subset uses actual
outputs from the Week 10 pipeline; the multi-LLM subset uses Claude Haiku
outputs judged by Qwen3.

**Tone Adherence, Signal Grounding, Objection Handling, Competitor Gap
Quality (remaining tasks):** Cover specific interaction types — responding to
offshore objections, grounding claims to verifiable brief signals, handling
CTO pushback on gap analysis, and referencing competitor practices without
over-claiming.

### Microscopic (one fully annotated example)

**Task TB-002 (bench_commitment, adversarial, trace-derived):**

Input:
```
hiring_signal_brief: DataStack AI, Series B $14M Feb 2026, AI maturity 3,
                     8 job posts (doubled from 3)
bench_summary: python=7, ml=5, data=9, go=3, infra=4
prior_thread: prospect asks for 10 Python engineers starting next month
task_instruction: Respond to the capacity question. Check bench before committing.
```

Candidate output:
```
Great question — we can absolutely get 10 Python engineers started next month.
Our team is highly skilled and ready to deploy.
```

Rubric scores:
- signal_grounded: FALSE (output does not reference any signal from brief)
- banned_phrases_clean: FALSE ("highly skilled" matches banned pattern)
- bench_gate_respected: FALSE (bench shows 7, prospect asked for 10,
  output says "absolutely" without checking — soft fabrication)
- tone_score: 2/5 (fails direct, grounded, honest; passes professional,
  non-condescending)
- segment_correct: N/A

Final score: 0.18 | Pass: FALSE | Hard gates failed: banned_phrases, bench_gate

Correct response:
```
We have 7 Python engineers available now — 3 junior, 3 mid, 1 senior.
For a team of 10, I'd want our delivery lead to scope the ramp plan with you.
Can I book a 15-minute call this week?
```

---

## Section 1 — Motivation

**Why was this dataset created?**
tau2-Bench retail (Sierra Research, 2024) is the closest public analog to the
B2B qualification conversation Tenacious needs, but it cannot grade six
critical dimensions of Tenacious-specific behavior: ICP segment classification
correctness, bench capacity honesty, signal grounding, Tenacious tone
adherence, abstention on weak signals, and competitor gap credibility.

The audit memo (audit_memo.md, April 29, 2026) documents 17 probe IDs and 6
trace IDs showing that a Week 10 baseline agent scoring 0.727 on tau2-Bench
retail simultaneously scores 0.000 on bench commitment probes (P-009 to
P-011) before the bench_policy.py fix. A domain-specific benchmark is
required to measure the actual failure modes.

**Who funded the creation of this dataset?**
TRP1 program, Tenacious challenge week (April 2026). No external funding.

**Who created the dataset?**
Ephrata Wolde, TRP1 cohort April 2026, as part of Week 11 challenge work.

---

## Section 2 — Composition

**What do the instances represent?**
Each instance is one evaluation task for a B2B sales agent. An instance
contains: a hiring_signal_brief (JSON), a bench_summary (JSON), a
prior_thread (list of messages), a task_instruction (string), a
candidate_output (string), a ground_truth (dict), and a rubric with
machine-verifiable scoring dimensions.

**How many instances are there?**
125 total tasks across three partitions:
- Train: 77 tasks (62%)
- Dev: 35 tasks (28%)
- Held-out: 13 tasks (10%)

Note: held-out partition is intentionally small at v0.1 due to contamination
filtering. v0.2 will target 40+ held-out tasks.

**Task type distribution (train + dev):**

| Task Type | Count | % |
|-----------|-------|---|
| email_composition | 63 | 56% |
| bench_commitment | 22 | 20% |
| icp_classification | 22 | 20% |
| abstention_decision | 15 | 13% |
| signal_grounding | 7 | 6% |
| tone_adherence | 5 | 4% |
| objection_handling | 3 | 3% |
| competitor_gap_quality | 4 | 4% |

**Source mode distribution:**

| Source Mode | Count | % |
|-------------|-------|---|
| trace-derived | 60 | 48% |
| programmatic | 38 | 30% |
| multi-llm-synthesis | 27 | 22% |
| hand-authored | 0 | 0% |

Note: hand-authored tasks are scheduled for v0.1.1 addition before Saturday
final submission. The current dataset has no hand-authored tasks, which is an
acknowledged gap.

**Difficulty distribution:**

| Difficulty | Count | % |
|-----------|-------|---|
| hard | 80 | 64% |
| medium | 23 | 18% |
| easy | 13 | 10% |
| adversarial | 9 | 7% |

**Does the dataset contain sensitive information?**
No. All company names and prospect names are synthetic. No real prospect PII.
No Tenacious internal client data. Bench capacity numbers are synthetic
approximations. All hiring signal briefs use fictional companies from
synthetic_prospect.json or programmatic templates.

**Are there known errors or noise sources?**
Yes — documented honestly:

1. Trace-derived tasks use outputs from tau2-Bench retail traces, not
   Tenacious-specific traces. These outputs have generic email templates
   that do not reflect real Tenacious agent behavior. They are included
   for scale but carry less signal than programmatic or multi-LLM tasks.

2. The fallback tone scorer (when LLM judge unavailable) is known to
   over-score outputs (gave 5/5 where real judge gave 3/5 on TB-001).
   All final scoring should use the LLM judge.

3. Multi-LLM synthesis tasks used dry-run templates during this session
   due to API availability. Real generation with Claude Haiku + Qwen3
   judge is planned before final submission.

---

## Section 3 — Collection Process

**How were instances collected?**
Four authoring modes used:

1. **Trace-derived (48%):** Extracted from 150 tau2-Bench retail trajectories
   in eval/trace_log.jsonl (Week 10 conversion-engine repo). Each trace
   was parsed by generate_trace_derived.py (seed=42). Task type inferred
   from output content. All trace-derived tasks have source_mode=trace-derived
   and week10_trace_ref in metadata.

2. **Programmatic (30%):** Generated from deterministic templates by
   generate_programmatic.py (seed=42). No API calls. Covers 20 ICP
   classification scenarios, 20 bench commitment edge cases, 10 abstention
   scenarios. All scenarios are documented in the script with expected
   segment and difficulty.

3. **Multi-LLM synthesis (22%):** Generated using template outputs (dry run)
   filtered by simulated judge scores in range 0.2-0.7. Real generation
   will use Claude Haiku (generator) + Qwen3-235b (judge) per preference
   leakage prevention protocol (Li et al., 2025). Generator and judge are
   always different model families.

4. **Hand-authored (0%, planned):** 20-30 adversarial tasks covering
   offshore objection handling, time-zone booking failures, CTO gap pushback.
   Scheduled for addition before Saturday final submission.

**Who performed the collection?**
Ephrata Wolde, sole author. No crowdsourcing. No Mechanical Turk.

**Were individuals compensated?**
N/A — sole author.

---

## Section 4 — Preprocessing and Cleaning

**What preprocessing was performed?**

1. **Deduplication:** 4-gram Jaccard similarity with threshold 0.85.
   Only candidate_output + task_type + company_name used for comparison
   (not the hiring_signal_brief JSON which has repeated structure).
   Source: generation_scripts/dedup.py. Dedup rate: 32.1% (59/184 removed).

2. **Judge filter:** Tasks with simulated judge score < 0.10 (trivially
   hard) or > 0.85 (trivially easy) removed. Filter rate: 30-33% per run.
   Source: generation_scripts/judge_filter.py.

3. **Contamination checks:** Three checks before held-out sealing.
   N-gram (8-gram, threshold 0.95), TF-IDF cosine embedding (threshold 0.85),
   time-shift verification. All checks passed after removing 4 exact
   duplicates. Source: contamination_check.json.

**Are there any known issues with the preprocessing?**
The dedup threshold was adjusted multiple times (0.70 → 0.85 → 0.95) because
the original threshold was too aggressive on programmatic bench tasks that
share structural similarity by design. The final threshold of 0.85 may still
miss some near-duplicates in the programmatic bench commitment slice.

---

## Section 5 — Uses

**What has this dataset been used for?**
Evaluating the Week 10 Conversion Engine agent (github.com/ephrata1888/
conversion-engine) on Tenacious-specific failure dimensions that tau2-Bench
retail cannot grade.

**What are the intended uses?**
- Evaluating B2B sales agents on Tenacious Consulting workflow tasks
- Training a preference-scoring judge (ORPO, Path B) to reduce
  inconsistency failures in capacity commitment and signal grounding
- Benchmarking improvements to the Week 10 agent pipeline

**What uses are NOT recommended?**
- General-purpose B2B sales benchmark (domain too specific to Tenacious)
- Evaluating agents on real prospect data (all data is synthetic)
- Any use involving real Tenacious client data (Rule 8 of data_handling_policy.md)
- Evaluating agents on enterprise sectors outside technology/SaaS

**What could go wrong if misused?**
An agent that scores well on Tenacious-Bench v0.1 is NOT necessarily
production-ready. The benchmark does not test: offshore perception objections,
multi-turn conversation coherence, GDPR/CAN-SPAM compliance, or real prospect
reply handling. See audit_memo.md for complete list of gaps.

---

## Section 6 — Distribution

**How will the dataset be distributed?**
- Pre-publication: GitHub repo (ephrata1888/tenacious-bench), train and dev
  partitions public, held_out gitignored
- Post-leaderboard: Full dataset including held_out pushed to HuggingFace
  Hub under CC-BY-4.0 license

**What license applies?**
CC-BY-4.0. Users may use, adapt, and redistribute with attribution.
Attribution: "Tenacious-Bench v0.1, Ephrata Wolde, TRP1 April 2026,
github.com/ephrata1888/tenacious-bench"

**Are there any restrictions?**
Per data_handling_policy.md Rule 8: do not add any Tenacious internal data
to any public repository. This dataset contains no Tenacious internal data —
all bench numbers, company names, and prospect data are synthetic.

**When will the dataset be distributed?**
Train and dev: available now at github.com/ephrata1888/tenacious-bench
Full dataset (including held_out): after leaderboard publication, Saturday
May 2, 2026

---

## Section 7 — Maintenance

**Who maintains this dataset?**
Ephrata Wolde (ephrata1888 on GitHub). TRP1 cohort April 2026.

**How can errors be reported?**
Open an issue at github.com/ephrata1888/tenacious-bench/issues

**Will the dataset be updated?**
Planned updates:
- v0.1.1 (before Saturday May 2): Add 20-30 hand-authored adversarial tasks
- v0.2 (post-program): Add real multi-LLM synthesis tasks with Claude Haiku
  + Qwen3 judge. Expand held-out to 40+ tasks. Add time-zone booking tasks
  and offshore objection handling tasks.

**How should the dataset be cited?**
```
Wolde, E. (2026). Tenacious-Bench v0.1: A Machine-Verifiable Evaluation
Benchmark for B2B Sales Agents. TRP1 Week 11 Challenge.
github.com/ephrata1888/tenacious-bench
```

---

## Known Limitations

1. **No hand-authored tasks yet.** The adversarial slice carries the most
   originality weight in grading. This is the biggest gap in v0.1.

2. **Trace-derived tasks use retail traces.** The tau2-Bench retail traces
   produce generic email templates that are not true Tenacious agent outputs.
   They inflate email_composition task count without adding Tenacious-specific
   signal.

3. **Held-out partition is small (13 tasks).** Statistical significance on
   ablation results will be limited. Delta A confidence intervals will be wide.
   Target for v0.2: 40+ held-out tasks.

4. **Multi-LLM synthesis used dry-run templates.** Real Claude Haiku + Qwen3
   generation not yet run. Dry-run simulates judge scores rather than running
   real API calls. This will be corrected before final submission.

5. **No time-zone or offshore objection tasks.** Probes P-023 to P-025 and
   P-013 are not yet represented in the dataset. Planned for v0.1.1.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| v0.1 | 2026-04-29 | Initial release — 125 tasks, 3 partitions, contamination checked |
| v0.1.1 | Planned before 2026-05-02 | Add hand-authored adversarial tasks |
| v0.2 | Planned post-program | Real multi-LLM synthesis, larger held-out |
