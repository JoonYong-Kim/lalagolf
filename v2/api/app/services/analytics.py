import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from lalagolf_analytics_core.boundary import (
    shot_values_to_persistence_rows,
    upload_preview_to_analytics_payload,
)
from lalagolf_analytics_core.insights import build_insight_unit, dedupe_insights
from lalagolf_analytics_core.shot_model import normalize_shot_states
from lalagolf_analytics_core.upload_normalizer import normalize_upload_content
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AnalysisSnapshot,
    ExpectedScoreTable,
    Hole,
    Insight,
    Round,
    RoundMetric,
    Shot,
    ShotValue,
    User,
)
from app.models.constants import COMPUTED_STATUS_FAILED, COMPUTED_STATUS_READY


def parse_upload_preview(raw_content: str, *, file_name: str) -> dict[str, Any]:
    return normalize_upload_content(raw_content, file_name)


def build_shot_facts_from_upload_preview(
    parsed_round: dict[str, Any],
    *,
    round_ref: str | int = "upload_preview",
) -> list[dict[str, Any]]:
    payload = upload_preview_to_analytics_payload(parsed_round, round_ref=round_ref)
    return normalize_shot_states(payload["round_info"], payload["holes"], payload["shots"])


def build_shot_value_rows(shot_values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(shot_values_to_persistence_rows(shot_values))


class AnalyticsNotFoundError(Exception):
    pass


def recalculate_round_metrics(db: Session, *, owner: User, round_id: uuid.UUID) -> dict[str, Any]:
    round_ = _get_round(db, owner=owner, round_id=round_id)
    try:
        _replace_round_metrics(db, round_)
        _recalculate_expected_table(db, owner)
        _replace_shot_values(db, owner=owner, round_=round_)
        active_insights = _replace_insights(db, owner=owner)
        _replace_snapshot(db, owner=owner, insights=active_insights)
        round_.computed_status = COMPUTED_STATUS_READY
        db.commit()
    except Exception as exc:
        db.rollback()
        round_ = _get_round(db, owner=owner, round_id=round_id)
        round_.computed_status = COMPUTED_STATUS_FAILED
        db.add(
            AnalysisSnapshot(
                user_id=owner.id,
                scope_type="job_error",
                scope_key=f"round:{round_id}",
                payload={
                    "job": "recalculate_round_metrics",
                    "round_id": str(round_id),
                    "error": str(exc),
                },
            )
        )
        db.commit()
        raise

    return {"round_id": round_.id, "computed_status": round_.computed_status}


def recalculate_user_expected_table(db: Session, *, owner: User) -> ExpectedScoreTable:
    table = _recalculate_expected_table(db, owner)
    db.commit()
    return table


def recalculate_shot_values(db: Session, *, owner: User) -> list[ShotValue]:
    rounds = _owned_rounds(db, owner)
    rows: list[ShotValue] = []
    for round_ in rounds:
        rows.extend(_replace_shot_values(db, owner=owner, round_=round_))
    db.commit()
    return rows


def generate_insights(db: Session, *, owner: User) -> list[Insight]:
    insights = _replace_insights(db, owner=owner)
    _replace_snapshot(db, owner=owner, insights=insights)
    db.commit()
    return insights


def get_trends(db: Session, *, owner: User) -> dict[str, Any]:
    rounds = _owned_rounds(db, owner)
    insights = _active_insights(db, owner)
    shot_values = db.scalars(select(ShotValue).where(ShotValue.user_id == owner.id)).all()

    category_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"category": "", "count": 0, "total_shot_value": 0.0}
    )
    for value in shot_values:
        bucket = category_totals[value.category]
        bucket["category"] = value.category
        bucket["count"] += 1
        bucket["total_shot_value"] += value.shot_value or 0

    category_summary = []
    for row in category_totals.values():
        count = row["count"]
        total = row["total_shot_value"]
        category_summary.append(
            {
                **row,
                "avg_shot_value": round(total / count, 3) if count else 0,
            }
        )
    category_summary.sort(key=lambda item: item["total_shot_value"])

    return {
        "kpis": _kpis(rounds),
        "score_trend": _score_trend(rounds),
        "category_summary": category_summary,
        "insights": [_insight_response(insight) for insight in insights],
    }


def get_round_analytics(db: Session, *, owner: User, round_id: uuid.UUID) -> dict[str, Any]:
    round_ = _get_round(db, owner=owner, round_id=round_id)
    metrics = db.scalars(
        select(RoundMetric).where(
            RoundMetric.user_id == owner.id,
            RoundMetric.round_id == round_.id,
        )
    ).all()
    shot_values = db.scalars(
        select(ShotValue).where(ShotValue.user_id == owner.id, ShotValue.round_id == round_.id)
    ).all()
    insights = db.scalars(
        select(Insight).where(
            Insight.user_id == owner.id,
            Insight.status == "active",
            (Insight.round_id == round_.id) | (Insight.round_id.is_(None)),
        )
    ).all()
    return {
        "round_id": round_.id,
        "metrics": {metric.metric_key: metric.payload for metric in metrics},
        "shot_values": [
            {
                "shot_id": str(row.shot_id),
                "category": row.category,
                "shot_value": row.shot_value,
                "expected_confidence": row.expected_confidence,
            }
            for row in shot_values
        ],
        "insights": [_insight_response(insight) for insight in insights],
    }


def compare_analytics(db: Session, *, owner: User, group_by: str = "category") -> dict[str, Any]:
    if group_by not in {"category", "club"}:
        group_by = "category"
    shot_values = db.scalars(select(ShotValue).where(ShotValue.user_id == owner.id)).all()
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"label": "", "count": 0, "total": 0.0}
    )
    for value in shot_values:
        label = (
            value.category
            if group_by == "category"
            else str(value.payload.get("club") or "unknown")
        )
        bucket = buckets[label]
        bucket["label"] = label
        bucket["count"] += 1
        bucket["total"] += value.shot_value or 0

    rows = [
        {
            "label": bucket["label"],
            "sample_count": bucket["count"],
            "total_shot_value": round(bucket["total"], 3),
            "avg_shot_value": round(bucket["total"] / bucket["count"], 3)
            if bucket["count"]
            else 0,
        }
        for bucket in buckets.values()
    ]
    rows.sort(key=lambda item: item["total_shot_value"])
    return {"group_by": group_by, "rows": rows}


def list_insights(db: Session, *, owner: User, status: str = "active") -> list[dict[str, Any]]:
    insights = db.scalars(
        select(Insight)
        .where(Insight.user_id == owner.id, Insight.status == status)
        .order_by(Insight.priority_score.desc(), Insight.created_at.desc())
    ).all()
    return [_insight_response(insight) for insight in insights]


def update_insight_status(
    db: Session,
    *,
    owner: User,
    insight_id: uuid.UUID,
    status: str,
) -> dict[str, Any]:
    insight = db.scalars(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == owner.id)
    ).first()
    if insight is None:
        raise AnalyticsNotFoundError
    if status not in {"active", "dismissed"}:
        status = "active"
    insight.status = status
    insight.dismissed_at = datetime.now(UTC) if status == "dismissed" else None
    db.commit()
    db.refresh(insight)
    return _insight_response(insight)


def active_priority_insights(db: Session, *, owner: User, limit: int = 3) -> list[dict[str, Any]]:
    return [
        _insight_response(insight)
        for insight in db.scalars(
            select(Insight)
            .where(Insight.user_id == owner.id, Insight.status == "active")
            .order_by(Insight.priority_score.desc(), Insight.created_at.desc())
            .limit(limit)
        ).all()
    ]


def _get_round(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = db.scalars(
        select(Round)
        .options(selectinload(Round.holes).selectinload(Hole.shots))
        .where(Round.id == round_id, Round.user_id == owner.id, Round.deleted_at.is_(None))
    ).first()
    if round_ is None:
        raise AnalyticsNotFoundError
    return round_


def _owned_rounds(db: Session, owner: User) -> list[Round]:
    return db.scalars(
        select(Round)
        .options(selectinload(Round.holes).selectinload(Hole.shots))
        .where(Round.user_id == owner.id, Round.deleted_at.is_(None))
        .order_by(Round.play_date.asc(), Round.created_at.asc())
    ).all()


def _replace_round_metrics(db: Session, round_: Round) -> list[RoundMetric]:
    db.query(RoundMetric).filter(RoundMetric.round_id == round_.id).delete()
    holes = sorted(round_.holes, key=lambda item: item.hole_number)
    metrics = _round_metric_payloads(holes)
    rows = [
        RoundMetric(
            user_id=round_.user_id,
            round_id=round_.id,
            category=metric["category"],
            metric_key=metric["metric_key"],
            value=metric["value"],
            sample_count=metric["sample_count"],
            payload=metric,
        )
        for metric in metrics
    ]
    db.add_all(rows)
    return rows


def _round_metric_payloads(holes: list[Hole]) -> list[dict[str, Any]]:
    putts = [hole.putts for hole in holes if hole.putts is not None]
    penalties = sum(hole.penalties for hole in holes)
    gir_count = sum(1 for hole in holes if hole.gir is True)
    three_putts = sum(1 for hole in holes if hole.putts is not None and hole.putts >= 3)
    fairways = [hole for hole in holes if hole.fairway_hit is not None]
    fairway_hits = sum(1 for hole in fairways if hole.fairway_hit is True)
    return [
        _metric("score", "total_score", sum(hole.score or 0 for hole in holes), len(holes)),
        _metric("putting", "putts_total", sum(putts) if putts else None, len(putts)),
        _metric(
            "putting",
            "three_putt_rate",
            three_putts / len(putts) if putts else None,
            len(putts),
        ),
        _metric("approach", "gir_rate", gir_count / len(holes) if holes else None, len(holes)),
        _metric(
            "off_the_tee",
            "fairway_hit_rate",
            fairway_hits / len(fairways) if fairways else None,
            len(fairways),
        ),
        _metric("penalty_impact", "penalty_strokes", penalties, len(holes)),
    ]


def _metric(category: str, key: str, value: float | None, sample_count: int) -> dict[str, Any]:
    return {
        "category": category,
        "metric_key": key,
        "value": value,
        "sample_count": sample_count,
    }


def _recalculate_expected_table(db: Session, owner: User) -> ExpectedScoreTable:
    rounds = _owned_rounds(db, owner)
    category_samples: dict[str, list[int]] = defaultdict(list)
    for round_ in rounds:
        for hole in round_.holes:
            remaining = hole.score or 0
            for shot in sorted(hole.shots, key=lambda item: item.shot_number):
                category_samples[_shot_category(shot, hole)].append(max(remaining, 0))
                remaining -= (shot.score_cost or 1) + (shot.penalty_strokes or 0)

    payload = {
        category: {
            "expected_strokes": round(sum(values) / len(values), 3),
            "sample_count": len(values),
        }
        for category, values in category_samples.items()
    }
    sample_count = sum(len(values) for values in category_samples.values())

    table = db.scalars(
        select(ExpectedScoreTable).where(
            ExpectedScoreTable.user_id == owner.id,
            ExpectedScoreTable.scope_type == "user",
            ExpectedScoreTable.scope_key == "all",
        )
    ).first()
    if table is None:
        table = ExpectedScoreTable(user_id=owner.id, scope_type="user", scope_key="all")
        db.add(table)
    table.sample_count = sample_count
    table.table_payload = payload
    return table


def _replace_shot_values(db: Session, *, owner: User, round_: Round) -> list[ShotValue]:
    db.query(ShotValue).filter(ShotValue.round_id == round_.id).delete()
    table = db.scalars(
        select(ExpectedScoreTable).where(
            ExpectedScoreTable.user_id == owner.id,
            ExpectedScoreTable.scope_type == "user",
            ExpectedScoreTable.scope_key == "all",
        )
    ).first()
    expected = table.table_payload if table else {}
    rows: list[ShotValue] = []
    for hole in sorted(round_.holes, key=lambda item: item.hole_number):
        for shot in sorted(hole.shots, key=lambda item: item.shot_number):
            category = _shot_category(shot, hole)
            category_expected = expected.get(category) or {}
            expected_before = category_expected.get("expected_strokes")
            shot_cost = (shot.score_cost or 1) + (shot.penalty_strokes or 0)
            shot_value = _estimate_shot_value(shot, expected_before, shot_cost)
            rows.append(
                ShotValue(
                    user_id=owner.id,
                    round_id=round_.id,
                    hole_id=hole.id,
                    shot_id=shot.id,
                    category=category,
                    expected_before=expected_before,
                    expected_after=None,
                    shot_cost=shot_cost,
                    shot_value=shot_value,
                    expected_lookup_level="category",
                    expected_sample_count=category_expected.get("sample_count") or 0,
                    expected_source_scope="user",
                    expected_confidence=_confidence(category_expected.get("sample_count") or 0),
                    payload={
                        "hole_number": hole.hole_number,
                        "shot_number": shot.shot_number,
                        "club": shot.club,
                        "distance": shot.distance,
                        "result_grade": shot.result_grade,
                        "penalty_type": shot.penalty_type,
                    },
                )
            )
    db.add_all(rows)
    return rows


def _replace_insights(db: Session, *, owner: User) -> list[Insight]:
    candidates = _build_insight_candidates(db, owner)
    selected = _select_dashboard_insights(candidates, limit=3)
    selected_keys = {str(item["dedupe_key"]) for item in selected}

    existing = db.scalars(select(Insight).where(Insight.user_id == owner.id)).all()
    existing_by_key = {insight.dedupe_key: insight for insight in existing}
    for insight in existing:
        if insight.dedupe_key not in selected_keys and insight.status == "active":
            insight.status = "superseded"

    rows: list[Insight] = []
    for item in selected:
        row = existing_by_key.get(str(item["dedupe_key"]))
        if row is None:
            row = Insight(user_id=owner.id, dedupe_key=str(item["dedupe_key"]))
            db.add(row)
        row.round_id = None
        row.scope_type = str(item["scope_type"])
        row.scope_key = str(item["scope_key"])
        row.category = str(item["category"])
        row.root_cause = str(item["root_cause"])
        row.primary_evidence_metric = str(item["primary_evidence_metric"])
        row.problem = str(item["problem"])
        row.evidence = str(item["evidence"])
        row.impact = str(item["impact"])
        row.next_action = str(item["next_action"])
        row.confidence = str(item["confidence"])
        row.priority_score = float(item["priority_score"] or 0)
        row.status = "active"
        row.dismissed_at = None
        rows.append(row)
    return rows


def _select_dashboard_insights(
    candidates: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    seen_evidence: set[str] = set()
    for insight in dedupe_insights(candidates, limit=None):
        category = str(insight.get("category") or "")
        evidence_metric = str(insight.get("primary_evidence_metric") or "")
        if category in seen_categories or evidence_metric in seen_evidence:
            continue
        selected.append(insight)
        seen_categories.add(category)
        seen_evidence.add(evidence_metric)
        if len(selected) >= limit:
            break
    return selected


def _build_insight_candidates(db: Session, owner: User) -> list[dict[str, Any]]:
    rounds = _owned_rounds(db, owner)
    shot_values = db.scalars(select(ShotValue).where(ShotValue.user_id == owner.id)).all()
    candidates: list[dict[str, Any]] = []
    penalties = sum(hole.penalties for round_ in rounds for hole in round_.holes)
    putts = [hole.putts for round_ in rounds for hole in round_.holes if hole.putts is not None]
    three_putts = sum(1 for putt in putts if putt >= 3)
    avg_score = _kpis(rounds).get("average_score")

    if penalties:
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="penalty_impact",
                root_cause="penalty_strokes",
                primary_evidence_metric="penalty_strokes",
                problem="페널티가 스코어를 직접 밀어 올립니다.",
                evidence=f"저장된 라운드에서 페널티가 총 {penalties}타 기록됐습니다.",
                impact="페널티 1타는 회복 샷까지 이어져 실제 손실이 더 커질 수 있습니다.",
                next_action="위험 홀이 보이면 티샷 목표 폭과 세이프 클럽 기준을 먼저 정하세요.",
                confidence=_confidence(sum(1 for round_ in rounds for hole in round_.holes)),
                priority_score=float(penalties),
            )
        )
    if putts and three_putts:
        rate = three_putts / len(putts)
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="putting",
                root_cause="three_putt",
                primary_evidence_metric="three_putt_rate",
                problem="3퍼트가 반복될 여지가 있습니다.",
                evidence=f"퍼트 기록 {len(putts)}개 중 3퍼트 이상이 {three_putts}개입니다.",
                impact="3퍼트는 파 세이브 흐름을 끊고 보기 이상으로 이어지기 쉽습니다.",
                next_action="6-12m 래그 퍼트 거리감과 1-2m 마무리 퍼트를 묶어서 점검하세요.",
                confidence=_confidence(len(putts)),
                priority_score=rate * 4,
            )
        )
    category_losses = _category_losses(shot_values)
    for category, payload in category_losses[:3]:
        if payload["total"] >= 0:
            continue
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category=category,
                root_cause="shot_value_loss",
                primary_evidence_metric=f"{category}_shot_value",
                problem=f"{category} 손실이 우선 점검 대상입니다.",
                evidence=(
                    f"{payload['count']}샷에서 추정 shot value 합계가 "
                    f"{payload['total']:.2f}타입니다."
                ),
                impact="같은 유형의 손실이 반복되면 라운드 평균 스코어가 고정됩니다.",
                next_action=(
                    "다음 라운드에서 이 카테고리의 큰 미스와 페널티 여부를 먼저 기록하세요."
                ),
                confidence=_confidence(payload["count"]),
                priority_score=abs(payload["total"]),
            )
        )
    if avg_score is not None:
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="score",
                root_cause="baseline",
                primary_evidence_metric="average_score",
                problem="현재 스코어 기준선을 확인했습니다.",
                evidence=f"저장된 라운드 평균 스코어는 {avg_score}타입니다.",
                impact="MVP 분석은 이 기준선에서 카테고리별 손실을 좁히는 방식으로 확장됩니다.",
                next_action="라운드를 더 누적한 뒤 카테고리별 shot value 신뢰도를 올리세요.",
                confidence=_confidence(len(rounds)),
                priority_score=0.2,
            )
        )
    return candidates


def _replace_snapshot(db: Session, *, owner: User, insights: list[Insight]) -> AnalysisSnapshot:
    snapshot = AnalysisSnapshot(
        user_id=owner.id,
        scope_type="window",
        scope_key="all",
        payload={"insight_ids": [str(insight.id) for insight in insights]},
    )
    db.add(snapshot)
    return snapshot


def _active_insights(db: Session, owner: User) -> list[Insight]:
    return db.scalars(
        select(Insight)
        .where(Insight.user_id == owner.id, Insight.status == "active")
        .order_by(Insight.priority_score.desc(), Insight.created_at.desc())
        .limit(3)
    ).all()


def _insight_response(insight: Insight) -> dict[str, Any]:
    return {
        "id": insight.id,
        "round_id": insight.round_id,
        "scope_type": insight.scope_type,
        "scope_key": insight.scope_key,
        "category": insight.category,
        "root_cause": insight.root_cause,
        "primary_evidence_metric": insight.primary_evidence_metric,
        "dedupe_key": insight.dedupe_key,
        "problem": insight.problem,
        "evidence": insight.evidence,
        "impact": insight.impact,
        "next_action": insight.next_action,
        "confidence": insight.confidence,
        "priority_score": insight.priority_score,
        "status": insight.status,
    }


def _score_trend(rounds: list[Round]) -> list[dict[str, Any]]:
    return [
        {
            "round_id": str(round_.id),
            "play_date": round_.play_date.isoformat(),
            "course_name": round_.course_name,
            "total_score": round_.total_score,
            "score_to_par": round_.score_to_par,
        }
        for round_ in rounds
        if round_.total_score is not None
    ][-10:]


def _kpis(rounds: list[Round]) -> dict[str, Any]:
    completed = [round_ for round_ in rounds if round_.total_score is not None]
    scores = [round_.total_score for round_ in completed if round_.total_score is not None]
    putt_totals = [
        sum(hole.putts for hole in round_.holes if hole.putts is not None)
        for round_ in rounds
        if any(hole.putts is not None for hole in round_.holes)
    ]
    return {
        "round_count": len(rounds),
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "best_score": min(scores) if scores else None,
        "average_putts": round(sum(putt_totals) / len(putt_totals), 1) if putt_totals else None,
    }


def _category_losses(shot_values: list[ShotValue]) -> list[tuple[str, dict[str, Any]]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0.0})
    for value in shot_values:
        buckets[value.category]["count"] += 1
        buckets[value.category]["total"] += value.shot_value or 0
    return sorted(buckets.items(), key=lambda item: item[1]["total"])


def _shot_category(shot: Shot, hole: Hole) -> str:
    club = (shot.club_normalized or shot.club or "").upper()
    if shot.penalty_strokes:
        return "penalty_impact"
    if club in {"P", "PT"} or "PUTT" in club:
        return "putting"
    if shot.shot_number == 1 and hole.par in {4, 5}:
        return "off_the_tee"
    if shot.distance is not None and shot.distance <= 50:
        return "short_game"
    if shot.start_lie in {"R", "B", "H", "O"}:
        return "recovery"
    return "approach"


def _estimate_shot_value(shot: Shot, expected_before: float | None, shot_cost: int) -> float:
    penalty_loss = float(shot.penalty_strokes or 0) * -1.0
    result_loss = -0.35 if shot.result_grade == "C" else 0.15 if shot.result_grade == "A" else 0.0
    baseline = (
        0.0
        if expected_before is None
        else min(max((expected_before - shot_cost) * 0.05, -0.3), 0.3)
    )
    return round(baseline + result_loss + penalty_loss, 3)


def _confidence(sample_count: int) -> str:
    if sample_count >= 20:
        return "high"
    if sample_count >= 10:
        return "medium"
    return "low"
