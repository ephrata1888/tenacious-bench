# generation_scripts/

Scripts for authoring Tenacious-Bench v0.1 tasks.
All scripts are reproducible from a fixed seed (default: 42).

---

## Pipeline Order

```
1. generate_trace_derived.py   → raw/trace_derived.jsonl   (~50 tasks)
2. generate_programmatic.py    → raw/programmatic.jsonl    (~70 tasks)
3. generate_multi_llm.py       → raw/multi_llm.jsonl       (~100 tasks)
4. [hand-authored tasks]       → raw/hand_authored.jsonl   (~40 tasks)
5. dedup.py (merge + dedup)    → deduped/all_tasks.jsonl
6. judge_filter.py             → filtered/all_tasks.jsonl
7. partition.py                → train/ dev/ held_out/
8. contamination_check.py      → contamination_check.json
```

---

## Scripts

### generate_trace_derived.py
Extracts tasks from Week 10 trace_log.jsonl.
Each trace becomes one scored task.

```bash
python generate_trace_derived.py \
  --trace_log ../conversion-engine/eval/trace_log.jsonl \
  --output ../tenacious_bench_v0.1/raw/trace_derived.jsonl \
  --seed 42 \
  --max_tasks 60
```

If trace_log.jsonl is not found, creates synthetic traces automatically.

### generate_programmatic.py
Generates tasks from deterministic rules. No API calls.
Covers ICP classification (20), bench commitment (20), abstention (20),
signal grounding (10).

```bash
python generate_programmatic.py \
  --output ../tenacious_bench_v0.1/raw/programmatic.jsonl \
  --seed 42
```

### generate_multi_llm.py
Uses two model families (Claude Haiku + Qwen3) to avoid preference leakage.
Generator: Claude Haiku (Anthropic family)
Judge: Qwen3-235b (Alibaba family)
Keeps only tasks where judge score is 0.2-0.7.

```bash
# With API (real generation)
export OPENROUTER_API_KEY=your_key
python generate_multi_llm.py \
  --output ../tenacious_bench_v0.1/raw/multi_llm.jsonl \
  --seed 42 \
  --target 100

# Without API (dry run with templates)
python generate_multi_llm.py \
  --output ../tenacious_bench_v0.1/raw/multi_llm.jsonl \
  --seed 42 \
  --target 100 \
  --dry_run
```

### judge_filter.py
Filters tasks by scoring_evaluator.py score range.
Removes trivially easy (> 0.85) and trivially hard (< 0.10) tasks.

```bash
python judge_filter.py \
  --input ../tenacious_bench_v0.1/raw/all_tasks.jsonl \
  --output ../tenacious_bench_v0.1/filtered/all_tasks.jsonl \
  --min_score 0.10 \
  --max_score 0.85
```

### dedup.py
Removes near-duplicate tasks using 4-gram Jaccard similarity.
Threshold: 0.70 (remove if > 70% overlap).
Can also merge multiple JSONL files before dedup.

```bash
# Merge all raw files then dedup
python dedup.py \
  --merge ../tenacious_bench_v0.1/raw/trace_derived.jsonl \
          ../tenacious_bench_v0.1/raw/programmatic.jsonl \
          ../tenacious_bench_v0.1/raw/multi_llm.jsonl \
  --input ../tenacious_bench_v0.1/raw/all_merged.jsonl \
  --output ../tenacious_bench_v0.1/deduped/all_tasks.jsonl \
  --threshold 0.70 \
  --ngram_n 4
```

---

## Model Routes

| Script | Model | Family | Role |
|--------|-------|--------|------|
| generate_multi_llm.py | claude-haiku-4-5 | Anthropic | Generator |
| generate_multi_llm.py | qwen/qwen3-235b-a22b | Alibaba | Quality judge |
| judge_filter.py | qwen/qwen3-235b-a22b | Alibaba | Filter judge |
| scoring_evaluator.py | qwen/qwen3-235b-a22b | Alibaba | Tone judge |

**Preference leakage prevention:** Generator and judge are always different
model families. Never use the same model to generate and grade the same task.
Per Li et al., 2025.

---

## Logs

Each script writes a log JSON to the output directory:
- `trace_derived_log.json`
- `programmatic_log.json`
- `multi_llm_log.json`
- `judge_filter_log.json`
- `dedup_log.json`

Logs include: seed, model routes, task counts, filter rates, timestamps.

---

## Seed Policy

All scripts accept `--seed` (default: 42).
Seed is recorded in every task's metadata.generation_seed field.
Reproduce any script's output by passing the same seed.

---

## Cost Estimates

| Script | API calls | Estimated cost |
|--------|-----------|---------------|
| generate_trace_derived.py | 0 | $0 |
| generate_programmatic.py | 0 | $0 |
| generate_multi_llm.py (100 tasks) | ~200 | ~$0.15 |
| judge_filter.py (200 tasks) | ~200 | ~$0.10 |
| **Total** | | **~$0.25** |

All charges logged to cost_log.csv in repo root.
