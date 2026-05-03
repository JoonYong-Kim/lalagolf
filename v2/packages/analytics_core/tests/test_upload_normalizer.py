from lalagolf_analytics_core.upload_normalizer import normalize_upload_content


def test_normalize_upload_content_returns_review_preview_shape():
    raw_content = "\n".join(
        [
            "2024.07.13 08:00",
            "Lala Golf Club",
            "John, Jane",
            "1P4",
            "D B C",
            "I5 A C 150 H",
            "P C A 10 OK",
            "2P3",
            "I7 A A",
            "P B B 5",
        ]
    )

    result = normalize_upload_content(raw_content, "round.txt")
    parsed_round = result["parsed_round"]

    assert parsed_round["file_name"] == "round.txt"
    assert parsed_round["play_date"] == "2024-07-13"
    assert parsed_round["tee_off_time"] == "2024-07-13 08:00"
    assert parsed_round["course_name"] == "Lala Golf Club"
    assert parsed_round["companions"] == ["John", "Jane"]
    assert parsed_round["total_score"] == 7
    assert parsed_round["total_par"] == 7
    assert parsed_round["hole_count"] == 2
    assert parsed_round["holes"][0]["hole_number"] == 1
    assert parsed_round["holes"][0]["score"] == 5
    assert parsed_round["holes"][0]["penalties"] == 1
    assert parsed_round["holes"][0]["shots"][0] == {
        "shot_number": 1,
        "club": "D",
        "club_normalized": "D",
        "distance": 220,
        "start_lie": "T",
        "end_lie": "R",
        "result_grade": "C",
        "feel_grade": "B",
        "penalty_type": None,
        "penalty_strokes": 0,
        "score_cost": 1,
        "raw_text": "D B C",
        "path": "holes[0].shots[0]",
    }
    assert result["warnings"] == [
        {
            "code": "non_standard_hole_count",
            "message": "Parsed hole count is not 9, 18, or 27.",
            "path": "hole_count",
            "details": {"hole_count": 2},
        }
    ]


def test_normalize_upload_content_returns_stable_unparsed_line_warnings():
    raw_content = "\n".join(
        [
            "2024.07.13 10:00",
            "Warning Course",
            "Charlie",
            "1P4",
            "D B C",
            "This is an unparseable line",
            "I5 A C 150 H",
        ]
    )

    result = normalize_upload_content(raw_content, "warning.txt")

    assert {
        "code": "unparsed_line",
        "message": "Line could not be parsed as round metadata, a hole, or a shot.",
        "path": "raw_lines[5]",
        "raw_text": "This is an unparseable line",
    } in result["warnings"]


def test_normalize_upload_content_warns_for_missing_metadata_and_empty_round():
    result = normalize_upload_content("not a round", "bad.txt")

    assert result["parsed_round"]["play_date"] is None
    assert result["parsed_round"]["course_name"] is None
    assert result["parsed_round"]["holes"] == []
    warning_codes = {warning["code"] for warning in result["warnings"]}
    assert {"missing_tee_off_time", "missing_course_name", "empty_round", "unparsed_line"} <= warning_codes


def test_normalize_upload_content_splits_space_separated_korean_companions():
    raw_content = "\n".join(
        [
            "2026-04-11 13:23",
            "베르힐 영종",
            "홍성걸 양명욱 임길수",
            "1P4",
            "D C C",
            "I7 C C",
            "P B B 12 OK",
        ]
    )

    result = normalize_upload_content(raw_content, "round.txt")

    assert result["parsed_round"]["companions"] == ["홍성걸", "양명욱", "임길수"]
