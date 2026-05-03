from __future__ import annotations

from typing import Any, TypedDict


class AnalyticsRoundInput(TypedDict):
    id: str | int


class AnalyticsHoleInput(TypedDict, total=False):
    holenum: int
    par: int
    score: int | None
    putt: int | None


class AnalyticsShotInput(TypedDict, total=False):
    holenum: int
    club: str | None
    on: str | None
    retplace: str | None
    distance: int | None
    score: int
    penalty: str | None
    feel: str | None
    result: str | None


class AnalyticsRoundPayload(TypedDict):
    round_info: AnalyticsRoundInput
    holes: list[AnalyticsHoleInput]
    shots: list[AnalyticsShotInput]


class PersistenceShotValueRow(TypedDict, total=False):
    round_ref: str | int | None
    hole_number: int | None
    shot_number: int | None
    category: str | None
    expected_before: float | None
    expected_after: float | None
    shot_cost: int | float
    shot_value: float | None
    expected_lookup_level: str | None
    expected_sample_count: int
    expected_source_scope: str | None
    expected_confidence: str | None
    payload: dict[str, Any]
