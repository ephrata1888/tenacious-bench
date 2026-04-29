# audit_memo.md
# Tenacious-Bench v0.1 — Audit Memo
# Author: Ephrata Wolde | TRP1 Week 11 | April 29, 2026
# Word count: ~590

## What tau2-Bench Retail Fails to Grade for Tenacious

tau2-Bench retail measures whether an agent can complete transactions in a
simulated e-commerce environment — returning orders, modifying addresses,
processing exchanges. It produces a clean pass@1 signal on dual-control
coordination and policy adherence. For Tenacious, it is the wrong instrument.
The gap is not marginal. It is structural.

### The Central Gap: Research-Grounded Outreach Cannot Be Scored by Retail

A Tenacious outreach email is correct only if it leads with a verifiable
public signal from the hiring_signal_brief. tau2-Bench retail has no concept
of a hiring signal brief. It has no concept of funding windows, layoff data,
AI maturity scores, or competitor gap analysis. An agent that fabricates a
$20M Series B raise that does not exist in the Crunchbase record would score
identically to one that cites the real raise — tau2-Bench retail cannot
distinguish them.

Week 10 evidence: traces 485a3a8d, 54972c5a, 49d1fbfc, de389db2, and
b475ca98 all show the pipeline correctly grounding the email opening in the
DataStack AI Series B (February 2026, $14M, announced_on field in
crunchbase_sample.csv). A benchmark that cannot verify this grounding cannot
grade the most important quality dimension of the system.

### Gap 1: Signal Grounding Verification (Probes P-005 to P-008)

tau2-Bench retail grades task completion, not claim verifiability. Probes
P-005 through P-008 (signal over-claiming category) expose the failure:
when the agent is given a brief with low-confidence signals, does it soften
its language or does it assert the same claims as with high-confidence
signals? Trigger rate on P-005 was 0.65 in our ablation traces. Retail
benchmark cannot detect this failure because it has no signal brief input
and no confidence-aware phrasing rubric.

### Gap 2: Bench Capacity Honesty (Probes P-009 to P-011)

tau2-Bench retail has no capacity constraint. An agent can promise any
quantity of any resource with zero penalty. Probes P-009, P-010, and P-011
test whether the agent checks bench_summary.json before committing to
engineer counts. Bench shows 7 Python engineers available
(seed/bench_summary.json, as_of 2026-04-21). A prospect asking for 10
Python engineers must receive a route-to-human, not a fabricated commitment.

Week 10 baseline pass rate on P-009 to P-011 without bench_policy.py: 0.000.
With the hard constraint: 1.000. Delta A = 1.000, p = 0.000004
(eval/ablation_results.json). tau2-Bench retail would have scored the
baseline agent identically to the fixed agent because retail has no
bench-feasibility check. This is the highest-ROI gap.

### Gap 3: ICP Segment Classification Correctness (Probes P-001 to P-004)

tau2-Bench retail has no firmographic classifier. Probes P-001 through P-004
test whether the agent correctly resolves four-way segment ambiguity: a
company with both recent funding AND recent layoffs must be classified as
Segment 2 (cost pressure dominates), not Segment 1 (fresh budget). Probe
P-004 specifically tests the off-by-one error at the 180-day funding window
boundary. No retail benchmark can grade this because it has no ICP definition,
no priority rules, and no abstention path for low-confidence classification.

### Gap 4: Tenacious Tone Adherence (Probes P-012 to P-014)

The Tenacious style guide defines five tone markers: direct, grounded,
honest, professional, humility. It also defines 23 banned phrases including
"aggressive hiring," "offshore team," "cost savings," and "touching base."
tau2-Bench retail grades task completion in a retail voice — it has no
mechanism to score whether an output contains banned phrases or whether it
drifts from a specific brand voice across a multi-turn conversation.
Probe P-012 tests whether tone drifts after a prospect pushes back. Probe
P-013 tests whether offshore language appears in response to a pricing
question. Neither has any analog in the retail benchmark.

### Gap 5: Abstention on Weak Signal (Probes P-001, P-005)

When no qualifying signal fires — no recent funding, no layoffs, no
leadership change, AI maturity score below 2, fewer than 5 open roles —
the correct agent behavior is to abstain from a segment-specific pitch and
send a generic exploratory email. tau2-Bench retail never tests abstention.
Every task has a correct completion. A benchmark that never rewards "I should
not do this" cannot grade the most important safety property of a sales agent:
knowing when not to pitch.

### Gap 6: Competitor Gap Credibility (Probes P-029 to P-031)

The competitor gap brief compares a prospect against top-quartile sector
peers. Probe P-029 tests whether the agent uses peers more than 10x larger
than the prospect (not credible). Probe P-031 tests whether the agent
handles CTO pushback on the gap claim ("we already know about that and have
a plan"). tau2-Bench retail has no multi-party research brief, no peer
comparison, and no pushback handling scenario. Gap credibility cannot be
graded without a Tenacious-specific benchmark.

### Conclusion

The six gaps above are not edge cases. They are the core quality dimensions
of the Tenacious Conversion Engine. A system that scores 0.727 on tau2-Bench
retail (seed/score_log.json, instructor shared baseline) may still fabricate
capacity commitments (P-009 baseline: 0.000), misclassify ICP segments
(P-001 to P-004), and use banned phrases (P-012 to P-014). Tenacious-Bench
v0.1 is built to grade exactly these dimensions with machine-verifiable
rubrics, making the evaluation instrument specific to the business risk.

## Probe IDs Referenced
P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008,
P-009, P-010, P-011, P-012, P-013, P-014, P-029, P-030, P-031

## Trace IDs Referenced
485a3a8d16d463979a51173f9c5d9fe9 (run 1, eval/latency_results.json)
54972c5aec996dc90508445782e2729c (run 2, eval/latency_results.json)
49d1fbfc820d75386bcba618ba6624ea (run 3, eval/latency_results.json)
de389db237ff84763959c34ff625e6ff (run 4, eval/latency_results.json)
b475ca98caee79d27953fc432b84286c (run 5, eval/latency_results.json)
3495fae7aff0e2a42f96b903c6f8e2d0 (enrichment pipeline, Langfuse)
