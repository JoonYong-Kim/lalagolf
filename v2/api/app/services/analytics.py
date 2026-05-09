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
from app.services.insight_i18n import render_insight_payload


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


def get_trends(db: Session, *, owner: User, locale: str | None = None) -> dict[str, Any]:
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
        "item_summary": _analysis_item_summary(rounds, shot_values),
        "shot_quality_summary": _shot_quality_summary_for_rounds(rounds),
        "insights": [_insight_response(insight, locale=locale) for insight in insights],
    }


def get_round_analytics(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    locale: str | None = None,
) -> dict[str, Any]:
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
        "shot_quality_summary": _shot_quality_summary_for_rounds([round_]),
        "shot_values": [
            {
                "shot_id": str(row.shot_id),
                "category": row.category,
                "shot_value": row.shot_value,
                "expected_before": row.expected_before,
                "expected_after": row.expected_after,
                "shot_cost": row.shot_cost,
                "expected_confidence": row.expected_confidence,
            }
            for row in shot_values
        ],
        "insights": [_insight_response(insight, locale=locale) for insight in insights],
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


def list_insights(
    db: Session,
    *,
    owner: User,
    status: str = "active",
    locale: str | None = None,
) -> list[dict[str, Any]]:
    insights = db.scalars(
        select(Insight)
        .where(Insight.user_id == owner.id, Insight.status == status)
        .order_by(Insight.priority_score.desc(), Insight.created_at.desc())
    ).all()
    return [_insight_response(insight, locale=locale) for insight in insights]


def update_insight_status(
    db: Session,
    *,
    owner: User,
    insight_id: uuid.UUID,
    status: str,
    locale: str | None = None,
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
    return _insight_response(insight, locale=locale)


def active_priority_insights(
    db: Session,
    *,
    owner: User,
    limit: int = 3,
    locale: str | None = None,
) -> list[dict[str, Any]]:
    return [
        _insight_response(insight, locale=locale)
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
            expected_after = (
                round(expected_before - shot_cost - shot_value, 3)
                if expected_before is not None and shot_value is not None
                else None
            )
            rows.append(
                ShotValue(
                    user_id=owner.id,
                    round_id=round_.id,
                    hole_id=hole.id,
                    shot_id=shot.id,
                    category=category,
                    expected_before=expected_before,
                    expected_after=expected_after,
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
                        "expected_before": expected_before,
                        "expected_after": expected_after,
                        "shot_cost": shot_cost,
                        "shot_value": shot_value,
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
    quality = _shot_quality_summary_for_rounds(rounds)
    risk = quality.get("risk") or {}

    if penalties:
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="penalty_impact",
                root_cause="penalty_strokes",
                primary_evidence_metric="penalty_strokes",
                problem="페널티 손실",
                evidence=f"총 {penalties}타 페널티가 기록됐습니다.",
                impact="페널티는 회복 샷까지 비용을 키웁니다.",
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
                problem="3퍼트 위험",
                evidence=f"{len(putts)}개 퍼트 기록 중 3퍼트 이상 {three_putts}개.",
                impact="3퍼트는 파 세이브 흐름을 끊습니다.",
                next_action="6-12m 래그 퍼트 거리감과 1-2m 마무리 퍼트를 묶어서 점검하세요.",
                confidence=_confidence(len(putts)),
                priority_score=rate * 4,
            )
        )
    driver_result_c_rate = _number_or_none(risk.get("driver_result_c_rate"))
    if driver_result_c_rate is not None and driver_result_c_rate >= 0.3:
        driver_result_c_count = int(risk.get("driver_result_c_count") or 0)
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="off_the_tee",
                root_cause="driver_result_c",
                primary_evidence_metric="driver_result_c_rate",
                problem="드라이버 큰 미스",
                evidence=(
                    f"드라이버 티샷 Result C가 {driver_result_c_count}개, "
                    f"비율 {driver_result_c_rate * 100:.1f}%입니다."
                ),
                impact="큰 미스 비율이 높으면 페널티가 없어도 다음 샷 난도가 올라갑니다.",
                next_action=(
                    "비거리보다 넓은 랜딩 구역과 허용 미스 방향을 먼저 정하고 "
                    "출발선 루틴을 반복하세요."
                ),
                confidence=_confidence(int(risk.get("driver_tee_shot_count") or 0)),
                priority_score=driver_result_c_rate * 3,
            )
        )
    strategy_issue_count = int(risk.get("strategy_issue_count") or 0)
    if strategy_issue_count:
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category="score",
                root_cause="feel_result_mismatch",
                primary_evidence_metric="strategy_issue_count",
                problem="전략/판단 미스",
                evidence=f"Feel A/B였지만 Result C인 샷이 {strategy_issue_count}개입니다.",
                impact=(
                    "컨택 감각이 나쁘지 않은데 결과가 나쁘면 타깃, 클럽 선택, "
                    "리스크 판단 문제가 섞였을 가능성이 큽니다."
                ),
                next_action=(
                    "다음 라운드에서 공격 핀과 보수 목표를 구분하고, "
                    "각 샷의 허용 미스 방향을 먼저 적으세요."
                ),
                confidence=_confidence(int(quality.get("sample_count") or 0)),
                priority_score=min(strategy_issue_count, 10) / 3,
            )
        )
    category_losses = _category_losses(shot_values)
    for category, payload in category_losses[:3]:
        if payload["total"] >= 0:
            continue
        label = _category_label_ko(category)
        candidates.append(
            build_insight_unit(
                scope_type="window",
                scope_key="all",
                category=category,
                root_cause="shot_value_loss",
                primary_evidence_metric=f"{category}_shot_value",
                problem=f"{label} 손실",
                evidence=f"{payload['count']}샷 합계 {payload['total']:.2f}타.",
                impact="반복 손실은 평균 스코어를 고정합니다.",
                next_action=f"다음 라운드에서 {label}의 큰 미스와 페널티를 먼저 기록하세요.",
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
                problem="스코어 기준선",
                evidence=f"평균 스코어 {avg_score}타.",
                impact="이 기준선에서 손실 카테고리를 좁힙니다.",
                next_action="라운드를 더 누적한 뒤 카테고리별 shot value 신뢰도를 올리세요.",
                confidence=_confidence(len(rounds)),
                priority_score=0.2,
            )
        )
    return candidates


def _category_label_ko(category: str) -> str:
    return {
        "off_the_tee": "티샷",
        "short_game": "쇼트게임",
        "control_shot": "컨트롤샷",
        "iron_shot": "아이언샷",
        "putting": "퍼팅",
        "recovery": "리커버리",
        "penalty_impact": "페널티",
        "score": "스코어",
    }.get(category, category)


def _analysis_item_summary(
    rounds: list[Round],
    shot_values: list[ShotValue],
) -> list[dict[str, Any]]:
    shot_value_by_id = {value.shot_id: value for value in shot_values}
    buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "group": "",
            "item": "",
            "count": 0,
            "total_shot_value": 0.0,
            "result_c_count": 0,
            "feel_c_count": 0,
            "penalty_count": 0,
            "made_count": 0,
            "ok_count": 0,
            "recovered_count": 0,
            "failed_recovery_count": 0,
            "ob_count": 0,
            "hazard_count": 0,
            "good_feel_penalty_count": 0,
            "primary_clubs": defaultdict(int),
            "up_and_down_chance_count": 0,
            "up_and_down_success_count": 0,
        }
    )
    for round_ in rounds:
        for hole in round_.holes:
            for shot in hole.shots:
                for group, item in _analysis_items_for_shot(shot, hole):
                    bucket = buckets[(group, item)]
                    bucket["group"] = group
                    bucket["item"] = item
                    bucket["count"] += 1
                    shot_value = shot_value_by_id.get(shot.id)
                    bucket["total_shot_value"] += shot_value.shot_value if shot_value else 0
                    if (shot.result_grade or "").upper() == "C":
                        bucket["result_c_count"] += 1
                    if (shot.feel_grade or "").upper() == "C":
                        bucket["feel_c_count"] += 1
                    if shot.penalty_strokes:
                        bucket["penalty_count"] += 1
                    if group == "putting":
                        if _putt_ok(shot):
                            bucket["ok_count"] += 1
                        elif _putt_made(shot, hole):
                            bucket["made_count"] += 1
                    if group == "recovery":
                        if _recovery_success(shot):
                            bucket["recovered_count"] += 1
                        else:
                            bucket["failed_recovery_count"] += 1
                    if group == "penalty_impact":
                        penalty_type = (shot.penalty_type or "").upper()
                        if penalty_type == "OB":
                            bucket["ob_count"] += 1
                        if penalty_type == "H":
                            bucket["hazard_count"] += 1
                        if (shot.feel_grade or "").upper() in {"A", "B"}:
                            bucket["good_feel_penalty_count"] += 1
                    if group == "shot_quality":
                        bucket["primary_clubs"][_club_group(shot.club_normalized or shot.club)] += 1
                    if group == "short_game":
                        bucket["up_and_down_chance_count"] += 1
                        if _up_and_down_success(hole):
                            bucket["up_and_down_success_count"] += 1
    rows = []
    for bucket in buckets.values():
        count = bucket["count"]
        rows.append(
            {
                **bucket,
                "total_shot_value": round(bucket["total_shot_value"], 3),
                "avg_shot_value": round(bucket["total_shot_value"] / count, 3)
                if count
                else 0,
                "result_c_rate": _safe_rate(bucket["result_c_count"], count),
                "feel_c_rate": _safe_rate(bucket["feel_c_count"], count),
                "penalty_rate": _safe_rate(bucket["penalty_count"], count),
                "made_rate": _safe_rate(bucket["made_count"], count),
                "ok_rate": _safe_rate(bucket["ok_count"], count),
                "recovered_rate": _safe_rate(bucket["recovered_count"], count),
                "failed_recovery_rate": _safe_rate(bucket["failed_recovery_count"], count),
                "ob_rate": _safe_rate(bucket["ob_count"], count),
                "hazard_rate": _safe_rate(bucket["hazard_count"], count),
                "good_feel_penalty_rate": _safe_rate(bucket["good_feel_penalty_count"], count),
                "item_rate": _safe_rate(count, _quality_denominator(rounds))
                if bucket["group"] == "shot_quality"
                else None,
                "primary_club_group": _top_bucket(bucket["primary_clubs"]),
                "up_and_down_success_rate": _safe_rate(
                    bucket["up_and_down_success_count"],
                    bucket["up_and_down_chance_count"],
                ),
            }
        )
    rows.sort(key=lambda item: (item["group"], item["total_shot_value"]))
    return rows


def _analysis_items_for_shot(shot: Shot, hole: Hole) -> list[tuple[str, str]]:
    club = (shot.club_normalized or shot.club or "").upper()
    items: list[tuple[str, str]] = []
    if club in {"P", "PT"} or "PUTT" in club:
        items.append(("putting", _putting_item(shot.distance)))
    elif shot.shot_number == 1 and hole.par in {4, 5}:
        items.append(("off_the_tee", _tee_item(club)))
        if shot.penalty_strokes:
            items.append(("penalty_impact", _penalty_item(shot, is_tee=True)))
    elif shot.penalty_strokes:
        items.append(("penalty_impact", _penalty_item(shot, is_tee=False)))
    elif shot.distance is not None and shot.distance < 40:
        items.append(("short_game", _short_game_item(shot)))
    elif shot.start_lie in {"R", "B", "H", "O"}:
        items.append(("recovery", _recovery_item(shot)))
    elif shot.distance is not None and shot.distance < 90:
        items.append(("control_shot", _control_shot_item(shot.distance)))
    elif shot.distance is not None and shot.distance >= 90:
        items.append(("iron_shot", _iron_item(club)))
    else:
        items.append(("control_shot", "unknown_distance"))

    quality_item = _quality_item(shot)
    if quality_item:
        items.append(("shot_quality", quality_item))
    return items


def _putting_item(distance: int | None) -> str:
    if distance is None:
        return "putt_unknown"
    if distance <= 2:
        return "putt_0_2"
    if distance <= 7:
        return "putt_2_7"
    if distance <= 10:
        return "putt_7_10"
    if distance <= 20:
        return "putt_10_20"
    return "putt_20_plus"


def _putt_ok(shot: Shot) -> bool:
    raw_text = (shot.raw_text or "").upper()
    return "OK" in raw_text.split() or shot.score_cost > 1


def _putt_made(shot: Shot, hole: Hole) -> bool:
    putts = [
        item
        for item in hole.shots
        if (item.club_normalized or item.club or "").upper() in {"P", "PT"}
    ]
    if not putts:
        return False
    return shot.id == max(putts, key=lambda item: item.shot_number).id and not _putt_ok(shot)


def _short_game_item(shot: Shot) -> str:
    if (shot.start_lie or "").upper() == "B":
        return "greenside_bunker"
    distance = shot.distance
    if distance is None:
        return "short_unknown"
    if distance < 10:
        return "short_chip"
    if distance < 25:
        return "mid_approach"
    return "long_approach"


def _up_and_down_success(hole: Hole) -> bool:
    return hole.score is not None and hole.score <= hole.par


def _control_shot_item(distance: int | None) -> str:
    if distance is None:
        return "control_unknown"
    if distance < 60:
        return "control_40_60"
    if distance < 75:
        return "control_60_75"
    return "control_75_90"


def _iron_item(club: str) -> str:
    if club in {"I3", "I4"}:
        return "long_iron"
    if club in {"I5", "I6", "I7"}:
        return club
    if club in {"I8", "I9"}:
        return club
    if club in {"IP", "IW", "IA", "PW"}:
        return "pitching_wedge"
    return "other_iron"


def _tee_item(club: str) -> str:
    if club == "D":
        return "driver"
    if club.startswith("W") or club.startswith("U"):
        return "wood_utility"
    if club.startswith("I"):
        return "iron_tee"
    return "other_tee"


def _recovery_item(shot: Shot) -> str:
    start_lie = (shot.start_lie or "").upper()
    if start_lie == "B":
        if shot.distance is not None and shot.distance < 40:
            return "greenside_bunker"
        return "fairway_bunker"
    if start_lie == "R":
        return "rough"
    return "other_recovery"


def _recovery_success(shot: Shot) -> bool:
    return (shot.end_lie or "").upper() not in {"R", "B", "H", "O"}


def _penalty_item(shot: Shot, *, is_tee: bool) -> str:
    penalty_type = (shot.penalty_type or "").upper()
    prefix = "tee" if is_tee else "non_tee"
    if penalty_type == "OB":
        return f"{prefix}_ob"
    if penalty_type == "H":
        return f"{prefix}_hazard"
    return f"{prefix}_other_penalty"


def _quality_item(shot: Shot) -> str | None:
    feel = (shot.feel_grade or "").upper()
    result = (shot.result_grade or "").upper()
    if result == "C" or shot.penalty_strokes:
        if feel in {"A", "B"} and result == "C":
            return "strategy_issue"
        if feel == "C" and result == "C":
            return "technical_miss"
        return "high_risk_shot"
    if feel == "C" and result in {"A", "B"}:
        return "lucky_result"
    if feel in {"A", "B"} and result in {"A", "B"}:
        return "reproducible_shot"
    return None


def _quality_denominator(rounds: list[Round]) -> int:
    return sum(
        1
        for round_ in rounds
        for hole in round_.holes
        for shot in hole.shots
        if (shot.club_normalized or shot.club or "").upper() not in {"P", "PT"}
    )


def _top_bucket(values: dict[str, int]) -> str | None:
    if not values:
        return None
    return max(values.items(), key=lambda item: item[1])[0]


def _shot_quality_summary_for_rounds(rounds: list[Round]) -> dict[str, Any]:
    shots = [
        shot
        for round_ in rounds
        for hole in round_.holes
        for shot in hole.shots
        if shot.club_normalized != "P" and shot.club != "P"
    ]
    feel_counts = _grade_counts(shot.feel_grade for shot in shots)
    result_counts = _grade_counts(shot.result_grade for shot in shots)
    matrix = {feel: {result: 0 for result in ("A", "B", "C")} for feel in ("A", "B", "C")}
    club_groups: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "club_group": "",
            "count": 0,
            "feel": {"A": 0, "B": 0, "C": 0},
            "result": {"A": 0, "B": 0, "C": 0},
            "penalty_count": 0,
        }
    )
    risk = {
        "reproducible_count": 0,
        "technical_miss_count": 0,
        "lucky_result_count": 0,
        "strategy_issue_count": 0,
        "high_risk_count": 0,
        "driver_tee_shot_count": 0,
        "driver_result_c_count": 0,
    }
    tee_result_counts = {"A": 0, "B": 0, "C": 0}
    under_90_result_counts = {"A": 0, "B": 0, "C": 0}
    over_90_result_counts = {"A": 0, "B": 0, "C": 0}

    for round_ in rounds:
        for hole in round_.holes:
            for shot in hole.shots:
                if shot.club_normalized == "P" or shot.club == "P":
                    continue
                feel = _grade(shot.feel_grade)
                result = _grade(shot.result_grade)
                if feel and result:
                    matrix[feel][result] += 1
                    if feel in {"A", "B"} and result in {"A", "B"}:
                        risk["reproducible_count"] += 1
                    if feel == "C" and result == "C":
                        risk["technical_miss_count"] += 1
                    if feel == "C" and result in {"A", "B"}:
                        risk["lucky_result_count"] += 1
                    if feel in {"A", "B"} and result == "C":
                        risk["strategy_issue_count"] += 1
                if result == "C" or shot.penalty_strokes:
                    risk["high_risk_count"] += 1
                if shot.shot_number == 1 and hole.par in {4, 5}:
                    if result:
                        tee_result_counts[result] += 1
                    if (shot.club_normalized or shot.club or "").upper() == "D":
                        risk["driver_tee_shot_count"] += 1
                        if result == "C":
                            risk["driver_result_c_count"] += 1
                if shot.distance is not None and result:
                    if shot.distance < 90:
                        under_90_result_counts[result] += 1
                    else:
                        over_90_result_counts[result] += 1
                group = _club_group(shot.club_normalized or shot.club)
                bucket = club_groups[group]
                bucket["club_group"] = group
                bucket["count"] += 1
                if feel:
                    bucket["feel"][feel] += 1
                if result:
                    bucket["result"][result] += 1
                if shot.penalty_strokes:
                    bucket["penalty_count"] += 1

    total = len(shots)
    risk["driver_result_c_rate"] = _safe_rate(
        risk["driver_result_c_count"],
        risk["driver_tee_shot_count"],
    )
    risk["strategy_issue_rate"] = _safe_rate(risk["strategy_issue_count"], total)
    risk["technical_miss_rate"] = _safe_rate(risk["technical_miss_count"], total)
    risk["lucky_result_rate"] = _safe_rate(risk["lucky_result_count"], total)
    risk["high_risk_rate"] = _safe_rate(risk["high_risk_count"], total)

    return {
        "sample_count": total,
        "feel_distribution": _distribution(feel_counts),
        "result_distribution": _distribution(result_counts),
        "feel_result_matrix": matrix,
        "risk": risk,
        "tee_result_distribution": _distribution(tee_result_counts),
        "under_90_result_distribution": _distribution(under_90_result_counts),
        "over_90_result_distribution": _distribution(over_90_result_counts),
        "club_groups": [
            _club_group_summary(bucket)
            for bucket in sorted(club_groups.values(), key=lambda item: item["club_group"])
        ],
    }


def _club_group_summary(bucket: dict[str, Any]) -> dict[str, Any]:
    count = bucket["count"]
    return {
        **bucket,
        "feel_c_rate": _safe_rate(bucket["feel"]["C"], count),
        "result_c_rate": _safe_rate(bucket["result"]["C"], count),
        "penalty_rate": _safe_rate(bucket["penalty_count"], count),
    }


def _grade_counts(values: Any) -> dict[str, int]:
    counts = {"A": 0, "B": 0, "C": 0}
    for value in values:
        grade = _grade(value)
        if grade:
            counts[grade] += 1
    return counts


def _distribution(counts: dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    return {
        "counts": counts,
        "rates": {grade: _safe_rate(count, total) for grade, count in counts.items()},
        "total": total,
    }


def _grade(value: str | None) -> str | None:
    normalized = (value or "").upper()
    return normalized if normalized in {"A", "B", "C"} else None


def _club_group(club: str | None) -> str:
    normalized = (club or "").upper()
    if normalized == "D":
        return "D"
    if normalized in {"W3", "W5", "UW"}:
        return "W"
    if normalized in {"U3", "U4", "U5"}:
        return "U"
    if normalized in {"I3", "I4"}:
        return "LI"
    if normalized in {"I5", "I6", "I7"}:
        return "MI"
    if normalized in {"I8", "I9", "IP", "IW", "IA", "48", "50", "52", "56", "58", "60"}:
        return "SI"
    if normalized in {"P", "PT"}:
        return "P"
    return "OTHER"


def _safe_rate(numerator: int | float, denominator: int | float) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def _number_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


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


def _insight_response(insight: Insight, *, locale: str | None = None) -> dict[str, Any]:
    payload = {
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
    return render_insight_payload(payload, locale=locale)


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
    if shot.start_lie in {"R", "B", "H", "O"}:
        return "recovery"
    if shot.distance is not None and shot.distance < 40:
        return "short_game"
    if shot.distance is not None and shot.distance < 90:
        return "control_shot"
    if shot.distance is not None and shot.distance >= 90:
        return "iron_shot"
    return "control_shot"


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
