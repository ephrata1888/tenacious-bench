"""
generate_multi_llm.py
Generates tasks using two different model families to avoid preference leakage.
Model A (Claude Haiku) generates candidate outputs.
Model B (Qwen3-235b) judges quality.
Only keeps pairs where judge score is 0.2-0.7 (diagnostic range).

Usage:
    python generate_multi_llm.py --output ../tenacious_bench_v0.1/raw/multi_llm.jsonl
                                  --seed 42
                                  --target 100
                                  --dry_run  (skip API calls, use templates)
"""

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

SEED = 42
random.seed(SEED)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GENERATOR_MODEL = "anthropic/claude-haiku-4-5"
JUDGE_MODEL = "qwen/qwen3-235b-a22b"

BENCH_SUMMARY = {
    "python": {"available_engineers": 7},
    "ml": {"available_engineers": 5},
    "data": {"available_engineers": 9},
    "go": {"available_engineers": 3},
    "infra": {"available_engineers": 4},
}

# Task prompts for generation
GENERATION_PROMPTS = [
    {
        "task_type": "email_composition",
        "difficulty": "medium",
        "probe_ref": "P-005",
        "system": "You are a B2B sales agent for Tenacious Consulting. Write outreach emails.",
        "brief": {
            "company": {"name": "DataScale Inc", "employees": "51-100", "country": "US"},
            "signals": {
                "funding": {"has_recent_funding": True, "confidence": "medium",
                            "recent_rounds": [{"announced_on": "2026-03-01",
                                               "money_raised": {"currency": "USD", "value": 8000000},
                                               "funding_type": "series_a"}]},
                "ai_maturity": {"score": 2, "confidence": "medium",
                                "signals": ["Snowflake tech stack", "ML Engineer role open"]},
                "job_posts": {"count": 4, "confidence": "medium",
                              "confidence_reason": "4 engineering posts found"},
                "layoffs": {"has_recent_layoffs": False},
                "leadership_change": {"has_leadership_change": False}
            },
            "icp_segment": {"segment": 1, "confidence": 0.75},
            "honesty_flags": ["weak_hiring_velocity_signal"]
        },
        "instruction": (
            "Compose a cold outreach email to the VP Engineering. "
            "Reference at least one verifiable signal from the brief. "
            "Body under 120 words. Include subject line. "
            "Do not claim 'aggressive hiring' — job count is below threshold."
        )
    },
    {
        "task_type": "objection_handling",
        "difficulty": "hard",
        "probe_ref": "P-013",
        "system": "You are a B2B sales agent for Tenacious Consulting.",
        "brief": {
            "company": {"name": "PriceCheck Corp", "employees": "101-250"},
            "signals": {
                "funding": {"has_recent_funding": True, "confidence": "medium",
                            "recent_rounds": [{"announced_on": "2026-01-15",
                                               "money_raised": {"currency": "USD", "value": 12000000},
                                               "funding_type": "series_b"}]},
                "ai_maturity": {"score": 2, "confidence": "medium"},
                "job_posts": {"count": 6, "confidence": "high"},
                "layoffs": {"has_recent_layoffs": False},
                "leadership_change": {"has_leadership_change": False}
            },
            "icp_segment": {"segment": 1, "confidence": 0.8},
            "honesty_flags": []
        },
        "instruction": (
            "The prospect replied: 'Your price is higher than Indian vendors.' "
            "Respond using the approved Tenacious objection-handling pattern: "
            "reliability, time-zone overlap, retention. "
            "Never offer a discount. Never use 'cost savings' or 'offshore team'."
        )
    },
    {
        "task_type": "competitor_gap_quality",
        "difficulty": "hard",
        "probe_ref": "P-029",
        "system": "You are a B2B sales agent for Tenacious Consulting.",
        "brief": {
            "company": {"name": "GapTarget Co", "employees": "51-100"},
            "signals": {
                "funding": {"has_recent_funding": True, "confidence": "high",
                            "recent_rounds": [{"announced_on": "2026-02-20",
                                               "money_raised": {"currency": "USD", "value": 18000000},
                                               "funding_type": "series_b"}]},
                "ai_maturity": {"score": 1, "confidence": "low"},
                "job_posts": {"count": 7, "confidence": "high"},
                "layoffs": {"has_recent_layoffs": False},
                "leadership_change": {"has_leadership_change": False}
            },
            "icp_segment": {"segment": 1, "confidence": 0.8},
            "honesty_flags": []
        },
        "competitor_gap": {
            "top_quartile_practices": [
                "Dedicated MLOps team of 3+ engineers",
                "Real-time feature store (Feast or Tecton)",
                "Weekly AI model performance reviews"
            ],
            "prospect_current": "No public signal of MLOps function"
        },
        "instruction": (
            "Reference the competitor gap brief to mention that peers in your sector "
            "have dedicated MLOps teams. Frame this as a research finding, not a failure. "
            "Do not say 'you are missing' or 'your competitors are ahead'. "
            "Body under 120 words."
        )
    },
    {
        "task_type": "tone_adherence",
        "difficulty": "medium",
        "probe_ref": "P-012",
        "system": "You are a B2B sales agent for Tenacious Consulting.",
        "brief": {
            "company": {"name": "ToneDrift Inc", "employees": "101-250"},
            "signals": {
                "funding": {"has_recent_funding": False, "confidence": "low"},
                "ai_maturity": {"score": 2, "confidence": "medium"},
                "job_posts": {"count": 5, "confidence": "high"},
                "layoffs": {"has_recent_layoffs": False},
                "leadership_change": {"has_leadership_change": False}
            },
            "icp_segment": {"segment": 4, "confidence": 0.6},
            "honesty_flags": []
        },
        "instruction": (
            "The prospect replied: 'We actually considered outsourcing before and had "
            "a bad experience with an Indian vendor.' "
            "Respond while maintaining Tenacious tone — direct, grounded, professional. "
            "Do not say 'offshore team', 'cost savings', or use any of the 23 banned phrases. "
            "Acknowledge their experience without dismissing it."
        )
    },
    {
        "task_type": "signal_grounding",
        "difficulty": "hard",
        "probe_ref": "P-007",
        "system": "You are a B2B sales agent for Tenacious Consulting.",
        "brief": {
            "company": {"name": "WeakData Corp", "employees": "51-100"},
            "signals": {
                "funding": {"has_recent_funding": False, "confidence": "low"},
                "ai_maturity": {"score": 1, "confidence": "low",
                                "signals": ["one AI keyword in job description"]},
                "job_posts": {"count": 2, "confidence": "low",
                              "confidence_reason": "2 posts found — below 5 threshold"},
                "layoffs": {"has_recent_layoffs": False},
                "leadership_change": {"has_leadership_change": False}
            },
            "icp_segment": {"segment": "abstain", "confidence": 0.0},
            "honesty_flags": ["weak_hiring_velocity_signal", "tech_stack_inferred_not_confirmed"]
        },
        "instruction": (
            "Compose a cold outreach email. The hiring signal brief shows WEAK signals only. "
            "Do NOT claim 'aggressive hiring' — only 2 job posts found. "
            "Do NOT claim strong AI strategy — maturity score is 1, confidence low. "
            "Use honest, exploratory language. "
            "Body under 120 words."
        )
    }
]

JUDGE_PROMPT = """You are evaluating a Tenacious Consulting sales agent output.

Task type: {task_type}
Task instruction: {instruction}
Hiring signal brief: {brief_summary}

Agent output:
{output}

Score this output on a scale of 0.0 to 1.0 based on:
- Signal grounding (does it reference verifiable facts from the brief?)
- Banned phrases (zero of the 23 banned phrases including: aggressive hiring,
  offshore team, cost savings, world-class, top talent, synergy, leverage, etc.)
- Tenacious tone (direct, grounded, honest, professional, non-condescending)
- Task completion (does it do what was asked?)

Return ONLY a JSON object:
{{"score": 0.0-1.0, "reasoning": "one sentence", "primary_failure": "dimension that failed most"}}"""


def call_openrouter(model: str, messages: list, max_tokens: int = 400) -> str:
    """Call OpenRouter API."""
    import requests
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ephrata1888/tenacious-bench",
            "X-Title": "Tenacious-Bench v0.1 Dataset Generator"
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=45
    )
    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}: {response.text[:200]}")
    return response.json()["choices"][0]["message"]["content"]


def generate_output(prompt_config: dict) -> str:
    """Generate candidate output using Model A (Claude Haiku)."""
    brief = prompt_config["brief"]
    messages = [
        {"role": "system", "content": prompt_config["system"]},
        {"role": "user", "content": (
            f"Hiring signal brief:\n{json.dumps(brief, indent=2)}\n\n"
            f"Task: {prompt_config['instruction']}"
        )}
    ]
    return call_openrouter(GENERATOR_MODEL, messages, max_tokens=300)


def judge_output(output: str, prompt_config: dict) -> dict:
    """Judge output quality using Model B (Qwen3)."""
    brief = prompt_config["brief"]
    brief_summary = f"Company: {brief['company']['name']}, ICP: {brief['icp_segment']['segment']}"

    judge_content = JUDGE_PROMPT.format(
        task_type=prompt_config["task_type"],
        instruction=prompt_config["instruction"][:200],
        brief_summary=brief_summary,
        output=output[:500]
    )

    response = call_openrouter(
        JUDGE_MODEL,
        [{"role": "user", "content": judge_content}],
        max_tokens=150
    )

    import re
    response = re.sub(r"```json\s*", "", response)
    response = re.sub(r"```\s*", "", response).strip()

    try:
        return json.loads(response)
    except:
        return {"score": 0.5, "reasoning": "parse error", "primary_failure": "unknown"}


def make_template_output(prompt_config: dict, variant: int) -> str:
    """Template-based output for dry run mode."""
    task_type = prompt_config["task_type"]
    brief = prompt_config["brief"]
    company = brief["company"]["name"]

    templates = {
        "email_composition": [
            f"Subject: Engineering capacity at {company} — quick observation\n\nHi,\n\nYou're clearly scaling aggressively with your AI strategy. We can provide world-class engineers to help. Let's synergize!\n\nBest,\nResearch Partner\nTenacious",
            f"Subject: Context: Tenacious for {company}\n\nHi,\n\nNoticed 4 engineering roles open since January — is hiring velocity matching your runway after the Series A?\n\nWe help teams at your stage scale engineering without the 3-month recruiting cycle.\n\nOpen to a 15-minute conversation?\n\nBest,\nResearch Partner\nTenacious Intelligence Corporation\ngettenacious.com",
            f"Subject: Request: 15 minutes re {company} engineering roadmap\n\nHi,\n\nTwo peers in your sector have recently scaled ML teams ahead of product launches. Curious whether that's on your roadmap or already planned internally.\n\nWe work with Series A teams typically 3-4 months post-raise. Happy to share what we've seen.\n\nBest,\nResearch Partner\nTenacious",
        ],
        "objection_handling": [
            "That's fair. We're not the cheapest option. What Tenacious offers is reliability and overlap — our engineers are available during your core hours, not just a few. Would love to show you the difference on a small engagement.",
            "Understood — bad outsourcing experiences are common. The key difference with Tenacious is we guarantee 3 hours of synchronous overlap per day and our engineers have gone through a rigorous selection process. Not trying to replace anyone, just fill a specific gap.",
            "Appreciate you sharing that. We hear this often. Our value isn't cost — it's reliability and timezone overlap. Happy to put you in touch with a reference who had a similar concern before working with us.",
        ],
        "competitor_gap_quality": [
            "Your competitors are clearly ahead of you in MLOps. You're missing critical capabilities that will hurt you long-term.",
            "Three peers in your sector have posted MLOps engineer roles in the last 90 days. Curious whether you've made a deliberate choice not to build that function yet, or whether it's still being scoped.",
            "Looking at public signal from similar-sized companies in your space — a few have stood up dedicated MLOps functions recently. Wondering how you're thinking about that vs your current setup.",
        ],
        "tone_adherence": [
            "I understand you had a bad experience. Our offshore team is different — we provide top talent with cutting-edge skills at competitive rates!",
            "That's a common concern and a fair one. The main difference with Tenacious is timezone overlap and accountability — we're not just dropping engineers in and walking away. Happy to share how we've handled this for other teams if useful.",
            "Appreciate you sharing that context. What typically goes wrong is communication gaps and accountability. We structure engagements to prevent both — would it help to walk through how?",
        ],
        "signal_grounding": [
            "You're clearly scaling aggressively with your aggressive AI strategy. Your world-class team needs top talent to succeed. Let's synergize on this!",
            "Noticed 2 open engineering roles — not a huge signal, but enough to ask whether there's a specific capability you're trying to bring in-house. Happy to share what similar teams have done.\n\nOpen to a quick call?",
            "We work with enterprise software teams at your size. I don't see strong public signal of active hiring or recent changes, so I'll be direct: is there an engineering constraint worth a 15-minute conversation?\n\nIf not, no follow-up.",
        ]
    }

    options = templates.get(task_type, templates["email_composition"])
    return options[variant % len(options)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str,
                        default="../tenacious_bench_v0.1/raw/multi_llm.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--dry_run", action="store_true",
                        help="Use templates instead of API calls")
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    use_api = bool(OPENROUTER_API_KEY) and not args.dry_run
    if not use_api:
        print("Running in DRY RUN mode — using templates (no API calls)")
        print("Set OPENROUTER_API_KEY and remove --dry_run for real generation")

    tasks = []
    idx = 1
    attempts = 0
    kept = 0
    filtered = 0

    # Cycle through prompts to reach target
    prompt_cycle = GENERATION_PROMPTS * (args.target // len(GENERATION_PROMPTS) + 2)
    random.shuffle(prompt_cycle)

    for prompt_config in prompt_cycle:
        if kept >= args.target:
            break

        attempts += 1

        # Generate output
        if use_api:
            try:
                output = generate_output(prompt_config)
                time.sleep(0.5)  # Rate limit
            except Exception as e:
                print(f"  Generation error: {e}")
                continue
        else:
            output = make_template_output(prompt_config, attempts)

        # Judge output
        if use_api:
            try:
                judgment = judge_output(output, prompt_config)
                time.sleep(0.5)
            except Exception as e:
                print(f"  Judge error: {e}")
                judgment = {"score": 0.5, "reasoning": "error", "primary_failure": "unknown"}
        else:
            # Simulate varying judge scores for dry run
            score = round(0.1 + (attempts % 9) * 0.1, 2)
            judgment = {
                "score": score,
                "reasoning": f"Simulated score {score}",
                "primary_failure": "banned_phrases" if score < 0.4 else "tone"
            }

        judge_score = judgment.get("score", 0.5)

        # Filter: keep only diagnostic range 0.2-0.7
        if judge_score < 0.2 or judge_score > 0.7:
            filtered += 1
            print(f"  [{idx:03d}] Filtered out — judge score {judge_score:.2f} "
                  f"(outside 0.2-0.7 range)")
            continue

        # Determine difficulty from score
        if judge_score >= 0.6:
            difficulty = "medium"
        elif judge_score >= 0.4:
            difficulty = "hard"
        else:
            difficulty = "adversarial"

        task = {
            "task_id": f"TB-ML-{idx:03d}",
            "task_type": prompt_config["task_type"],
            "difficulty": difficulty,
            "source_mode": "multi-llm-synthesis",
            "input": {
                "hiring_signal_brief": prompt_config["brief"],
                "bench_summary": BENCH_SUMMARY,
                "prior_thread": [],
                "task_instruction": prompt_config["instruction"]
            },
            "candidate_output": output,
            "ground_truth": {},
            "rubric_scores": None,
            "final_score": None,
            "pass": None,
            "metadata": {
                "week10_probe_ref": prompt_config.get("probe_ref"),
                "week10_trace_ref": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "author_model": GENERATOR_MODEL if use_api else "template",
                "judge_model": JUDGE_MODEL if use_api else "simulated",
                "judge_score": judge_score,
                "judge_reasoning": judgment.get("reasoning", ""),
                "primary_failure": judgment.get("primary_failure", ""),
                "generation_seed": args.seed,
                "generation_mode": "api" if use_api else "template"
            }
        }

        tasks.append(task)
        kept += 1
        idx += 1
        print(f"  [{idx-1:03d}] Kept — judge score {judge_score:.2f} | "
              f"type: {prompt_config['task_type']}")

    with open(args.output, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    print(f"\nGenerated {len(tasks)} multi-LLM tasks → {args.output}")
    print(f"Attempts: {attempts} | Kept: {kept} | Filtered: {filtered}")
    print(f"Filter rate: {filtered/max(1,attempts)*100:.1f}%")

    types = {}
    diffs = {}
    for t in tasks:
        types[t["task_type"]] = types.get(t["task_type"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"Task types: {types}")
    print(f"Difficulties: {diffs}")

    log = {
        "script": "generate_multi_llm.py",
        "seed": args.seed,
        "generator_model": GENERATOR_MODEL if use_api else "template",
        "judge_model": JUDGE_MODEL if use_api else "simulated",
        "preference_leakage_prevention": "different model families: Anthropic (generator) vs Alibaba (judge)",
        "judge_filter_range": [0.2, 0.7],
        "attempts": attempts,
        "kept": kept,
        "filtered": filtered,
        "filter_rate": round(filtered/max(1,attempts), 3),
        "tasks_generated": len(tasks),
        "task_type_distribution": types,
        "difficulty_distribution": diffs,
        "dry_run": not use_api,
        "run_at": datetime.now(timezone.utc).isoformat()
    }
    log_path = os.path.join(os.path.dirname(args.output), "multi_llm_log.json")
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log saved to {log_path}")

if __name__ == "__main__":
    main()
