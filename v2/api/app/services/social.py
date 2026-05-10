from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Follow, Hole, Round, RoundComment, RoundCompanion, RoundLike, User
from app.models.constants import VISIBILITY_FOLLOWERS, VISIBILITY_LINK_ONLY, VISIBILITY_PUBLIC
from app.services.insight_i18n import render_insight_payload


class SocialAccessError(Exception):
    pass


class SocialNotFoundError(Exception):
    pass


def load_viewable_round(
    db: Session,
    *,
    viewer: User | None,
    round_id: uuid.UUID,
    public_only: bool = False,
) -> Round:
    query = select(Round).options(
        selectinload(Round.companions),
        selectinload(Round.holes).selectinload(Hole.shots),
        selectinload(Round.shared_insights),
    )
    if viewer is not None:
        query = query.where(Round.deleted_at.is_(None), Round.id == round_id)
    else:
        query = query.where(Round.deleted_at.is_(None), Round.id == round_id)

    round_ = db.scalars(query).first()
    if round_ is None:
        raise SocialNotFoundError

    if public_only:
        if round_.visibility != VISIBILITY_PUBLIC:
            raise SocialNotFoundError
        return round_

    if viewer is not None and round_.user_id == viewer.id:
        return round_

    if round_.visibility == VISIBILITY_PUBLIC:
        return round_

    if viewer is not None and round_.visibility == VISIBILITY_FOLLOWERS and _has_accepted_follow(
        db,
        follower_id=viewer.id,
        following_id=round_.user_id,
    ):
        return round_

    if round_.visibility == VISIBILITY_LINK_ONLY:
        raise SocialNotFoundError

    raise SocialNotFoundError


def can_react_to_round(db: Session, *, viewer: User, round_: Round) -> bool:
    if round_.user_id == viewer.id:
        return True
    if round_.visibility not in {VISIBILITY_PUBLIC, VISIBILITY_FOLLOWERS}:
        return False
    return _has_accepted_follow(db, follower_id=viewer.id, following_id=round_.user_id)


def list_public_rounds(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    course: str | None = None,
    handle: str | None = None,
    keyword: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    base = (
        select(Round, User.display_name, User.handle)
        .join(User, User.id == Round.user_id)
        .where(Round.deleted_at.is_(None), Round.visibility == VISIBILITY_PUBLIC)
    )
    base = _apply_public_filters(base, course=course, handle=handle, keyword=keyword, year=year)
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0

    rows = db.execute(
        base.order_by(Round.play_date.desc(), Round.created_at.desc()).limit(limit).offset(offset)
    ).all()
    items = [
        _public_round_card(
            round_,
            owner_id=round_.user_id,
            owner_display_name=display_name,
            owner_handle=user_handle,
        )
        for round_, display_name, user_handle in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_public_round_detail(
    db: Session,
    *,
    round_id: uuid.UUID,
    locale: str | None = None,
) -> dict[str, Any]:
    round_ = load_viewable_round(db, viewer=None, round_id=round_id, public_only=True)
    owner = db.get(User, round_.user_id)
    if owner is None:
        raise SocialNotFoundError

    comments = list_round_comments(db, viewer=None, round_=round_)
    like_count = _like_count(db, round_.id)
    comment_count = len(comments)
    return _public_round_detail(
        round_,
        owner_display_name=owner.display_name,
        owner_handle=owner.handle,
        locale=locale,
        like_count=like_count,
        comment_count=comment_count,
    )


def create_follow(db: Session, *, viewer: User, following_id: uuid.UUID) -> Follow:
    if following_id == viewer.id:
        raise SocialAccessError("Cannot follow yourself")
    target = db.get(User, following_id)
    if target is None or target.status != "active":
        raise SocialNotFoundError

    existing = db.get(Follow, (viewer.id, following_id))
    now = datetime.now(UTC)
    if existing is not None:
        if existing.status == "blocked":
            existing.requested_at = now
            existing.blocked_at = None
        elif existing.status == "accepted":
            return existing
        existing.status = "pending"
        existing.accepted_at = None
        existing.blocked_at = None
    else:
        existing = Follow(
            follower_id=viewer.id,
            following_id=following_id,
            status="pending",
            requested_at=now,
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def list_follows(
    db: Session,
    *,
    viewer: User,
    scope: str = "all",
) -> list[dict[str, Any]]:
    query = select(Follow, User,).join(User, User.id == Follow.following_id)
    if scope == "incoming":
        query = query.where(Follow.following_id == viewer.id)
    elif scope == "outgoing":
        query = query.where(Follow.follower_id == viewer.id)
    else:
        query = query.where(or_(Follow.follower_id == viewer.id, Follow.following_id == viewer.id))
    rows = db.execute(query.order_by(Follow.updated_at.desc())).all()

    results = []
    for follow, _other_user in rows:
        results.append(
            {
                "follower_id": follow.follower_id,
                "following_id": follow.following_id,
                "status": follow.status,
                "requested_at": follow.requested_at,
                "accepted_at": follow.accepted_at,
                "blocked_at": follow.blocked_at,
                "follower_display_name": _user_display_name(db, follow.follower_id),
                "follower_handle": _user_handle(db, follow.follower_id),
                "following_display_name": _user_display_name(db, follow.following_id),
                "following_handle": _user_handle(db, follow.following_id),
            }
        )
    return results


def update_follow(
    db: Session,
    *,
    viewer: User,
    follower_id: uuid.UUID,
    following_id: uuid.UUID,
    status: str,
) -> Follow:
    follow = db.get(Follow, (follower_id, following_id))
    if follow is None:
        raise SocialNotFoundError

    if viewer.id not in {follower_id, following_id}:
        raise SocialAccessError("Cannot update this follow relationship")

    if status not in {"pending", "accepted", "blocked"}:
        raise SocialAccessError("Invalid follow status")

    now = datetime.now(UTC)
    follow.status = status
    if status == "accepted":
        follow.accepted_at = now
        follow.blocked_at = None
    elif status == "blocked":
        follow.blocked_at = now
        follow.accepted_at = None
    else:
        follow.accepted_at = None
        follow.blocked_at = None
    db.commit()
    db.refresh(follow)
    return follow


def follow_payload(db: Session, follow: Follow) -> dict[str, Any]:
    return {
        "follower_id": follow.follower_id,
        "following_id": follow.following_id,
        "status": follow.status,
        "requested_at": follow.requested_at,
        "accepted_at": follow.accepted_at,
        "blocked_at": follow.blocked_at,
        "follower_display_name": _user_display_name(db, follow.follower_id),
        "follower_handle": _user_handle(db, follow.follower_id),
        "following_display_name": _user_display_name(db, follow.following_id),
        "following_handle": _user_handle(db, follow.following_id),
    }


def delete_follow(
    db: Session,
    *,
    viewer: User,
    follower_id: uuid.UUID,
    following_id: uuid.UUID,
) -> None:
    follow = db.get(Follow, (follower_id, following_id))
    if follow is None:
        raise SocialNotFoundError
    if viewer.id not in {follower_id, following_id}:
        raise SocialAccessError("Cannot delete this follow relationship")
    db.delete(follow)
    db.commit()


def add_like(db: Session, *, viewer: User, round_id: uuid.UUID) -> dict[str, Any]:
    round_ = load_viewable_round(db, viewer=viewer, round_id=round_id)
    if not can_react_to_round(db, viewer=viewer, round_=round_):
        raise SocialAccessError("Like is allowed only for accepted follow relationships")

    like = db.get(RoundLike, (round_.id, viewer.id))
    if like is None:
        like = RoundLike(round_id=round_.id, user_id=viewer.id)
        db.add(like)
        db.commit()

    return {"round_id": round_.id, "like_count": _like_count(db, round_.id), "liked": True}


def remove_like(db: Session, *, viewer: User, round_id: uuid.UUID) -> dict[str, Any]:
    round_ = load_viewable_round(db, viewer=viewer, round_id=round_id)
    like = db.get(RoundLike, (round_.id, viewer.id))
    if like is not None:
        db.delete(like)
        db.commit()
    return {"round_id": round_.id, "like_count": _like_count(db, round_.id), "liked": False}


def list_round_comments(
    db: Session,
    *,
    viewer: User | None,
    round_: Round,
) -> list[dict[str, Any]]:
    if viewer is not None and not _can_view_for_comments(db, viewer=viewer, round_=round_):
        raise SocialAccessError("Round is not visible")

    comments = db.scalars(
        select(RoundComment)
        .where(RoundComment.round_id == round_.id, RoundComment.status == "active")
        .order_by(RoundComment.created_at.asc())
    ).all()
    return [_comment_payload(db, comment) for comment in comments]


def add_comment(
    db: Session,
    *,
    viewer: User,
    round_id: uuid.UUID,
    body: str,
    parent_comment_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    round_ = load_viewable_round(db, viewer=viewer, round_id=round_id)
    if not can_react_to_round(db, viewer=viewer, round_=round_):
        raise SocialAccessError("Comment is allowed only for accepted follow relationships")

    if parent_comment_id is not None:
        parent = db.get(RoundComment, parent_comment_id)
        if parent is None or parent.round_id != round_.id:
            raise SocialNotFoundError

    comment = RoundComment(
        round_id=round_.id,
        user_id=viewer.id,
        parent_comment_id=parent_comment_id,
        body=body.strip(),
        status="active",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_payload(db, comment)


def delete_comment(
    db: Session,
    *,
    viewer: User,
    comment_id: uuid.UUID,
) -> dict[str, Any]:
    comment = db.get(RoundComment, comment_id)
    if comment is None:
        raise SocialNotFoundError
    if comment.user_id != viewer.id:
        round_ = db.get(Round, comment.round_id)
        if round_ is None or round_.user_id != viewer.id:
            raise SocialAccessError("Cannot delete this comment")
    comment.status = "deleted"
    comment.deleted_at = datetime.now(UTC)
    db.commit()
    db.refresh(comment)
    return _comment_payload(db, comment)


def list_comparison_candidates(
    db: Session,
    *,
    viewer: User,
    round_id: uuid.UUID,
) -> list[dict[str, Any]]:
    base_round = load_viewable_round(db, viewer=viewer, round_id=round_id)
    companion_names = [
        companion.name.strip()
        for companion in base_round.companions
        if companion.name.strip()
    ]
    if not companion_names:
        return []

    candidates: dict[uuid.UUID, dict[str, Any]] = {}
    for companion_name in companion_names:
        query = (
            select(Round, User.display_name, User.handle)
            .join(User, User.id == Round.user_id)
            .join(RoundCompanion, RoundCompanion.round_id == Round.id)
            .where(
                Round.deleted_at.is_(None),
                Round.id != base_round.id,
                RoundCompanion.name.ilike(companion_name),
                Round.course_name == base_round.course_name,
                Round.play_date == base_round.play_date,
            )
        )
        if base_round.tee_off_time:
            query = query.where(Round.tee_off_time == base_round.tee_off_time)
        rows = db.execute(query.order_by(Round.play_date.desc(), Round.created_at.desc())).all()
        for round_, display_name, handle in rows:
            if not _can_view_round_for_viewer(db, viewer=viewer, round_=round_):
                continue
            candidates[round_.id] = {
                "round_id": round_.id,
                "course_name": round_.course_name,
                "play_date": round_.play_date.isoformat(),
                "tee_off_time": round_.tee_off_time,
                "companion_name": companion_name,
                "visibility": round_.visibility,
                "owner_display_name": display_name,
                "owner_handle": handle,
            }
    return list(candidates.values())


def _apply_public_filters(
    query: Select[tuple[Round, str, str | None]],
    *,
    course: str | None,
    handle: str | None,
    keyword: str | None,
    year: int | None,
) -> Select[tuple[Round, str, str | None]]:
    if year is not None:
        query = query.where(func.extract("year", Round.play_date) == year)
    if course:
        query = query.where(Round.course_name.ilike(f"%{course}%"))
    if handle:
        query = query.where(User.handle == handle)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                Round.course_name.ilike(pattern),
                func.coalesce(Round.notes_public, "").ilike(pattern),
                User.display_name.ilike(pattern),
                User.handle.ilike(pattern),
            )
        )
    return query


def _public_round_card(
    round_: Round,
    *,
    owner_id: uuid.UUID,
    owner_display_name: str,
    owner_handle: str | None,
) -> dict[str, Any]:
    return {
        "id": round_.id,
        "owner_id": owner_id,
        "owner_display_name": owner_display_name,
        "owner_handle": owner_handle,
        "course_name": round_.course_name,
        "play_date": round_.play_date,
        "total_score": round_.total_score,
        "total_par": round_.total_par,
        "score_to_par": round_.score_to_par,
        "hole_count": round_.hole_count,
        "visibility": round_.visibility,
        "notes_public": round_.notes_public,
    }


def _public_round_detail(
    round_: Round,
    *,
    owner_display_name: str,
    owner_handle: str | None,
    locale: str | None,
    like_count: int,
    comment_count: int,
) -> dict[str, Any]:
    holes = sorted(round_.holes, key=lambda item: item.hole_number)
    return {
        **_public_round_card(
            round_,
            owner_id=round_.user_id,
            owner_display_name=owner_display_name,
            owner_handle=owner_handle,
        ),
        "tee_off_time": round_.tee_off_time,
        "tee": round_.tee,
        "weather": round_.weather,
        "target_score": round_.target_score,
        "metrics": _round_metrics(round_),
        "holes": [
            {
                "id": hole.id,
                "round_id": hole.round_id,
                "hole_number": hole.hole_number,
                "par": hole.par,
                "score": hole.score,
                "putts": hole.putts,
                "fairway_hit": hole.fairway_hit,
                "gir": hole.gir,
                "up_and_down": hole.up_and_down,
                "sand_save": hole.sand_save,
                "penalties": hole.penalties,
                "shots": [
                    {
                        "id": shot.id,
                        "round_id": shot.round_id,
                        "hole_id": shot.hole_id,
                        "shot_number": shot.shot_number,
                        "club": shot.club,
                        "club_normalized": shot.club_normalized,
                        "distance": shot.distance,
                        "start_lie": shot.start_lie,
                        "end_lie": shot.end_lie,
                        "result_grade": shot.result_grade,
                        "feel_grade": shot.feel_grade,
                        "penalty_type": shot.penalty_type,
                        "penalty_strokes": shot.penalty_strokes,
                        "score_cost": shot.score_cost,
                    }
                    for shot in sorted(hole.shots, key=lambda item: item.shot_number)
                ],
            }
            for hole in holes
        ],
        "insights": _public_insights(round_, locale=locale),
        "like_count": like_count,
        "comment_count": comment_count,
    }


def _public_insights(round_: Round, *, locale: str | None = None) -> list[dict[str, Any]]:
    active_insights = [
        insight
        for insight in getattr(round_, "shared_insights", [])
        if insight.status == "active"
    ]
    if not active_insights:
        fallback = _public_scorecard_issue(round_, locale=locale)
        return [fallback] if fallback else []

    top_issue = sorted(
        active_insights,
        key=lambda insight: (insight.priority_score, insight.created_at),
        reverse=True,
    )[0]
    rendered = render_insight_payload(
        {
            "category": top_issue.category,
            "root_cause": top_issue.root_cause,
            "primary_evidence_metric": top_issue.primary_evidence_metric,
            "problem": top_issue.problem,
            "evidence": top_issue.evidence,
            "impact": top_issue.impact,
            "next_action": top_issue.next_action,
            "confidence": top_issue.confidence,
            "priority_score": top_issue.priority_score,
        },
        locale=locale,
    )
    return [
        {
            "category": rendered["category"],
            "problem": rendered["problem"],
            "evidence": rendered["evidence"],
            "impact": rendered["impact"],
            "next_action": rendered["next_action"],
            "confidence": rendered["confidence"],
            "priority_score": rendered["priority_score"],
        }
    ]


def _public_scorecard_issue(round_: Round, *, locale: str | None = None) -> dict[str, Any] | None:
    holes = list(round_.holes)
    penalties = sum(hole.penalties for hole in holes)
    three_putts = sum(1 for hole in holes if (hole.putts or 0) >= 3)
    played_holes = len(holes)

    if penalties > 0:
        if locale == "en":
            return {
                "category": "penalty_impact",
                "problem": "Penalties are the top issue in this round.",
                "evidence": f"The scorecard includes {penalties} total penalty strokes.",
                "impact": "Penalties immediately add strokes and make the next shot choice harder.",
                "next_action": "Start with the penalty holes and reset tee targets and safe clubs.",
                "confidence": _round_issue_confidence(played_holes),
                "priority_score": float(penalties),
            }
        return {
            "category": "penalty_impact",
            "problem": "페널티가 이 라운드의 최우선 이슈입니다.",
            "evidence": f"스코어카드에 페널티가 총 {penalties}타 기록됐습니다.",
            "impact": "페널티는 즉시 1타 이상을 더하고 다음 샷 선택까지 어렵게 만듭니다.",
            "next_action": "공개 라운드의 페널티 홀부터 티샷 목표와 세이프 클럽을 다시 정하세요.",
            "confidence": _round_issue_confidence(played_holes),
            "priority_score": float(penalties),
        }

    if three_putts > 0:
        if locale == "en":
            return {
                "category": "putting",
                "problem": "3-putts are the top issue in this round.",
                "evidence": f"The scorecard includes {three_putts} holes with 3-putts or worse.",
                "impact": "3-putts can still turn GIR holes into bogey or worse.",
                "next_action": "Check long-putt distance control and 1-2m finish putts first.",
                "confidence": _round_issue_confidence(played_holes),
                "priority_score": float(three_putts),
            }
        return {
            "category": "putting",
            "problem": "3퍼트가 이 라운드의 최우선 이슈입니다.",
            "evidence": f"스코어카드에 3퍼트 이상 홀이 {three_putts}개 있습니다.",
            "impact": "3퍼트는 그린 적중 이후에도 보기 이상으로 이어지기 쉽습니다.",
            "next_action": "긴 퍼트 거리감과 1-2m 마무리 퍼트를 먼저 점검하세요.",
            "confidence": _round_issue_confidence(played_holes),
            "priority_score": float(three_putts),
        }

    return None


def _round_issue_confidence(played_holes: int) -> str:
    if played_holes < 9:
        return "low"
    if played_holes < 18:
        return "medium"
    return "high"


def _comment_payload(db: Session, comment: RoundComment) -> dict[str, Any]:
    return {
        "id": comment.id,
        "round_id": comment.round_id,
        "user_id": comment.user_id,
        "parent_comment_id": comment.parent_comment_id,
        "body": comment.body,
        "status": comment.status,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "deleted_at": comment.deleted_at,
        "author_display_name": _user_display_name(db, comment.user_id),
        "author_handle": _user_handle(db, comment.user_id),
    }


def _like_count(db: Session, round_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(RoundLike).where(RoundLike.round_id == round_id)
        )
        or 0
    )


def _has_accepted_follow(db: Session, *, follower_id: uuid.UUID, following_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(Follow).where(
                Follow.follower_id == follower_id,
                Follow.following_id == following_id,
                Follow.status == "accepted",
            )
        )
        is not None
    )


def _can_view_for_comments(db: Session, *, viewer: User, round_: Round) -> bool:
    if round_.user_id == viewer.id:
        return True
    if round_.visibility not in {VISIBILITY_PUBLIC, VISIBILITY_FOLLOWERS}:
        return False
    return _has_accepted_follow(db, follower_id=viewer.id, following_id=round_.user_id)


def _can_view_round_for_viewer(db: Session, *, viewer: User, round_: Round) -> bool:
    try:
        load_viewable_round(db, viewer=viewer, round_id=round_.id)
        return True
    except SocialNotFoundError:
        return False


def _round_metrics(round_: Round) -> dict[str, Any]:
    holes = sorted(round_.holes, key=lambda item: item.hole_number)
    putts = [hole.putts for hole in holes if hole.putts is not None]
    gir_count = sum(1 for hole in holes if hole.gir is True)
    fairways = [hole for hole in holes if hole.fairway_hit is not None]
    fairway_hits = sum(1 for hole in fairways if hole.fairway_hit is True)
    return {
        "putts_total": sum(putts) if putts else None,
        "gir_count": gir_count,
        "fairway_hit_rate": round(fairway_hits / len(fairways), 3) if fairways else None,
        "penalties_total": sum(hole.penalties for hole in holes),
    }


def _user_display_name(db: Session, user_id: uuid.UUID) -> str | None:
    return db.scalar(select(User.display_name).where(User.id == user_id))


def _user_handle(db: Session, user_id: uuid.UUID) -> str | None:
    return db.scalar(select(User.handle).where(User.id == user_id))
