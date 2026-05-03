from app.services.analytics import (
    build_shot_facts_from_upload_preview,
    build_shot_value_rows,
    parse_upload_preview,
)


def test_parse_upload_preview_uses_analytics_core_normalizer():
    raw_content = "\n".join(
        [
            "2024.07.13 08:00",
            "Lala Golf Club",
            "John",
            "1P4",
            "D A B",
            "I7 B A 145",
            "P A A 4",
        ]
    )

    result = parse_upload_preview(raw_content, file_name="round.txt")

    assert result["parsed_round"]["play_date"] == "2024-07-13"
    assert result["parsed_round"]["course_name"] == "Lala Golf Club"
    assert result["parsed_round"]["holes"][0]["shots"][0]["club"] == "D"


def test_build_shot_facts_from_upload_preview_maps_without_db_models():
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

    facts = build_shot_facts_from_upload_preview(parsed_round, round_ref="round-1")

    assert facts[0]["round_id"] == "round-1"
    assert facts[0]["hole_num"] == 1
    assert facts[0]["shot_category"] == "off_the_tee"


def test_build_shot_value_rows_returns_persistence_payloads():
    rows = build_shot_value_rows(
        [
            {
                "round_id": "round-1",
                "hole_num": 1,
                "shot_num": 1,
                "shot_category": "off_the_tee",
                "shot_cost": 1,
                "shot_value": 0.2,
            }
        ]
    )

    assert rows[0]["round_ref"] == "round-1"
    assert rows[0]["hole_number"] == 1
    assert rows[0]["category"] == "off_the_tee"
    assert rows[0]["payload"]["shot_value"] == 0.2
