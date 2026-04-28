from collections import Counter, defaultdict


DISTANCE_BANDS = [
    ("0_30", "0-30m", 0, 30),
    ("30_80", "30-80m", 30, 80),
    ("80_120", "80-120m", 80, 120),
    ("120_160", "120-160m", 120, 160),
    ("160_plus", "160m+", 160, None),
]


def group_shots_by_hole(shots):
    grouped = defaultdict(list)
    for shot in shots:
        holenum = shot.get("holenum")
        if holenum is None:
            continue
        grouped[holenum].append(shot)
    return dict(grouped)


def _safe_rate(numerator, denominator):
    return numerator / denominator if denominator else 0


def _mean(values):
    return sum(values) / len(values) if values else 0


def _hole_has_bunker(shots):
    return any(shot.get("on") == "B" or shot.get("retplace") == "B" for shot in shots)


def _penalty_strokes(penalty):
    if penalty in {"H", "UN"}:
        return 1
    if penalty == "OB":
        return 2
    return 0


def _club_group(club):
    if club == "D":
        return "D"
    if club in {"UW", "W3", "W5"}:
        return "W"
    if club in {"U3", "U4"}:
        return "U"
    if club in {"I3", "I4"}:
        return "LI"
    if club in {"I5", "I6", "I7"}:
        return "MI"
    if club in {"I8", "I9", "IP", "IW", "IA", "48", "52", "56", "58"}:
        return "SI"
    if club == "P":
        return "P"
    return "OTHER"


def _init_distance_band_stats():
    return {
        "shot_count": 0,
        "average_error": 0,
        "result_distribution": {"A": 0, "B": 0, "C": 0},
    }


def _build_distance_band_metrics(shots):
    band_values = {name: {"errors": [], "results": Counter()} for name, _, _, _ in DISTANCE_BANDS}
    for shot in shots:
        if shot.get("club") == "P":
            continue
        distance = shot.get("distance")
        if distance is None:
            continue
        for name, _, low, high in DISTANCE_BANDS:
            if distance >= low and (high is None or distance < high):
                if shot.get("error") is not None:
                    band_values[name]["errors"].append(shot["error"])
                result = shot.get("result")
                if result in {"A", "B", "C"}:
                    band_values[name]["results"][result] += 1
                break

    metrics = {}
    for name, label, _, _ in DISTANCE_BANDS:
        results = band_values[name]["results"]
        metrics[name] = {
            "label": label,
            "shot_count": sum(results.values()) if results else len(band_values[name]["errors"]),
            "average_error": _mean(band_values[name]["errors"]),
            "result_distribution": {
                "A": results.get("A", 0),
                "B": results.get("B", 0),
                "C": results.get("C", 0),
            },
        }
    return metrics


def build_round_metrics(round_info, holes, shots):
    hole_count = len(holes)
    score_to_par = sum(hole.get("diff", 0) for hole in holes)
    shots_by_hole = group_shots_by_hole(shots)

    scoring_counter = Counter()
    par_type_buckets = {
        3: {"count": 0, "total_score": 0, "total_par": 0},
        4: {"count": 0, "total_score": 0, "total_par": 0},
        5: {"count": 0, "total_score": 0, "total_par": 0},
    }

    gir_holes = []
    non_gir_holes = []
    first_putt_distances = []
    one_putt_count = 0
    three_putt_count = 0
    scramble_success = 0
    up_and_down_chances = 0
    up_and_down_success = 0
    bunker_holes = 0
    bunker_saves = 0
    penalty_holes = 0
    tee_shot_penalty_holes = 0
    driver_tee_shots = 0
    driver_penalty_tee_shots = 0
    driver_result_c_tee_shots = 0
    tee_shot_results = Counter()
    tee_shot_clubs = Counter()
    tee_shot_club_scores = defaultdict(list)
    tee_by_par_type = {
        3: defaultdict(list),
        4: defaultdict(list),
        5: defaultdict(list),
    }

    penalty_counts = Counter()
    penalty_by_club_group = Counter()
    penalty_strokes = 0

    under_160_results = Counter()
    under_160_errors = []
    under_160_holes = 0
    under_160_gir_holes = 0

    for hole in holes:
        diff = hole.get("diff", 0)
        if diff <= -1:
            scoring_counter["birdie"] += 1
        elif diff == 0:
            scoring_counter["par"] += 1
        elif diff == 1:
            scoring_counter["bogey"] += 1
        else:
            scoring_counter["double_bogey_plus"] += 1

        par = hole.get("par")
        if par in par_type_buckets:
            par_type_buckets[par]["count"] += 1
            par_type_buckets[par]["total_score"] += hole.get("score", 0)
            par_type_buckets[par]["total_par"] += par

        putt = hole.get("putt", 0) or 0
        if putt == 1:
            one_putt_count += 1
        if putt >= 3:
            three_putt_count += 1

        if hole.get("GIR"):
            gir_holes.append(putt)
        else:
            non_gir_holes.append(putt)
            if hole.get("score", 0) <= hole.get("par", 0):
                scramble_success += 1

        hole_shots = shots_by_hole.get(hole["holenum"], [])
        under_160_hole = False
        up_and_down_hole = False
        bunker_hole = _hole_has_bunker(hole_shots)
        if bunker_hole:
            bunker_holes += 1
            if hole.get("score", 0) <= hole.get("par", 0):
                bunker_saves += 1

        first_putt = next((shot for shot in hole_shots if shot.get("club") == "P"), None)
        if first_putt and first_putt.get("distance") is not None:
            first_putt_distances.append(first_putt["distance"])

        tee_shot = hole_shots[0] if hole_shots else None
        if tee_shot:
            club = tee_shot.get("club")
            tee_shot_clubs[club] += 1
            tee_shot_club_scores[club].append(diff)
            if par in tee_by_par_type:
                tee_by_par_type[par][club].append(diff)
            result = tee_shot.get("result")
            if result in {"A", "B", "C"}:
                tee_shot_results[result] += 1
            if tee_shot.get("penalty"):
                tee_shot_penalty_holes += 1
            if club == "D":
                driver_tee_shots += 1
                if tee_shot.get("penalty"):
                    driver_penalty_tee_shots += 1
                if result == "C":
                    driver_result_c_tee_shots += 1

        hole_has_penalty = False
        for shot in hole_shots:
            penalty = shot.get("penalty")
            if penalty:
                hole_has_penalty = True
                penalty_counts[penalty] += 1
                penalty_strokes += _penalty_strokes(penalty)
                penalty_by_club_group[_club_group(shot.get("club"))] += 1

            if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] < 160:
                under_160_hole = True
                result = shot.get("result")
                if result in {"A", "B", "C"}:
                    under_160_results[result] += 1
                if shot.get("error") is not None:
                    under_160_errors.append(shot["error"])
            if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] <= 30:
                up_and_down_hole = True

        if hole_has_penalty:
            penalty_holes += 1
        if under_160_hole:
            under_160_holes += 1
            if hole.get("GIR"):
                under_160_gir_holes += 1
        if not hole.get("GIR") and up_and_down_hole:
            up_and_down_chances += 1
            if hole.get("score", 0) <= hole.get("par", 0):
                up_and_down_success += 1

    total_putts = sum((hole.get("putt", 0) or 0) for hole in holes)
    total_tee_shots = sum(tee_shot_clubs.values())
    sorted_tee_club_usage = sorted(tee_shot_clubs.items(), key=lambda item: (-item[1], item[0]))
    sorted_tee_club_scores = sorted(tee_shot_club_scores.items(), key=lambda item: item[0])

    par_type_metrics = {}
    for par_value, bucket in par_type_buckets.items():
        par_type_metrics[f"par{par_value}"] = {
            "count": bucket["count"],
            "avg_score": _safe_rate(bucket["total_score"], bucket["count"]),
            "score_to_par": bucket["total_score"] - bucket["total_par"],
        }
        par_type_metrics[f"par{par_value}"]["tee_strategy"] = [
            {
                "club": club,
                "count": len(values),
                "avg_score_to_par": _mean(values),
            }
            for club, values in sorted(tee_by_par_type[par_value].items(), key=lambda item: item[0])
        ]

    return {
        "summary": {
            "hole_count": hole_count,
            "score": round_info.get("score", 0),
            "score_to_par": score_to_par,
            "gir": round_info.get("gir", 0),
        },
        "scoring": {
            "birdie_count": scoring_counter["birdie"],
            "par_count": scoring_counter["par"],
            "bogey_count": scoring_counter["bogey"],
            "double_bogey_plus_count": scoring_counter["double_bogey_plus"],
            "birdie_rate": _safe_rate(scoring_counter["birdie"], hole_count),
            "par_rate": _safe_rate(scoring_counter["par"], hole_count),
            "bogey_rate": _safe_rate(scoring_counter["bogey"], hole_count),
            "double_bogey_plus_rate": _safe_rate(scoring_counter["double_bogey_plus"], hole_count),
        },
        "par_types": par_type_metrics,
        "putting": {
            "avg_putts_per_hole": _safe_rate(total_putts, hole_count),
            "one_putt_rate": _safe_rate(one_putt_count, hole_count),
            "three_putt_rate": _safe_rate(three_putt_count, hole_count),
            "first_putt_distance_avg": _mean(first_putt_distances),
            "first_putt_sample_size": len(first_putt_distances),
            "putts_per_gir_hole": _mean(gir_holes),
            "putts_per_non_gir_hole": _mean(non_gir_holes),
        },
        "short_game": {
            "scrambling_rate": _safe_rate(scramble_success, len(non_gir_holes)),
            "sand_save_rate": _safe_rate(bunker_saves, bunker_holes),
            "up_and_down_rate": _safe_rate(up_and_down_success, up_and_down_chances),
        },
        "penalties": {
            "penalty_strokes_per_round": penalty_strokes,
            "ob_count": penalty_counts["OB"],
            "hazard_count": penalty_counts["H"],
            "unplayable_count": penalty_counts["UN"],
            "penalty_hole_rate": _safe_rate(penalty_holes, hole_count),
            "tee_shot_penalty_rate": _safe_rate(tee_shot_penalty_holes, hole_count),
            "penalty_by_club_group": {
                "D": penalty_by_club_group["D"],
                "W": penalty_by_club_group["W"],
                "U": penalty_by_club_group["U"],
                "LI": penalty_by_club_group["LI"],
                "MI": penalty_by_club_group["MI"],
                "SI": penalty_by_club_group["SI"],
                "P": penalty_by_club_group["P"],
                "OTHER": penalty_by_club_group["OTHER"],
            },
        },
        "tee_shots": {
            "club_usage": dict(tee_shot_clubs),
            "club_usage_sorted": sorted_tee_club_usage,
            "result_distribution": {
                "A": tee_shot_results["A"],
                "B": tee_shot_results["B"],
                "C": tee_shot_results["C"],
            },
            "club_avg_score_to_par": {
                club: _mean(values) for club, values in tee_shot_club_scores.items()
            },
            "club_avg_score_to_par_sorted": [
                {"club": club, "avg_score_to_par": _mean(values)}
                for club, values in sorted_tee_club_scores
            ],
            "total_tee_shots": total_tee_shots,
            "driver_penalty_rate": _safe_rate(driver_penalty_tee_shots, driver_tee_shots),
            "driver_result_c_rate": _safe_rate(driver_result_c_tee_shots, driver_tee_shots),
            "driver_tee_shot_count": driver_tee_shots,
        },
        "approach": {
            "under_160_result_distribution": {
                "A": under_160_results["A"],
                "B": under_160_results["B"],
                "C": under_160_results["C"],
            },
            "under_160_average_error": _mean(under_160_errors),
            "gir_from_under_160_rate": _safe_rate(under_160_gir_holes, under_160_holes),
            "distance_bands": _build_distance_band_metrics(shots),
        },
    }


def build_recent_summary(raw_trend_data, window=10):
    rounds = defaultdict(lambda: {
        "score": None,
        "gir": None,
        "playdate": None,
        "hole_pars": {},
        "hole_scores": {},
        "hole_putts": {},
        "shots_per_hole": defaultdict(list),
        "penalty_strokes": 0,
    })

    for row in raw_trend_data:
        round_id = row["round_id"]
        round_data = rounds[round_id]
        if round_data["score"] is None:
            round_data["score"] = row["round_score"]
            round_data["gir"] = row["round_gir"]
            round_data["playdate"] = row["playdate"]

        if row["penalty"] == "OB":
            round_data["penalty_strokes"] += 2
        elif row["penalty"] in {"H", "UN"}:
            round_data["penalty_strokes"] += 1

        if row["holenum"] is not None and row["hole_par"] is not None and row["hole_score"] is not None:
            round_data["hole_pars"][row["holenum"]] = row["hole_par"]
            round_data["hole_scores"][row["holenum"]] = row["hole_score"]
        if row["holenum"] is not None and row["putt"] is not None and row["holenum"] not in round_data["hole_putts"]:
            round_data["hole_putts"][row["holenum"]] = row["putt"]
        if row["holenum"] is not None and row["club"] is not None:
            round_data["shots_per_hole"][row["holenum"]].append({
                "club": row["club"],
                "penalty": row["penalty"],
            })

    sorted_round_entries = sorted(
        [
            (round_id, round_data)
            for round_id, round_data in rounds.items()
            if round_data["score"] is not None and round_data["playdate"] is not None
        ],
        key=lambda item: item[1]["playdate"],
        reverse=True,
    )[:window]
    sorted_rounds = [round_data for _, round_data in sorted_round_entries]

    round_count = len(sorted_rounds)
    if not round_count:
        return {
            "window": window,
            "round_count": 0,
            "avg_score": None,
            "avg_gir": None,
            "avg_putts": None,
            "avg_three_putt_rate": None,
            "avg_scrambling_rate": None,
            "avg_penalty_strokes": None,
            "avg_tee_shot_penalty_rate": None,
            "avg_driver_penalty_rate": None,
            "avg_driver_result_c_rate": None,
            "avg_gir_from_under_160_rate": None,
            "avg_up_and_down_rate": None,
            "avg_back_minus_front_to_par": None,
            "avg_last_three_to_par": None,
            "avg_closing_16_18_to_par": None,
            "birdie_follow_up_count": 0,
            "avg_birdie_follow_up_to_par": None,
            "birdie_follow_up_par_save_rate": None,
            "penalty_recovery_count": 0,
            "avg_penalty_recovery_to_par": None,
            "penalty_recovery_par_save_rate": None,
            "positive_momentum_count": 0,
            "avg_positive_momentum_to_par": None,
            "positive_momentum_par_save_rate": None,
            "negative_momentum_count": 0,
            "avg_negative_momentum_to_par": None,
            "negative_momentum_par_save_rate": None,
            "target_pressure_count": 0,
            "target_hit_rate": None,
            "avg_target_closing_delta": None,
            "insights": [],
        }

    summary_rows = []
    for round_data in sorted_rounds:
        total_holes = len(round_data["hole_pars"])
        total_putts = 0
        three_putts = 0
        scrambling_chances = 0
        scrambling_success = 0
        tee_shot_penalty_holes = 0
        driver_tee_shots = 0
        driver_penalty_tee_shots = 0
        driver_result_c_tee_shots = 0
        under_160_holes = 0
        under_160_gir_holes = 0
        up_and_down_chances = 0
        up_and_down_success = 0
        score_to_par = 0

        for holenum, hole_par in round_data["hole_pars"].items():
            hole_score = round_data["hole_scores"][holenum]
            putt = round_data["hole_putts"].get(holenum, 0)
            total_putts += putt
            if putt >= 3:
                three_putts += 1

            score_to_par += hole_score - hole_par
            gir = hole_par >= hole_score - putt + 2
            if not gir:
                scrambling_chances += 1
                if hole_score <= hole_par:
                    scrambling_success += 1

            shots = round_data["shots_per_hole"].get(holenum, [])
            under_160_hole = False
            up_and_down_hole = False
            if shots and shots[0].get("penalty"):
                tee_shot_penalty_holes += 1
            if shots and shots[0].get("club") == "D":
                driver_tee_shots += 1
                if shots[0].get("penalty"):
                    driver_penalty_tee_shots += 1
                if shots[0].get("result") == "C":
                    driver_result_c_tee_shots += 1
            for shot in shots:
                if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] < 160:
                    under_160_hole = True
                if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] <= 30:
                    up_and_down_hole = True
            if under_160_hole:
                under_160_holes += 1
                if gir:
                    under_160_gir_holes += 1
            if not gir and up_and_down_hole:
                up_and_down_chances += 1
                if hole_score <= hole_par:
                    up_and_down_success += 1

        summary_rows.append({
            "score": round_data["score"],
            "gir": round_data["gir"],
            "avg_putts": _safe_rate(total_putts, total_holes),
            "three_putt_rate": _safe_rate(three_putts, total_holes),
            "scrambling_rate": _safe_rate(scrambling_success, scrambling_chances),
            "penalty_strokes": round_data["penalty_strokes"],
            "tee_shot_penalty_rate": _safe_rate(tee_shot_penalty_holes, total_holes),
            "score_to_par": score_to_par,
            "driver_penalty_rate": _safe_rate(driver_penalty_tee_shots, driver_tee_shots),
            "driver_result_c_rate": _safe_rate(driver_result_c_tee_shots, driver_tee_shots),
            "gir_from_under_160_rate": _safe_rate(under_160_gir_holes, under_160_holes),
            "up_and_down_rate": _safe_rate(up_and_down_success, up_and_down_chances),
        })

    summary = {
        "window": window,
        "round_count": round_count,
        "avg_score": _mean([row["score"] for row in summary_rows]),
        "avg_gir": _mean([row["gir"] for row in summary_rows]),
        "avg_putts": _mean([row["avg_putts"] for row in summary_rows]),
        "avg_three_putt_rate": _mean([row["three_putt_rate"] for row in summary_rows]),
        "avg_scrambling_rate": _mean([row["scrambling_rate"] for row in summary_rows]),
        "avg_penalty_strokes": _mean([row["penalty_strokes"] for row in summary_rows]),
        "avg_tee_shot_penalty_rate": _mean([row["tee_shot_penalty_rate"] for row in summary_rows]),
        "avg_score_to_par": _mean([row["score_to_par"] for row in summary_rows]),
        "avg_driver_penalty_rate": _mean([row["driver_penalty_rate"] for row in summary_rows]),
        "avg_driver_result_c_rate": _mean([row["driver_result_c_rate"] for row in summary_rows]),
        "avg_gir_from_under_160_rate": _mean([row["gir_from_under_160_rate"] for row in summary_rows]),
        "avg_up_and_down_rate": _mean([row["up_and_down_rate"] for row in summary_rows]),
    }

    selected_round_ids = {round_id for round_id, _ in sorted_round_entries}
    nine_split_summary = build_nine_split_summary(raw_trend_data)
    closing_stretch_summary = build_closing_stretch_summary(raw_trend_data)
    birdie_follow_up_summary = build_birdie_follow_up_summary(raw_trend_data)
    penalty_recovery_summary = build_penalty_recovery_summary(raw_trend_data)
    momentum_follow_up_summary = build_momentum_follow_up_summary(raw_trend_data)
    target_pressure_summary = build_target_pressure_summary(raw_trend_data)

    back_minus_front_values = [
        nine_split_summary[round_id]["back_minus_front_to_par"]
        for round_id in selected_round_ids
        if round_id in nine_split_summary and nine_split_summary[round_id]["back_minus_front_to_par"] is not None
    ]
    last_three_values = [
        closing_stretch_summary[round_id]["last_three_holes"]["to_par"]
        for round_id in selected_round_ids
        if round_id in closing_stretch_summary and closing_stretch_summary[round_id]["last_three_holes"]["to_par"] is not None
    ]
    closing_values = [
        closing_stretch_summary[round_id]["closing_16_18"]["to_par"]
        for round_id in selected_round_ids
        if round_id in closing_stretch_summary and closing_stretch_summary[round_id]["closing_16_18"]["to_par"] is not None
    ]
    birdie_follow_up_values = [
        birdie_follow_up_summary[round_id]["avg_follow_up_to_par"]
        for round_id in selected_round_ids
        if round_id in birdie_follow_up_summary and birdie_follow_up_summary[round_id]["avg_follow_up_to_par"] is not None
    ]
    birdie_follow_up_rates = [
        birdie_follow_up_summary[round_id]["par_save_rate"]
        for round_id in selected_round_ids
        if round_id in birdie_follow_up_summary and birdie_follow_up_summary[round_id]["par_save_rate"] is not None
    ]
    penalty_recovery_values = [
        penalty_recovery_summary[round_id]["avg_recovery_to_par"]
        for round_id in selected_round_ids
        if round_id in penalty_recovery_summary and penalty_recovery_summary[round_id]["avg_recovery_to_par"] is not None
    ]
    penalty_recovery_rates = [
        penalty_recovery_summary[round_id]["par_save_rate"]
        for round_id in selected_round_ids
        if round_id in penalty_recovery_summary and penalty_recovery_summary[round_id]["par_save_rate"] is not None
    ]
    positive_momentum_values = [
        momentum_follow_up_summary[round_id]["positive_avg_to_par"]
        for round_id in selected_round_ids
        if round_id in momentum_follow_up_summary and momentum_follow_up_summary[round_id]["positive_avg_to_par"] is not None
    ]
    positive_momentum_rates = [
        momentum_follow_up_summary[round_id]["positive_par_save_rate"]
        for round_id in selected_round_ids
        if round_id in momentum_follow_up_summary and momentum_follow_up_summary[round_id]["positive_par_save_rate"] is not None
    ]
    negative_momentum_values = [
        momentum_follow_up_summary[round_id]["negative_avg_to_par"]
        for round_id in selected_round_ids
        if round_id in momentum_follow_up_summary and momentum_follow_up_summary[round_id]["negative_avg_to_par"] is not None
    ]
    negative_momentum_rates = [
        momentum_follow_up_summary[round_id]["negative_par_save_rate"]
        for round_id in selected_round_ids
        if round_id in momentum_follow_up_summary and momentum_follow_up_summary[round_id]["negative_par_save_rate"] is not None
    ]
    target_closing_deltas = [
        target_pressure_summary[round_id]["closing_delta_to_target"]
        for round_id in selected_round_ids
        if round_id in target_pressure_summary and target_pressure_summary[round_id]["closing_delta_to_target"] is not None
    ]

    summary.update({
        "avg_back_minus_front_to_par": _mean(back_minus_front_values) if back_minus_front_values else None,
        "avg_last_three_to_par": _mean(last_three_values) if last_three_values else None,
        "avg_closing_16_18_to_par": _mean(closing_values) if closing_values else None,
        "birdie_follow_up_count": sum(
            birdie_follow_up_summary[round_id]["follow_up_count"]
            for round_id in selected_round_ids
            if round_id in birdie_follow_up_summary
        ),
        "avg_birdie_follow_up_to_par": _mean(birdie_follow_up_values) if birdie_follow_up_values else None,
        "birdie_follow_up_par_save_rate": _mean(birdie_follow_up_rates) if birdie_follow_up_rates else None,
        "penalty_recovery_count": sum(
            penalty_recovery_summary[round_id]["recovery_count"]
            for round_id in selected_round_ids
            if round_id in penalty_recovery_summary
        ),
        "avg_penalty_recovery_to_par": _mean(penalty_recovery_values) if penalty_recovery_values else None,
        "penalty_recovery_par_save_rate": _mean(penalty_recovery_rates) if penalty_recovery_rates else None,
        "positive_momentum_count": sum(
            momentum_follow_up_summary[round_id]["positive_count"]
            for round_id in selected_round_ids
            if round_id in momentum_follow_up_summary
        ),
        "avg_positive_momentum_to_par": _mean(positive_momentum_values) if positive_momentum_values else None,
        "positive_momentum_par_save_rate": _mean(positive_momentum_rates) if positive_momentum_rates else None,
        "negative_momentum_count": sum(
            momentum_follow_up_summary[round_id]["negative_count"]
            for round_id in selected_round_ids
            if round_id in momentum_follow_up_summary
        ),
        "avg_negative_momentum_to_par": _mean(negative_momentum_values) if negative_momentum_values else None,
        "negative_momentum_par_save_rate": _mean(negative_momentum_rates) if negative_momentum_rates else None,
        "target_pressure_count": sum(
            1
            for round_id in selected_round_ids
            if round_id in target_pressure_summary and target_pressure_summary[round_id]["target_score"] is not None
        ),
        "target_hit_rate": _mean([
            1 if target_pressure_summary[round_id]["target_hit"] else 0
            for round_id in selected_round_ids
            if round_id in target_pressure_summary and target_pressure_summary[round_id]["target_hit"] is not None
        ]) if any(
            round_id in target_pressure_summary and target_pressure_summary[round_id]["target_hit"] is not None
            for round_id in selected_round_ids
        ) else None,
        "avg_target_closing_delta": _mean(target_closing_deltas) if target_closing_deltas else None,
    })

    insights = []
    context_insights = []
    if summary["avg_three_putt_rate"] >= 0.15:
        insights.append(f"최근 {window}라운드 3퍼트율이 {summary['avg_three_putt_rate'] * 100:.1f}%입니다.")
    if summary["avg_penalty_strokes"] >= 2:
        insights.append(f"최근 라운드 평균 페널티 타수가 {summary['avg_penalty_strokes']:.1f}타입니다.")
    if summary["avg_scrambling_rate"] <= 0.35:
        insights.append(f"스크램블링이 {summary['avg_scrambling_rate'] * 100:.1f}%로 쇼트게임 보완이 필요합니다.")
    if summary["avg_tee_shot_penalty_rate"] >= 0.1:
        insights.append(f"티샷 페널티가 홀 기준 {summary['avg_tee_shot_penalty_rate'] * 100:.1f}% 발생했습니다.")
    if summary["avg_driver_penalty_rate"] >= 0.12:
        insights.append(f"드라이버 사용 시 페널티율이 {summary['avg_driver_penalty_rate'] * 100:.1f}%입니다.")
    if summary["avg_driver_result_c_rate"] >= 0.3:
        insights.append(f"드라이버 결과 C 비율이 {summary['avg_driver_result_c_rate'] * 100:.1f}%로 높습니다.")
    if summary["avg_gir_from_under_160_rate"] <= 0.45:
        insights.append(f"160m 이내 공략 후 GIR 비율이 {summary['avg_gir_from_under_160_rate'] * 100:.1f}%입니다.")
    if summary["avg_up_and_down_rate"] <= 0.3:
        insights.append(f"업앤다운 성공률이 {summary['avg_up_and_down_rate'] * 100:.1f}%에 머물고 있습니다.")
    if summary["avg_back_minus_front_to_par"] is not None and summary["avg_back_minus_front_to_par"] >= 1.0:
        context_insights.append(f"후반이 전반보다 평균 {summary['avg_back_minus_front_to_par']:.1f}타 더 무겁습니다.")
    if summary["avg_closing_16_18_to_par"] is not None and summary["avg_closing_16_18_to_par"] >= 1.5:
        context_insights.append(f"16-18번 마무리 구간이 평균 {summary['avg_closing_16_18_to_par']:.1f}타로 무겁습니다.")
    if summary["birdie_follow_up_count"] >= 2 and summary["avg_birdie_follow_up_to_par"] is not None and summary["avg_birdie_follow_up_to_par"] > 0.3:
        context_insights.append(f"버디 직후 다음 홀 평균이 {summary['avg_birdie_follow_up_to_par']:.1f}타로 흔들립니다.")
    if summary["penalty_recovery_count"] >= 2 and summary["avg_penalty_recovery_to_par"] is not None and summary["avg_penalty_recovery_to_par"] > 0.5:
        context_insights.append(f"페널티 직후 다음 홀 평균이 {summary['avg_penalty_recovery_to_par']:.1f}타로 회복이 더딥니다.")
    if summary["positive_momentum_count"] >= 2 and summary["avg_positive_momentum_to_par"] is not None and summary["avg_positive_momentum_to_par"] > 0.3:
        context_insights.append(f"좋은 흐름 직후 다음 홀 평균이 {summary['avg_positive_momentum_to_par']:.1f}타로 흔들립니다.")
    if summary["negative_momentum_count"] >= 2 and summary["avg_negative_momentum_to_par"] is not None and summary["avg_negative_momentum_to_par"] > 0.5:
        context_insights.append(f"나쁜 흐름 직후 다음 홀 평균이 {summary['avg_negative_momentum_to_par']:.1f}타로 추가 손실이 이어집니다.")
    if summary["target_pressure_count"] >= 2 and summary["avg_target_closing_delta"] is not None and summary["avg_target_closing_delta"] > 0.5:
        context_insights.append(f"목표 타수 방어 구간에서 마무리 3홀이 평균 {summary['avg_target_closing_delta']:.1f}타 무겁습니다.")

    summary["insights"] = (context_insights + insights)[:3]
    return summary


def build_course_adjustment_summary(raw_trend_data):
    rounds = defaultdict(lambda: {
        "gcname": None,
        "score": None,
        "playdate": None,
        "hole_pars": {},
        "hole_scores": {},
    })

    for row in raw_trend_data:
        round_id = row["round_id"]
        round_data = rounds[round_id]
        if round_data["score"] is None:
            round_data["score"] = row["round_score"]
            round_data["playdate"] = row["playdate"]
            round_data["gcname"] = row.get("gcname")

        if row["holenum"] is not None and row["hole_par"] is not None and row["hole_score"] is not None:
            round_data["hole_pars"][row["holenum"]] = row["hole_par"]
            round_data["hole_scores"][row["holenum"]] = row["hole_score"]

    completed_rounds = []
    for round_id, round_data in rounds.items():
        if round_data["score"] is None or not round_data["gcname"]:
            continue
        score_to_par = sum(
            round_data["hole_scores"][holenum] - round_data["hole_pars"][holenum]
            for holenum in round_data["hole_pars"]
            if holenum in round_data["hole_scores"]
        )
        completed_rounds.append({
            "round_id": round_id,
            "gcname": round_data["gcname"],
            "score": round_data["score"],
            "playdate": round_data["playdate"],
            "score_to_par": score_to_par,
        })

    course_groups = defaultdict(list)
    for round_data in completed_rounds:
        course_groups[round_data["gcname"]].append(round_data)

    course_baselines = {}
    for gcname, course_rounds in course_groups.items():
        course_baselines[gcname] = {
            "gcname": gcname,
            "round_count": len(course_rounds),
            "avg_score": sum(item["score"] for item in course_rounds) / len(course_rounds),
            "avg_score_to_par": sum(item["score_to_par"] for item in course_rounds) / len(course_rounds),
        }

    round_summary = {}
    for round_data in completed_rounds:
        baseline = course_baselines[round_data["gcname"]]
        round_summary[round_data["round_id"]] = {
            "gcname": round_data["gcname"],
            "course_round_count": baseline["round_count"],
            "course_avg_score": baseline["avg_score"],
            "course_avg_score_to_par": baseline["avg_score_to_par"],
            "course_adjusted_score": round_data["score"] - baseline["avg_score"],
            "course_adjusted_to_par": round_data["score_to_par"] - baseline["avg_score_to_par"],
        }

    return {
        "rounds": round_summary,
        "course_baselines": sorted(
            course_baselines.values(),
            key=lambda item: (-item["round_count"], item["gcname"]),
        ),
    }


def build_nine_split_summary(raw_trend_data):
    rounds = defaultdict(lambda: {
        "score": None,
        "playdate": None,
        "holes": {},
    })

    for row in raw_trend_data:
        round_id = row["round_id"]
        round_data = rounds[round_id]
        if round_data["score"] is None:
            round_data["score"] = row["round_score"]
            round_data["playdate"] = row["playdate"]

        holenum = row.get("holenum")
        if holenum is None or row.get("hole_par") is None or row.get("hole_score") is None:
            continue
        round_data["holes"][holenum] = {
            "par": row["hole_par"],
            "score": row["hole_score"],
        }

    round_summary = {}
    for round_id, round_data in rounds.items():
        front_holes = [hole for holenum, hole in round_data["holes"].items() if 1 <= holenum <= 9]
        back_holes = [hole for holenum, hole in round_data["holes"].items() if 10 <= holenum <= 18]

        front_score = sum(hole["score"] for hole in front_holes)
        front_par = sum(hole["par"] for hole in front_holes)
        back_score = sum(hole["score"] for hole in back_holes)
        back_par = sum(hole["par"] for hole in back_holes)

        front_to_par = front_score - front_par if front_holes else None
        back_to_par = back_score - back_par if back_holes else None
        split_delta = (
            back_to_par - front_to_par
            if front_to_par is not None and back_to_par is not None else None
        )

        round_summary[round_id] = {
            "front_hole_count": len(front_holes),
            "back_hole_count": len(back_holes),
            "front_score": front_score if front_holes else None,
            "back_score": back_score if back_holes else None,
            "front_to_par": front_to_par,
            "back_to_par": back_to_par,
            "back_minus_front_to_par": split_delta,
        }

    return round_summary


def build_closing_stretch_summary(raw_trend_data):
    rounds = defaultdict(dict)

    for row in raw_trend_data:
        holenum = row.get("holenum")
        if holenum is None or row.get("hole_par") is None or row.get("hole_score") is None:
            continue
        rounds[row["round_id"]][holenum] = {
            "par": row["hole_par"],
            "score": row["hole_score"],
        }

    summary = {}
    for round_id, holes in rounds.items():
        sorted_holes = sorted(holes.items())
        last_three = sorted_holes[-3:]
        closing_16_18 = [(holenum, holes[holenum]) for holenum in (16, 17, 18) if holenum in holes]

        def _segment_metrics(segment):
            if not segment:
                return {
                    "hole_count": 0,
                    "score": None,
                    "to_par": None,
                }
            total_score = sum(hole["score"] for _, hole in segment)
            total_par = sum(hole["par"] for _, hole in segment)
            return {
                "hole_count": len(segment),
                "score": total_score,
                "to_par": total_score - total_par,
            }

        last_three_metrics = _segment_metrics(last_three)
        closing_metrics = _segment_metrics(closing_16_18)
        summary[round_id] = {
            "last_three_holes": last_three_metrics,
            "closing_16_18": closing_metrics,
        }

    return summary


def build_birdie_follow_up_summary(raw_trend_data):
    rounds = defaultdict(dict)

    for row in raw_trend_data:
        holenum = row.get("holenum")
        if holenum is None or row.get("hole_par") is None or row.get("hole_score") is None:
            continue
        rounds[row["round_id"]][holenum] = {
            "par": row["hole_par"],
            "score": row["hole_score"],
        }

    summary = {}
    for round_id, holes in rounds.items():
        birdie_follow_ups = []
        for holenum in sorted(holes):
            current_hole = holes[holenum]
            if current_hole["score"] - current_hole["par"] != -1:
                continue
            next_hole = holes.get(holenum + 1)
            if not next_hole:
                continue
            next_to_par = next_hole["score"] - next_hole["par"]
            birdie_follow_ups.append({
                "holenum": holenum + 1,
                "score": next_hole["score"],
                "to_par": next_to_par,
                "par_save": next_to_par <= 0,
            })

        sample_count = len(birdie_follow_ups)
        summary[round_id] = {
            "follow_up_count": sample_count,
            "avg_follow_up_to_par": (
                sum(item["to_par"] for item in birdie_follow_ups) / sample_count
                if sample_count else None
            ),
            "par_save_rate": (
                sum(1 for item in birdie_follow_ups if item["par_save"]) / sample_count
                if sample_count else None
            ),
        }

    return summary


def build_penalty_recovery_summary(raw_trend_data):
    rounds = defaultdict(lambda: {
        "holes": {},
        "penalty_holes": set(),
    })

    for row in raw_trend_data:
        round_id = row["round_id"]
        holenum = row.get("holenum")
        if holenum is None:
            continue

        if row.get("hole_par") is not None and row.get("hole_score") is not None:
            rounds[round_id]["holes"][holenum] = {
                "par": row["hole_par"],
                "score": row["hole_score"],
            }

        if row.get("penalty"):
            rounds[round_id]["penalty_holes"].add(holenum)

    summary = {}
    for round_id, round_data in rounds.items():
        recovery_samples = []
        for holenum in sorted(round_data["penalty_holes"]):
            next_hole = round_data["holes"].get(holenum + 1)
            if not next_hole:
                continue
            next_to_par = next_hole["score"] - next_hole["par"]
            recovery_samples.append({
                "holenum": holenum + 1,
                "score": next_hole["score"],
                "to_par": next_to_par,
                "par_save": next_to_par <= 0,
            })

        sample_count = len(recovery_samples)
        summary[round_id] = {
            "recovery_count": sample_count,
            "avg_recovery_to_par": (
                sum(item["to_par"] for item in recovery_samples) / sample_count
                if sample_count else None
            ),
            "par_save_rate": (
                sum(1 for item in recovery_samples if item["par_save"]) / sample_count
                if sample_count else None
            ),
        }

    return summary


def build_momentum_follow_up_summary(raw_trend_data):
    rounds = defaultdict(dict)

    for row in raw_trend_data:
        holenum = row.get("holenum")
        if holenum is None or row.get("hole_par") is None or row.get("hole_score") is None:
            continue
        rounds[row["round_id"]][holenum] = {
            "par": row["hole_par"],
            "score": row["hole_score"],
        }

    summary = {}
    for round_id, holes in rounds.items():
        positive_samples = []
        negative_samples = []

        for holenum in sorted(holes):
            current_hole = holes[holenum]
            current_to_par = current_hole["score"] - current_hole["par"]
            next_hole = holes.get(holenum + 1)
            if not next_hole:
                continue

            next_to_par = next_hole["score"] - next_hole["par"]
            sample = {
                "holenum": holenum + 1,
                "score": next_hole["score"],
                "to_par": next_to_par,
                "par_save": next_to_par <= 0,
            }

            if current_to_par <= -1:
                positive_samples.append(sample)
            if current_to_par >= 2:
                negative_samples.append(sample)

        positive_count = len(positive_samples)
        negative_count = len(negative_samples)
        summary[round_id] = {
            "positive_count": positive_count,
            "positive_avg_to_par": (
                sum(item["to_par"] for item in positive_samples) / positive_count
                if positive_count else None
            ),
            "positive_par_save_rate": (
                sum(1 for item in positive_samples if item["par_save"]) / positive_count
                if positive_count else None
            ),
            "negative_count": negative_count,
            "negative_avg_to_par": (
                sum(item["to_par"] for item in negative_samples) / negative_count
                if negative_count else None
            ),
            "negative_par_save_rate": (
                sum(1 for item in negative_samples if item["par_save"]) / negative_count
                if negative_count else None
            ),
        }

    return summary


def build_target_pressure_summary(raw_trend_data):
    rounds = defaultdict(lambda: {
        "score": None,
        "holes": {},
    })

    for row in raw_trend_data:
        round_id = row["round_id"]
        if rounds[round_id]["score"] is None:
            rounds[round_id]["score"] = row.get("round_score")
        holenum = row.get("holenum")
        if holenum is None or row.get("hole_score") is None:
            continue
        rounds[round_id]["holes"][holenum] = row["hole_score"]

    def _target_score(total_score):
        if total_score is None:
            return None
        if total_score <= 79:
            return 79
        if total_score <= 84:
            return 84
        if total_score <= 89:
            return 89
        if total_score <= 94:
            return 94
        return None

    summary = {}
    for round_id, round_data in rounds.items():
        total_score = round_data["score"]
        target_score = _target_score(total_score)
        closing_holes = [round_data["holes"][holenum] for holenum in (16, 17, 18) if holenum in round_data["holes"]]
        score_through_15 = sum(
            score for holenum, score in round_data["holes"].items()
            if holenum < 16
        )
        if target_score is None or len(closing_holes) != 3:
            summary[round_id] = {
                "target_score": None,
                "target_hit": None,
                "closing_delta_to_target": None,
            }
            continue

        allowed_closing_score = target_score - score_through_15
        actual_closing_score = sum(closing_holes)
        summary[round_id] = {
            "target_score": target_score,
            "target_hit": total_score <= target_score if total_score is not None else None,
            "closing_delta_to_target": actual_closing_score - allowed_closing_score,
        }

    return summary
