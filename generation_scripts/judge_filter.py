"""
judge_filter.py
Runs scoring_evaluator.py on all tasks in a JSONL file.
Removes tasks where judge confidence < 0.4 (too ambiguous)
or > 0.95 (trivially easy, no signal).
Keeps only diagnostically useful tasks.

Usage:
    python judge_filter.py --input ../tenacious_bench_v0.1/raw/multi_llm.jsonl
                           --output ../tenacious_bench_v0.1/filtered/multi_llm.jsonl
                           --min_score 0.1
                           --max_score 0.85
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_filter(input_path: str, output_path: str,
               min_score: float = 0.1, max_score: float = 0.85) -> dict:
    """Filter tasks by judge score range."""

    try:
        from scoring_evaluator import score_task
        use_evaluator = True
    except ImportError:
        print("[WARN] scoring_evaluator.py not found — using metadata judge_score only")
        use_evaluator = False

    tasks = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))

    print(f"Loaded {len(tasks)} tasks from {input_path}")

    kept = []
    removed_too_easy = []
    removed_too_hard = []
    errors = []

    for task in tasks:
        task_id = task.get("task_id", "unknown")

        # Use existing judge_score from metadata if available
        meta_score = task.get("metadata", {}).get("judge_score")

        if meta_score is not None and not use_evaluator:
            score = meta_score
        elif use_evaluator:
            try:
                result = score_task(task)
                score = result["final_score"]
                # Update task with actual scores
                task["rubric_scores"] = result["dimension_scores"]
                task["final_score"] = result["final_score"]
                task["pass"] = result["pass"]
            except Exception as e:
                print(f"  [ERROR] {task_id}: {e}")
                errors.append(task_id)
                continue
        else:
            score = 0.5  # Default if no info

        if score > max_score:
            removed_too_easy.append(task_id)
            print(f"  REMOVED (too easy, score={score:.2f}): {task_id}")
        elif score < min_score:
            removed_too_hard.append(task_id)
            print(f"  REMOVED (too hard, score={score:.2f}): {task_id}")
        else:
            kept.append(task)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for task in kept:
            f.write(json.dumps(task) + "\n")

    stats = {
        "input_count": len(tasks),
        "kept_count": len(kept),
        "removed_too_easy": len(removed_too_easy),
        "removed_too_hard": len(removed_too_hard),
        "errors": len(errors),
        "filter_range": [min_score, max_score],
        "keep_rate": round(len(kept) / max(1, len(tasks)), 3),
        "run_at": datetime.now(timezone.utc).isoformat()
    }

    print(f"\nFilter complete:")
    print(f"  Input: {len(tasks)} | Kept: {len(kept)} | "
          f"Too easy: {len(removed_too_easy)} | Too hard: {len(removed_too_hard)}")
    print(f"  Keep rate: {stats['keep_rate']:.1%}")

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--min_score", type=float, default=0.1)
    parser.add_argument("--max_score", type=float, default=0.85)
    parser.add_argument("--save_log", type=str, default=None)
    args = parser.parse_args()

    stats = run_filter(args.input, args.output, args.min_score, args.max_score)

    log_path = args.save_log or os.path.join(
        os.path.dirname(args.output), "judge_filter_log.json"
    )

    existing_log = []
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                existing_log = json.load(f)
            if not isinstance(existing_log, list):
                existing_log = [existing_log]
        except:
            pass

    existing_log.append({"input": args.input, **stats})
    with open(log_path, "w") as f:
        json.dump(existing_log, f, indent=2)
    print(f"Log saved to {log_path}")

if __name__ == "__main__":
    main()
