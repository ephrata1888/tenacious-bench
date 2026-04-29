"""
partition.py
Splits deduped tasks into train (50%), dev (30%), held_out (20%).
Stratified by source_mode and difficulty.

Usage:
    python generation_scripts\partition.py
      --input tenacious_bench_v0.1\raw\all_deduped.jsonl
      --output_dir tenacious_bench_v0.1
      --seed 42
"""

import argparse
import json
import os
import random
from datetime import datetime, timezone

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str,
                        default="tenacious_bench_v0.1/raw/all_deduped.jsonl")
    parser.add_argument("--output_dir", type=str,
                        default="tenacious_bench_v0.1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_pct", type=float, default=0.50)
    parser.add_argument("--dev_pct",   type=float, default=0.30)
    args = parser.parse_args()

    random.seed(args.seed)

    tasks = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))

    print(f"Loaded {len(tasks)} tasks")
    random.shuffle(tasks)

    # Separate trace-derived — keep out of held_out (too noisy for evaluation)
    trace_tasks = [t for t in tasks if t.get("source_mode") == "trace-derived"]
    other_tasks = [t for t in tasks if t.get("source_mode") != "trace-derived"]

    # held_out only from non-trace tasks
    n_other = len(other_tasks)
    n_held_out = max(10, int(n_other * 0.25))
    n_train_other = int(n_other * 0.50)
    n_dev_other = n_other - n_held_out - n_train_other

    held_out = other_tasks[:n_held_out]
    dev      = other_tasks[n_held_out:n_held_out + n_dev_other] + trace_tasks[:int(len(trace_tasks)*0.30)]
    train    = other_tasks[n_held_out + n_dev_other:] + trace_tasks[int(len(trace_tasks)*0.30):]

    print(f"Split: train={len(train)} dev={len(dev)} held_out={len(held_out)}")

    for split_name, split_tasks in [
        ("train", train), ("dev", dev), ("held_out", held_out)
    ]:
        split_dir = os.path.join(args.output_dir, split_name)
        os.makedirs(split_dir, exist_ok=True)
        out_path = os.path.join(split_dir, "tasks.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for task in split_tasks:
                f.write(json.dumps(task) + "\n")
        print(f"  Saved {len(split_tasks)} tasks → {out_path}")

        # Print distribution
        types = {}
        modes = {}
        diffs = {}
        for t in split_tasks:
            types[t["task_type"]] = types.get(t["task_type"], 0) + 1
            modes[t["source_mode"]] = modes.get(t["source_mode"], 0) + 1
            diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
        print(f"    types: {types}")
        print(f"    modes: {modes}")
        print(f"    diffs: {diffs}")

    # Save partition manifest
    manifest = {
        "total": n,
        "train": len(train),
        "dev": len(dev),
        "held_out": len(held_out),
        "seed": args.seed,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    manifest_path = os.path.join(args.output_dir, "partition_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {manifest_path}")

if __name__ == "__main__":
    main()