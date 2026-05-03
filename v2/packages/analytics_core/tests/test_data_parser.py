from pathlib import Path

from lalagolf_analytics_core.data_parser import parse_content, parse_file


def test_parse_content_basic_round() -> None:
    raw_content = "\n".join(
        [
            "2024.07.13 08:00",
            "Lala Golf Club",
            "John, Jane, Mike",
            "1P4",
            "D B C",
            "I5 A C 150 H",
            "P C A 10 OK",
            "2P3",
            "I7 A A",
            "P B B 5",
        ]
    )

    _raw, parsed_data, stats = parse_content(raw_content, "<test>")

    assert parsed_data["file_name"] == "<test>"
    assert parsed_data["tee_off_time"] == "2024-07-13 08:00"
    assert parsed_data["golf_course"] == "Lala Golf Club"
    assert parsed_data["co_players"] == "John, Jane, Mike"
    assert parsed_data["unparsed_lines"] == []
    assert len(parsed_data["holes"]) == 2
    assert parsed_data["holes"][0]["shots"][0]["club"] == "D"
    assert parsed_data["holes"][0]["shots"][1]["penalty"] == "H"
    assert parsed_data["holes"][0]["shots"][2]["concede"] is True
    assert stats["overall"]["total_shots"] == 7
    assert stats["overall"]["total_par"] == 7


def test_parse_content_collects_unparsed_lines() -> None:
    raw_content = "\n".join(
        [
            "2024.07.13 10:00",
            "Unparsed Test Course",
            "Charlie, David",
            "1P4",
            "D B C",
            "This is an unparseable line",
            "I5 A C 150 H",
            "Another unparseable line",
            "2P3",
            "I7 A A",
        ]
    )

    _raw, parsed_data, _stats = parse_content(raw_content, "<test>")

    assert parsed_data["unparsed_lines"] == [
        "This is an unparseable line",
        "Another unparseable line",
    ]
    assert len(parsed_data["holes"]) == 2


def test_parse_27_hole_fixture() -> None:
    fixture_path = Path(__file__).parent / "data" / "test_27.txt"

    _raw, parsed_data, _stats = parse_file(str(fixture_path))

    assert parsed_data["tee_off_time"] == "2020-07-21 06:38"
    assert parsed_data["golf_course"] == "킹스데일"
    assert parsed_data["co_players"] == "바시공"
    assert len(parsed_data["holes"]) == 27
    assert parsed_data["unparsed_lines"] == []
    assert parsed_data["holes"][0]["hole_num"] == 1
    assert parsed_data["holes"][-1]["hole_num"] == 27
