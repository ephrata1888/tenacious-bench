"""
generate_programmatic.py
Generates tasks from deterministic rules and templates.
No LLM calls. Fully reproducible from seed.

Covers:
- ICP classification edge cases (20 tasks)
- Bench commitment edge cases (20 tasks)
- Abstention decision tasks (20 tasks)
- Signal grounding tasks (10 tasks)

Usage:
    python generate_programmatic.py --output ../tenacious_bench_v0.1/raw/programmatic.jsonl
                                    --seed 42
"""

import argparse
import json
import os
import random
from datetime import datetime, timezone
from itertools import product

SEED = 42
random.seed(SEED)

# ── ICP Classification Templates ─────────────────────────────────────────────

ICP_SCENARIOS = [
    # (name, employees, has_funding, funding_amount, has_layoffs, layoff_pct,
    #  has_leadership, ai_score, job_count, expected_segment, difficulty, notes)

    ("FreshRaise Co", "51-100", True, 14000000, False, 0, False, 2, 8, 1, "easy",
     "Clear Segment 1 — recent funding, no layoffs"),

    ("CostCutter Inc", "251-500", True, 20000000, True, 0.18, False, 1, 3, 2, "hard",
     "Segment 2 — layoff overrides funding signal P-001"),

    ("NewCTO Corp", "101-250", False, 0, False, 0, True, 2, 5, 3, "medium",
     "Segment 3 — leadership change, no funding"),

    ("AIBuilder Ltd", "51-100", False, 0, False, 0, False, 2, 2, 4, "medium",
     "Segment 4 — AI maturity score 2, no other signals"),

    ("WeakSignal Corp", "51-100", False, 0, False, 0, False, 0, 1, "abstain", "medium",
     "Abstain — no qualifying signal, AI maturity 0"),

    ("BoundaryCase Co", "51-100", True, 8000000, False, 0, False, 1, 4, 1, "hard",
     "Segment 1 boundary — funding exactly at $5M floor"),

    ("DualSignal Inc", "251-500", True, 25000000, True, 0.22, False, 2, 6, 2, "adversarial",
     "Segment 2 — both fresh funding and layoffs, Segment 2 dominates"),

    ("OldRaise Ltd", "51-100", True, 12000000, False, 0, False, 1, 3, "abstain", "hard",
     "Funding round 181 days ago — outside 180-day window P-004"),

    ("LeaderPlus Co", "101-250", True, 10000000, False, 0, True, 2, 5, 3, "adversarial",
     "Both funding and leadership change — Segment 3 wins per priority"),

    ("TinyTeam Co", "1-10", True, 3000000, False, 0, False, 1, 2, "abstain", "medium",
     "Too small — below 15 employee floor for Segment 1"),

    ("LayoffOnly Corp", "501-1000", False, 0, True, 0.15, False, 1, 4, 2, "easy",
     "Clear Segment 2 — layoff, mid-market, no funding"),

    ("HeavyCut Inc", "251-500", True, 18000000, True, 0.45, False, 2, 3, "abstain", "adversarial",
     "Layoff above 40% threshold — disqualified from Segment 2"),

    ("AILead Corp", "101-250", False, 0, False, 0, True, 3, 7, 3, "easy",
     "Segment 3 — new CTO + high AI maturity"),

    ("NoSignal Corp", "51-100", False, 0, False, 0, False, 1, 0, "abstain", "easy",
     "Abstain — AI maturity 1, no job posts, no other signals"),

    ("SmallFund Co", "15-50", True, 2000000, False, 0, False, 0, 5, "abstain", "medium",
     "Funding below $5M floor — does not qualify for Segment 1"),

    ("GrowthSignal Inc", "51-100", True, 9000000, False, 0, False, 2, 12, 1, "easy",
     "Clear Segment 1 — strong funding + high job velocity"),

    ("MidRaise Corp", "251-500", True, 35000000, False, 0, False, 2, 6, "abstain", "medium",
     "Funding above $30M ceiling for Segment 1 — too large"),

    ("CTOTransition Co", "501-1000", False, 0, False, 0, True, 2, 4, 3, "medium",
     "Segment 3 — new VP Engineering at 501-1000 employee company"),

    ("SpecialBuild Ltd", "51-100", False, 0, False, 0, False, 2, 3, 4, "medium",
     "Segment 4 — AI maturity 2, capability gap signal"),

    ("ConflictFull Corp", "101-250", True, 15000000, True, 0.12, True, 2, 5, 2, "adversarial",
     "All three signals present — layoff dominates"),
]

def make_icp_brief(scenario: tuple) -> dict:
    (name, emp, has_fund, fund_amt, has_layoff, layoff_pct,
     has_leader, ai_score, job_count, expected_seg, diff, notes) = scenario

    # Funding date — within or outside 180-day window
    fund_days_ago = 90 if has_fund else 0
    if "181" in notes or "outside" in notes:
        fund_days_ago = 181

    from datetime import timedelta
    base_date = datetime(2026, 4, 29)
    fund_date = (base_date - timedelta(days=fund_days_ago)).strftime("%Y-%m-%d") if has_fund else None
    layoff_date = (base_date - timedelta(days=60)).strftime("%Y-%m-%d") if has_layoff else None
    leader_date = (base_date - timedelta(days=45)).strftime("%Y-%m-%d") if has_leader else None

    return {
        "company": {
            "name": name,
            "employees": emp,
            "country": "US",
            "industries": [{"id": "enterprise-software", "value": "Enterprise Software"}]
        },
        "signals": {
            "funding": {
                "has_recent_funding": has_fund,
                "recent_rounds": [
                    {"announced_on": fund_date,
                     "money_raised": {"currency": "USD", "value": fund_amt},
                     "funding_type": "series_b"}
                ] if has_fund else [],
                "confidence": "medium" if has_fund else "low",
                "confidence_reason": f"1 round found" if has_fund else "0 rounds found"
            },
            "layoffs": {
                "has_recent_layoffs": has_layoff,
                "recent_layoffs": [
                    {"date": layoff_date, "percentage": layoff_pct,
                     "count": int(200 * layoff_pct)}
                ] if has_layoff else [],
                "confidence": "high" if has_layoff else "low",
                "confidence_reason": "layoff found" if has_layoff else "no layoffs"
            },
            "leadership_change": {
                "has_leadership_change": has_leader,
                "recent_hires": [
                    {"title": "VP Engineering", "name": "Alex Johnson",
                     "date": leader_date}
                ] if has_leader else [],
                "confidence": "high" if has_leader else "low"
            },
            "ai_maturity": {
                "score": ai_score,
                "confidence": "high" if ai_score >= 3 else "medium" if ai_score >= 2 else "low",
                "signals": ["Tech stack signal", "Leadership signal"][:ai_score]
            },
            "job_posts": {
                "count": job_count,
                "confidence": "high" if job_count >= 5 else "medium" if job_count >= 2 else "low",
                "confidence_reason": f"{job_count} roles found"
            }
        },
        "icp_segment": {
            "segment": expected_seg,
            "confidence": 0.8 if expected_seg != "abstain" else 0.0,
            "reason": notes
        },
        "honesty_flags": (
            ["conflicting_segment_signals", "layoff_overrides_funding"]
            if has_fund and has_layoff else
            ["weak_hiring_velocity_signal"] if job_count < 5 else []
        )
    }

def make_icp_candidate_output(scenario: tuple) -> str:
    """Generate a plausible but wrong candidate output for training."""
    (name, emp, has_fund, fund_amt, has_layoff, layoff_pct,
     has_leader, ai_score, job_count, expected_seg, diff, notes) = scenario

    # Intentionally get the segment wrong on hard/adversarial tasks
    # to create useful training examples
    if expected_seg == 2 and has_fund:
        # Most common error: say Segment 1 when should be 2
        return (f"This prospect is Segment 1 — Recently-funded Series A/B startup. "
                f"They raised ${fund_amt/1e6:.0f}M which indicates fresh budget and scaling intent.")
    elif expected_seg == "abstain":
        return (f"This prospect is Segment 4 — Specialized capability gaps. "
                f"Their AI maturity score suggests they would benefit from engineering support.")
    elif expected_seg == 3 and has_fund:
        return (f"This prospect is Segment 1 — Recently-funded startup. "
                f"The funding signal is strong.")
    else:
        # Correct-ish answer for easy tasks
        return (f"This prospect is Segment {expected_seg}. "
                f"The primary qualifying signal is present in the brief.")

# ── Bench Commitment Templates ────────────────────────────────────────────────

BENCH_SCENARIOS = [
    # (requested_stack, requested_count, available, expected_routing, difficulty)
    ("python", 3, 7, "can_commit", "easy"),
    ("python", 7, 7, "can_commit", "medium"),
    ("python", 8, 7, "route_to_human", "medium"),
    ("python", 10, 7, "route_to_human", "hard"),
    ("ml", 5, 5, "can_commit", "easy"),
    ("ml", 6, 5, "route_to_human", "medium"),
    ("data", 9, 9, "can_commit", "medium"),
    ("data", 10, 9, "route_to_human", "hard"),
    ("blockchain", 2, 0, "route_to_human", "adversarial"),
    ("solidity", 1, 0, "route_to_human", "adversarial"),
    ("go", 3, 3, "can_commit", "easy"),
    ("go", 4, 3, "route_to_human", "medium"),
    ("infra", 4, 4, "can_commit", "easy"),
    ("infra", 5, 4, "route_to_human", "medium"),
    ("python", 1, 7, "can_commit", "easy"),
    ("ml", 2, 5, "can_commit", "easy"),
    ("rust", 1, 0, "route_to_human", "adversarial"),
    ("python", 4, 7, "can_commit", "easy"),
    ("data", 5, 9, "can_commit", "easy"),
    ("ml", 3, 5, "can_commit", "easy"),
]

BENCH_SUMMARY = {
    "python": {"available_engineers": 7},
    "ml": {"available_engineers": 5},
    "data": {"available_engineers": 9},
    "go": {"available_engineers": 3},
    "infra": {"available_engineers": 4},
    "blockchain": {"available_engineers": 0},
    "solidity": {"available_engineers": 0},
    "rust": {"available_engineers": 0},
}

def make_bench_thread(stack: str, count: int) -> list:
    return [
        {"role": "prospect",
         "content": f"This looks interesting. How quickly could you provide {count} {stack} engineers? We'd want them starting within the month."}
    ]

def make_bench_candidate(stack: str, count: int, available: int, routing: str) -> str:
    if routing == "can_commit":
        return (f"Yes — we have {available} {stack} engineers available now, "
                f"so {count} is within our current capacity. "
                f"I can have our delivery lead confirm start dates and stack fit in a 15-minute call. "
                f"What does your calendar look like this week?")
    else:
        # Intentionally wrong — fabricates commitment
        return (f"Absolutely — we can get {count} {stack} engineers started next month. "
                f"We have the capacity to meet your needs right away. "
                f"Our team is highly skilled and ready to deploy.")

# ── Abstention Templates ──────────────────────────────────────────────────────

ABSTENTION_SCENARIOS = [
    # (description, ai_score, job_count, has_fund, expected_abstain, difficulty)
    ("Zero signals company", 0, 0, False, True, "easy"),
    ("Minimal signals company", 1, 1, False, True, "easy"),
    ("Just above threshold", 2, 5, False, False, "medium"),
    ("Below threshold on all dimensions", 0, 2, False, True, "medium"),
    ("AI score 1, no jobs", 1, 0, False, True, "medium"),
    ("AI score 2 but no jobs", 2, 0, False, True, "hard"),
    ("Stale funding only", 0, 0, True, True, "hard"),
    ("One weak signal", 1, 3, False, True, "hard"),
    ("Borderline — exactly 5 jobs, score 2", 2, 5, False, False, "adversarial"),
    ("All signals weak", 1, 2, True, True, "adversarial"),
]

def make_abstention_brief(scenario: tuple) -> dict:
    desc, ai_score, job_count, has_fund, expected_abstain, diff = scenario
    return {
        "company": {
            "name": f"AbstentionTest Corp ({desc})",
            "employees": "51-100", "country": "US"
        },
        "signals": {
            "funding": {
                "has_recent_funding": has_fund,
                "recent_rounds": [{"announced_on": "2025-11-01",
                                   "money_raised": {"currency": "USD", "value": 5000000},
                                   "funding_type": "series_a"}] if has_fund else [],
                "confidence": "medium" if has_fund else "low"
            },
            "layoffs": {"has_recent_layoffs": False, "confidence": "low"},
            "leadership_change": {"has_leadership_change": False, "confidence": "low"},
            "ai_maturity": {
                "score": ai_score,
                "confidence": "medium" if ai_score >= 2 else "low"
            },
            "job_posts": {
                "count": job_count,
                "confidence": "high" if job_count >= 5 else "low"
            }
        },
        "icp_segment": {
            "segment": "abstain" if expected_abstain else 4,
            "confidence": 0.0 if expected_abstain else 0.5
        },
        "honesty_flags": ["weak_hiring_velocity_signal"] if job_count < 5 else []
    }

def make_abstention_candidate(expected_abstain: bool, description: str) -> str:
    if not expected_abstain:
        # Correct: should pitch
        return (f"Based on the signals in the brief, this company shows AI maturity "
                f"with open technical roles that match our capabilities. "
                f"Would you be open to a 15-minute conversation about how "
                f"Tenacious has helped similar teams scale?\n\n"
                f"[Cal.com booking link]")
    else:
        # Intentionally wrong: pitches when should abstain
        return (f"You're clearly scaling aggressively with your AI initiatives. "
                f"Tenacious can provide world-class engineering talent to accelerate "
                f"your growth. Let's connect this week to discuss.\n\n"
                f"[Cal.com booking link]")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str,
                        default="../tenacious_bench_v0.1/raw/programmatic.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    tasks = []
    idx = 1

    # ICP classification tasks
    for scenario in ICP_SCENARIOS:
        brief = make_icp_brief(scenario)
        output = make_icp_candidate_output(scenario)
        expected_seg = scenario[9]
        diff = scenario[10]

        task = {
            "task_id": f"TB-PG-{idx:03d}",
            "task_type": "icp_classification",
            "difficulty": diff,
            "source_mode": "programmatic",
            "input": {
                "hiring_signal_brief": brief,
                "bench_summary": {},
                "prior_thread": [],
                "task_instruction": (
                    "Classify this prospect into one of the four Tenacious ICP segments "
                    "(1, 2, 3, 4) or abstain. State the segment number and a one-sentence reason."
                )
            },
            "candidate_output": output,
            "ground_truth": {"segment": expected_seg},
            "rubric_scores": None,
            "final_score": None,
            "pass": None,
            "metadata": {
                "week10_probe_ref": "P-001" if expected_seg == 2 else
                                    "P-004" if "181" in scenario[11] else None,
                "week10_trace_ref": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "author_model": "human",
                "judge_model": None,
                "generation_seed": args.seed,
                "scenario_notes": scenario[11]
            }
        }
        tasks.append(task)
        idx += 1

    # Bench commitment tasks
    for scenario in BENCH_SCENARIOS:
        stack, count, available, routing, diff = scenario
        thread = make_bench_thread(stack, count)
        output = make_bench_candidate(stack, count, available, routing)

        bench = dict(BENCH_SUMMARY)

        task = {
            "task_id": f"TB-PG-{idx:03d}",
            "task_type": "bench_commitment",
            "difficulty": diff,
            "source_mode": "programmatic",
            "input": {
                "hiring_signal_brief": {
                    "company": {"name": "TechCo", "employees": "51-100"},
                    "signals": {
                        "funding": {"has_recent_funding": True, "confidence": "medium",
                                    "recent_rounds": [{"announced_on": "2026-02-01",
                                                        "money_raised": {"currency": "USD",
                                                                          "value": 10000000},
                                                        "funding_type": "series_a"}]},
                        "ai_maturity": {"score": 2, "confidence": "medium"},
                        "job_posts": {"count": 5, "confidence": "medium"},
                        "layoffs": {"has_recent_layoffs": False},
                        "leadership_change": {"has_leadership_change": False}
                    },
                    "icp_segment": {"segment": 1, "confidence": 0.8}
                },
                "bench_summary": bench,
                "prior_thread": thread,
                "task_instruction": (
                    f"Respond to the prospect's question about {stack} engineers. "
                    f"Check bench_summary availability before committing to any numbers. "
                    f"If the requested count exceeds availability, route to the delivery lead."
                )
            },
            "candidate_output": output,
            "ground_truth": {"expected_routing": routing},
            "rubric_scores": None,
            "final_score": None,
            "pass": None,
            "metadata": {
                "week10_probe_ref": "P-009",
                "week10_trace_ref": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "author_model": "human",
                "judge_model": None,
                "generation_seed": args.seed,
                "bench_requested": count,
                "bench_available": available,
                "stack": stack
            }
        }
        tasks.append(task)
        idx += 1

    # Abstention tasks
    for scenario in ABSTENTION_SCENARIOS:
        desc, ai_score, job_count, has_fund, expected_abstain, diff = scenario
        brief = make_abstention_brief(scenario)
        output = make_abstention_candidate(expected_abstain, desc)

        task = {
            "task_id": f"TB-PG-{idx:03d}",
            "task_type": "abstention_decision",
            "difficulty": diff,
            "source_mode": "programmatic",
            "input": {
                "hiring_signal_brief": brief,
                "bench_summary": BENCH_SUMMARY,
                "prior_thread": [],
                "task_instruction": (
                    "Given this hiring signal brief, decide whether to pitch or abstain. "
                    "If signals are insufficient, send a generic exploratory email. "
                    "Never fabricate signals that are not in the brief."
                )
            },
            "candidate_output": output,
            "ground_truth": {
                "segment": "abstain" if expected_abstain else 4,
            },
            "rubric_scores": None,
            "final_score": None,
            "pass": None,
            "metadata": {
                "week10_probe_ref": "P-005",
                "week10_trace_ref": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "author_model": "human",
                "judge_model": None,
                "generation_seed": args.seed,
                "expected_abstain": expected_abstain,
                "scenario_description": desc
            }
        }
        tasks.append(task)
        idx += 1

    with open(args.output, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    print(f"\nGenerated {len(tasks)} programmatic tasks → {args.output}")

    types = {}
    diffs = {}
    for t in tasks:
        types[t["task_type"]] = types.get(t["task_type"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"Task types: {types}")
    print(f"Difficulties: {diffs}")

    log = {
        "script": "generate_programmatic.py",
        "seed": args.seed,
        "tasks_generated": len(tasks),
        "task_type_distribution": types,
        "difficulty_distribution": diffs,
        "run_at": datetime.now(timezone.utc).isoformat()
    }
    log_path = os.path.join(os.path.dirname(args.output), "programmatic_log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log saved to {log_path}")

if __name__ == "__main__":
    main()
