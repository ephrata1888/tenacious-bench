\# Synthesis Memo: Gebru et al. (2021) + Pushkarna et al. (FAccT 2022)

\# Author: Ephrata Wolde | TRP1 Week 11



\## Key Takeaway from Gebru

The seven sections exist to answer one question a downstream user

needs answered before trusting a dataset: "Should I use this, and

for what?" The most important sections are Uses (what it's NOT for)

and Limitations (what you know is wrong). Most dataset papers skip

both.



\## Key Takeaway from Pushkarna

Layered detail solves the tension between accessibility and depth.

The telescopic summary (2-3 sentences) lets a practitioner decide

in 30 seconds whether the dataset is relevant. The microscopic

annotated example gives a researcher enough to replicate the rubric.

Both are needed — one without the other fails a different audience.



\## How Applied in datasheet.md

All seven Gebru sections completed with non-stub content.

Pushkarna layered detail implemented:

\- Telescopic: 3-sentence opening summary

\- Periscopic: one paragraph per task type explaining what it tests

\- Microscopic: TB-002 fully annotated with input, output, rubric scores,

&#x20; correct response example



The Uses section explicitly lists what the dataset is NOT for —

general-purpose B2B benchmarking, real prospect data, non-SaaS sectors.

This follows Gebru's strongest recommendation: "document the contexts

in which a dataset should NOT be used, because practitioners will use

datasets in ways the creators never intended."



\## One Disagreement



Gebru recommends documenting "who funded the creation" as a proxy

for potential bias. For Tenacious-Bench, this section is less

informative than Gebru assumes — the funder (TRP1 program) and the

creator (Ephrata Wolde) have aligned incentives to make the benchmark

as honest as possible, because grading rewards honest failure

disclosure over inflated metrics.



The more important bias disclosure for this dataset is not funding

but the data construction method: trace-derived tasks use outputs

from a Week 10 agent that was specifically trained to avoid banned

phrases and check bench capacity. This means the "rejected" outputs

in the dataset may be systematically less bad than real-world agent

failures. A benchmark built from a well-behaved agent's traces

underestimates the severity of real failures.



This is documented in datasheet.md Section 4 under known limitations

but deserves emphasis: the contamination we should worry about most

is not n-gram overlap between partitions — it is semantic contamination

from using a corrected agent's outputs as the basis for training data.

