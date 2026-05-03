from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Confidence = Literal["low", "medium", "high"]

CONFIDENCE_WEIGHT: dict[Confidence, float] = {
    "low": 0.0,
    "medium": 0.25,
    "high": 0.5,
}

CATEGORY_EVIDENCE_METRICS = {
    "approach": "gir_from_under_160_rate",
    "off_the_tee": "driver_penalty_rate",
    "penalty_impact": "penalty_strokes",
    "putting": "three_putt_rate",
    "recovery": "penalty_strokes",
    "short_game": "up_and_down_rate",
}


@dataclass(frozen=True)
class InsightUnit:
    scope_type: str
    scope_key: str
    category: str
    root_cause: str
    primary_evidence_metric: str
    problem: str
    evidence: str
    impact: str
    next_action: str
    confidence: Confidence
    priority_score: float = 0.0

    @property
    def dedupe_key(self) -> str:
        return build_dedupe_key(
            scope_type=self.scope_type,
            scope_key=self.scope_key,
            category=self.category,
            root_cause=self.root_cause,
            primary_evidence_metric=self.primary_evidence_metric,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_type": self.scope_type,
            "scope_key": self.scope_key,
            "category": self.category,
            "root_cause": self.root_cause,
            "primary_evidence_metric": self.primary_evidence_metric,
            "dedupe_key": self.dedupe_key,
            "problem": self.problem,
            "evidence": self.evidence,
            "impact": self.impact,
            "next_action": self.next_action,
            "confidence": self.confidence,
            "priority_score": self.priority_score,
        }


def build_dedupe_key(
    *,
    scope_type: str,
    scope_key: str,
    category: str,
    root_cause: str,
    primary_evidence_metric: str,
) -> str:
    parts = [scope_type, scope_key, category, root_cause, primary_evidence_metric]
    return ":".join(_normalize_key_part(part) for part in parts)


def build_insight_unit(
    *,
    scope_type: str,
    scope_key: str,
    category: str,
    root_cause: str,
    primary_evidence_metric: str,
    problem: str,
    evidence: str,
    impact: str,
    next_action: str,
    confidence: Confidence,
    priority_score: float = 0.0,
) -> dict[str, Any]:
    return InsightUnit(
        scope_type=scope_type,
        scope_key=scope_key,
        category=category,
        root_cause=root_cause,
        primary_evidence_metric=primary_evidence_metric,
        problem=problem,
        evidence=evidence,
        impact=impact,
        next_action=next_action,
        confidence=confidence,
        priority_score=priority_score,
    ).to_dict()


def recommendation_to_insight_unit(
    recommendation: dict[str, Any],
    *,
    scope_type: str = "window",
    scope_key: str = "last_10",
) -> dict[str, Any]:
    category = str(recommendation.get("category") or "unknown")
    root_cause = str(
        recommendation.get("context_subtype")
        or recommendation.get("urgency_label")
        or recommendation.get("trend_direction")
        or "general"
    )
    primary_evidence_metric = CATEGORY_EVIDENCE_METRICS.get(category, f"{category}_shot_value")
    sample = recommendation.get("sample") or {}
    confidence = _coerce_confidence(sample.get("level"))

    return build_insight_unit(
        scope_type=scope_type,
        scope_key=scope_key,
        category=category,
        root_cause=root_cause,
        primary_evidence_metric=primary_evidence_metric,
        problem=_first_text(
            recommendation.get("message"),
            recommendation.get("title"),
            f"{category} needs attention.",
        ),
        evidence=_build_evidence(recommendation),
        impact=_first_text(
            recommendation.get("priority_reason"),
            _format_loss_impact(recommendation),
            "Score impact is not estimated yet.",
        ),
        next_action=_first_text(
            recommendation.get("priority_action"),
            recommendation.get("practice"),
            "Track this pattern in the next round.",
        ),
        confidence=confidence,
        priority_score=_priority_score(recommendation, confidence),
    )


def dedupe_insights(
    insights: list[dict[str, Any]],
    *,
    limit: int | None = 3,
    suppress_same_evidence: bool = True,
) -> list[dict[str, Any]]:
    sorted_insights = sorted(insights, key=_sort_key, reverse=True)
    selected: list[dict[str, Any]] = []
    seen_dedupe_keys: set[str] = set()
    seen_evidence_metrics: set[str] = set()

    for insight in sorted_insights:
        dedupe_key = _ensure_dedupe_key(insight)
        if dedupe_key in seen_dedupe_keys:
            continue

        evidence_metric = str(insight.get("primary_evidence_metric") or "")
        if suppress_same_evidence and evidence_metric and evidence_metric in seen_evidence_metrics:
            continue

        selected.append({**insight, "dedupe_key": dedupe_key})
        seen_dedupe_keys.add(dedupe_key)
        if evidence_metric:
            seen_evidence_metrics.add(evidence_metric)

        if limit is not None and len(selected) >= limit:
            break

    return selected


def _normalize_key_part(value: object) -> str:
    return str(value or "unknown").strip().lower().replace(" ", "_")


def _coerce_confidence(value: object) -> Confidence:
    if value in {"low", "medium", "high"}:
        return value  # type: ignore[return-value]
    return "low"


def _first_text(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_evidence(recommendation: dict[str, Any]) -> str:
    reasons = [reason for reason in recommendation.get("reasons", []) if isinstance(reason, str)]
    context_note = recommendation.get("context_note")
    if isinstance(context_note, str) and context_note:
        reasons.append(context_note)
    if reasons:
        return " ".join(reasons[:2])

    count = recommendation.get("count")
    average_loss = recommendation.get("average_loss")
    if count is not None and average_loss is not None:
        return f"{count} shots, average shot value {average_loss:.2f}."
    return "Evidence is not available."


def _format_loss_impact(recommendation: dict[str, Any]) -> str:
    loss = recommendation.get("loss")
    if isinstance(loss, int | float):
        return f"Estimated score impact is {abs(loss):.2f} strokes."
    return ""


def _priority_score(insight: dict[str, Any], confidence: Confidence) -> float:
    base_score = float(insight.get("priority_score") or 0.0)
    loss = insight.get("loss")
    if isinstance(loss, int | float):
        base_score = max(base_score, abs(loss))
    return base_score + CONFIDENCE_WEIGHT[confidence]


def _ensure_dedupe_key(insight: dict[str, Any]) -> str:
    dedupe_key = insight.get("dedupe_key")
    if isinstance(dedupe_key, str) and dedupe_key:
        return dedupe_key
    return build_dedupe_key(
        scope_type=str(insight.get("scope_type") or "unknown"),
        scope_key=str(insight.get("scope_key") or "unknown"),
        category=str(insight.get("category") or "unknown"),
        root_cause=str(insight.get("root_cause") or "unknown"),
        primary_evidence_metric=str(insight.get("primary_evidence_metric") or "unknown"),
    )


def _sort_key(insight: dict[str, Any]) -> tuple[float, float]:
    confidence = _coerce_confidence(insight.get("confidence"))
    return (float(insight.get("priority_score") or 0.0), CONFIDENCE_WEIGHT[confidence])
