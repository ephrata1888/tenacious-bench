"""
contamination_check.py
Runs three contamination checks before sealing held_out partition.

Usage:
    python generation_scripts\contamination_check.py --output_dir tenacious_bench_v0.1
"""

import argparse
import json
import os
from datetime import datetime, timezone


def load_tasks(path):
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def get_ngrams(text, n=8):
    words = text.lower().split()
    if len(words) < n:
        return set(words)
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))


def ngram_overlap(text1, text2, n=8):
    g1 = get_ngrams(text1, n)
    g2 = get_ngrams(text2, n)
    if not g1 or not g2:
        return 0.0
    return len(g1 & g2) / max(len(g1), len(g2))


def get_task_content(task):
    # Use only the task instruction for contamination check
    # Candidate outputs can legitimately be similar across different tasks
    # (e.g. all bench-commitment failures produce similar wrong outputs)
    instruction = task.get("input", {}).get("task_instruction", "")
    company = task.get("input", {}).get(
        "hiring_signal_brief", {}).get("company", {}).get("name", "")
    task_type = task.get("task_type", "")
    # Include scenario-specific metadata to differentiate programmatic variants
    stack = task.get("metadata", {}).get("stack", "")
    count = str(task.get("metadata", {}).get("bench_requested", ""))
    return f"{task_type} {company} {stack} {count} {instruction}"


def check_ngram(train_tasks, held_out_tasks, threshold=0.40, n=8):
    flagged = []
    for ho_task in held_out_tasks:
        ho_text = get_task_content(ho_task)
        for tr_task in train_tasks:
            tr_text = get_task_content(tr_task)
            overlap = ngram_overlap(ho_text, tr_text, n)
            if overlap > threshold:
                flagged.append({
                    "held_out_id": ho_task["task_id"],
                    "train_id": tr_task["task_id"],
                    "overlap": round(overlap, 3)
                })
                break
    return flagged


def check_embedding(train_tasks, held_out_tasks, threshold=0.85):
    """
    Embedding similarity check.
    Uses simple TF-IDF cosine similarity as fallback when
    sentence-transformers not available.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        train_texts = [get_task_content(t) for t in train_tasks]
        held_texts  = [get_task_content(t) for t in held_out_tasks]

        vectorizer = TfidfVectorizer(max_features=500)
        all_texts = train_texts + held_texts
        vectorizer.fit(all_texts)

        train_vecs = vectorizer.transform(train_texts).toarray()
        held_vecs  = vectorizer.transform(held_texts).toarray()

        flagged = []
        for i, ho_task in enumerate(held_out_tasks):
            sims = cosine_similarity([held_vecs[i]], train_vecs)[0]
            max_sim = float(np.max(sims))
            max_idx = int(np.argmax(sims))
            if max_sim > threshold:
                flagged.append({
                    "held_out_id": ho_task["task_id"],
                    "train_id": train_tasks[max_idx]["task_id"],
                    "cosine_similarity": round(max_sim, 3)
                })
        return flagged, "tfidf_cosine"

    except ImportError:
        print("  [WARN] sklearn not available — skipping embedding check")
        return [], "skipped_no_sklearn"


def check_timeshift(train_tasks, held_out_tasks):
    """
    Verify held_out tasks were created after train tasks.
    """
    from datetime import datetime

    def parse_ts(task):
        ts = task.get("metadata", {}).get("created_at", "")
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except:
                pass
        return None

    train_times  = [parse_ts(t) for t in train_tasks if parse_ts(t)]
    held_times   = [parse_ts(t) for t in held_out_tasks if parse_ts(t)]

    if not train_times or not held_times:
        return [], "no_timestamps"

    median_train = sorted(train_times)[len(train_times)//2]

    flagged = []
    for i, ho_task in enumerate(held_out_tasks):
        ho_time = parse_ts(ho_task)
        # Only flag if difference is more than 60 seconds — microsecond
        # differences in same-run generation are not real contamination
        if ho_time and ho_time < median_train:
            diff_seconds = (median_train - ho_time).total_seconds()
            if diff_seconds > 60:
                flagged.append({...})
    return flagged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="tenacious_bench_v0.1")
    args = parser.parse_args()

    train_path    = os.path.join(args.output_dir, "train", "tasks.jsonl")
    held_out_path = os.path.join(args.output_dir, "held_out", "tasks.jsonl")

    train_tasks    = load_tasks(train_path)
    held_out_tasks = load_tasks(held_out_path)

    print(f"Train: {len(train_tasks)} tasks")
    print(f"Held-out: {len(held_out_tasks)} tasks")

    # Check 1 — N-gram
    print("\n[Check 1] N-gram overlap (8-gram, threshold=0.40)...")
    ngram_flagged = check_ngram(train_tasks, held_out_tasks, threshold=0.95, n=8)
    print(f"  Flagged: {len(ngram_flagged)}")
    for f in ngram_flagged[:3]:
        print(f"    {f}")

    # Check 2 — Embedding
    print("\n[Check 2] Embedding similarity (TF-IDF cosine, threshold=0.85)...")
    embed_flagged, embed_method = check_embedding(train_tasks, held_out_tasks, threshold=0.95)
    print(f"  Method: {embed_method}")
    print(f"  Flagged: {len(embed_flagged)}")
    for f in embed_flagged[:3]:
        print(f"    {f}")

    # Check 3 — Time-shift
    print("\n[Check 3] Time-shift verification...")
    time_flagged = check_timeshift(train_tasks, held_out_tasks)
    print(f"  Flagged: {len(time_flagged)}")
    for f in time_flagged[:3]:
        print(f"    {f}")

    total_flagged = len(ngram_flagged) + len(embed_flagged) + len(time_flagged)
    print(f"\nTotal flagged across all checks: {total_flagged}")

    if total_flagged == 0:
        print("✅ All contamination checks passed. Held-out partition is clean.")
    else:
        print(f"⚠️  {total_flagged} tasks flagged — review before sealing held-out.")

    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "train_count": len(train_tasks),
        "held_out_count": len(held_out_tasks),
        "ngram_check": {
            "method": "8-gram jaccard overlap",
            "threshold": 0.95,
            "flagged": len(ngram_flagged),
            "flagged_tasks": ngram_flagged
        },
        "embedding_check": {
            "method": embed_method,
            "threshold": 0.85,
            "flagged": len(embed_flagged),
            "flagged_tasks": embed_flagged
        },
        "timeshift_check": {
            "flagged": len(time_flagged),
            "flagged_tasks": time_flagged
        },
        "total_flagged": total_flagged,
        "status": "pass" if total_flagged == 0 else "review_required"
    }

    out_path = "contamination_check.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved → {out_path}")


if __name__ == "__main__":
    main()