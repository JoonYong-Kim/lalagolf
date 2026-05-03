from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from lalagolf_analytics_core.data_parser import parse_content


PENALTY_STROKES = {
    "H": 1,
    "UN": 1,
    "OB": 2,
}


def normalize_upload_content(raw_content: str, file_name: str = "<memory>") -> dict[str, Any]:
    raw, parsed_data, stats = parse_content(raw_content, file_name)
    parsed_round = normalize_parsed_round(parsed_data, stats)
    warnings = build_upload_warnings(raw, parsed_data, parsed_round)

    return {
        "raw_content": raw,
        "parsed_round": parsed_round,
        "warnings": warnings,
        "stats": stats,
    }


def normalize_parsed_round(parsed_data: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    overall = stats.get("overall") or {}
    tee_off_time = parsed_data.get("tee_off_time")
    holes = [
        _normalize_hole(hole_index, hole)
        for hole_index, hole in enumerate(parsed_data.get("holes", []))
    ]
    companions = _split_companions(parsed_data.get("co_players"))

    return {
        "file_name": parsed_data.get("file_name"),
        "play_date": _play_date(tee_off_time),
        "tee_off_time": tee_off_time,
        "course_name": parsed_data.get("golf_course"),
        "companions": companions,
        "total_score": overall.get("total_shots"),
        "total_par": overall.get("total_par"),
        "score_to_par": overall.get("score_relative_to_par"),
        "hole_count": len(holes),
        "holes": holes,
    }


def build_upload_warnings(
    raw_content: str,
    parsed_data: dict[str, Any],
    parsed_round: dict[str, Any],
) -> list[dict[str, Any]]:
    warnings = []

    if not parsed_round.get("play_date"):
        warnings.append(
            _warning(
                code="missing_tee_off_time",
                message="Tee-off date could not be parsed.",
                path="play_date",
            )
        )
    if not parsed_round.get("course_name"):
        warnings.append(
            _warning(
                code="missing_course_name",
                message="Course name is missing.",
                path="course_name",
            )
        )
    if parsed_round["hole_count"] == 0:
        warnings.append(
            _warning(
                code="empty_round",
                message="No holes were parsed from the uploaded file.",
                path="holes",
            )
        )
    elif parsed_round["hole_count"] not in {9, 18, 27}:
        warnings.append(
            _warning(
                code="non_standard_hole_count",
                message="Parsed hole count is not 9, 18, or 27.",
                path="hole_count",
                details={"hole_count": parsed_round["hole_count"]},
            )
        )

    for hole_index, hole in enumerate(parsed_round["holes"]):
        if not hole["shots"]:
            warnings.append(
                _warning(
                    code="hole_without_shots",
                    message="Hole has no parsed shots.",
                    path=f"holes[{hole_index}].shots",
                    details={"hole_number": hole["hole_number"]},
                )
            )

    line_paths = _line_paths_for_unparsed(raw_content, parsed_data.get("unparsed_lines", []))
    for unparsed_index, original_line in enumerate(parsed_data.get("unparsed_lines", [])):
        warnings.append(
            _warning(
                code="unparsed_line",
                message="Line could not be parsed as round metadata, a hole, or a shot.",
                path=line_paths.get(unparsed_index, f"unparsed_lines[{unparsed_index}]"),
                raw_text=original_line,
            )
        )

    return warnings


def _normalize_hole(hole_index: int, hole: dict[str, Any]) -> dict[str, Any]:
    shots = [
        _normalize_shot(hole_index, shot_index, shot)
        for shot_index, shot in enumerate(hole.get("shots", []))
    ]
    penalties = sum(shot["penalty_strokes"] for shot in shots)
    score = sum(shot["score_cost"] for shot in shots)

    return {
        "hole_number": hole.get("hole_num"),
        "par": hole.get("par"),
        "score": score,
        "putts": hole.get("putt"),
        "gir": _is_gir(hole.get("par"), score, hole.get("putt")),
        "penalties": penalties,
        "shots": shots,
    }


def _normalize_shot(hole_index: int, shot_index: int, shot: dict[str, Any]) -> dict[str, Any]:
    penalty_type = shot.get("penalty")
    return {
        "shot_number": shot_index + 1,
        "club": shot.get("club"),
        "club_normalized": shot.get("club"),
        "distance": _int_or_none(shot.get("distance")),
        "start_lie": shot.get("on"),
        "end_lie": shot.get("retplace"),
        "result_grade": shot.get("result"),
        "feel_grade": shot.get("feel"),
        "penalty_type": penalty_type,
        "penalty_strokes": PENALTY_STROKES.get(penalty_type, 0),
        "score_cost": shot.get("score", 1),
        "raw_text": shot.get("original_line"),
        "path": f"holes[{hole_index}].shots[{shot_index}]",
    }


def _is_gir(par: int | None, score: int | None, putts: int | None) -> bool | None:
    if par is None or score is None or putts is None:
        return None
    return par >= score - putts + 2


def _split_companions(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    separator = "," if "," in value else r"\s+"
    return [name.strip() for name in re.split(separator, value.strip()) if name.strip()]


def _play_date(tee_off_time: object) -> str | None:
    if not isinstance(tee_off_time, str) or not tee_off_time:
        return None
    try:
        return datetime.strptime(tee_off_time, "%Y-%m-%d %H:%M").date().isoformat()
    except ValueError:
        return None


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _warning(
    *,
    code: str,
    message: str,
    path: str,
    raw_text: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warning = {
        "code": code,
        "message": message,
        "path": path,
    }
    if raw_text is not None:
        warning["raw_text"] = raw_text
    if details:
        warning["details"] = details
    return warning


def _line_paths_for_unparsed(raw_content: str, unparsed_lines: list[str]) -> dict[int, str]:
    line_paths = {}
    raw_lines = [line.strip() for line in raw_content.splitlines()]
    cursor = 0

    for unparsed_index, unparsed_line in enumerate(unparsed_lines):
        for line_index in range(cursor, len(raw_lines)):
            if raw_lines[line_index] == unparsed_line:
                line_paths[unparsed_index] = f"raw_lines[{line_index}]"
                cursor = line_index + 1
                break

    return line_paths
