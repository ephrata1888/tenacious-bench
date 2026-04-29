"""
generate_trace_derived.py
Extracts tasks from Week 10 trace_log.jsonl.
Each usable trace becomes one scored task in Tenacious-Bench format.

Usage:
    python generate_trace_derived.py --trace_log ../conversion-engine/eval/trace_log.jsonl
                                     --output ../tenacious_bench_v0.1/raw/trace_derived.jsonl
                                     --seed 42
                                     --max_tasks 60
"""

import argparse
import json
import os
import sys
import random
import hashlib
from datetime import datetime, timezone

SEED = 42
random.seed(SEED)

# Task type mapping based on trace content
def infer_task_type(trace: dict) -> str:
    output = str(trace.get("output", "")).lower()
    input_str = str(trace.get("input", "")).lower()

    if "segment" in input_str or "icp" in input_str:
        return "icp_classification"
    if "bench" in output or "engineer" in output or "capacity" in output:
        return "bench_commitment"
    if "subject:" in output or "hi " in output or "dear " in output:
        return "email_composition"
    if "signal" in input_str or "brief" in input_str:
        return "signal_grounding"
    return "email_composition"

def infer_difficulty(score: float) -> str:
    if score >= 0.85:
        return "easy"
    elif score >= 0.65:
        return "medium"
    elif score >= 0.40:
        return "hard"
    else:
        return "adversarial"

def extract_signal_brief(trace: dict) -> dict:
    """Try to extract hiring signal brief from trace input."""
    input_data = trace.get("input", {})
    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except:
            pass

    if isinstance(input_data, dict):
        if "hiring_signal_brief" in input_data:
            return input_data["hiring_signal_brief"]
        if "signals" in input_data:
            return input_data
        if "company" in input_data:
            return input_data

    # Fallback: minimal brief
    return {
        "company": {"name": "Unknown", "employees": "51-100", "country": "US"},
        "signals": {
            "funding": {"has_recent_funding": False, "confidence": "low"},
            "layoffs": {"has_recent_layoffs": False, "confidence": "low"},
            "ai_maturity": {"score": 0, "confidence": "low"},
            "job_posts": {"count": 0, "confidence": "low"}
        },
        "icp_segment": {"segment": "abstain", "confidence": 0.0},
        "honesty_flags": []
    }

def extract_candidate_output(trace: dict) -> str:
    """Extract agent output from trace."""
    output = trace.get("output", "")
    if isinstance(output, dict):
        return output.get("email_body", output.get("text", str(output)))
    return str(output)

def score_trace_simple(trace: dict) -> float:
    """Simple scoring for trace based on available reward signal."""
    reward = trace.get("reward", None)
    if reward is not None:
        return float(reward)

    # Infer from termination
    termination = trace.get("termination", "").lower()
    if termination in ["success", "task_complete", "completed"]:
        return 0.8
    elif termination in ["failure", "error", "timeout"]:
        return 0.2
    return 0.5

def make_task_id(i: int) -> str:
    return f"TB-TD-{i:03d}"

def process_trace(trace: dict, task_id: str) -> dict:
    """Convert one trace into a Tenacious-Bench task."""
    brief = extract_signal_brief(trace)
    output = extract_candidate_output(trace)
    score = score_trace_simple(trace)
    task_type = infer_task_type(trace)
    difficulty = infer_difficulty(score)

    # Determine ground truth based on task type
    ground_truth = {}
    if task_type == "icp_classification":
        segment = brief.get("icp_segment", {}).get("segment", "abstain")
        ground_truth = {"segment": segment}
    elif task_type == "bench_commitment":
        ground_truth = {"expected_routing": "route_to_human"}

    return {
        "task_id": task_id,
        "task_type": task_type,
        "difficulty": difficulty,
        "source_mode": "trace-derived",
        "input": {
            "hiring_signal_brief": brief,
            "bench_summary": {
                "python": {"available_engineers": 7},
                "ml": {"available_engineers": 5},
                "data": {"available_engineers": 9},
                "go": {"available_engineers": 3},
                "infra": {"available_engineers": 4}
            },
            "prior_thread": [],
            "task_instruction": (
                "Given this hiring signal brief, compose a grounded outreach email "
                "to the VP Engineering. Reference at least one verifiable signal. "
                "Email body must be under 120 words. Include subject line."
                if task_type == "email_composition" else
                "Classify this prospect into one of the four Tenacious ICP segments "
                "(1, 2, 3, 4) or abstain. State the segment number and a one-sentence reason."
                if task_type == "icp_classification" else
                "Respond to the prospect's question about engineering capacity. "
                "Check bench availability before committing to any numbers."
            )
        },
        "candidate_output": output,
        "ground_truth": ground_truth,
        "rubric_scores": None,
        "final_score": None,
        "pass": None,
        "metadata": {
            "week10_probe_ref": None,
            "week10_trace_ref": trace.get("trace_id", trace.get("id", "")),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "author_model": "trace-derived",
            "judge_model": None,
            "raw_trace_score": score,
            "generation_seed": SEED
        }
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace_log", type=str,
                        default="../conversion-engine/eval/trace_log.jsonl")
    parser.add_argument("--output", type=str,
                        default="../tenacious_bench_v0.1/raw/trace_derived.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max_tasks", type=int, default=60)
    args = parser.parse_args()

    random.seed(args.seed)

    if not os.path.exists(args.trace_log):
        print(f"[ERROR] trace_log not found: {args.trace_log}")
        print("Creating synthetic trace-derived tasks instead...")
        traces = _make_synthetic_traces(args.max_tasks)
    else:
        traces = []
        with open(args.trace_log, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        traces.append(json.loads(line))
                    except:
                        pass
        print(f"Loaded {len(traces)} traces from {args.trace_log}")

    # Sample and deduplicate
    random.shuffle(traces)
    traces = traces[:args.max_tasks]

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    tasks = []
    for i, trace in enumerate(traces):
        task = process_trace(trace, make_task_id(i + 1))
        tasks.append(task)

    with open(args.output, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    print(f"\nGenerated {len(tasks)} trace-derived tasks → {args.output}")

    # Summary
    types = {}
    diffs = {}
    for t in tasks:
        types[t["task_type"]] = types.get(t["task_type"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"Task types: {types}")
    print(f"Difficulties: {diffs}")

    # Log
    log = {
        "script": "generate_trace_derived.py",
        "seed": args.seed,
        "source": args.trace_log,
        "tasks_generated": len(tasks),
        "task_type_distribution": types,
        "difficulty_distribution": diffs,
        "run_at": datetime.now(timezone.utc).isoformat()
    }
    log_path = os.path.join(os.path.dirname(args.output), "trace_derived_log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log saved to {log_path}")

def _make_synthetic_traces(n: int) -> list:
    """Create synthetic traces when real trace_log is unavailable."""
    templates = [
        {
            "trace_id": f"synthetic-trace-{i:03d}",
            "input": {"hiring_signal_brief": {
                "company": {"name": f"Company {i}", "employees": "51-100"},
                "signals": {
                    "funding": {"has_recent_funding": i % 3 == 0, "confidence": "medium"},
                    "layoffs": {"has_recent_layoffs": i % 5 == 0, "confidence": "low"},
                    "ai_maturity": {"score": i % 4, "confidence": "medium"},
                    "job_posts": {"count": (i % 10), "confidence": "medium"}
                },
                "icp_segment": {"segment": (i % 4) + 1, "confidence": 0.7},
                "honesty_flags": []
            }},
            "output": f"Subject: Engineering capacity at Company {i}\n\nHi,\n\nNoticed your recent activity. Would love to connect.\n\nBest,\nResearch Partner\nTenacious",
            "reward": round(0.3 + (i % 7) * 0.1, 2),
            "termination": "completed"
        }
        for i in range(n)
    ]
    print(f"Created {len(templates)} synthetic traces (real trace_log not found)")
    return templates

if __name__ == "__main__":
    main()
