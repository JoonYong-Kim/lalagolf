from src.expected_value import (
    annotate_expected_scores,
    build_round_recency_weights,
    build_expected_score_table,
    lookup_expected_score,
)
from src.shot_model import normalize_shot_states
import pytest


def _sample_shot_facts():
    round_1 = {"id": 1}
    round_2 = {"id": 2}
    holes = [
        {"holenum": 1, "par": 4},
        {"holenum": 2, "par": 4},
    ]
    shots_round_1 = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "F", "distance": 220, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "I7", "on": "F", "retplace": "G", "distance": 145, "score": 1, "penalty": None, "feel": "B", "result": "A"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 4, "score": 1, "penalty": None, "feel": "A", "result": "A"},
        {"holenum": 2, "club": "D", "on": "T", "retplace": "F", "distance": 210, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 2, "club": "52", "on": "F", "retplace": "G", "distance": 25, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 2, "club": "P", "on": "G", "retplace": "H", "distance": 3, "score": 1, "penalty": None, "feel": "B", "result": "A"},
    ]
    shots_round_2 = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "F", "distance": 230, "score": 1, "penalty": None, "feel": "A", "result": "A"},
        {"holenum": 1, "club": "I6", "on": "F", "retplace": "G", "distance": 150, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 5, "score": 1, "penalty": None, "feel": "A", "result": "A"},
    ]
    facts = normalize_shot_states(round_1, holes, shots_round_1)
    facts.extend(normalize_shot_states(round_2, holes[:1], shots_round_2))
    return facts


def test_build_expected_score_table():
    shot_facts = _sample_shot_facts()

    table = build_expected_score_table(shot_facts)

    assert "full" in table
    assert "start_only" in table
    tee_key = ("tee", "160_plus", 4, "off_the_tee")
    assert table["full"][tee_key]["sample_count"] == 3
    assert table["full"][tee_key]["expected_strokes"] == 3


def test_build_expected_score_table_prunes_low_sample_states():
    shot_facts = _sample_shot_facts()

    table = build_expected_score_table(
        shot_facts,
        min_samples_by_level={
            "full": 4,
            "no_par": 3,
            "no_distance": 2,
            "start_category": 2,
            "start_only": 1,
        },
        prune_low_sample=True,
    )

    tee_key = ("tee", "160_plus", 4, "off_the_tee")
    assert tee_key not in table["full"]
    no_par_key = ("tee", "160_plus", "off_the_tee")
    assert no_par_key in table["no_par"]


def test_lookup_expected_score_fallback():
    shot_facts = _sample_shot_facts()
    table = build_expected_score_table(shot_facts)
    unseen_fact = {
        "start_state": "fairway",
        "distance_bucket": "80_120",
        "par_type": 5,
        "shot_category": "approach",
    }

    result = lookup_expected_score(unseen_fact, table, min_samples=1)

    assert result is not None
    assert result["level"] in {"start_category", "start_only"}
    assert result["expected_strokes"] > 0


def test_annotate_expected_scores():
    shot_facts = _sample_shot_facts()
    table = build_expected_score_table(shot_facts)

    annotated = annotate_expected_scores(shot_facts, table, min_samples=1)

    assert len(annotated) == len(shot_facts)
    assert annotated[0]["expected_before"] == 3
    assert annotated[0]["expected_after"] > 0
    assert annotated[0]["expected_lookup_level"] == "full"


def test_lookup_expected_score_uses_level_specific_thresholds():
    shot_facts = _sample_shot_facts()
    table = build_expected_score_table(shot_facts)
    fact = {
        "start_state": "tee",
        "distance_bucket": "160_plus",
        "par_type": 4,
        "shot_category": "off_the_tee",
    }

    result = lookup_expected_score(
        fact,
        table,
        min_samples=1,
        min_samples_by_level={
            "full": 4,
            "no_par": 3,
            "no_distance": 2,
            "start_category": 2,
            "start_only": 1,
        },
    )

    assert result is not None
    assert result["level"] == "no_par"


def test_build_round_recency_weights():
    raw_trend_data = [
        {"round_id": 1, "playdate": "2026-04-01"},
        {"round_id": 2, "playdate": "2026-04-10"},
        {"round_id": 3, "playdate": "2026-04-15"},
    ]

    weights = build_round_recency_weights(raw_trend_data, decay=0.8)

    assert weights[3] == 1.0
    assert weights[2] == 0.8
    assert weights[1] == pytest.approx(0.64)


def test_build_expected_score_table_uses_round_weights():
    round_1 = {"id": 1}
    round_2 = {"id": 2}
    holes = [{"holenum": 1, "par": 4}]
    shots_round_1 = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "F", "distance": 220, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "I7", "on": "F", "retplace": "G", "distance": 145, "score": 1, "penalty": None, "feel": "B", "result": "A"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "G", "distance": 8, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 1, "score": 1, "penalty": None, "feel": "A", "result": "A"},
    ]
    shots_round_2 = [
        {"holenum": 1, "club": "D", "on": "T", "retplace": "F", "distance": 220, "score": 1, "penalty": None, "feel": "A", "result": "B"},
        {"holenum": 1, "club": "I7", "on": "F", "retplace": "G", "distance": 145, "score": 1, "penalty": None, "feel": "B", "result": "A"},
        {"holenum": 1, "club": "P", "on": "G", "retplace": "H", "distance": 1, "score": 1, "penalty": None, "feel": "A", "result": "A"},
    ]
    shot_facts = normalize_shot_states(round_1, holes, shots_round_1)
    shot_facts.extend(normalize_shot_states(round_2, holes, shots_round_2))

    plain_table = build_expected_score_table(
        shot_facts,
        min_samples_by_level={
            "full": 1,
            "no_par": 1,
            "no_distance": 1,
            "start_category": 1,
            "start_only": 1,
        },
    )
    weighted_table = build_expected_score_table(
        shot_facts,
        min_samples_by_level={
            "full": 1,
            "no_par": 1,
            "no_distance": 1,
            "start_category": 1,
            "start_only": 1,
        },
        round_weights={1: 0.5, 2: 1.0},
    )

    tee_key = ("tee", "160_plus", 4, "off_the_tee")
    assert plain_table["full"][tee_key]["expected_strokes"] == pytest.approx(3.5)
    assert weighted_table["full"][tee_key]["expected_strokes"] == pytest.approx((4 * 0.5 + 3 * 1.0) / 1.5)
