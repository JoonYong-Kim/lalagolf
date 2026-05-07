from collections import defaultdict


DISTANCE_BANDS = [
    ("0_30", "0-30m", 0, 30),
    ("30_80", "30-80m", 30, 80),
    ("80_120", "80-120m", 80, 120),
    ("120_160", "120-160m", 120, 160),
    ("160_plus", "160m+", 160, None),
]


LIE_MAP = {
    "T": "tee",
    "F": "fairway",
    "R": "recovery",
    "B": "bunker",
    "G": "green",
    "H": "hole",
}


def classify_club_group(club):
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


def classify_distance_bucket(distance):
    if distance is None:
        return None
    for bucket_key, _, low, high in DISTANCE_BANDS:
        if distance >= low and (high is None or distance < high):
            return bucket_key
    return None


def normalize_lie_state(code):
    return LIE_MAP.get(code, "unknown")


def categorize_shot(shot):
    club = shot.get("club")
    start_state = normalize_lie_state(shot.get("on"))
    distance = shot.get("distance")

    if club == "P":
        return "putting"
    if start_state == "tee":
        return "off_the_tee"
    if shot.get("penalty") or start_state == "recovery":
        return "recovery"
    if distance is not None and distance < 40:
        return "short_game"
    if distance is not None and distance < 90:
        return "control_shot"
    if distance is not None and distance >= 90:
        return "iron_shot"
    return "control_shot"


def _group_shots_by_hole(shots):
    grouped = defaultdict(list)
    for shot in shots:
        holenum = shot.get("holenum")
        if holenum is None:
            continue
        grouped[holenum].append(shot)
    return grouped


def normalize_shot_states(round_info, holes, shots):
    hole_map = {}
    for hole in holes:
        hole_num = hole.get("hole_num", hole.get("holenum"))
        if hole_num is None:
            continue
        hole_map[hole_num] = hole

    grouped_shots = _group_shots_by_hole(shots)
    shot_facts = []

    for holenum in sorted(grouped_shots.keys()):
        hole = hole_map.get(holenum, {})
        par = hole.get("par")
        ordered_shots = grouped_shots[holenum]
        for idx, shot in enumerate(ordered_shots, start=1):
            start_state = normalize_lie_state(shot.get("on"))
            end_state = normalize_lie_state(shot.get("retplace"))
            distance = shot.get("distance")
            fact = {
                "round_id": round_info.get("id"),
                "hole_num": holenum,
                "shot_num": idx,
                "par_type": par,
                "club": shot.get("club"),
                "club_group": classify_club_group(shot.get("club")),
                "start_state": start_state,
                "end_state": end_state,
                "distance": distance,
                "distance_bucket": classify_distance_bucket(distance),
                "is_tee_shot": idx == 1,
                "is_putt": shot.get("club") == "P",
                "is_recovery": start_state == "recovery" or bool(shot.get("penalty")),
                "shot_category": categorize_shot(shot),
                "penalty_strokes": 2 if shot.get("penalty") == "OB" else 1 if shot.get("penalty") in {"H", "UN"} else 0,
                "score_cost": shot.get("score", 1),
                "feel": shot.get("feel"),
                "result": shot.get("result"),
                "expected_before": None,
                "expected_after": None,
                "shot_value": None,
            }
            shot_facts.append(fact)

    return shot_facts


def build_shot_state_summary(shot_facts):
    summary = {
        "total_shots": len(shot_facts),
        "by_category": defaultdict(int),
        "by_start_state": defaultdict(int),
        "by_club_group": defaultdict(int),
        "by_distance_bucket": defaultdict(int),
        "tee_shots": 0,
        "putts": 0,
        "recovery_shots": 0,
        "penalty_shots": 0,
    }

    for fact in shot_facts:
        summary["by_category"][fact["shot_category"]] += 1
        summary["by_start_state"][fact["start_state"]] += 1
        summary["by_club_group"][fact["club_group"]] += 1
        if fact["distance_bucket"] is not None:
            summary["by_distance_bucket"][fact["distance_bucket"]] += 1
        if fact["is_tee_shot"]:
            summary["tee_shots"] += 1
        if fact["is_putt"]:
            summary["putts"] += 1
        if fact["is_recovery"]:
            summary["recovery_shots"] += 1
        if fact["penalty_strokes"] > 0:
            summary["penalty_shots"] += 1

    summary["by_category"] = dict(summary["by_category"])
    summary["by_start_state"] = dict(summary["by_start_state"])
    summary["by_club_group"] = dict(summary["by_club_group"])
    summary["by_distance_bucket"] = dict(summary["by_distance_bucket"])
    return summary
