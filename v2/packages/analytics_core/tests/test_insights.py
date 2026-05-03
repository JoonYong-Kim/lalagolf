from lalagolf_analytics_core.insights import (
    build_insight_unit,
    dedupe_insights,
    recommendation_to_insight_unit,
)


def test_build_insight_unit_has_required_shape():
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

    assert insight["problem"]
    assert insight["evidence"]
    assert insight["impact"]
    assert insight["next_action"]
    assert insight["confidence"] == "medium"
    assert insight["dedupe_key"] == "window:last_10:putting:three_putt:three_putt_rate"


def test_recommendation_to_insight_unit_maps_priority_card():
    recommendation = {
        "category": "approach",
        "message": "최근 10라운드 어프로치 반복 손실은 -2.40타입니다.",
        "reasons": ["최근 20샷에서 평균 shot value가 -0.12타입니다."],
        "priority_reason": "총 손실 2.40타입니다.",
        "priority_action": "클럽별 캐리 기준을 먼저 다시 고정하세요.",
        "context_subtype": "거리 오차형",
        "sample": {"level": "medium"},
        "priority_score": 3.55,
    }

    insight = recommendation_to_insight_unit(recommendation)

    assert insight["category"] == "approach"
    assert insight["root_cause"] == "거리 오차형"
    assert insight["primary_evidence_metric"] == "gir_from_under_160_rate"
    assert insight["confidence"] == "medium"
    assert insight["problem"].startswith("최근 10라운드")
    assert insight["next_action"] == "클럽별 캐리 기준을 먼저 다시 고정하세요."


def test_dedupe_insights_keeps_highest_priority_for_same_key():
    lower = build_insight_unit(
        scope_type="window",
        scope_key="last_10",
        category="putting",
        root_cause="three_putt",
        primary_evidence_metric="three_putt_rate",
        problem="Lower",
        evidence="Evidence",
        impact="Impact",
        next_action="Action",
        confidence="high",
        priority_score=1.0,
    )
    higher = {**lower, "problem": "Higher", "priority_score": 2.0}

    deduped = dedupe_insights([lower, higher], limit=None)

    assert len(deduped) == 1
    assert deduped[0]["problem"] == "Higher"


def test_dedupe_insights_suppresses_same_dashboard_evidence_metric():
    putting = build_insight_unit(
        scope_type="window",
        scope_key="last_10",
        category="putting",
        root_cause="three_putt",
        primary_evidence_metric="three_putt_rate",
        problem="Putting",
        evidence="Evidence",
        impact="Impact",
        next_action="Action",
        confidence="high",
        priority_score=3.0,
    )
    duplicate_evidence = build_insight_unit(
        scope_type="window",
        scope_key="last_10",
        category="putting",
        root_cause="lag_putt",
        primary_evidence_metric="three_putt_rate",
        problem="Lag putting",
        evidence="Evidence",
        impact="Impact",
        next_action="Action",
        confidence="high",
        priority_score=2.0,
    )
    approach = build_insight_unit(
        scope_type="window",
        scope_key="last_10",
        category="approach",
        root_cause="distance_control",
        primary_evidence_metric="gir_from_under_160_rate",
        problem="Approach",
        evidence="Evidence",
        impact="Impact",
        next_action="Action",
        confidence="medium",
        priority_score=1.0,
    )

    deduped = dedupe_insights([approach, duplicate_evidence, putting], limit=3)

    assert [insight["problem"] for insight in deduped] == ["Putting", "Approach"]


def test_dedupe_insights_defaults_to_three_items():
    insights = [
        build_insight_unit(
            scope_type="window",
            scope_key="last_10",
            category=f"category_{index}",
            root_cause="root",
            primary_evidence_metric=f"metric_{index}",
            problem=f"Problem {index}",
            evidence="Evidence",
            impact="Impact",
            next_action="Action",
            confidence="medium",
            priority_score=float(index),
        )
        for index in range(5)
    ]

    deduped = dedupe_insights(insights)

    assert len(deduped) == 3
    assert [insight["problem"] for insight in deduped] == ["Problem 4", "Problem 3", "Problem 2"]
