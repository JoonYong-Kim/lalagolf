import re
from typing import Any

Locale = str


def normalize_locale(locale: str | None) -> Locale:
    return "en" if locale == "en" else "ko"


def render_insight_payload(payload: dict[str, Any], *, locale: str | None) -> dict[str, Any]:
    if normalize_locale(locale) != "en":
        return payload

    rendered = _render_known_english(payload)
    if rendered is None:
        return payload
    return {**payload, **rendered}


def _render_known_english(payload: dict[str, Any]) -> dict[str, str] | None:
    metric = str(payload.get("primary_evidence_metric") or "")
    root_cause = str(payload.get("root_cause") or "")
    category = str(payload.get("category") or "")

    if metric == "penalty_strokes" or root_cause == "penalty_strokes":
        penalties = _first_number(payload.get("evidence"))
        penalty_text = f"{int(penalties)} total penalty strokes" if penalties else "penalty strokes"
        return {
            "problem": "Penalties loss",
            "evidence": f"Saved rounds include {penalty_text}.",
            "impact": "Penalties often add recovery-shot cost.",
            "next_action": "Set tee target width and safe-club rules before risky holes.",
        }

    if metric == "three_putt_rate" or root_cause == "three_putt":
        numbers = _numbers(payload.get("evidence"))
        evidence = (
            f"{int(numbers[1])} of {int(numbers[0])} putting records were 3-putts or worse."
            if len(numbers) >= 2
            else "Your putting records include 3-putts or worse."
        )
        return {
            "problem": "3-putt risk",
            "evidence": evidence,
            "impact": "3-putts quickly break par-save momentum.",
            "next_action": "Pair 6-12m lag-putt distance control with 1-2m finish-putt checks.",
        }

    if metric.endswith("_shot_value") or root_cause == "shot_value_loss":
        count = _first_number(payload.get("evidence"))
        total = _last_number(payload.get("evidence"))
        label = _category_label(category)
        evidence = (
            f"Across {int(count)} shots, estimated shot value totals {total:.2f} strokes."
            if count is not None and total is not None
            else f"Estimated shot value shows repeated loss in {label.lower()}."
        )
        return {
            "problem": f"{label} loss",
            "evidence": evidence,
            "impact": "Repeated category loss can lock in your scoring average.",
            "next_action": f"Track big misses and penalties in {label.lower()} first.",
        }

    if metric == "average_score" or root_cause == "baseline":
        avg_score = _first_number(payload.get("evidence"))
        evidence = (
            f"Your saved-round average score is {avg_score:g}."
            if avg_score is not None
            else "Your saved-round scoring baseline is available."
        )
        return {
            "problem": "Scoring baseline",
            "evidence": evidence,
            "impact": "Use this baseline to narrow category losses.",
            "next_action": "Add more rounds to improve category shot-value confidence.",
        }

    return None


def _category_label(category: str) -> str:
    return {
        "score": "Score",
        "off_the_tee": "Tee shot",
        "approach": "Approach",
        "short_game": "Short game",
        "control_shot": "Control shot",
        "iron_shot": "Iron shot",
        "putting": "Putting",
        "recovery": "Recovery",
        "penalty_impact": "Penalty",
    }.get(category, category.replace("_", " ").title())


def _first_number(value: object) -> float | None:
    numbers = _numbers(value)
    return numbers[0] if numbers else None


def _last_number(value: object) -> float | None:
    numbers = _numbers(value)
    return numbers[-1] if numbers else None


def _numbers(value: object) -> list[float]:
    if not isinstance(value, str):
        return []
    return [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", value)]
