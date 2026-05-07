# GolfRaiders v2 Insight Dedupe

## 1. Purpose

GolfRaiders v2 should reduce repeated recommendation cards by grouping the same root cause, evidence, and action into one insight unit.

MVP dedupe is deterministic and explainable. Semantic clustering and LLM-based dedupe are post-MVP.

## 2. Insight Unit Shape

Every persisted insight should support:

- `problem`: what is going wrong or improving
- `evidence`: the metric, sample count, and comparison behind the claim
- `impact`: how it affects score or round outcome
- `next_action`: what the user should try next
- `confidence`: low, medium, or high

## 3. MVP Dedupe Key

Initial dedupe key:

```text
scope_type + scope_key + category + root_cause + primary_evidence_metric
```

Examples:

- `window:last_10 + tee + penalty_rate + driver_penalty_strokes`
- `window:last_10 + putting + three_putt + three_putt_rate`
- `round:<id> + approach + miss_short + approach_short_miss_rate`

## 4. Priority Score Inputs

MVP priority score should be based on deterministic inputs:

- estimated score impact
- recentness
- sample count
- confidence
- whether the same issue has appeared across multiple rounds
- whether the user has dismissed similar insights

MVP weighting:

```text
priority_score =
  abs(estimated_score_impact)
  + confidence_weight
  + min(sample_count, 20) * 0.02
```

Confidence weights:

- low: `0.0`
- medium: `0.25`
- high: `0.5`

## 5. Evidence Suppression

- Do not show multiple active dashboard insights with the same primary evidence metric.
- Do not show multiple active dashboard insights from the same category in the default top-3.
- If multiple insights share evidence, keep the higher priority one and link secondary explanations in detail.
- Dashboard default is max 3 active insights.
- Analysis pages may keep a small deduplicated set for the current tab/filter, but the UI presents
  one insight at a time in a switchable widget instead of stacking repeated cards.
- Insight display text should remain concise. Long evidence/impact/action text can be truncated in
  the UI with the full text available through hover/title or detail affordances.
- Practice and goal actions derived from an insight should be expressed at the same level: plan
  selection creates a practice plan, goal selection creates the measurable next-round goal.

## 6. Required Example Set

Before finalizing M5 acceptance, collect 10-20 v1 examples that feel duplicated in the current UI.

For each example:

- source screen
- duplicated text or metric
- suspected root cause
- proposed dedupe key
- expected merged insight

## 7. Example Log

| ID | Source | Duplicate Pattern | Proposed Key | Expected Result |
| --- | --- | --- | --- | --- |
| P5-001 | Dashboard | 페널티 총량과 티샷 페널티가 별도 카드로 반복 | `window:all:penalty_impact:penalty_strokes:penalty_strokes` | 페널티 영향 insight unit 1개만 노출 |
| P5-002 | Analysis / Putting | 평균 퍼트와 3퍼트 경고가 같은 근거로 반복 | `window:all:putting:three_putt:three_putt_rate` | 3퍼트 insight unit 1개로 evidence/impact/action 통합 |
| P5-003 | Analysis / Category | 어프로치 손실과 클럽 손실이 같은 shot value 근거로 반복 | `window:all:approach:shot_value_loss:approach_shot_value` | approach 손실 insight 1개를 우선 노출 |
| P5-004 | Dashboard | 평균 스코어 요약과 기준선 설명이 중복 | `window:all:score:baseline:average_score` | 낮은 우선순위 기준선 insight로만 유지 |
