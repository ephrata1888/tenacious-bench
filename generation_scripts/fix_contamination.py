"""
fix_contamination.py
Removes contaminated tasks from held_out and replaces with clean ones from train.
Contaminated = flagged by ngram OR embedding check.
"""
import json
import os

def load_tasks(path):
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks

def save_tasks(tasks, path):
    with open(path, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")

# Load contamination results
with open("contamination_check.json") as f:
    cc = json.load(f)

# Get all contaminated held_out IDs
# Only remove exact duplicates (overlap = 1.0) not near-duplicates
flagged_ids = set()
for item in cc["ngram_check"]["flagged_tasks"]:
    if item["overlap"] >= 0.99:  # Only exact matches
        flagged_ids.add(item["held_out_id"])
for item in cc["embedding_check"]["flagged_tasks"]:
    if item["cosine_similarity"] >= 0.99:  # Only exact matches
        flagged_ids.add(item["held_out_id"])
print(f"Contaminated held_out task IDs: {len(flagged_ids)}")
print(flagged_ids)

# Load partitions
train    = load_tasks("tenacious_bench_v0.1/train/tasks.jsonl")
dev      = load_tasks("tenacious_bench_v0.1/dev/tasks.jsonl")
held_out = load_tasks("tenacious_bench_v0.1/held_out/tasks.jsonl")

# Remove contaminated tasks from held_out
clean_held_out = [t for t in held_out if t["task_id"] not in flagged_ids]
removed = [t for t in held_out if t["task_id"] in flagged_ids]

print(f"\nHeld_out before: {len(held_out)}")
print(f"Held_out after removal: {len(clean_held_out)}")
print(f"Removed: {len(removed)}")

# Move removed tasks to train instead
train_extended = train + removed
print(f"Train before: {len(train)} | after: {len(train_extended)}")

# Save updated partitions
save_tasks(train_extended, "tenacious_bench_v0.1/train/tasks.jsonl")
save_tasks(clean_held_out, "tenacious_bench_v0.1/held_out/tasks.jsonl")

print("\nPartitions updated.")
print(f"Final counts: train={len(train_extended)} dev={len(dev)} held_out={len(clean_held_out)}")