\# Tenacious-Bench v0.1



\*\*A machine-verifiable evaluation benchmark for B2B sales agents

operating in the Tenacious Consulting and Outsourcing workflow.\*\*



TRP1 Week 11 Challenge · Ephrata Wolde · April 2026



\---



\## Why This Exists



tau2-Bench retail cannot grade six critical dimensions of Tenacious-specific

agent behavior: ICP segment classification, bench capacity honesty, signal

grounding, tone adherence, abstention on weak signals, and competitor gap

credibility. A baseline agent scoring 0.727 on tau2-Bench retail scored 0.000

on bench commitment probes before the bench\_policy.py fix (Delta A = 1.000,

p = 0.000004). This benchmark measures what actually matters.



See `audit\_memo.md` for the full evidence.



\---



\## Quick Start



```bash

git clone https://github.com/ephrata1888/tenacious-bench.git

cd tenacious-bench

pip install requests python-dotenv scikit-learn

export OPENROUTER\_API\_KEY=your\_key



\# Score all three example tasks

python scoring\_evaluator.py --schema schema.json --all



\# Score a single task

python scoring\_evaluator.py --schema schema.json --task\_id TB-001



\# Generate programmatic tasks

python generation\_scripts/generate\_programmatic.py \\

&#x20; --output tenacious\_bench\_v0.1/raw/programmatic.jsonl --seed 42

```



Expected output on TB-002 (bench over-commitment):

