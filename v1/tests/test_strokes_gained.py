from src.expected_value import build_expected_score_table
from src.shot_model import normalize_shot_states
from src.strokes_gained import (
    summarize_approach_strategy_comparison,
    build_historical_shot_facts,
    build_shot_values,
    summarize_club_reliability,
    summarize_tee_strategy_comparison,
    summarize_category_window,
    summarize_shot_values,
    summarize_shot_values_by_round,
)


def _sample_history_rows():
    return [
        {
            "round_id": 1,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 4,
            "putt": 1,
            "club": "D",
            "shot_score": 1,
            "feelgrade": "A",
            "penalty": None,
            "shotplace": "T",
            "retplace": "F",
            "distance": 220,
            "retgrade": "B",
        },
        {
            "round_id": 1,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 4,
            "putt": 1,
            "club": "I7",
            "shot_score": 1,
            "feelgrade": "B",
            "penalty": None,
            "shotplace": "F",
            "retplace": "G",
            "distance": 145,
            "retgrade": "A",
        },
        {
            "round_id": 1,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 4,
            "putt": 1,
            "club": "P",
            "shot_score": 1,
            "feelgrade": "A",
            "penalty": None,
            "shotplace": "G",
            "retplace": "H",
            "distance": 4,
            "retgrade": "A",
        },
        {
            "round_id": 2,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 6,
            "putt": 1,
            "club": "D",
            "shot_score": 1,
            "feelgrade": "C",
            "penalty": "OB",
            "shotplace": "T",
            "retplace": "R",
            "distance": 220,
            "retgrade": "C",
        },
        {
            "round_id": 2,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 6,
            "putt": 1,
            "club": "52",
            "shot_score": 1,
            "feelgrade": "B",
            "penalty": None,
            "shotplace": "R",
            "retplace": "G",
            "distance": 25,
            "retgrade": "B",
        },
        {
            "round_id": 2,
            "holenum": 1,
            "hole_par": 4,
            "hole_score": 6,
            "putt": 1,
            "club": "P",
            "shot_score": 1,
            "feelgrade": "A",
            "penalty": None,
            "shotplace": "G",
            "retplace": "H",
            "distance": 3,
            "retgrade": "A",
        },
    ]


def test_build_historical_shot_facts():
    facts = build_historical_shot_facts(_sample_history_rows())

    assert len(facts) == 6
    assert facts[0]["start_state"] == "tee"
    assert facts[0]["end_state"] == "fairway"
    assert facts[3]["penalty_strokes"] == 2


def test_build_shot_values_includes_penalty_cost():
    round_info = {"id": 2}
    holes = [{"holenum": 1, "par": 4}]
    current_shots = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "R", "distance": 220, "score": 1, "penalty": "OB", "feel": "C", "result": "C"},
        {"holenum": 1, "club": "52", "on": "R", "retplace": "G", "distance": 25, "score": 1, "penalty": None, "feel": "B", "result": "B"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 3, "score": 1, "penalty": None, "feel": "A", "result": "A"},
    ]
    history_facts = build_historical_shot_facts(_sample_history_rows())
    expected_table = build_expected_score_table(history_facts)
    current_facts = normalize_shot_states(round_info, holes, current_shots)

    valued_facts = build_shot_values(current_facts, expected_table, min_samples=1)

    assert valued_facts[0]["shot_cost"] == 3
    assert valued_facts[0]["expected_before"] is not None
    assert valued_facts[0]["shot_value"] < 0


def test_summarize_shot_values():
    history_facts = build_historical_shot_facts(_sample_history_rows())
    expected_table = build_expected_score_table(history_facts)
    valued_facts = build_shot_values(history_facts, expected_table, min_samples=1)

    summary = summarize_shot_values(valued_facts)

    assert summary["covered_shots"] == len(valued_facts)
    assert any(item["category"] == "off_the_tee" for item in summary["category_summary"])
    assert any(item["category"] == "penalty_impact" for item in summary["category_summary"])
    assert any(item["club_group"] == "D" for item in summary["club_group_summary"])


def test_summarize_shot_values_by_round_and_window():
    history_facts = build_historical_shot_facts(_sample_history_rows())
    expected_table = build_expected_score_table(history_facts)
    valued_facts = build_shot_values(history_facts, expected_table, min_samples=1)

    by_round = summarize_shot_values_by_round(valued_facts)
    window = summarize_category_window(list(by_round.values()))

    assert set(by_round.keys()) == {1, 2}
    assert window["covered_shots"] == len(valued_facts)
    assert any(item["category"] == "putting" for item in window["category_summary"])


def test_summarize_club_reliability():
    history_facts = build_historical_shot_facts(_sample_history_rows())
    expected_table = build_expected_score_table(history_facts)
    valued_facts = build_shot_values(history_facts, expected_table, min_samples=1)

    reliability = summarize_club_reliability(valued_facts, min_samples=1)

    assert reliability
    assert any(item["club_group"] == "D" for item in reliability)
    driver_row = next(item for item in reliability if item["club_group"] == "D")
    assert "avg_distance" in driver_row
    assert "result_c_rate" in driver_row
    assert "shot_value_stddev" in driver_row
    assert "shot_value_p25" in driver_row
    assert driver_row["sample_level"] in {"low", "medium", "high"}


def test_summarize_tee_strategy_comparison():
    shot_facts = [
        {"shot_category": "off_the_tee", "par_type": 4, "club_group": "D", "shot_value": -0.20, "penalty_strokes": 1, "result": "C"},
        {"shot_category": "off_the_tee", "par_type": 4, "club_group": "D", "shot_value": -0.10, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "off_the_tee", "par_type": 4, "club_group": "W", "shot_value": 0.02, "penalty_strokes": 0, "result": "A"},
        {"shot_category": "off_the_tee", "par_type": 4, "club_group": "U", "shot_value": -0.01, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "off_the_tee", "par_type": 5, "club_group": "D", "shot_value": 0.03, "penalty_strokes": 0, "result": "A"},
        {"shot_category": "off_the_tee", "par_type": 5, "club_group": "D", "shot_value": -0.02, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "off_the_tee", "par_type": 5, "club_group": "W", "shot_value": -0.05, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "off_the_tee", "par_type": 5, "club_group": "U", "shot_value": -0.06, "penalty_strokes": 0, "result": "C"},
    ]

    comparison = summarize_tee_strategy_comparison(shot_facts, min_samples=2)

    assert comparison["comparison_ready"] is True
    assert len(comparison["rows"]) == 4
    driver_row = next(row for row in comparison["rows"] if row["strategy"] == "Driver" and row["par_type"] == 4)
    assert "shot_value_stddev" in driver_row
    assert "shot_value_p25" in driver_row


def test_summarize_approach_strategy_comparison():
    shot_facts = [
        {"shot_category": "approach", "distance": 145, "end_state": "green", "shot_value": 0.05, "penalty_strokes": 0, "result": "A"},
        {"shot_category": "approach", "distance": 150, "end_state": "green", "shot_value": 0.02, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "approach", "distance": 140, "end_state": "fairway", "shot_value": -0.03, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "approach", "distance": 130, "end_state": "fairway", "shot_value": -0.05, "penalty_strokes": 0, "result": "C"},
        {"shot_category": "approach", "distance": 170, "end_state": "green", "shot_value": -0.01, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "approach", "distance": 175, "end_state": "green", "shot_value": 0.01, "penalty_strokes": 0, "result": "A"},
        {"shot_category": "approach", "distance": 180, "end_state": "fairway", "shot_value": -0.04, "penalty_strokes": 0, "result": "B"},
        {"shot_category": "approach", "distance": 165, "end_state": "fairway", "shot_value": -0.06, "penalty_strokes": 0, "result": "C"},
    ]

    comparison = summarize_approach_strategy_comparison(shot_facts, min_samples=2)

    assert comparison["comparison_ready"] is True
    assert len(comparison["rows"]) == 4
    attack_row = next(row for row in comparison["rows"] if row["distance_band"] == "120-160m" and row["strategy"] == "attack")
    assert "shot_value_stddev" in attack_row
    assert "shot_value_p25" in attack_row
