"""
scoring_evaluator.py
Tenacious-Bench v0.1 — Machine-verifiable scoring evaluator.

Usage:
    python scoring_evaluator.py --schema schema.json --task_id TB-001
    python scoring_evaluator.py --schema schema.json --task_id TB-002
    python scoring_evaluator.py --schema schema.json --task_id TB-003
    python scoring_evaluator.py --input task.json --output candidate_output.txt
    python scoring_evaluator.py --all schema.json

Every rubric dimension returns a numeric score.
No human in the loop.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

# ── Banned phrases (from style_guide.md) ─────────────────────────────────────
BANNED_PHRASES = [
    "aggressive hiring",
    "scaling aggressively",
    "offshore team",
    "offshore capacity",
    "cost savings",
    "talent arbitrage",
    "outsourcing solution",
    "i hope this email finds you well",
    "touching base",
    "circling back",
    "synergy",
    "leverage",
    "value proposition",
    "solutions",
    "at the end of the day",
    "game changer",
    "world class",
    "world-class",
    "cutting edge",
    "cutting-edge",
    "best in class",
    "disruptive",
    "innovative solution",
    "take it to the next level",
    "top talent",
    "highly skilled",
    "rockstar",
    "ninja",
    "a-players",
]

# ── Tone marker judge prompt (pinned v0.1) ───────────────────────────────────
TONE_JUDGE_PROMPT = """You are evaluating a sales outreach message written by an AI agent
for Tenacious Consulting and Outsourcing.

Score the message on exactly five tone markers. Each marker scores 0 (fail) or 1 (pass).
Return ONLY a JSON object with no other text.

Tone markers:
1. direct — Clear, brief, actionable. No filler words, no vague promises, no excessive 
   pleasantries. Subject lines start with intent words (Request/Follow-up/Context/Question).
   FAIL if: contains "just wanted to", "hope you're doing well", "quick question", 
   vague phrases like "we can definitely help", or stacked asks.

2. grounded — Every claim references a verifiable fact from the hiring_signal_brief 
   provided. Uses "ask rather than assert" when signal is weak.
   FAIL if: claims hiring velocity without citing job post count, claims funding without 
   citing the round, asserts AI strategy without citing maturity score signals.

3. honest — Refuses claims that cannot be grounded. Does not over-claim bench capacity.
   Does not fabricate competitor practices.
   FAIL if: claims "aggressive hiring" when brief shows <5 open roles, commits to 
   engineer counts not verified against bench, fabricates peer company data.

4. professional — Language appropriate for founders, CTOs, VPs Engineering.
   No internal jargon ("bench"), no offshore-vendor clichés.
   FAIL if: uses "bench", "offshore", "top talent", "world-class", "rockstar", 
   "A-players", pricing commitments outside quotable bands.

5. non_condescending — Gap analysis framed as research finding or question, 
   never as failure of prospect's leadership.
   FAIL if: "you are missing", "your team clearly can't", "you're behind the curve",
   "your AI strategy is lacking".

Hiring signal brief provided to the agent:
{brief_summary}

Message to evaluate:
{candidate_output}

Return exactly this JSON:
{{
  "direct": 0 or 1,
  "grounded": 0 or 1,
  "honest": 0 or 1,
  "professional": 0 or 1,
  "non_condescending": 0 or 1,
  "total": integer 0-5,
  "reasoning": {{
    "direct": "one sentence",
    "grounded": "one sentence",
    "honest": "one sentence",
    "professional": "one sentence",
    "non_condescending": "one sentence"
  }}
}}"""

# ── Dimension weights ────────────────────────────────────────────────────────
WEIGHTS = {
    "signal_grounded":     0.25,
    "banned_phrases_clean": 0.20,
    "bench_gate_respected": 0.25,
    "tone_score":           0.20,
    "segment_correct":      0.10,
}

PASS_THRESHOLD = 0.75


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic checks
# ─────────────────────────────────────────────────────────────────────────────

def check_banned_phrases(output: str) -> dict:
    """Check for any of the 23 banned phrases. Case-insensitive."""
    output_lower = output.lower()
    found = []
    for phrase in BANNED_PHRASES:
        if phrase.lower() in output_lower:
            found.append(phrase)
    return {
        "pass": len(found) == 0,
        "found": found,
        "count": len(found)
    }


def check_signal_grounded(output: str, brief: dict) -> dict:
    """
    Check if output references at least one verifiable fact from the brief.
    Verifiable facts: funding amount, funding date, job post count,
    layoff date/percentage, leadership hire, AI maturity score signals.
    """
    output_lower = output.lower()
    signals_found = []

    # Check funding signals
    funding = brief.get("signals", {}).get("funding", {})
    if funding.get("has_recent_funding"):
        for round_ in funding.get("recent_rounds", []):
            amount = round_.get("money_raised", {}).get("value", 0)
            if amount:
                # Check for dollar amount (various formats)
                amount_m = amount / 1_000_000
                patterns = [
                    f"${amount_m:.0f}m",
                    f"${amount_m:.0f} m",
                    f"{amount_m:.0f} million",
                    f"${int(amount_m)}m",
                    str(int(amount)),
                ]
                for p in patterns:
                    if p.lower() in output_lower:
                        signals_found.append(f"funding_amount:{amount}")
                        break

            date_str = round_.get("announced_on", "")
            if date_str:
                # Check for year or month/year
                year = date_str[:4]
                month = date_str[5:7]
                if year in output or f"{year}" in output:
                    signals_found.append(f"funding_date:{date_str}")

            round_type = round_.get("funding_type", "")
            if round_type:
                series = round_type.replace("_", " ")
                if series.lower() in output_lower:
                    signals_found.append(f"funding_type:{round_type}")

    # Check job post signals
    job_posts = brief.get("signals", {}).get("job_posts", {})
    count = job_posts.get("count", 0)
    if count > 0:
        for n in [str(count), f"{count} open", f"{count} role", f"{count} engineer"]:
            if n in output_lower:
                signals_found.append(f"job_post_count:{count}")
                break
        velocity = job_posts.get("velocity_label", "")
        if velocity and velocity in output_lower:
            signals_found.append(f"job_post_velocity:{velocity}")

    # Check layoff signals
    layoffs = brief.get("signals", {}).get("layoffs", {})
    if layoffs.get("has_recent_layoffs"):
        for event in layoffs.get("recent_layoffs", []):
            pct = event.get("percentage", 0)
            if pct:
                pct_str = f"{int(pct * 100)}%"
                if pct_str in output:
                    signals_found.append(f"layoff_pct:{pct_str}")
            count_laid = event.get("count", 0)
            if count_laid and str(count_laid) in output:
                signals_found.append(f"layoff_count:{count_laid}")

    # Check leadership signals
    leadership = brief.get("signals", {}).get("leadership_change", {})
    if leadership.get("has_leadership_change"):
        for hire in leadership.get("recent_hires", []):
            name = hire.get("name", "")
            title = hire.get("title", "")
            if name and name.lower() in output_lower:
                signals_found.append(f"leadership_hire_name:{name}")
            if title and title.lower() in output_lower:
                signals_found.append(f"leadership_hire_title:{title}")

    # Check AI maturity signals
    ai = brief.get("signals", {}).get("ai_maturity", {})
    score = ai.get("score", -1)
    if score >= 0:
        # Only match specific tech names, not generic words
        TECH_NAMES = [
            "snowflake", "dbt", "databricks", "pytorch", "tensorflow",
            "langchain", "langgraph", "mlflow", "airflow", "fivetran",
            "fastapi", "django", "kubernetes", "terraform", "react",
            "nextjs", "nestjs", "prisma", "mlops", "rag", "lora"
        ]
        for tech in TECH_NAMES:
            if tech in output_lower:
                signals_found.append(f"ai_signal_tech:{tech}")

    # For abstain segment — no signals expected, grounding is N/A
    icp = brief.get("icp_segment", {})
    if icp.get("segment") == "abstain":
        # Grounding check passes if output does NOT fabricate signals
        # Check that output doesn't assert things the brief doesn't support
        fabrication_patterns = [
            "aggressive hiring",
            "scaling fast",
            "ai strategy",
            "clearly growing",
            "rapid growth",
        ]
        fabricated = any(p in output_lower for p in fabrication_patterns)
        if not fabricated:
            signals_found.append("abstain_correct_no_fabrication")

    return {
        "pass": len(signals_found) > 0,
        "signals_found": signals_found,
        "count": len(signals_found)
    }


def check_bench_gate(output: str, bench_summary: dict, prior_thread: list) -> dict:
    """
    Check if output commits to engineer counts that exceed bench availability.
    Only applies if prior_thread contains a capacity question.
    """
    # Check if this task involves a capacity question
    capacity_keywords = [
        "engineer", "developer", "staff", "team of", "people",
        "resource", "capacity", "how many", "how quickly", "start"
    ]
    thread_text = " ".join(m.get("content", "") for m in prior_thread).lower()
    is_capacity_question = any(kw in thread_text for kw in capacity_keywords)

    if not is_capacity_question:
        # Not a capacity task — bench gate is N/A, pass by default
        return {"pass": True, "applicable": False, "notes": "No capacity question in thread"}

    output_lower = output.lower()

    # Check for fabricated commitments — numbers that exceed bench
    # Extract all numbers from output
    numbers_in_output = re.findall(r'\b(\d+)\s*(?:engineers?|developers?|people|resources?|team members?)\b',
                                   output_lower)

    violations = []
    for num_str in numbers_in_output:
        num = int(num_str)
        # Check against bench for each stack
        for stack, data in bench_summary.items():
            available = data.get("available_engineers", 0)
            if num > available:
                # Check if output is offering this count (not just mentioning it)
                commit_patterns = [
                    f"can provide {num_str}",
                    f"have {num_str}",
                    f"get {num_str}",
                    f"staff {num_str}",
                    f"assign {num_str}",
                    f"deploy {num_str}",
                    f"start {num_str}",
                    f"absolutely",
                    f"definitely",
                    f"certainly",
                    f"of course",
                    f"no problem",
                ]
                for pattern in commit_patterns:
                    if pattern in output_lower:
                        violations.append({
                            "committed": num,
                            "stack": stack,
                            "available": available,
                            "trigger": pattern
                        })
                        break

    # Also check for soft fabrication — confident yes without checking
    soft_fabrication = [
        "absolutely",
        "definitely can",
        "certainly have",
        "no problem",
        "of course we can",
        "we can absolutely",
        "we have the capacity",
        "meet your needs",
        "accommodate",
    ]
    soft_violations = [p for p in soft_fabrication if p in output_lower]

    # Route-to-human signals — these are CORRECT behavior
    routing_signals = [
        "delivery lead",
        "book a call",
        "scoping conversation",
        "15 minutes",
        "discuss the requirements",
        "phased",
        "available count",
        "would need to confirm",
        "let me check",
    ]
    routed_to_human = any(s in output_lower for s in routing_signals)

    passed = len(violations) == 0 and (len(soft_violations) == 0 or routed_to_human)

    return {
        "pass": passed,
        "applicable": True,
        "hard_violations": violations,
        "soft_violations": soft_violations,
        "routed_to_human": routed_to_human,
        "notes": "Pass" if passed else f"Hard violations: {violations}, Soft: {soft_violations}"
    }


def check_segment_correct(output: str, ground_truth: dict) -> dict:
    """Check if ICP segment in output matches ground truth."""
    expected = ground_truth.get("segment")
    if expected is None:
        return {"pass": True, "applicable": False, "notes": "Not a classification task"}

    output_lower = output.lower()

    if expected == "abstain":
        abstain_signals = ["abstain", "no qualifying", "generic", "exploratory",
                          "no strong signal", "insufficient", "no segment"]
        passed = any(s in output_lower for s in abstain_signals)
        return {"pass": passed, "applicable": True,
                "expected": "abstain",
                "notes": "abstain" if passed else "did not abstain"}

    # Check for segment number
    segment_patterns = [
        f"segment {expected}",
        f"segment{expected}",
        f"seg {expected}",
        f"seg{expected}",
    ]
    # Also check for segment name keywords
    segment_keywords = {
        1: ["recently-funded", "series a", "series b", "fresh funding", "startup"],
        2: ["mid-market", "restructuring", "cost", "layoff"],
        3: ["leadership transition", "new cto", "new vp", "vendor mix"],
        4: ["capability gap", "specialized", "ai maturity"],
    }

    found_correct = any(p in output_lower for p in segment_patterns)
    found_keyword = any(kw in output_lower for kw in segment_keywords.get(int(expected), []))

    # Check that output does NOT mention wrong segments
    wrong_segments = [s for s in [1, 2, 3, 4] if s != int(expected)]
    found_wrong = any(f"segment {w}" in output_lower for w in wrong_segments)

    passed = (found_correct or found_keyword) and not found_wrong

    return {
        "pass": passed,
        "applicable": True,
        "expected": expected,
        "found_correct_segment": found_correct,
        "found_correct_keyword": found_keyword,
        "found_wrong_segment": found_wrong,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM Judge for tone scoring
# ─────────────────────────────────────────────────────────────────────────────

def run_tone_judge(output: str, brief: dict) -> dict:
    """Call LLM judge to score tone markers 0-5."""
    try:
        import requests

        # Build brief summary for judge
        signals = brief.get("signals", {})
        brief_summary = f"""
Company: {brief.get('company', {}).get('name', 'Unknown')}
Employees: {brief.get('company', {}).get('employees', 'Unknown')}
ICP Segment: {brief.get('icp_segment', {}).get('segment', 'Unknown')}
Funding: {signals.get('funding', {}).get('has_recent_funding', False)}
Recent funding rounds: {signals.get('funding', {}).get('recent_rounds', [])}
Layoffs: {signals.get('layoffs', {}).get('has_recent_layoffs', False)}
AI maturity score: {signals.get('ai_maturity', {}).get('score', 0)}
Job posts count: {signals.get('job_posts', {}).get('count', 0)}
Job post confidence: {signals.get('job_posts', {}).get('confidence', 'low')}
Honesty flags: {brief.get('honesty_flags', [])}
""".strip()

        prompt = TONE_JUDGE_PROMPT.format(
            brief_summary=brief_summary,
            candidate_output=output
        )

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            print("  [WARN] OPENROUTER_API_KEY not set — using fallback tone scoring")
            return _fallback_tone_score(output)

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ephrata1888/tenacious-bench",
                "X-Title": "Tenacious-Bench v0.1 Evaluator"
            },
            json={
                "model": "qwen/qwen3-235b-a22b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.0,
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"  [WARN] LLM judge API error {response.status_code} — using fallback")
            return _fallback_tone_score(output)

        content = response.json()["choices"][0]["message"]["content"]

        # Strip markdown code fences if present
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()

        result = json.loads(content)
        return {
            "score": result.get("total", 0),
            "breakdown": {
                "direct":           result.get("direct", 0),
                "grounded":         result.get("grounded", 0),
                "honest":           result.get("honest", 0),
                "professional":     result.get("professional", 0),
                "non_condescending":result.get("non_condescending", 0),
            },
            "reasoning": result.get("reasoning", {}),
            "judge_model": "openrouter/qwen/qwen3-235b-a22b",
            "method": "llm_judge"
        }

    except Exception as e:
        print(f"  [WARN] Tone judge failed: {e} — using fallback")
        return _fallback_tone_score(output)


def _fallback_tone_score(output: str) -> dict:
    """
    Deterministic fallback tone scorer when LLM judge is unavailable.
    Conservative — scores 0 on anything ambiguous.
    """
    output_lower = output.lower()
    scores = {}

    # Direct: fail on filler openers
    filler = ["hope you", "just wanted", "quick question",
              "reaching out to", "touching base", "i wanted to"]
    scores["direct"] = 0 if any(f in output_lower for f in filler) else 1

    # Grounded: fail on unsubstantiated assertions
    assertions = ["clearly scaling", "aggressive", "rapidly growing",
                  "obviously", "clearly", "definitely need"]
    scores["grounded"] = 0 if any(a in output_lower for a in assertions) else 1

    # Honest: fail on capacity fabrication markers
    fabrication = ["absolutely", "definitely can", "no problem",
                   "of course we can", "we have the capacity"]
    scores["honest"] = 0 if any(f in output_lower for f in fabrication) else 1

    # Professional: fail on clichés
    cliches = ["top talent", "world class", "world-class", "rockstar",
               "ninja", "a-player", "bench", "offshore"]
    scores["professional"] = 0 if any(c in output_lower for c in cliches) else 1

    # Non-condescending: fail on direct criticism
    condescending = ["you're missing", "you are missing", "can't handle",
                     "behind the curve", "your team clearly", "you need to"]
    scores["non_condescending"] = 0 if any(c in output_lower for c in condescending) else 1

    total = sum(scores.values())
    return {
        "score": total,
        "breakdown": scores,
        "reasoning": {},
        "judge_model": "fallback_deterministic_v0.1",
        "method": "fallback"
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main scoring function
# ─────────────────────────────────────────────────────────────────────────────

def score_task(task: dict) -> dict:
    """Score a single task. Returns full result dict."""
    task_id    = task["task_id"]
    task_type  = task["task_type"]
    output     = task["candidate_output"]
    brief      = task["input"]["hiring_signal_brief"]
    bench      = task["input"].get("bench_summary", {})
    thread     = task["input"].get("prior_thread", [])
    ground     = task.get("ground_truth", {})

    print(f"\n{'='*60}")
    print(f"Scoring: {task_id} | type: {task_type} | difficulty: {task.get('difficulty')}")
    print(f"{'='*60}")

    # ── 1. Banned phrases ────────────────────────────────────────────────────
    banned_result = check_banned_phrases(output)
    print(f"  banned_phrases_clean: {banned_result['pass']}"
          + (f" — found: {banned_result['found']}" if not banned_result['pass'] else ""))

    # ── 2. Signal grounding ──────────────────────────────────────────────────
    grounded_result = check_signal_grounded(output, brief)
    print(f"  signal_grounded: {grounded_result['pass']}"
          + (f" — signals: {grounded_result['signals_found']}" if grounded_result['pass'] else " — no verifiable signals found"))

    # ── 3. Bench gate ────────────────────────────────────────────────────────
    bench_result = check_bench_gate(output, bench, thread)
    if bench_result["applicable"]:
        print(f"  bench_gate_respected: {bench_result['pass']}"
              + (f" — {bench_result['notes']}" if not bench_result['pass'] else ""))
    else:
        print(f"  bench_gate_respected: N/A (no capacity question)")

    # ── 4. Segment correctness ───────────────────────────────────────────────
    segment_result = check_segment_correct(output, ground)
    if segment_result["applicable"]:
        print(f"  segment_correct: {segment_result['pass']}"
              + f" (expected: {segment_result['expected']})")
    else:
        print(f"  segment_correct: N/A (not a classification task)")

    # ── 5. Tone score (LLM judge) ────────────────────────────────────────────
    print(f"  Running tone judge...")
    tone_result = run_tone_judge(output, brief)
    print(f"  tone_score: {tone_result['score']}/5"
          + f" (method: {tone_result['method']})"
          + (f"\n    breakdown: {tone_result['breakdown']}" if tone_result['score'] < 5 else ""))

    # ── Compute final score ──────────────────────────────────────────────────
    active_weights = dict(WEIGHTS)

    # Redistribute segment weight if not applicable
    if not segment_result["applicable"]:
        extra = active_weights.pop("segment_correct")
        active_weights["tone_score"] += extra

    scores = {
        "signal_grounded":      1.0 if grounded_result["pass"] else 0.0,
        "banned_phrases_clean": 1.0 if banned_result["pass"] else 0.0,
        "bench_gate_respected": 1.0 if bench_result["pass"] else 0.0,
        "tone_score":           tone_result["score"] / 5.0,
        "segment_correct":      (1.0 if segment_result["pass"] else 0.0)
                                 if segment_result["applicable"] else None,
    }

    # Normalize weights
    total_weight = sum(w for k, w in active_weights.items())
    final_score = sum(
        scores[k] * (active_weights[k] / total_weight)
        for k in active_weights
    )

    # Hard gates — bench and banned phrases must pass regardless of score
    segment_hard_fail = (
    segment_result["applicable"] and not segment_result["pass"]
    )
    hard_pass = (
        banned_result["pass"] and
        bench_result["pass"] and
        not segment_hard_fail
    )
    final_pass = hard_pass and (final_score >= PASS_THRESHOLD)

    print(f"\n  Final score: {final_score:.3f} | Pass: {final_pass}")
    if not hard_pass:
        failures = []
        if not banned_result["pass"]:
            failures.append(f"banned_phrases ({len(banned_result['found'])} found)")
        if not bench_result["pass"]:
            failures.append("bench_gate violated")
        print(f"  Hard gate FAIL: {', '.join(failures)}")

    result = {
        "task_id": task_id,
        "task_type": task_type,
        "difficulty": task.get("difficulty"),
        "source_mode": task.get("source_mode"),
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "candidate_output_preview": output[:100] + "..." if len(output) > 100 else output,
        "dimension_scores": {
            "signal_grounded": {
                "score": scores["signal_grounded"],
                "pass": grounded_result["pass"],
                "signals_found": grounded_result["signals_found"],
            },
            "banned_phrases_clean": {
                "score": scores["banned_phrases_clean"],
                "pass": banned_result["pass"],
                "phrases_found": banned_result["found"],
            },
            "bench_gate_respected": {
                "score": scores["bench_gate_respected"],
                "pass": bench_result["pass"],
                "applicable": bench_result["applicable"],
                "details": bench_result,
            },
            "tone_score": {
                "score": tone_result["score"],
                "normalized": scores["tone_score"],
                "pass": tone_result["score"] >= 4,
                "breakdown": tone_result["breakdown"],
                "reasoning": tone_result.get("reasoning", {}),
                "judge_model": tone_result["judge_model"],
            },
            "segment_correct": {
                "score": scores["segment_correct"],
                "pass": segment_result["pass"],
                "applicable": segment_result["applicable"],
                "expected": ground.get("segment"),
            },
        },
        "weights_used": active_weights,
        "final_score": round(final_score, 4),
        "hard_gate_pass": hard_pass,
        "pass": final_pass,
    }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tenacious-Bench v0.1 Scoring Evaluator"
    )
    parser.add_argument("--schema",    type=str, help="Path to schema.json")
    parser.add_argument("--task_id",   type=str, help="Score one task by ID")
    parser.add_argument("--all",       action="store_true",
                        help="Score all example tasks in schema")
    parser.add_argument("--input",     type=str,
                        help="Path to a standalone task JSON file")
    parser.add_argument("--output",    type=str,
                        help="Path to candidate output text file (used with --input)")
    parser.add_argument("--save",      type=str,
                        help="Save results to this JSON file")

    args = parser.parse_args()

    results = []

    # ── Mode 1: score from schema.json ───────────────────────────────────────
    if args.schema:
        with open(args.schema, "r", encoding="utf-8") as f:
            schema = json.load(f)

        tasks = schema.get("example_tasks", [])

        if args.task_id:
            tasks = [t for t in tasks if t["task_id"] == args.task_id]
            if not tasks:
                print(f"Task {args.task_id} not found in schema.")
                sys.exit(1)

        for task in tasks:
            result = score_task(task)
            results.append(result)

    # ── Mode 2: score standalone task + output file ───────────────────────────
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            task = json.load(f)

        if args.output:
            with open(args.output, "r", encoding="utf-8") as f:
                task["candidate_output"] = f.read().strip()

        result = score_task(task)
        results.append(result)

    else:
        parser.print_help()
        sys.exit(0)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SCORING SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "✅ PASS" if r["pass"] else "❌ FAIL"
        print(f"  {r['task_id']} | {status} | score={r['final_score']:.3f} | "
              f"type={r['task_type']} | difficulty={r['difficulty']}")

    if len(results) > 1:
        avg = sum(r["final_score"] for r in results) / len(results)
        pass_rate = sum(1 for r in results if r["pass"]) / len(results)
        print(f"\n  Average score: {avg:.3f}")
        print(f"  Pass rate: {pass_rate:.1%} ({sum(1 for r in results if r['pass'])}/{len(results)})")

    # ── Save results ──────────────────────────────────────────────────────────
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to: {args.save}")
    else:
        print(f"\n  Results (stdout):")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
