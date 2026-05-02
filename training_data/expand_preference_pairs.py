import json, os, random
from datetime import datetime, timezone, timedelta

SEED = 42
random.seed(SEED)

BENCH = {"python":7,"ml":5,"data":9,"go":3,"infra":4,"blockchain":0,"rust":0,"solidity":0}

SYSTEM_PROMPT_SHORT = """You are a B2B sales agent for Tenacious Consulting.
Rules: ground every claim in the brief, never commit to counts exceeding bench,
never use banned phrases (world-class, top talent, offshore team, cost savings,
synergy, leverage, absolutely, highly skilled, cutting-edge, game-changer)."""

COMPANIES = [
    {"name":"DataFlow AI","employees":"51-100","segment":1,"funding":8000000,"fund_date":"2026-03-01","jobs":6,"ai":2},
    {"name":"ScaleOps Inc","employees":"51-100","segment":1,"funding":12000000,"fund_date":"2026-02-10","jobs":7,"ai":3},
    {"name":"PlatformX Corp","employees":"101-250","segment":3,"funding":0,"fund_date":None,"jobs":5,"ai":2,"new_cto":"Jordan Lee","cto_date":"2026-03-15"},
    {"name":"RestructureTech","employees":"251-500","segment":2,"funding":15000000,"fund_date":"2026-01-20","jobs":4,"ai":1,"layoff":True,"lpct":0.15,"lcount":75},
    {"name":"AIBuild Co","employees":"51-100","segment":4,"funding":0,"fund_date":None,"jobs":8,"ai":3},
    {"name":"WeakSignal Corp","employees":"51-100","segment":"abstain","funding":0,"fund_date":None,"jobs":1,"ai":0},
    {"name":"StackMigrate Inc","employees":"101-250","segment":1,"funding":20000000,"fund_date":"2026-02-28","jobs":9,"ai":2},
    {"name":"CloudRebuild Ltd","employees":"251-500","segment":2,"funding":0,"fund_date":None,"jobs":3,"ai":2,"layoff":True,"lpct":0.20,"lcount":100},
]

STACKS = [("python",2),("python",4),("python",6),("python",8),("python",10),
          ("ml",2),("ml",4),("ml",6),("data",3),("data",5),("data",8),
          ("go",2),("go",4),("infra",3),("infra",5),("blockchain",2),("rust",1)]

def bench_pair(company, stack, count, idx):
    avail = BENCH.get(stack, 0)
    question = f"Can you provide {count} {stack} engineers by next quarter?"
    if avail == 0:
        chosen = (f"{stack} is outside our current bench. "
                  f"We don't commit to stacks we don't have - I'd rather tell you now "
                  f"than discover the gap three weeks in. "
                  f"Want me to check what adjacent capabilities we have that might fit?")
    elif count <= avail:
        chosen = (f"We have {avail} {stack} engineers available now, so {count} is within capacity. "
                  f"I'd suggest a squad of {count}: 1 senior, {count-1} mid-level if you need more than one. "
                  f"One of our fractional PMs can overlay at 0.4 FTE - joining your standups without a parallel process. "
                  f"Want me to book a 15-minute scoping call with our delivery lead?")
    else:
        chosen = (f"We have {avail} {stack} engineers available right now. "
                  f"For {count}, we'd need our delivery lead to scope a phased ramp starting with {avail}. "
                  f"Can I book a 15-minute call this week to discuss the specific requirements?")
    rejected = (f"Absolutely - we can get {count} {stack} engineers started next month. "
                f"Our world-class team is highly skilled and ready to deploy immediately. "
                f"We have the capacity to meet your needs right away - top talent guaranteed!")
    return {
        "id": f"PP-BC-{idx:03d}",
        "source": f"programmatic_{company['name'].lower().replace(' ','_')}",
        "task_type": "bench_commitment",
        "difficulty": "adversarial" if avail==0 else ("hard" if count>avail else "medium"),
        "week10_probe_ref": "P-009",
        "prompt": f"{SYSTEM_PROMPT_SHORT}\n\nCompany: {company['name']} | Bench {stack}={avail}\nQuestion: {question}",
        "chosen": chosen,
        "rejected": rejected,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_seed": SEED
    }

def email_pair(company, idx):
    seg = company["segment"]
    if seg == 1 and company.get("funding",0) > 0:
        chosen = (f"Subject: Context: Tenacious for {company['name']} - engineering capacity\n\n"
                  f"Hi,\n\nNoticed {company['jobs']} open engineering roles at {company['name']} "
                  f"since your ${company['funding']//1000000}M raise - is hiring velocity matching your runway?\n\n"
                  f"We work with Series A/B teams at your stage: 7-14 days to first commit, "
                  f"engineers who stay for the engagement, structured overlap.\n\n"
                  f"Worth a 15-minute call?\n\nBest,\nResearch Partner\nTenacious")
        rejected = (f"Subject: {company['name']} - explosive growth opportunity!\n\n"
                    f"You're clearly scaling aggressively! Our world-class offshore team can "
                    f"supercharge your growth with top talent. Let's synergize!")
    elif seg == 2 and company.get("layoff"):
        chosen = (f"Subject: Context: Tenacious for {company['name']} engineering roadmap\n\n"
                  f"Hi,\n\nNoticed {company['jobs']} open roles alongside the "
                  f"{int(company['lpct']*100)}% restructure at {company['name']} - "
                  f"the pattern usually means delivery capacity is the constraint.\n\n"
                  f"We work with mid-market teams in this situation: replacing delivery capacity "
                  f"without a one-for-one headcount narrative.\n\nWorth a 15-minute call?\n\nBest,\nResearch Partner\nTenacious")
        rejected = (f"We can replace your {company['lcount']} laid-off engineers at 40% of the cost! "
                    f"Our world-class offshore team delivers top talent. Let's synergize on cost savings!")
    elif seg == 3 and company.get("new_cto"):
        chosen = (f"Subject: Context: Tenacious for {company['name']} - CTO transition timing\n\n"
                  f"Hi {company['new_cto']},\n\nCongratulations on the CTO role. "
                  f"In our experience, the first 90 days are when vendor mix gets a fresh look.\n\n"
                  f"I don't want to pitch anything today. "
                  f"If a 15-minute call to understand your reassessment shape is useful, I'm happy to book it. "
                  f"If not, no follow-up.\n\nBest,\nResearch Partner\nTenacious")
        rejected = (f"You should definitely reassess your vendor stack now! "
                    f"Our world-class offshore team can leverage cutting-edge solutions to supercharge {company['name']}!")
    elif seg == "abstain":
        chosen = (f"Subject: Context: Tenacious for {company['name']}\n\n"
                  f"Hi,\n\nWe work with {company['employees']} teams - typically when hiring velocity "
                  f"outpaces recruiting or a capability gap appears on the roadmap.\n\n"
                  f"I don't see strong public signal of either right now, "
                  f"so I'll be direct: is there an engineering constraint worth a 15-minute conversation?\n\n"
                  f"If not, no follow-up.\n\nBest,\nResearch Partner\nTenacious")
        rejected = (f"You're clearly scaling aggressively! Our world-class offshore team "
                    f"provides top talent with cutting-edge solutions. Let's synergize!")
    else:
        return None
    return {
        "id": f"PP-EML-{idx:03d}",
        "source": f"programmatic_email_seg{seg}",
        "task_type": "email_composition",
        "difficulty": "medium",
        "week10_probe_ref": "P-005" if seg=="abstain" else "P-012",
        "prompt": f"{SYSTEM_PROMPT_SHORT}\n\nCompany: {company['name']} | Segment: {seg} | Jobs: {company['jobs']}",
        "chosen": chosen,
        "rejected": rejected,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_seed": SEED
    }

# Objection pairs
OBJECTION_PAIRS = [
    {"q":"Your price is higher than Indian vendors. Why pay more?",
     "chosen":"We're not the cheapest option - that's accurate. We compete on reliability and retention, not hourly rate. Named engineers who stay for the engagement, 3-hour overlap as a baseline, salaried employees with benefits. Any vendor quoting percentage savings without a scoping conversation is making up numbers. Worth a 15-minute call?",
     "rejected":"Our offshore team offers incredible cost savings! We guarantee 40% improvement in velocity. Our world-class engineers are best in class top talent!","probe":"P-013","diff":"adversarial"},
    {"q":"We've been burned by offshore vendors before.",
     "chosen":"Fair. The smallest real engagement we do is a fixed-scope project - specific deliverable, evaluable output, named engineers before you commit. If it works, you know our team is real. If after a technical walkthrough you decide we're not the right fit, tell us - a no saves us both time.",
     "rejected":"We're different - we guarantee you won't be burned again! Our world-class team has a proven track record. We're the best in class!","probe":"P-013","diff":"hard"},
    {"q":"We're concerned about timezone overlap with an African team.",
     "chosen":"3-hour overlap with Pacific as a baseline - we don't pretend otherwise. Standups are async-first with a synchronous review window from 9-12 your time. For teams that need real-time pairing all day, we're not the right fit. For teams that need reliable delivery with structured overlap, we are.",
     "rejected":"Don't worry - our offshore team works around the clock! Our world-class engineers are always available to synergize with your team!","probe":"P-023","diff":"hard"},
    {"q":"We only hire engineers in-house. We don't outsource.",
     "chosen":"Understood - and that's a legitimate position. The teams we work with typically reach out when a specific deliverable has a tighter timeline than in-house recruiting can match. If that situation comes up, we're here. If not, no follow-up from me.",
     "rejected":"You're missing out on incredible cost savings and top talent! Our world-class offshore team can transform your hiring strategy!","probe":"P-001","diff":"adversarial"},
    {"q":"We need a quick 2-week POC. Can you do that?",
     "chosen":"The minimum real engagement we do is a fixed-scope project with a specific evaluable deliverable - typically 4 weeks minimum to do it honestly. Two weeks produces something too thin to evaluate properly. I'd rather tell you now than take the contract and deliver something you can't assess.",
     "rejected":"Absolutely - we can definitely deliver a world-class POC in 2 weeks! Our highly skilled team can handle any timeline!","probe":"P-017","diff":"hard"},
]

def main():
    os.makedirs("training_data", exist_ok=True)
    random.seed(SEED)

    # Load base pairs
    base = []
    base_path = "training_data/preference_pairs.jsonl"
    if os.path.exists(base_path):
        with open(base_path) as f:
            for line in f:
                if line.strip():
                    base.append(json.loads(line))
    print(f"Base pairs: {len(base)}")

    # Generate bench pairs
    bench = []
    idx = 1
    for company in COMPANIES:
        for stack, count in random.sample(STACKS, min(10, len(STACKS))):
            bench.append(bench_pair(company, stack, count, idx))
            idx += 1

    # Generate email pairs
    emails = []
    for i, company in enumerate(COMPANIES):
        p = email_pair(company, i+1)
        if p:
            emails.append(p)

    # Objection pairs
    objections = []
    for i, obj in enumerate(OBJECTION_PAIRS):
        for company in random.sample(COMPANIES[:4], 3):
            brief_str = f"Company: {company['name']} | Segment: {company['segment']}"
            objections.append({
                "id": f"PP-OBJ-{i*3+len(objections)+1:03d}",
                "source": "objection_handling_programmatic",
                "task_type": "objection_handling",
                "difficulty": obj["diff"],
                "week10_probe_ref": obj["probe"],
                "prompt": f"{SYSTEM_PROMPT_SHORT}\n\n{brief_str}\nProspect: {obj['q']}",
                "chosen": obj["chosen"],
                "rejected": obj["rejected"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generation_seed": SEED
            })

    all_pairs = base + bench + emails + objections
    random.shuffle(all_pairs)

    output_path = "training_data/preference_pairs_expanded.jsonl"
    with open(output_path, "w") as f:
        for p in all_pairs:
            f.write(json.dumps(p) + "\n")

    print(f"Total: {len(all_pairs)} pairs -> {output_path}")
    types = {}
    diffs = {}
    for p in all_pairs:
        t = p["task_type"]; d = p["difficulty"]
        types[t] = types.get(t,0)+1
        diffs[d] = diffs.get(d,0)+1
    print(f"Types: {types}")
    print(f"Diffs: {diffs}")

    log = {"total":len(all_pairs),"types":types,"diffs":diffs,
           "run_at":datetime.now(timezone.utc).isoformat()}
    with open("training_data/preference_pairs_expanded_log.json","w") as f:
        json.dump(log, f, indent=2)

main()
