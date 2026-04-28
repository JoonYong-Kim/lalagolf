from collections import defaultdict
from math import sqrt

from src.expected_value import annotate_expected_scores
from src.shot_model import normalize_shot_states


CATEGORY_ORDER = [
    "off_the_tee",
    "approach",
    "short_game",
    "putting",
    "recovery",
    "penalty_impact",
]


def build_historical_shot_facts(raw_trend_data):
    rounds = {}

    for row in raw_trend_data:
        round_id = row.get("round_id")
        if round_id is None:
            continue

        if round_id not in rounds:
            rounds[round_id] = {
                "round_info": {"id": round_id},
                "holes": {},
                "shots": [],
            }

        round_data = rounds[round_id]
        holenum = row.get("holenum")
        if holenum is not None and row.get("hole_par") is not None:
            round_data["holes"][holenum] = {
                "holenum": holenum,
                "par": row.get("hole_par"),
                "score": row.get("hole_score"),
                "putt": row.get("putt"),
            }

        if holenum is None or row.get("club") is None:
            continue

        round_data["shots"].append(
            {
                "holenum": holenum,
                "club": row.get("club"),
                "on": row.get("shotplace"),
                "retplace": row.get("retplace"),
                "distance": row.get("distance"),
                "score": row.get("shot_score"),
                "penalty": row.get("penalty"),
                "feel": row.get("feelgrade"),
                "result": row.get("retgrade"),
            }
        )

    shot_facts = []
    for round_data in rounds.values():
        holes = [round_data["holes"][key] for key in sorted(round_data["holes"].keys())]
        shot_facts.extend(
            normalize_shot_states(
                round_data["round_info"],
                holes,
                round_data["shots"],
            )
        )
    return shot_facts


def build_shot_values(shot_facts, expected_table, min_samples=1, min_samples_by_level=None):
    annotated_facts = annotate_expected_scores(
        shot_facts,
        expected_table,
        min_samples=min_samples,
        min_samples_by_level=min_samples_by_level,
    )
    enriched_facts = []

    for fact in annotated_facts:
        shot_cost = (fact.get("score_cost") or 0) + (fact.get("penalty_strokes") or 0)
        shot_value = None
        if fact.get("expected_before") is not None:
            shot_value = fact["expected_before"] - (shot_cost + (fact.get("expected_after") or 0))

        enriched_fact = dict(fact)
        enriched_fact["shot_cost"] = shot_cost
        enriched_fact["shot_value"] = shot_value
        enriched_facts.append(enriched_fact)

    return enriched_facts


def _summarize_group(values):
    count = len(values)
    total = sum(values)
    return {
        "count": count,
        "total_shot_value": total,
        "avg_shot_value": total / count if count else 0,
    }


def summarize_shot_values(shot_facts):
    category_values = defaultdict(list)
    club_group_values = defaultdict(list)
    covered_shots = 0
    total_shot_value = 0.0
    penalty_impact_total = 0.0

    for fact in shot_facts:
        shot_value = fact.get("shot_value")
        if shot_value is None:
            continue

        covered_shots += 1
        total_shot_value += shot_value
        category_values[fact.get("shot_category")].append(shot_value)
        club_group_values[fact.get("club_group")].append(shot_value)

        if fact.get("penalty_strokes"):
            penalty_impact_total -= fact["penalty_strokes"]

    category_summary = []
    for category in CATEGORY_ORDER:
        if category == "penalty_impact":
            category_summary.append(
                {
                    "category": category,
                    "count": sum(1 for fact in shot_facts if fact.get("penalty_strokes")),
                    "total_shot_value": penalty_impact_total,
                    "avg_shot_value": (
                        penalty_impact_total / sum(1 for fact in shot_facts if fact.get("penalty_strokes"))
                        if any(fact.get("penalty_strokes") for fact in shot_facts)
                        else 0
                    ),
                }
            )
            continue

        values = category_values.get(category, [])
        category_summary.append({"category": category, **_summarize_group(values)})

    club_group_summary = []
    for club_group in sorted(club_group_values.keys()):
        club_group_summary.append(
            {
                "club_group": club_group,
                **_summarize_group(club_group_values[club_group]),
            }
        )

    return {
        "covered_shots": covered_shots,
        "coverage_rate": covered_shots / len(shot_facts) if shot_facts else 0,
        "total_shot_value": total_shot_value,
        "avg_shot_value": total_shot_value / covered_shots if covered_shots else 0,
        "category_summary": category_summary,
        "club_group_summary": club_group_summary,
    }


def summarize_shot_values_by_round(shot_facts):
    by_round = defaultdict(list)
    for fact in shot_facts:
        round_id = fact.get("round_id")
        if round_id is None:
            continue
        by_round[round_id].append(fact)

    return {
        round_id: summarize_shot_values(round_facts)
        for round_id, round_facts in by_round.items()
    }


def summarize_category_window(round_summaries):
    category_totals = defaultdict(lambda: {"count": 0, "total_shot_value": 0.0})
    covered_shots = 0

    for summary in round_summaries:
        covered_shots += summary.get("covered_shots", 0)
        for item in summary.get("category_summary", []):
            bucket = category_totals[item["category"]]
            bucket["count"] += item["count"]
            bucket["total_shot_value"] += item["total_shot_value"]

    category_rows = []
    for category in CATEGORY_ORDER:
        totals = category_totals[category]
        count = totals["count"]
        total_value = totals["total_shot_value"]
        category_rows.append(
            {
                "category": category,
                "count": count,
                "total_shot_value": total_value,
                "avg_shot_value": total_value / count if count else 0,
                "share_of_covered_shots": count / covered_shots if covered_shots else 0,
            }
        )

    return {
        "covered_shots": covered_shots,
        "category_summary": category_rows,
    }


def _mean(values):
    return sum(values) / len(values) if values else 0


def _stddev(values):
    if len(values) < 2:
        return 0
    avg = _mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _percentile(values, percentile):
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * percentile
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    weight = index - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def _sample_label(count):
    if count >= 20:
        return "high"
    if count >= 10:
        return "medium"
    return "low"


def summarize_club_reliability(shot_facts, min_samples=5):
    buckets = defaultdict(lambda: {
        "distances": [],
        "shot_values": [],
        "result_c_count": 0,
        "penalty_count": 0,
        "total_count": 0,
    })

    for fact in shot_facts:
        club_group = fact.get("club_group")
        if not club_group:
            continue

        bucket = buckets[club_group]
        bucket["total_count"] += 1
        if fact.get("distance") is not None:
            bucket["distances"].append(fact["distance"])
        if fact.get("shot_value") is not None:
            bucket["shot_values"].append(fact["shot_value"])
        if fact.get("result") == "C":
            bucket["result_c_count"] += 1
        if fact.get("penalty_strokes", 0) > 0:
            bucket["penalty_count"] += 1

    summary = []
    for club_group in sorted(buckets.keys()):
        bucket = buckets[club_group]
        if bucket["total_count"] < min_samples:
            continue

        avg_shot_value = _mean(bucket["shot_values"])
        result_c_rate = bucket["result_c_count"] / bucket["total_count"] if bucket["total_count"] else 0
        penalty_rate = bucket["penalty_count"] / bucket["total_count"] if bucket["total_count"] else 0

        if penalty_rate >= 0.12 or result_c_rate >= 0.35 or avg_shot_value <= -0.12:
            risk_level = "high"
        elif penalty_rate >= 0.06 or result_c_rate >= 0.22 or avg_shot_value <= -0.05:
            risk_level = "medium"
        else:
            risk_level = "low"

        summary.append(
            {
                "club_group": club_group,
                "sample_count": bucket["total_count"],
                "sample_level": _sample_label(bucket["total_count"]),
                "avg_distance": _mean(bucket["distances"]),
                "distance_stddev": _stddev(bucket["distances"]),
                "avg_shot_value": avg_shot_value,
                "shot_value_stddev": _stddev(bucket["shot_values"]),
                "shot_value_p25": _percentile(bucket["shot_values"], 0.25),
                "result_c_rate": result_c_rate,
                "penalty_rate": penalty_rate,
                "risk_level": risk_level,
            }
        )

    summary.sort(key=lambda item: (item["risk_level"] != "high", item["avg_shot_value"]))
    return summary


def summarize_tee_strategy_comparison(shot_facts, min_samples=5):
    strategy_map = {
        "D": "Driver",
        "W": "Wood/Utility",
        "U": "Wood/Utility",
    }
    buckets = defaultdict(lambda: {
        "shot_values": [],
        "penalty_count": 0,
        "result_c_count": 0,
        "count": 0,
    })

    for fact in shot_facts:
        if fact.get("shot_category") != "off_the_tee":
            continue
        if fact.get("par_type") not in {4, 5}:
            continue
        strategy = strategy_map.get(fact.get("club_group"))
        if strategy is None:
            continue

        key = (fact.get("par_type"), strategy)
        bucket = buckets[key]
        bucket["count"] += 1
        if fact.get("shot_value") is not None:
            bucket["shot_values"].append(fact["shot_value"])
        if fact.get("penalty_strokes", 0) > 0:
            bucket["penalty_count"] += 1
        if fact.get("result") == "C":
            bucket["result_c_count"] += 1

    rows = []
    for par_type in [4, 5]:
        for strategy in ["Driver", "Wood/Utility"]:
            bucket = buckets[(par_type, strategy)]
            rows.append(
                {
                    "par_type": par_type,
                    "strategy": strategy,
                    "sample_count": bucket["count"],
                    "sample_ok": bucket["count"] >= min_samples,
                    "avg_shot_value": _mean(bucket["shot_values"]),
                    "shot_value_stddev": _stddev(bucket["shot_values"]),
                    "shot_value_p25": _percentile(bucket["shot_values"], 0.25),
                    "penalty_rate": bucket["penalty_count"] / bucket["count"] if bucket["count"] else 0,
                    "result_c_rate": bucket["result_c_count"] / bucket["count"] if bucket["count"] else 0,
                    "risk_index": (
                        (bucket["penalty_count"] / bucket["count"] if bucket["count"] else 0) * 2
                        + (bucket["result_c_count"] / bucket["count"] if bucket["count"] else 0)
                        + _stddev(bucket["shot_values"])
                        + abs(min(_percentile(bucket["shot_values"], 0.25), 0))
                    ),
                }
            )

    available = [
        row for row in rows
        if row["sample_ok"]
    ]
    comparison_ready = all(
        any(row["par_type"] == par_type and row["strategy"] == strategy and row["sample_ok"] for row in rows)
        for par_type in [4, 5]
        for strategy in ["Driver", "Wood/Utility"]
    )

    warnings = []
    if not comparison_ready:
        warnings.append(
            f"전략 비교는 최근 표본이 각 그룹당 최소 {min_samples}개일 때만 신뢰할 수 있습니다."
        )

    insights = []
    for par_type in [4, 5]:
        driver_row = next((row for row in rows if row["par_type"] == par_type and row["strategy"] == "Driver"), None)
        safe_row = next((row for row in rows if row["par_type"] == par_type and row["strategy"] == "Wood/Utility"), None)
        if not driver_row or not safe_row or not driver_row["sample_ok"] or not safe_row["sample_ok"]:
            continue

        if driver_row["avg_shot_value"] > safe_row["avg_shot_value"] + 0.03:
            insights.append(f"Par {par_type}에서는 Driver의 평균 shot value가 더 좋습니다.")
        elif safe_row["avg_shot_value"] > driver_row["avg_shot_value"] + 0.03:
            insights.append(f"Par {par_type}에서는 Wood/Utility의 평균 shot value가 더 안정적입니다.")

        if driver_row["risk_index"] > safe_row["risk_index"] + 0.08:
            insights.append(f"Par {par_type} Driver의 리스크가 더 높아 위험 홀에서는 대체 클럽 선택 여지가 큽니다.")
        if driver_row["shot_value_p25"] < safe_row["shot_value_p25"] - 0.05:
            insights.append(f"Par {par_type} Driver는 하위 25% 미스 폭이 더 커서 큰 실수 위험이 큽니다.")

    return {
        "min_samples": min_samples,
        "comparison_ready": comparison_ready,
        "rows": rows,
        "warnings": warnings,
        "insights": insights[:4],
    }


def summarize_approach_strategy_comparison(shot_facts, min_samples=5):
    buckets = defaultdict(lambda: {
        "count": 0,
        "shot_values": [],
        "penalty_count": 0,
        "result_c_count": 0,
    })

    for fact in shot_facts:
        if fact.get("shot_category") != "approach":
            continue
        distance = fact.get("distance")
        if distance is None or distance < 120:
            continue

        distance_band = "160m+" if distance >= 160 else "120-160m"
        strategy = "attack" if fact.get("end_state") == "green" else "layup_proxy"
        key = (distance_band, strategy)
        bucket = buckets[key]
        bucket["count"] += 1
        if fact.get("shot_value") is not None:
            bucket["shot_values"].append(fact["shot_value"])
        if fact.get("penalty_strokes", 0) > 0:
            bucket["penalty_count"] += 1
        if fact.get("result") == "C":
            bucket["result_c_count"] += 1

    rows = []
    for distance_band in ["120-160m", "160m+"]:
        for strategy in ["attack", "layup_proxy"]:
            bucket = buckets[(distance_band, strategy)]
            rows.append(
                {
                    "distance_band": distance_band,
                    "strategy": strategy,
                    "sample_count": bucket["count"],
                    "sample_ok": bucket["count"] >= min_samples,
                    "avg_shot_value": _mean(bucket["shot_values"]),
                    "shot_value_stddev": _stddev(bucket["shot_values"]),
                    "shot_value_p25": _percentile(bucket["shot_values"], 0.25),
                    "penalty_rate": bucket["penalty_count"] / bucket["count"] if bucket["count"] else 0,
                    "result_c_rate": bucket["result_c_count"] / bucket["count"] if bucket["count"] else 0,
                    "risk_index": (
                        (bucket["penalty_count"] / bucket["count"] if bucket["count"] else 0) * 2
                        + (bucket["result_c_count"] / bucket["count"] if bucket["count"] else 0)
                        + _stddev(bucket["shot_values"])
                        + abs(min(_percentile(bucket["shot_values"], 0.25), 0))
                    ),
                }
            )

    comparison_ready = all(
        any(row["distance_band"] == distance_band and row["strategy"] == strategy and row["sample_ok"] for row in rows)
        for distance_band in ["120-160m", "160m+"]
        for strategy in ["attack", "layup_proxy"]
    )

    warnings = []
    if not comparison_ready:
        warnings.append(
            f"layup vs 공격 비교는 최근 표본이 각 그룹당 최소 {min_samples}개일 때만 신뢰할 수 있습니다."
        )
        warnings.append("현재 비교는 샷 의도가 아니라 결과 상태를 기준으로 분류한 proxy입니다.")

    insights = []
    for distance_band in ["120-160m", "160m+"]:
        attack_row = next((row for row in rows if row["distance_band"] == distance_band and row["strategy"] == "attack"), None)
        layup_row = next((row for row in rows if row["distance_band"] == distance_band and row["strategy"] == "layup_proxy"), None)
        if not attack_row or not layup_row or not attack_row["sample_ok"] or not layup_row["sample_ok"]:
            continue

        if attack_row["avg_shot_value"] > layup_row["avg_shot_value"] + 0.03:
            insights.append(f"{distance_band}에서는 green 직접 공략 패턴의 평균 shot value가 더 좋습니다.")
        elif layup_row["avg_shot_value"] > attack_row["avg_shot_value"] + 0.03:
            insights.append(f"{distance_band}에서는 layup proxy 패턴이 평균 손실이 더 적습니다.")

        if attack_row["risk_index"] > layup_row["risk_index"] + 0.08:
            insights.append(f"{distance_band} 공격 패턴의 리스크가 더 높아 위험 핀에서는 보수적 선택이 유리할 수 있습니다.")
        if attack_row["shot_value_p25"] < layup_row["shot_value_p25"] - 0.05:
            insights.append(f"{distance_band} 공격 패턴은 하위 25% 결과가 더 나빠 큰 미스 비용이 큽니다.")

    return {
        "min_samples": min_samples,
        "comparison_ready": comparison_ready,
        "rows": rows,
        "warnings": warnings,
        "insights": insights[:4],
    }
