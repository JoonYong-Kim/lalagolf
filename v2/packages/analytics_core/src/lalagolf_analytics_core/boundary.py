from __future__ import annotations

from typing import Any

from lalagolf_analytics_core.contracts import (
    AnalyticsHoleInput,
    AnalyticsRoundInput,
    AnalyticsRoundPayload,
    AnalyticsShotInput,
    PersistenceShotValueRow,
)


def upload_preview_to_analytics_payload(
    parsed_round: dict[str, Any],
    *,
    round_ref: str | int = "upload_preview",
) -> AnalyticsRoundPayload:
    holes: list[AnalyticsHoleInput] = []
    shots: list[AnalyticsShotInput] = []

    for hole in parsed_round.get("holes", []):
        hole_number = hole.get("hole_number")
        holes.append(
            {
                "holenum": hole_number,
                "par": hole.get("par"),
                "score": hole.get("score"),
                "putt": hole.get("putts"),
            }
        )
        for shot in hole.get("shots", []):
            shots.append(
                {
                    "holenum": hole_number,
                    "club": shot.get("club"),
                    "on": shot.get("start_lie"),
                    "retplace": shot.get("end_lie"),
                    "distance": shot.get("distance"),
                    "score": shot.get("score_cost") or 1,
                    "penalty": shot.get("penalty_type"),
                    "feel": shot.get("feel_grade"),
                    "result": shot.get("result_grade"),
                }
            )

    round_info: AnalyticsRoundInput = {"id": round_ref}
    return {
        "round_info": round_info,
        "holes": holes,
        "shots": shots,
    }


def shot_values_to_persistence_rows(
    shot_values: list[dict[str, Any]],
) -> list[PersistenceShotValueRow]:
    rows: list[PersistenceShotValueRow] = []

    for fact in shot_values:
        rows.append(
            {
                "round_ref": fact.get("round_id"),
                "hole_number": fact.get("hole_num"),
                "shot_number": fact.get("shot_num"),
                "category": fact.get("shot_category"),
                "expected_before": fact.get("expected_before"),
                "expected_after": fact.get("expected_after"),
                "shot_cost": fact.get("shot_cost") or 0,
                "shot_value": fact.get("shot_value"),
                "expected_lookup_level": fact.get("expected_lookup_level"),
                "expected_sample_count": fact.get("expected_sample_count") or 0,
                "expected_source_scope": fact.get("expected_source_scope"),
                "expected_confidence": fact.get("expected_confidence"),
                "payload": dict(fact),
            }
        )

    return rows


def insight_to_persistence_payload(insight: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope_type": insight.get("scope_type"),
        "scope_key": insight.get("scope_key"),
        "category": insight.get("category"),
        "root_cause": insight.get("root_cause"),
        "primary_evidence_metric": insight.get("primary_evidence_metric"),
        "dedupe_key": insight.get("dedupe_key"),
        "problem": insight.get("problem"),
        "evidence": insight.get("evidence"),
        "impact": insight.get("impact"),
        "next_action": insight.get("next_action"),
        "confidence": insight.get("confidence"),
        "priority_score": insight.get("priority_score") or 0.0,
    }
