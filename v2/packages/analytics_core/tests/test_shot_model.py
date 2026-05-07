from lalagolf_analytics_core.shot_model import (
    build_shot_state_summary,
    categorize_shot,
    classify_club_group,
    classify_distance_bucket,
    normalize_lie_state,
    normalize_shot_states,
)


def _sample_inputs():
    round_info = {"id": 10}
    holes = [
        {"holenum": 1, "par": 4},
        {"holenum": 2, "par": 3},
    ]
    shots = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "F", "distance": 220, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "I7", "on": "F", "retplace": "G", "distance": 145, "score": 1, "penalty": None, "feel": "B", "result": "A"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 4, "score": 1, "penalty": None, "feel": "A", "result": "A"},
        {"holenum": 2, "club": "D", "on": "T", "retplace": "F", "distance": 210, "score": 3, "penalty": "OB", "feel": "C", "result": "C"},
        {"holenum": 2, "club": "52", "on": "F", "retplace": "G", "distance": 25, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 2, "club": "P", "on": "G", "retplace": "H", "distance": 3, "score": 1, "penalty": None, "feel": "B", "result": "A"},
    ]
    return round_info, holes, shots


def test_classifiers():
    assert classify_club_group("D") == "D"
    assert classify_club_group("I6") == "MI"
    assert classify_club_group("P") == "P"
    assert classify_distance_bucket(25) == "0_30"
    assert classify_distance_bucket(145) == "120_160"
    assert classify_distance_bucket(210) == "160_plus"
    assert normalize_lie_state("T") == "tee"
    assert normalize_lie_state("R") == "recovery"
    assert normalize_lie_state("X") == "unknown"


def test_categorize_shot():
    assert categorize_shot({"club": "D", "on": "T", "distance": 220}) == "off_the_tee"
    assert categorize_shot({"club": "P", "on": "G", "distance": 4}) == "putting"
    assert categorize_shot({"club": "52", "on": "F", "distance": 25}) == "short_game"
    assert categorize_shot({"club": "I7", "on": "R", "distance": 110}) == "recovery"
    assert categorize_shot({"club": "52", "on": "F", "distance": 65}) == "control_shot"
    assert categorize_shot({"club": "I7", "on": "F", "distance": 145}) == "iron_shot"


def test_normalize_shot_states_creates_fact_rows():
    round_info, holes, shots = _sample_inputs()

    facts = normalize_shot_states(round_info, holes, shots)

    assert len(facts) == 6
    assert facts[0]["round_id"] == 10
    assert facts[0]["hole_num"] == 1
    assert facts[0]["shot_num"] == 1
    assert facts[0]["par_type"] == 4
    assert facts[0]["club_group"] == "D"
    assert facts[0]["start_state"] == "tee"
    assert facts[0]["end_state"] == "fairway"
    assert facts[0]["shot_category"] == "off_the_tee"
    assert facts[0]["distance_bucket"] == "160_plus"
    assert facts[0]["is_tee_shot"] is True
    assert facts[0]["is_putt"] is False
    assert facts[0]["penalty_strokes"] == 0

    assert facts[3]["hole_num"] == 2
    assert facts[3]["shot_num"] == 1
    assert facts[3]["penalty_strokes"] == 2
    assert facts[3]["shot_category"] == "off_the_tee"
    assert facts[4]["shot_category"] == "short_game"
    assert facts[5]["is_putt"] is True


def test_build_shot_state_summary():
    round_info, holes, shots = _sample_inputs()

    facts = normalize_shot_states(round_info, holes, shots)
    summary = build_shot_state_summary(facts)

    assert summary["total_shots"] == 6
    assert summary["tee_shots"] == 2
    assert summary["putts"] == 2
    assert summary["recovery_shots"] == 1
    assert summary["penalty_shots"] == 1
    assert summary["by_category"]["off_the_tee"] == 2
    assert summary["by_category"]["iron_shot"] == 1
    assert summary["by_category"]["short_game"] == 1
    assert summary["by_category"]["putting"] == 2
    assert summary["by_start_state"]["tee"] == 2
    assert summary["by_club_group"]["D"] == 2
    assert summary["by_distance_bucket"]["160_plus"] == 2
