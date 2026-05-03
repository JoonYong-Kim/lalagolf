from lalagolf_analytics_core.boundary import (
    insight_to_persistence_payload,
    shot_values_to_persistence_rows,
    upload_preview_to_analytics_payload,
)
from lalagolf_analytics_core.insights import build_insight_unit
from lalagolf_analytics_core.shot_model import normalize_shot_states


def test_upload_preview_to_analytics_payload_maps_review_shape_to_shot_model_inputs():
    parsed_round = {
        "holes": [
            {
                "hole_number": 1,
                "par": 4,
                "score": 4,
                "putts": 1,
                "shots": [
                    {
                        "club": "D",
                        "start_lie": "T",
                        "end_lie": "F",
                        "distance": 220,
                        "score_cost": 1,
                        "penalty_type": None,
                        "feel_grade": "A",
                        "result_grade": "B",
                    }
                ],
            }
        ]
    }

    payload = upload_preview_to_analytics_payload(parsed_round, round_ref="review-1")
    facts = normalize_shot_states(payload["round_info"], payload["holes"], payload["shots"])

    assert payload["round_info"] == {"id": "review-1"}
    assert payload["holes"][0]["holenum"] == 1
    assert payload["shots"][0]["retplace"] == "F"
    assert facts[0]["round_id"] == "review-1"
    assert facts[0]["shot_category"] == "off_the_tee"


def test_shot_values_to_persistence_rows_keeps_lookup_metadata_and_payload():
    rows = shot_values_to_persistence_rows(
        [
            {
                "round_id": "round-1",
                "hole_num": 1,
                "shot_num": 2,
                "shot_category": "approach",
                "expected_before": 2.5,
                "expected_after": 1.2,
                "expected_lookup_level": "full",
                "expected_sample_count": 8,
                "expected_source_scope": "user",
                "expected_confidence": "high",
                "shot_cost": 1,
                "shot_value": 0.3,
            }
        ]
    )

    assert rows == [
        {
            "round_ref": "round-1",
            "hole_number": 1,
            "shot_number": 2,
            "category": "approach",
            "expected_before": 2.5,
            "expected_after": 1.2,
            "shot_cost": 1,
            "shot_value": 0.3,
            "expected_lookup_level": "full",
            "expected_sample_count": 8,
            "expected_source_scope": "user",
            "expected_confidence": "high",
            "payload": {
                "round_id": "round-1",
                "hole_num": 1,
                "shot_num": 2,
                "shot_category": "approach",
                "expected_before": 2.5,
                "expected_after": 1.2,
                "expected_lookup_level": "full",
                "expected_sample_count": 8,
                "expected_source_scope": "user",
                "expected_confidence": "high",
                "shot_cost": 1,
                "shot_value": 0.3,
            },
        }
    ]


def test_insight_to_persistence_payload_uses_public_insight_shape():
    insight = build_insight_unit(
        scope_type="window",
        scope_key="last_10",
        category="putting",
        root_cause="three_putt",
        primary_evidence_metric="three_putt_rate",
        problem="3-putt rate is high.",
        evidence="Recent 3-putt rate is 18.0%.",
        impact="Putting cost 1.2 strokes.",
        next_action="Start with lag putting.",
        confidence="medium",
        priority_score=2.0,
    )

    payload = insight_to_persistence_payload(insight)

    assert payload["dedupe_key"] == "window:last_10:putting:three_putt:three_putt_rate"
    assert payload["problem"] == "3-putt rate is high."
    assert payload["confidence"] == "medium"
