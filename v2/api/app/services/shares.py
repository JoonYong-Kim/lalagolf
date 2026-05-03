import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Hole, Round, ShareLink, User
from app.models.constants import VISIBILITY_LINK_ONLY


class ShareNotFoundError(Exception):
    pass


def create_share(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    title: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[ShareLink, str]:
    round_ = _get_owned_round(db, owner=owner, round_id=round_id)
    token = secrets.token_urlsafe(32)
    share = ShareLink(
        user_id=owner.id,
        round_id=round_.id,
        token_hash=_token_hash(token),
        title=title,
        expires_at=expires_at,
    )
    round_.visibility = VISIBILITY_LINK_ONLY
    db.add(share)
    db.commit()
    db.refresh(share)
    return share, token


def list_shares(db: Session, *, owner: User) -> list[ShareLink]:
    return db.scalars(
        select(ShareLink)
        .where(ShareLink.user_id == owner.id)
        .order_by(ShareLink.created_at.desc())
    ).all()


def update_share(
    db: Session,
    *,
    owner: User,
    share_id: uuid.UUID,
    title: str | None = None,
    expires_at: datetime | None = None,
    revoked: bool | None = None,
) -> ShareLink:
    share = db.scalars(
        select(ShareLink).where(ShareLink.id == share_id, ShareLink.user_id == owner.id)
    ).first()
    if share is None:
        raise ShareNotFoundError

    if title is not None:
        share.title = title
    if expires_at is not None:
        share.expires_at = expires_at
    if revoked is not None:
        share.revoked_at = datetime.now(UTC) if revoked else None
    db.commit()
    db.refresh(share)
    return share


def get_shared_round(db: Session, *, token: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    share = db.scalars(
        select(ShareLink).where(ShareLink.token_hash == _token_hash(token))
    ).first()
    if share is None or share.revoked_at is not None:
        raise ShareNotFoundError
    if share.expires_at is not None and share.expires_at <= now:
        raise ShareNotFoundError

    round_ = db.scalars(
        select(Round)
        .options(
            selectinload(Round.holes).selectinload(Hole.shots),
            selectinload(Round.shared_insights),
        )
        .where(Round.id == share.round_id, Round.deleted_at.is_(None))
    ).first()
    if round_ is None:
        raise ShareNotFoundError

    share.last_accessed_at = now
    db.commit()
    return _public_round_payload(round_, share)


def share_response(share: ShareLink) -> dict[str, Any]:
    return {
        "id": share.id,
        "round_id": share.round_id,
        "title": share.title,
        "url_path": None,
        "expires_at": share.expires_at,
        "revoked_at": share.revoked_at,
        "last_accessed_at": share.last_accessed_at,
    }


def share_create_response(share: ShareLink, token: str) -> dict[str, Any]:
    return {**share_response(share), "token": token, "url_path": f"/s/{token}"}


def _get_owned_round(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = db.scalars(
        select(Round).where(
            Round.id == round_id,
            Round.user_id == owner.id,
            Round.deleted_at.is_(None),
        )
    ).first()
    if round_ is None:
        raise ShareNotFoundError
    return round_


def _public_round_payload(round_: Round, share: ShareLink) -> dict[str, Any]:
    holes = sorted(round_.holes, key=lambda item: item.hole_number)
    insights = _public_top_issue(round_)
    # Public-safe: only non-private insight text, never source files, companions, or private notes.
    return {
        "title": share.title or "Shared round",
        "round": {
            "id": str(round_.id),
            "course_name": round_.course_name if round_.share_course else "Shared course",
            "play_date": round_.play_date.isoformat() if round_.share_exact_date else None,
            "play_month": round_.play_date.strftime("%Y-%m"),
            "total_score": round_.total_score,
            "total_par": round_.total_par,
            "score_to_par": round_.score_to_par,
            "hole_count": round_.hole_count,
        },
        "holes": [
            {
                "hole_number": hole.hole_number,
                "par": hole.par,
                "score": hole.score,
                "putts": hole.putts,
                "gir": hole.gir,
                "penalties": hole.penalties,
            }
            for hole in holes
        ],
        "metrics": {
            "putts_total": sum(hole.putts or 0 for hole in holes),
            "penalties_total": sum(hole.penalties for hole in holes),
            "gir_count": sum(1 for hole in holes if hole.gir is True),
        },
        "insights": insights,
    }


def _public_top_issue(round_: Round) -> list[dict[str, Any]]:
    active_insights = [
        insight
        for insight in getattr(round_, "shared_insights", [])
        if insight.status == "active"
    ]
    if not active_insights:
        fallback = _public_scorecard_issue(round_)
        return [fallback] if fallback else []

    top_issue = sorted(
        active_insights,
        key=lambda insight: (insight.priority_score, insight.created_at),
        reverse=True,
    )[0]
    return [
        {
            "category": top_issue.category,
            "problem": top_issue.problem,
            "evidence": top_issue.evidence,
            "impact": top_issue.impact,
            "next_action": top_issue.next_action,
            "confidence": top_issue.confidence,
            "priority_score": top_issue.priority_score,
        }
    ]


def _public_scorecard_issue(round_: Round) -> dict[str, Any] | None:
    holes = list(round_.holes)
    penalties = sum(hole.penalties for hole in holes)
    three_putts = sum(1 for hole in holes if (hole.putts or 0) >= 3)
    played_holes = len(holes)

    if penalties > 0:
        return {
            "category": "penalty_impact",
            "problem": "페널티가 이 라운드의 최우선 이슈입니다.",
            "evidence": f"스코어카드에 페널티가 총 {penalties}타 기록됐습니다.",
            "impact": "페널티는 즉시 1타 이상을 더하고 다음 샷 선택까지 어렵게 만듭니다.",
            "next_action": "공유된 라운드의 페널티 홀부터 티샷 목표와 세이프 클럽을 다시 정하세요.",
            "confidence": _round_issue_confidence(played_holes),
            "priority_score": float(penalties),
        }

    if three_putts > 0:
        return {
            "category": "putting",
            "problem": "3퍼트가 이 라운드의 최우선 이슈입니다.",
            "evidence": f"스코어카드에 3퍼트 이상 홀이 {three_putts}개 있습니다.",
            "impact": "3퍼트는 그린 적중 이후에도 보기 이상으로 이어지기 쉽습니다.",
            "next_action": "긴 퍼트 거리감과 1-2m 마무리 퍼트를 먼저 점검하세요.",
            "confidence": _round_issue_confidence(played_holes),
            "priority_score": float(three_putts),
        }

    if round_.score_to_par is not None and round_.score_to_par > 0:
        return {
            "category": "score",
            "problem": "파 대비 초과 타수가 이 라운드의 점검 대상입니다.",
            "evidence": f"최종 스코어가 파 대비 +{round_.score_to_par}입니다.",
            "impact": "추가 라운드가 쌓이면 초과 타수의 원인을 카테고리별로 더 좁힐 수 있습니다.",
            "next_action": "샷별 기록을 유지해 다음 공유에서는 손실 카테고리를 더 구체화하세요.",
            "confidence": _round_issue_confidence(played_holes),
            "priority_score": float(round_.score_to_par),
        }

    return None


def _round_issue_confidence(played_holes: int) -> str:
    if played_holes >= 18:
        return "high"
    if played_holes >= 9:
        return "medium"
    return "low"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
