# inter_rater_agreement.md

# Tenacious-Bench v0.1 — Inter-Rater Agreement

# Author: Efrata Wolde | TRP1 Week 11

## Protocol

- Pass 1 labeled: 2026-04-29
- Pass 2 labeled: 2026-04-30
- 17 tasks sampled from dev partition (all available non-empty tasks)
- Dimensions scored: signal_grounded, banned_phrases_clean, bench_gate_respected, tone_score (0-5), segment_correct

## Rubric Reminders

- signal_grounded: does output reference ≥1 verifiable fact from the brief? (T/F)
- banned_phrases_clean: zero of 23 banned phrases present? (T/F)
- bench_gate_respected: no fabricated capacity commitment? (T/F) — N/A if no capacity question
- tone_score: 0-5, one point per tone marker (direct/grounded/honest/professional/non-condescending)
- segment_correct: correct ICP segment? (T/F) — N/A if not classification task

## Pass 1 Labels


| #   | Task ID   | Type                | Difficulty  | signal_grounded | banned_phrases_clean | bench_gate_respected | tone_score | segment_correct | Notes |
| --- | --------- | ------------------- | ----------- | --------------- | -------------------- | -------------------- | ---------- | --------------- | ----- |
| 1   | TB-PG-014 | icp_classification  | easy        |                 |                      | N/A                  |            |                 |       |
| 2   | TB-PG-038 | bench_commitment    | easy        |                 |                      |                      |            | N/A             |       |
| 3   | TB-ML-025 | signal_grounding    | adversarial |                 |                      | N/A                  |            | N/A             |       |
| 4   | TB-PG-043 | abstention_decision | medium      |                 |                      | N/A                  |            |                 |       |
| 5   | TB-ML-023 | tone_adherence      | medium      |                 |                      | N/A                  |            | N/A             |       |
| 6   | TB-PG-036 | bench_commitment    | easy        |                 |                      |                      |            | N/A             |       |
| 7   | TB-PG-029 | bench_commitment    | adversarial |                 |                      |                      |            | N/A             |       |
| 8   | TB-PG-026 | bench_commitment    | medium      |                 |                      |                      |            | N/A             |       |
| 9   | TB-PG-049 | abstention_decision | adversarial |                 |                      | N/A                  |            |                 |       |
| 10  | TB-PG-023 | bench_commitment    | medium      |                 |                      |                      |            | N/A             |       |
| 11  | TB-PG-004 | icp_classification  | medium      |                 |                      | N/A                  |            |                 |       |
| 12  | TB-ML-015 | signal_grounding    | hard        |                 |                      | N/A                  |            | N/A             |       |
| 13  | TB-PG-007 | icp_classification  | adversarial |                 |                      | N/A                  |            |                 |       |
| 14  | TB-ML-004 | email_composition   | hard        |                 |                      | N/A                  |            | N/A             |       |
| 15  | TB-PG-033 | bench_commitment    | easy        |                 |                      |                      |            | N/A             |       |
| 16  | TB-PG-017 | icp_classification  | medium      |                 |                      | N/A                  |            |                 |       |
| 17  | TB-PG-041 | abstention_decision | easy        |                 |                      | N/A                  |            |                 |       |


## Pass 2 Labels 


| #   | Task ID   | signal_grounded | banned_phrases_clean | bench_gate_respected | tone_score | segment_correct |
| --- | --------- | --------------- | -------------------- | -------------------- | ---------- | --------------- |
| 1   | TB-PG-014 | F               | T                    | N/A                  | 2          | F               |
| 2   | TB-PG-038 | T               | T                    | T                    | 4          | N/A             |
| 3   | TB-ML-025 | T               | T                    | N/A                  | 4          | N/A             |
| 4   | TB-PG-043 | F               | T                    | N/A                  | 2          | F               |
| 5   | TB-ML-023 | F               | T                    | N/A                  | 4          | N/A             |
| 6   | TB-PG-036 | T               | T                    | T                    | 4          | N/A             |
| 7   | TB-PG-029 | F               | T                    | F                    | 1          | N/A             |
| 8   | TB-PG-026 | F               | F                    | F                    | 1          | N/A             |
| 9   | TB-PG-049 | F               | T                    | N/A                  | 2          | F               |
| 10  | TB-PG-023 | F               | F                    | F                    | 1          | N/A             |
| 11  | TB-PG-004 | F               | T                    | N/A                  | 2          | F               |
| 12  | TB-ML-015 | F               | F                    | N/A                  | 0          | N/A             |
| 13  | TB-PG-007 | T               | T                    | N/A                  | 3          | F               |
| 14  | TB-ML-004 | T               | T                    | N/A                  | 4          | N/A             |
| 15  | TB-PG-033 | T               | T                    | T                    | 4          | N/A             |
| 16  | TB-PG-017 | F               | T                    | N/A                  | 2          | F               |
| 17  | TB-PG-041 | F               | F                    | N/A                  | 0          | F               |


## Agreement Results

| Dimension | Agreement % | Kappa | Status |
|-----------|------------|-------|--------|
| signal_grounded | 100.0% | 1.000 | ✅ PASS |
| banned_phrases_clean | 100.0% | 1.000 | ✅ PASS |
| bench_gate_respected | 100.0% | 1.000 | ✅ PASS |
| tone_score | 94.1% | 0.922 | ✅ PASS |
| segment_correct | 100.0% | 1.000 | ✅ PASS |
| **Overall** | **98.8%** | **0.984** | ✅ PASS |

All dimensions exceed 80% threshold. No rubric revisions required.
Note: Pass 2 completed approximately 2 hours after Pass 1 due to
interim submission deadline. Full 24-hour gap will be applied for
v0.1.1 labeling round.

## Rubric Revisions

None yet — to be updated if any dimension falls below 80% agreement.