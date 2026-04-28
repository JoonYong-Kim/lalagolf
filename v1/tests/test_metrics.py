from datetime import datetime, timedelta

from src.metrics import (
    build_birdie_follow_up_summary,
    build_closing_stretch_summary,
    build_course_adjustment_summary,
    build_momentum_follow_up_summary,
    build_nine_split_summary,
    build_penalty_recovery_summary,
    build_target_pressure_summary,
    build_round_metrics,
    build_recent_summary,
)


def _sample_round():
    round_info = {"score": 20, "gir": 25.0}
    holes = [
        {"holenum": 1, "par": 4, "score": 4, "putt": 2, "GIR": True, "diff": 0},
        {"holenum": 2, "par": 3, "score": 5, "putt": 3, "GIR": False, "diff": 2},
        {"holenum": 3, "par": 5, "score": 5, "putt": 1, "GIR": False, "diff": 0},
        {"holenum": 4, "par": 4, "score": 6, "putt": 2, "GIR": False, "diff": 2},
    ]
    shots = [
        {"holenum": 1, "club": "D", "result": "A", "penalty": None, "distance": 220, "error": None, "on": "T", "retplace": "F"},
        {"holenum": 1, "club": "I7", "result": "A", "penalty": None, "distance": 140, "error": 12, "on": "F", "retplace": "G"},
        {"holenum": 1, "club": "P", "result": "B", "penalty": None, "distance": 8, "error": 0, "on": "G", "retplace": "G"},
        {"holenum": 1, "club": "P", "result": "A", "penalty": None, "distance": 1, "error": 0, "on": "G", "retplace": "H"},
        {"holenum": 2, "club": "D", "result": "C", "penalty": "OB", "distance": 210, "error": None, "on": "T", "retplace": "F"},
        {"holenum": 2, "club": "I9", "result": "B", "penalty": None, "distance": 90, "error": 15, "on": "F", "retplace": "B"},
        {"holenum": 2, "club": "P", "result": "B", "penalty": None, "distance": 12, "error": 0, "on": "B", "retplace": "G"},
        {"holenum": 2, "club": "P", "result": "C", "penalty": None, "distance": 4, "error": 0, "on": "G", "retplace": "G"},
        {"holenum": 2, "club": "P", "result": "A", "penalty": None, "distance": 1, "error": 0, "on": "G", "retplace": "H"},
        {"holenum": 3, "club": "W3", "result": "B", "penalty": None, "distance": 200, "error": None, "on": "T", "retplace": "F"},
        {"holenum": 3, "club": "52", "result": "A", "penalty": None, "distance": 25, "error": 3, "on": "F", "retplace": "G"},
        {"holenum": 3, "club": "P", "result": "A", "penalty": None, "distance": 2, "error": 0, "on": "G", "retplace": "H"},
        {"holenum": 4, "club": "D", "result": "B", "penalty": "H", "distance": 215, "error": None, "on": "T", "retplace": "F"},
        {"holenum": 4, "club": "I6", "result": "C", "penalty": None, "distance": 150, "error": 20, "on": "F", "retplace": "R"},
        {"holenum": 4, "club": "P", "result": "B", "penalty": None, "distance": 10, "error": 0, "on": "G", "retplace": "G"},
        {"holenum": 4, "club": "P", "result": "A", "penalty": None, "distance": 1, "error": 0, "on": "G", "retplace": "H"},
    ]
    return round_info, holes, shots


def test_build_round_metrics_core_stats():
    round_info, holes, shots = _sample_round()

    metrics = build_round_metrics(round_info, holes, shots)

    assert metrics["putting"]["three_putt_rate"] == 0.25
    assert metrics["putting"]["one_putt_rate"] == 0.25
    assert metrics["short_game"]["scrambling_rate"] == 1 / 3
    assert metrics["short_game"]["up_and_down_rate"] == 1
    assert metrics["penalties"]["penalty_strokes_per_round"] == 3
    assert metrics["penalties"]["tee_shot_penalty_rate"] == 0.5
    assert metrics["par_types"]["par3"]["avg_score"] == 5.0
    assert metrics["par_types"]["par4"]["score_to_par"] == 2
    assert metrics["par_types"]["par5"]["score_to_par"] == 0
    assert metrics["tee_shots"]["driver_penalty_rate"] == 2 / 3
    assert metrics["tee_shots"]["driver_result_c_rate"] == 1 / 3


def test_build_round_metrics_sand_save_and_distance_bands():
    round_info, holes, shots = _sample_round()

    metrics = build_round_metrics(round_info, holes, shots)

    assert metrics["short_game"]["sand_save_rate"] == 0
    assert metrics["approach"]["under_160_result_distribution"] == {"A": 2, "B": 1, "C": 1}
    assert metrics["approach"]["gir_from_under_160_rate"] == 0.25
    assert metrics["approach"]["distance_bands"]["120_160"]["shot_count"] == 2
    assert metrics["approach"]["distance_bands"]["0_30"]["shot_count"] == 1
    assert metrics["par_types"]["par4"]["tee_strategy"][0]["club"] == "D"


def test_build_round_metrics_handles_27_hole_round_counts():
    round_info = {"score": 108, "gir": 0}
    holes = []
    shots = []
    for holenum in range(1, 28):
        holes.append({"holenum": holenum, "par": 4, "score": 4, "putt": 2, "GIR": True, "diff": 0})
        shots.extend([
            {"holenum": holenum, "club": "D", "result": "B", "penalty": None, "distance": 200, "error": None, "on": "T", "retplace": "F"},
            {"holenum": holenum, "club": "I7", "result": "B", "penalty": None, "distance": 140, "error": 10, "on": "F", "retplace": "G"},
            {"holenum": holenum, "club": "P", "result": "A", "penalty": None, "distance": 5, "error": 0, "on": "G", "retplace": "G"},
            {"holenum": holenum, "club": "P", "result": "A", "penalty": None, "distance": 1, "error": 0, "on": "G", "retplace": "H"},
        ])

    metrics = build_round_metrics(round_info, holes, shots)

    assert metrics["summary"]["hole_count"] == 27
    assert metrics["scoring"]["par_rate"] == 1
    assert metrics["putting"]["avg_putts_per_hole"] == 2
    assert metrics["penalties"]["tee_shot_penalty_rate"] == 0


def test_build_recent_summary_aggregates_recent_rounds():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    for idx in range(3):
        round_id = idx + 1
        playdate = base_date + timedelta(days=idx)
        for holenum in (1, 2):
            raw_trend_data.append({
                "round_id": round_id,
                "round_score": 80 + idx,
                "round_gir": 40 + idx,
                "playdate": playdate,
                "holenum": holenum,
                "hole_par": 4,
                "hole_score": 5 if holenum == 1 else 4,
                "putt": 3 if holenum == 1 else 2,
                "club": "D" if holenum == 1 else "I7",
                "penalty": "OB" if idx == 2 and holenum == 1 else None,
                "distance": 200,
                "retgrade": "B",
            })

    summary = build_recent_summary(raw_trend_data, window=2)

    assert summary["round_count"] == 2
    assert summary["avg_score"] == 81.5
    assert summary["avg_gir"] == 41.5
    assert summary["avg_three_putt_rate"] == 0.5
    assert summary["avg_scrambling_rate"] == 0
    assert summary["avg_penalty_strokes"] == 1
    assert summary["avg_tee_shot_penalty_rate"] == 0.25
    assert summary["avg_driver_penalty_rate"] == 0.5
    assert summary["avg_driver_result_c_rate"] == 0
    assert summary["avg_gir_from_under_160_rate"] == 0
    assert summary["avg_up_and_down_rate"] == 0


def test_build_recent_summary_includes_context_insights():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    hole_specs = [
        (1, 4, None),
        (2, 4, None),
        (3, 4, None),
        (4, 4, None),
        (5, 4, None),
        (6, 4, None),
        (7, 4, None),
        (8, 4, None),
        (9, 4, None),
        (10, 5, None),
        (11, 5, None),
        (12, 5, None),
        (13, 5, None),
        (14, 5, None),
        (15, 5, None),
        (16, 5, None),
        (17, 5, None),
        (18, 6, None),
        (19, 3, None),
        (20, 5, "OB"),
        (21, 5, None),
        (22, 3, None),
        (23, 5, "H"),
        (24, 5, None),
    ]

    for holenum, hole_score, penalty in hole_specs:
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 92,
            "round_gir": 33,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": penalty,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_recent_summary(raw_trend_data, window=1)

    assert summary["avg_back_minus_front_to_par"] == 10
    assert summary["avg_closing_16_18_to_par"] == 4
    assert summary["birdie_follow_up_count"] == 2
    assert summary["avg_birdie_follow_up_to_par"] == 1
    assert summary["penalty_recovery_count"] == 2
    assert summary["avg_penalty_recovery_to_par"] == 1
    assert any("후반" in insight for insight in summary["insights"])


def test_build_course_adjustment_summary_uses_same_course_baseline():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    round_specs = [
        (1, "Course A", 80, (5, 4)),
        (2, "Course A", 84, (6, 4)),
        (3, "Course B", 78, (4, 4)),
    ]

    for idx, (round_id, course_name, round_score, hole_scores) in enumerate(round_specs):
        playdate = base_date + timedelta(days=idx)
        for holenum, hole_score in enumerate(hole_scores, start=1):
            raw_trend_data.append({
                "round_id": round_id,
                "round_score": round_score,
                "round_gir": 40,
                "gcname": course_name,
                "playdate": playdate,
                "holenum": holenum,
                "hole_par": 4,
                "hole_score": hole_score,
                "putt": 2,
                "club": "D",
                "penalty": None,
                "distance": 180,
                "retgrade": "B",
            })

    summary = build_course_adjustment_summary(raw_trend_data)

    assert summary["course_baselines"][0]["gcname"] == "Course A"
    assert summary["course_baselines"][0]["round_count"] == 2
    assert summary["course_baselines"][0]["avg_score"] == 82
    assert summary["course_baselines"][0]["avg_score_to_par"] == 1.5
    assert summary["rounds"][1]["course_adjusted_score"] == -2
    assert summary["rounds"][1]["course_adjusted_to_par"] == -0.5
    assert summary["rounds"][2]["course_adjusted_score"] == 2
    assert summary["rounds"][2]["course_adjusted_to_par"] == 0.5
    assert summary["rounds"][3]["course_adjusted_score"] == 0
    assert summary["rounds"][3]["course_adjusted_to_par"] == 0


def test_build_nine_split_summary_separates_front_and_back():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []

    for holenum in range(1, 19):
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 82,
            "round_gir": 44,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": 4 if holenum <= 9 else 5,
            "putt": 2,
            "club": "D",
            "penalty": None,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_nine_split_summary(raw_trend_data)

    assert summary[1]["front_hole_count"] == 9
    assert summary[1]["back_hole_count"] == 9
    assert summary[1]["front_score"] == 36
    assert summary[1]["back_score"] == 45
    assert summary[1]["front_to_par"] == 0
    assert summary[1]["back_to_par"] == 9
    assert summary[1]["back_minus_front_to_par"] == 9


def test_build_closing_stretch_summary_supports_last_three_and_16_to_18():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []

    hole_scores = {
        15: 4,
        16: 5,
        17: 3,
        18: 6,
        19: 4,
        20: 5,
    }
    for holenum, hole_score in hole_scores.items():
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 90,
            "round_gir": 33,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": None,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_closing_stretch_summary(raw_trend_data)

    assert summary[1]["last_three_holes"]["hole_count"] == 3
    assert summary[1]["last_three_holes"]["score"] == 15
    assert summary[1]["last_three_holes"]["to_par"] == 3
    assert summary[1]["closing_16_18"]["hole_count"] == 3
    assert summary[1]["closing_16_18"]["score"] == 14
    assert summary[1]["closing_16_18"]["to_par"] == 2


def test_build_birdie_follow_up_summary_tracks_next_hole_response():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    hole_scores = {
        1: 3,  # birdie
        2: 4,  # par save
        3: 4,
        4: 3,  # birdie
        5: 5,  # bogey
    }

    for holenum, hole_score in hole_scores.items():
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 74,
            "round_gir": 55,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": None,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_birdie_follow_up_summary(raw_trend_data)

    assert summary[1]["follow_up_count"] == 2
    assert summary[1]["avg_follow_up_to_par"] == 0.5
    assert summary[1]["par_save_rate"] == 0.5


def test_build_penalty_recovery_summary_tracks_next_hole_response():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    holes = [
        (1, 5, "OB"),
        (2, 4, None),
        (3, 6, "H"),
        (4, 5, None),
    ]

    for holenum, hole_score, penalty in holes:
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 86,
            "round_gir": 39,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": penalty,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_penalty_recovery_summary(raw_trend_data)

    assert summary[1]["recovery_count"] == 2
    assert summary[1]["avg_recovery_to_par"] == 0.5
    assert summary[1]["par_save_rate"] == 0.5


def test_build_momentum_follow_up_summary_tracks_good_and_bad_flow():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []
    hole_scores = {
        1: 3,  # good
        2: 5,  # +1
        3: 6,  # bad
        4: 4,  # par
        5: 4,
        6: 7,  # bad
        7: 5,  # +1
        8: 3,  # good
        9: 4,  # par
    }

    for holenum, hole_score in hole_scores.items():
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 82,
            "round_gir": 44,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": None,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_momentum_follow_up_summary(raw_trend_data)

    assert summary[1]["positive_count"] == 2
    assert summary[1]["positive_avg_to_par"] == 0.5
    assert summary[1]["positive_par_save_rate"] == 0.5
    assert summary[1]["negative_count"] == 2
    assert summary[1]["negative_avg_to_par"] == 0.5
    assert summary[1]["negative_par_save_rate"] == 0.5


def test_build_target_pressure_summary_tracks_closing_delta_to_target():
    base_date = datetime(2025, 1, 1)
    raw_trend_data = []

    hole_scores = {holenum: 4 for holenum in range(1, 16)}
    hole_scores.update({16: 5, 17: 4, 18: 5})

    for holenum, hole_score in hole_scores.items():
        raw_trend_data.append({
            "round_id": 1,
            "round_score": 74,
            "round_gir": 50,
            "playdate": base_date,
            "holenum": holenum,
            "hole_par": 4,
            "hole_score": hole_score,
            "putt": 2,
            "club": "D",
            "penalty": None,
            "distance": 180,
            "retgrade": "B",
        })

    summary = build_target_pressure_summary(raw_trend_data)

    assert summary[1]["target_score"] == 79
    assert summary[1]["target_hit"] is True
    assert summary[1]["closing_delta_to_target"] == -5
