from collections import defaultdict

from lalagolf_analytics_core.analytics_config import (
    EXPECTED_SCORE_MIN_SAMPLES_BY_LEVEL,
    EXPECTED_SCORE_RECENCY_DECAY,
)


FALLBACK_LEVELS = [
    ("full", ("start_state", "distance_bucket", "par_type", "shot_category")),
    ("no_par", ("start_state", "distance_bucket", "shot_category")),
    ("no_distance", ("start_state", "par_type", "shot_category")),
    ("start_category", ("start_state", "shot_category")),
    ("start_only", ("start_state",)),
]

EXPECTED_SCORE_SCOPE_ORDER = ("user", "global", "baseline")
HIGH_CONFIDENCE_LOOKUP_LEVELS = {"full", "no_par", "no_distance"}


def _group_facts_by_hole(shot_facts):
    grouped = defaultdict(list)
    for fact in shot_facts:
        grouped[(fact.get("round_id"), fact.get("hole_num"))].append(fact)
    for facts in grouped.values():
        facts.sort(key=lambda item: item.get("shot_num", 0))
    return grouped


def _remaining_strokes_map(shot_facts):
    remaining = {}
    grouped = _group_facts_by_hole(shot_facts)
    for key, facts in grouped.items():
        running_total = 0
        remaining_costs = [0] * len(facts)
        for idx in range(len(facts) - 1, -1, -1):
            fact = facts[idx]
            running_total += (fact.get("score_cost") or 0) + (fact.get("penalty_strokes") or 0)
            remaining_costs[idx] = running_total
        for idx, fact in enumerate(facts):
            remaining[(fact.get("round_id"), fact.get("hole_num"), fact.get("shot_num"))] = remaining_costs[idx]
    return remaining


def make_state_key(fact, fields):
    return tuple(fact.get(field) for field in fields)


def build_round_recency_weights(raw_trend_data, decay=EXPECTED_SCORE_RECENCY_DECAY):
    round_dates = {}
    for row in raw_trend_data:
        round_id = row.get("round_id")
        playdate = row.get("playdate")
        if round_id is None or playdate is None:
            continue
        round_dates[round_id] = playdate

    sorted_rounds = sorted(round_dates.items(), key=lambda item: item[1], reverse=True)
    return {
        round_id: decay ** idx
        for idx, (round_id, _) in enumerate(sorted_rounds)
    }


def build_expected_score_table(shot_facts, min_samples_by_level=None, prune_low_sample=True, round_weights=None):
    level_thresholds = min_samples_by_level or EXPECTED_SCORE_MIN_SAMPLES_BY_LEVEL
    remaining_map = _remaining_strokes_map(shot_facts)
    aggregates = {
        level_name: defaultdict(lambda: {"weighted_total": 0.0, "count": 0, "weighted_count": 0.0})
        for level_name, _ in FALLBACK_LEVELS
    }

    for fact in shot_facts:
        remaining_strokes = remaining_map[(fact.get("round_id"), fact.get("hole_num"), fact.get("shot_num"))]
        round_weight = 1.0
        if round_weights is not None:
            round_weight = round_weights.get(fact.get("round_id"), 1.0)
        for level_name, fields in FALLBACK_LEVELS:
            key = make_state_key(fact, fields)
            bucket = aggregates[level_name][key]
            bucket["weighted_total"] += remaining_strokes * round_weight
            bucket["count"] += 1
            bucket["weighted_count"] += round_weight

    table = {}
    for level_name, buckets in aggregates.items():
        table[level_name] = {}
        for key, values in buckets.items():
            if prune_low_sample and values["count"] < level_thresholds.get(level_name, 1):
                continue
            table[level_name][key] = {
                "expected_strokes": values["weighted_total"] / values["weighted_count"] if values["weighted_count"] else 0,
                "sample_count": values["count"],
                "weighted_sample_count": values["weighted_count"],
            }
    return table


def lookup_expected_score(fact, expected_table, min_samples=1, min_samples_by_level=None):
    level_thresholds = min_samples_by_level or EXPECTED_SCORE_MIN_SAMPLES_BY_LEVEL
    for level_name, fields in FALLBACK_LEVELS:
        key = make_state_key(fact, fields)
        level_table = expected_table.get(level_name, {})
        state_stats = level_table.get(key)
        required_samples = level_thresholds.get(level_name, min_samples)
        if state_stats and state_stats["sample_count"] >= required_samples:
            return {
                "expected_strokes": state_stats["expected_strokes"],
                "sample_count": state_stats["sample_count"],
                "level": level_name,
                "key": key,
            }
    return None


def lookup_expected_score_with_fallback(
    fact,
    scoped_expected_tables,
    min_samples=1,
    min_samples_by_level=None,
    scope_order=EXPECTED_SCORE_SCOPE_ORDER,
):
    level_thresholds = min_samples_by_level or EXPECTED_SCORE_MIN_SAMPLES_BY_LEVEL
    tables_by_scope = _index_scoped_expected_tables(scoped_expected_tables)
    scope_order = scope_order or EXPECTED_SCORE_SCOPE_ORDER

    for level_name, fields in FALLBACK_LEVELS:
        key = make_state_key(fact, fields)

        for scope_type in scope_order:
            candidate = tables_by_scope.get(scope_type)
            if not candidate:
                continue

            level_table = candidate["table"].get(level_name, {})
            state_stats = level_table.get(key)
            required_samples = level_thresholds.get(level_name, min_samples)
            candidate_min_samples_by_level = candidate.get("min_samples_by_level")
            if candidate_min_samples_by_level:
                required_samples = candidate_min_samples_by_level.get(level_name, required_samples)
            if state_stats and state_stats["sample_count"] >= required_samples:
                confidence = _expected_lookup_confidence(
                    source_scope=scope_type,
                    level_name=level_name,
                )
                return {
                    "expected_strokes": state_stats["expected_strokes"],
                    "sample_count": state_stats["sample_count"],
                    "level": level_name,
                    "key": key,
                    "source_scope": scope_type,
                    "confidence": confidence,
                }
    return None


def annotate_expected_scores_with_fallback(
    shot_facts,
    scoped_expected_tables,
    min_samples=1,
    min_samples_by_level=None,
    scope_order=EXPECTED_SCORE_SCOPE_ORDER,
):
    scope_order = scope_order or EXPECTED_SCORE_SCOPE_ORDER
    annotated = []
    grouped = _group_facts_by_hole(shot_facts)

    for facts in grouped.values():
        for idx, fact in enumerate(facts):
            annotated_fact = dict(fact)
            before = lookup_expected_score_with_fallback(
                fact,
                scoped_expected_tables,
                min_samples=min_samples,
                min_samples_by_level=min_samples_by_level,
                scope_order=scope_order,
            )
            after = None
            if idx + 1 < len(facts):
                after = lookup_expected_score_with_fallback(
                    facts[idx + 1],
                    scoped_expected_tables,
                    min_samples=min_samples,
                    min_samples_by_level=min_samples_by_level,
                    scope_order=scope_order,
                )

            annotated_fact["expected_before"] = before["expected_strokes"] if before else None
            annotated_fact["expected_after"] = after["expected_strokes"] if after else 0
            annotated_fact["expected_lookup_level"] = before["level"] if before else None
            annotated_fact["expected_sample_count"] = before["sample_count"] if before else 0
            annotated_fact["expected_source_scope"] = before["source_scope"] if before else None
            annotated_fact["expected_confidence"] = before["confidence"] if before else "low"
            annotated.append(annotated_fact)

    return annotated


def annotate_expected_scores(shot_facts, expected_table, min_samples=1, min_samples_by_level=None):
    annotated = []
    grouped = _group_facts_by_hole(shot_facts)

    for facts in grouped.values():
        for idx, fact in enumerate(facts):
            annotated_fact = dict(fact)
            before = lookup_expected_score(
                fact,
                expected_table,
                min_samples=min_samples,
                min_samples_by_level=min_samples_by_level,
            )
            after = None
            if idx + 1 < len(facts):
                after = lookup_expected_score(
                    facts[idx + 1],
                    expected_table,
                    min_samples=min_samples,
                    min_samples_by_level=min_samples_by_level,
                )

            annotated_fact["expected_before"] = before["expected_strokes"] if before else None
            annotated_fact["expected_after"] = after["expected_strokes"] if after else 0
            annotated_fact["expected_lookup_level"] = before["level"] if before else None
            annotated_fact["expected_sample_count"] = before["sample_count"] if before else 0
            annotated.append(annotated_fact)

    return annotated


def _index_scoped_expected_tables(scoped_expected_tables):
    indexed = {}
    for candidate in scoped_expected_tables:
        scope_type = candidate.get("scope_type")
        expected_table = candidate.get("table")
        if not scope_type or expected_table is None:
            continue
        indexed[scope_type] = candidate
    return indexed


def _expected_lookup_confidence(source_scope, level_name):
    if source_scope == "user" and level_name in HIGH_CONFIDENCE_LOOKUP_LEVELS:
        return "high"
    if source_scope == "user":
        return "medium"
    if level_name in HIGH_CONFIDENCE_LOOKUP_LEVELS:
        return "medium"
    return "low"
