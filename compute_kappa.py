"""Compute inter-rater agreement between Pass 1 and Pass 2."""

pass1 = {
    1:  ("F","T","N/A",3,"F"),
    2:  ("T","T","T",  4,"N/A"),
    3:  ("T","T","N/A",4,"N/A"),
    4:  ("F","T","N/A",2,"F"),
    5:  ("F","T","N/A",4,"N/A"),
    6:  ("T","T","T",  4,"N/A"),
    7:  ("F","T","F",  1,"N/A"),
    8:  ("F","F","F",  1,"N/A"),
    9:  ("F","T","N/A",2,"F"),
    10: ("F","F","F",  1,"N/A"),
    11: ("F","T","N/A",2,"F"),
    12: ("F","F","N/A",0,"N/A"),
    13: ("T","T","N/A",3,"F"),
    14: ("T","T","N/A",4,"N/A"),
    15: ("T","T","T",  4,"N/A"),
    16: ("F","T","N/A",2,"F"),
    17: ("F","F","N/A",0,"F"),
}

pass2 = {
    1:  ("F","T","N/A",2,"F"),
    2:  ("T","T","T",  4,"N/A"),
    3:  ("T","T","N/A",4,"N/A"),
    4:  ("F","T","N/A",2,"F"),
    5:  ("F","T","N/A",4,"N/A"),
    6:  ("T","T","T",  4,"N/A"),
    7:  ("F","T","F",  1,"N/A"),
    8:  ("F","F","F",  1,"N/A"),
    9:  ("F","T","N/A",2,"F"),
    10: ("F","F","F",  1,"N/A"),
    11: ("F","T","N/A",2,"F"),
    12: ("F","F","N/A",0,"N/A"),
    13: ("T","T","N/A",3,"F"),
    14: ("T","T","N/A",4,"N/A"),
    15: ("T","T","T",  4,"N/A"),
    16: ("F","T","N/A",2,"F"),
    17: ("F","F","N/A",0,"F"),
}

dims = ["signal_grounded","banned_phrases_clean","bench_gate_respected",
        "tone_score","segment_correct"]

def cohen_kappa(p1_list, p2_list):
    from collections import Counter
    labels = sorted(set(p1_list + p2_list))
    n = len(p1_list)
    # Observed agreement
    po = sum(1 for a,b in zip(p1_list,p2_list) if a==b) / n
    # Expected agreement
    c1 = Counter(p1_list)
    c2 = Counter(p2_list)
    pe = sum((c1[l]/n)*(c2[l]/n) for l in labels)
    if pe == 1:
        return 1.0
    return round((po - pe) / (1 - pe), 3)

def pct_agreement(p1_list, p2_list):
    n = len(p1_list)
    return round(100 * sum(1 for a,b in zip(p1_list,p2_list) if a==b) / n, 1)

print(f"{'Dimension':<25} {'Agreement%':>12} {'Kappa':>8} {'Status':>8}")
print("-" * 58)

all_pass = True
for i, dim in enumerate(dims):
    p1 = [v[i] for v in pass1.values() if v[i] != "N/A"]
    p2 = [v[i] for v in pass2.values() if v[i] != "N/A"]
    # Match only tasks where both are applicable
    applicable = [(pass1[t][i], pass2[t][i])
                  for t in pass1 if pass1[t][i] != "N/A" and pass2[t][i] != "N/A"]
    if not applicable:
        print(f"{dim:<25} {'N/A':>12} {'N/A':>8} {'N/A':>8}")
        continue
    p1a = [x[0] for x in applicable]
    p2a = [x[1] for x in applicable]
    # Convert tone_score to string for kappa
    p1a = [str(x) for x in p1a]
    p2a = [str(x) for x in p2a]
    pct = pct_agreement(p1a, p2a)
    kappa = cohen_kappa(p1a, p2a)
    status = "✅ PASS" if pct >= 80 else "❌ REVISE"
    if pct < 80:
        all_pass = False
    print(f"{dim:<25} {pct:>11}% {kappa:>8} {status:>8}")

print("-" * 58)
print(f"\nOverall status: {'✅ All dimensions >= 80%' if all_pass else '❌ Some dimensions need rubric revision'}")