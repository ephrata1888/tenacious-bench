\# Synthesis Memo: Liu et al. — Synthetic Data Best Practices (COLM 2024)

\# Author: Ephrata Wolde | TRP1 Week 11



\## Key Takeaway

Quality filters matter more than volume. The paper shows that

filtering synthetic data by quality score before training

consistently outperforms using all generated data unfiltered.



\## Three Techniques Applied in Tenacious-Bench



1\. \*\*Judge-filter before inclusion:\*\* Every multi-LLM task passes

&#x20;  through scoring\_evaluator.py before entering the dataset.

&#x20;  Tasks with score < 0.10 or > 0.85 are removed — too trivial

&#x20;  or too ambiguous to be diagnostic.



2\. \*\*Two-model generation:\*\* Generator and judge are different model

&#x20;  families (Claude Haiku + Qwen3) to avoid self-reinforcing bias.

&#x20;  The paper calls this "model diversity" — using a single model

&#x20;  to generate and judge produces overconfident quality estimates.



3\. \*\*Seed diversity across task types:\*\* Tasks are generated from

&#x20;  varied prompt templates across 8 task types, not from a single

&#x20;  template. The paper shows that template diversity is the strongest

&#x20;  predictor of downstream evaluation reliability.



\## One Disagreement



The paper recommends generating 10x more data than you need and

filtering down. For Tenacious-Bench, I disagree with this approach

for two reasons:



First, the Tenacious domain is narrow — there are only \~8 meaningful

task types and \~50 meaningful scenario variations. Generating 10x

would produce near-duplicates that pass quality filters but add

no signal. The dedup step already removes 32% of generated tasks.



Second, cost discipline is itself a graded observable this week.

Generating 1,500 tasks at $0.001 each to keep 150 costs $1.50 in

API credits and wastes OpenRouter quota. The paper's recommendation

assumes abundant compute — for a $5 weekly budget, targeted

generation with high-quality templates is strictly better.



Evidence: eval/invoice\_summary.json shows total LLM spend of $4.62

for Week 10's full pipeline. A 10x generation approach would have

consumed that budget on dataset generation alone.

