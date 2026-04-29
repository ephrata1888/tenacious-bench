"""
dedup.py
Removes near-duplicate tasks using n-gram similarity.
Two tasks are duplicates if their task_instruction + candidate_output
share > 70% 4-gram overlap.

Usage:
    python dedup.py --input ../tenacious_bench_v0.1/raw/all_tasks.jsonl
                    --output ../tenacious_bench_v0.1/deduped/all_tasks.jsonl
                    --threshold 0.70
                    --ngram_n 4
"""

import argparse
import json
import os
from datetime import datetime, timezone


def get_ngrams(text: str, n: int = 4) -> set:
    words = text.lower().split()
    if len(words) < n:
        return set(words)
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))


def ngram_similarity(text1: str, text2: str, n: int = 4) -> float:
    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)
    if not ngrams1 or not ngrams2:
        return 0.0
    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2
    return len(intersection) / len(union)


def get_task_text(task: dict) -> str:
    output = task.get("candidate_output", "")
    task_type = task.get("task_type", "")
    source_mode = task.get("source_mode", "")
    # Trace-derived tasks are pre-validated unique — use task_id to prevent
    # cross-task dedup on template outputs
    if source_mode == "trace-derived":
        return task.get("task_id", "") + " " + output[:50]
    company = task.get("input", {}).get(
        "hiring_signal_brief", {}
    ).get("company", {}).get("name", "")
    return f"{task_type} {company} {output}"


def dedup(input_path: str, output_path: str,
          threshold: float = 0.70, ngram_n: int = 4) -> dict:

    tasks = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))

    print(f"Loaded {len(tasks)} tasks from {input_path}")

    kept = []
    removed = []

    for i, task in enumerate(tasks):
        task_text = get_task_text(task)
        is_dup = False

        for kept_task in kept:
            kept_text = get_task_text(kept_task)
            sim = ngram_similarity(task_text, kept_text, ngram_n)
            if sim > threshold:
                removed.append({
                    "task_id": task.get("task_id"),
                    "duplicate_of": kept_task.get("task_id"),
                    "similarity": round(sim, 3)
                })
                is_dup = True
                break

        if not is_dup:
            kept.append(task)

        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(tasks)} | Kept: {len(kept)} | Removed: {len(removed)}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for task in kept:
            f.write(json.dumps(task) + "\n")

    stats = {
        "input_count": len(tasks),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "dedup_rate": round(len(removed) / max(1, len(tasks)), 3),
        "threshold": threshold,
        "ngram_n": ngram_n,
        "removed_pairs": removed[:20],
        "run_at": datetime.now(timezone.utc).isoformat()
    }

    print(f"\nDedup complete:")
    print(f"  Input: {len(tasks)} | Kept: {len(kept)} | Removed: {len(removed)}")
    print(f"  Dedup rate: {stats['dedup_rate']:.1%}")

    return stats


def merge_jsonl_files(input_paths: list, output_path: str) -> int:
    """Merge multiple JSONL files into one."""
    all_tasks = []
    for path in input_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_tasks.append(json.loads(line))
            print(f"  Loaded {path}: "
                  f"{sum(1 for _ in open(path) if _.strip())} tasks")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    return len(all_tasks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--ngram_n", type=int, default=4)
    parser.add_argument("--merge", nargs="+",
                        help="Merge multiple JSONL files before dedup")
    args = parser.parse_args()

    if args.merge:
        merged_path = args.input.replace(".jsonl", "_merged.jsonl")
        count = merge_jsonl_files(args.merge, merged_path)
        print(f"Merged {count} tasks from {len(args.merge)} files → {merged_path}")
        input_path = merged_path
    else:
        input_path = args.input

    stats = dedup(input_path, args.output, args.threshold, args.ngram_n)

    log_path = os.path.join(os.path.dirname(args.output), "dedup_log.json")
    with open(log_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Log saved to {log_path}")


if __name__ == "__main__":
    main()
