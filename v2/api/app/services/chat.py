import json
import logging
import re
import uuid
from datetime import date, timedelta
from typing import Any
from urllib import error, request

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models import Hole, LlmMessage, LlmThread, Round, Shot, User

logger = logging.getLogger("lalagolf.api.chat")


class ChatNotFoundError(Exception):
    pass


SUGGESTED_QUESTIONS = [
    "최근 10라운드 평균 스코어는?",
    "최근 라운드 퍼팅은 어땠어?",
    "드라이버 페널티율 알려줘",
    "7번 아이언 샷을 요약해줘",
    "어프로치 카테고리 손실이 큰가?",
]


def create_thread(
    db: Session,
    *,
    owner: User,
    title: str | None = None,
) -> LlmThread:
    thread = LlmThread(user_id=owner.id, title=(title or "Ask LalaGolf").strip())
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def list_threads(db: Session, *, owner: User) -> list[LlmThread]:
    return db.scalars(
        select(LlmThread)
        .where(LlmThread.user_id == owner.id)
        .order_by(LlmThread.updated_at.desc(), LlmThread.created_at.desc())
    ).all()


def get_thread(
    db: Session,
    *,
    owner: User,
    thread_id: uuid.UUID,
) -> tuple[LlmThread, list[LlmMessage]]:
    thread = db.scalars(
        select(LlmThread).where(LlmThread.id == thread_id, LlmThread.user_id == owner.id)
    ).first()
    if thread is None:
        raise ChatNotFoundError
    messages = db.scalars(
        select(LlmMessage)
        .where(LlmMessage.thread_id == thread.id, LlmMessage.user_id == owner.id)
        .order_by(LlmMessage.created_at.asc())
    ).all()
    return thread, messages


def add_message(
    db: Session,
    *,
    owner: User,
    thread_id: uuid.UUID,
    content: str,
    settings: Settings,
) -> tuple[LlmMessage, LlmMessage]:
    thread, _messages = get_thread(db, owner=owner, thread_id=thread_id)
    question = content.strip()
    answer = answer_question(db, owner=owner, question=question, settings=settings)

    user_message = LlmMessage(
        thread_id=thread.id,
        user_id=owner.id,
        role="user",
        content=question,
        evidence={},
    )
    assistant_message = LlmMessage(
        thread_id=thread.id,
        user_id=owner.id,
        role="assistant",
        content=answer["content"],
        evidence=answer["evidence"],
    )
    db.add_all([user_message, assistant_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return user_message, assistant_message


def answer_question(
    db: Session,
    *,
    owner: User,
    question: str,
    settings: Settings,
) -> dict[str, Any]:
    plan = plan_question(question)
    evidence = retrieve_context(db, owner=owner, plan=plan)
    deterministic_content = render_answer(question=question, plan=plan, evidence=evidence)
    content = deterministic_content
    if settings.ollama_enabled:
        llm_content, llm_status = _ollama_answer(
            question=question,
            deterministic_content=deterministic_content,
            evidence=evidence,
            settings=settings,
        )
        if llm_content:
            content = llm_content
        evidence["ollama"] = llm_status
    return {"content": content, "evidence": evidence}


def chat_status(settings: Settings) -> dict[str, Any]:
    if not settings.ollama_enabled:
        return {
            "enabled": False,
            "reachable": False,
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
            "mode": "deterministic",
            "detail": "OLLAMA_ENABLED is false",
        }
    reachable, detail = _ollama_reachable(settings)
    return {
        "enabled": True,
        "reachable": reachable,
        "model": settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "mode": "llm" if reachable else "deterministic",
        "detail": detail,
    }


def plan_question(question: str) -> dict[str, Any]:
    normalized = question.lower()
    window = _extract_window(normalized)
    date_range = _extract_date_range(normalized)
    club = _extract_club(question)
    category = _extract_category(normalized)
    intent = "summary"
    if any(keyword in normalized for keyword in ["퍼팅", "putt", "putting"]):
        intent = "putting"
    elif any(keyword in normalized for keyword in ["페널티", "penalty", "벌타", "ob", "해저드"]):
        intent = "penalty"
    elif club:
        intent = "club"
    elif category:
        intent = "category"
    elif any(keyword in normalized for keyword in ["최근", "평균", "스코어", "score"]):
        intent = "score"

    return {
        "intent": intent,
        "window": window,
        "date_range": date_range,
        "club": club,
        "category": category,
    }


def retrieve_context(db: Session, *, owner: User, plan: dict[str, Any]) -> dict[str, Any]:
    rounds = _filtered_rounds(db, owner=owner, plan=plan)
    round_ids = [round_.id for round_ in rounds]
    holes = db.scalars(
        select(Hole).where(Hole.user_id == owner.id, Hole.round_id.in_(round_ids))
    ).all()
    shots_query = select(Shot).where(Shot.user_id == owner.id, Shot.round_id.in_(round_ids))
    if plan.get("club"):
        club = str(plan["club"]).upper()
        shots_query = shots_query.where(
            func.upper(func.coalesce(Shot.club_normalized, Shot.club)).like(f"%{club}%")
        )
    shots = db.scalars(shots_query).all()
    if plan.get("category"):
        shots = [shot for shot in shots if _shot_category(shot) == plan["category"]]

    filters = {
        "window": plan.get("window"),
        "date_range": plan.get("date_range"),
        "club": plan.get("club"),
        "category": plan.get("category"),
    }
    return {
        "intent": plan["intent"],
        "filters": filters,
        "round_count": len(rounds),
        "shot_count": len(shots),
        "hole_count": len(holes),
        "rounds": [_round_evidence(round_) for round_ in rounds],
        "metrics": _metrics(rounds, holes, shots),
        "supported_questions": SUGGESTED_QUESTIONS,
    }


def render_answer(*, question: str, plan: dict[str, Any], evidence: dict[str, Any]) -> str:
    if evidence["round_count"] == 0:
        return "조건에 맞는 라운드가 없습니다. 업로드된 라운드나 필터 조건을 확인해 주세요."

    metrics = evidence["metrics"]
    prefix = (
        f"{evidence['round_count']}개 라운드, {evidence['shot_count']}개 샷을 기준으로 봤습니다."
    )
    intent = plan["intent"]
    if intent == "putting":
        return (
            f"{prefix} 평균 퍼트 수는 {metrics['average_putts'] or '-'}개이고, "
            f"3퍼트율은 {metrics['three_putt_rate_percent'] or 0}%입니다."
        )
    if intent == "penalty":
        return (
            f"{prefix} 페널티는 총 {metrics['penalty_strokes']}타이고, "
            f"페널티가 기록된 샷은 {metrics['penalty_shot_count']}개입니다."
        )
    if intent == "club":
        club = plan.get("club")
        return (
            f"{prefix} {club} 관련 샷은 {evidence['shot_count']}개입니다. "
            f"평균 거리는 {metrics['average_distance'] or '-'}m, "
            f"페널티 샷은 {metrics['penalty_shot_count']}개입니다."
        )
    if intent == "category":
        category = plan.get("category")
        return (
            f"{prefix} {category} 카테고리 샷은 {evidence['shot_count']}개입니다. "
            f"페널티 샷 {metrics['penalty_shot_count']}개, 평균 거리는 "
            f"{metrics['average_distance'] or '-'}m입니다."
        )
    return (
        f"{prefix} 평균 스코어는 {metrics['average_score'] or '-'}타, "
        f"베스트 스코어는 {metrics['best_score'] or '-'}타입니다."
    )


def _ollama_answer(
    *,
    question: str,
    deterministic_content: str,
    evidence: dict[str, Any],
    settings: Settings,
) -> tuple[str | None, dict[str, Any]]:
    evidence_json = json.dumps(_llm_safe_evidence(evidence), ensure_ascii=False, default=str)
    prompt = (
        "You are Ask GolfRaiders. Answer in Korean unless the question is in English. "
        "Use only the provided golf evidence. Be concise and include one practical next action.\n\n"
        f"Question: {question}\n"
        f"Deterministic baseline: {deterministic_content}\n"
        f"Evidence JSON: {evidence_json}"
    )
    payload = json.dumps(
        {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")
    try:
        req = request.Request(
            f"{settings.ollama_base_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=settings.ollama_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        llm_response = str(body.get("response") or "").strip()
        return llm_response or None, {
            "enabled": True,
            "used": bool(llm_response),
            "reachable": True,
            "model": settings.ollama_model,
            "status": "ok" if llm_response else "empty_response",
            "timeout_seconds": settings.ollama_timeout_seconds,
        }
    except (OSError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning(
            "ollama wording skipped; deterministic answer returned",
            extra={"error": str(exc)},
        )
        return None, {
            "enabled": True,
            "used": False,
            "reachable": False,
            "model": settings.ollama_model,
            "status": "fallback_deterministic",
            "error": str(exc),
            "timeout_seconds": settings.ollama_timeout_seconds,
        }


def _ollama_reachable(settings: Settings) -> tuple[bool, str]:
    try:
        req = request.Request(f"{settings.ollama_base_url.rstrip('/')}/api/tags", method="GET")
        with request.urlopen(req, timeout=settings.ollama_timeout_seconds) as response:
            response.read(1024)
        return True, "Ollama is reachable"
    except (OSError, error.URLError, TimeoutError) as exc:
        return False, str(exc)


def _llm_safe_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": evidence.get("intent"),
        "filters": evidence.get("filters"),
        "round_count": evidence.get("round_count"),
        "shot_count": evidence.get("shot_count"),
        "hole_count": evidence.get("hole_count"),
        "rounds": evidence.get("rounds", [])[:10],
        "metrics": evidence.get("metrics"),
    }


def message_response(message: LlmMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "evidence": message.evidence,
        "created_at": message.created_at,
    }


def thread_response(thread: LlmThread) -> dict[str, Any]:
    return {
        "id": thread.id,
        "title": thread.title,
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
    }


def _filtered_rounds(db: Session, *, owner: User, plan: dict[str, Any]) -> list[Round]:
    query = (
        select(Round)
        .options(selectinload(Round.holes))
        .where(Round.user_id == owner.id, Round.deleted_at.is_(None))
        .order_by(Round.play_date.desc(), Round.created_at.desc())
    )
    date_range = plan.get("date_range")
    if date_range:
        query = query.where(
            Round.play_date >= date_range["start"],
            Round.play_date <= date_range["end"],
        )
    rounds = list(db.scalars(query).all())
    window = plan.get("window")
    if isinstance(window, int):
        rounds = rounds[:window]
    return rounds


def _extract_window(text: str) -> int:
    match = re.search(r"최근\s*(\d+)", text)
    if match:
        return max(1, min(int(match.group(1)), 50))
    return 10


def _extract_date_range(text: str) -> dict[str, date] | None:
    match = re.search(r"(20\d{2})-(\d{2})", text)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return {"start": start, "end": end}


def _extract_club(question: str) -> str | None:
    patterns = [
        r"([DUPSW]\d?|D|드라이버|퍼터|웨지|유틸|우드)",
        r"(\d{1,2})번\s*아이언",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        if value == "드라이버":
            return "D"
        if value == "퍼터":
            return "P"
        if value == "웨지":
            return "W"
        if value == "유틸":
            return "U"
        if value == "우드":
            return "W"
        if value.isdigit():
            return f"I{value}"
        return value.upper()
    return None


def _extract_category(text: str) -> str | None:
    if "티샷" in text or "tee" in text:
        return "off_the_tee"
    if "어프로치" in text or "approach" in text:
        return "approach"
    if "쇼트" in text or "short" in text:
        return "short_game"
    if "리커버리" in text or "recovery" in text:
        return "recovery"
    return None


def _round_evidence(round_: Round) -> dict[str, Any]:
    return {
        "round_id": str(round_.id),
        "play_date": round_.play_date.isoformat(),
        "course_name": round_.course_name,
        "total_score": round_.total_score,
        "score_to_par": round_.score_to_par,
    }


def _metrics(rounds: list[Round], holes: list[Hole], shots: list[Shot]) -> dict[str, Any]:
    scores = [round_.total_score for round_ in rounds if round_.total_score is not None]
    putt_totals = [
        sum(hole.putts for hole in round_.holes if hole.putts is not None)
        for round_ in rounds
        if any(hole.putts is not None for hole in round_.holes)
    ]
    putts = [hole.putts for hole in holes if hole.putts is not None]
    distances = [shot.distance for shot in shots if shot.distance is not None]
    penalty_shots = [shot for shot in shots if shot.penalty_strokes]
    three_putts = [putt for putt in putts if putt >= 3]
    return {
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "best_score": min(scores) if scores else None,
        "average_putts": round(sum(putt_totals) / len(putt_totals), 1) if putt_totals else None,
        "three_putt_rate_percent": round(len(three_putts) / len(putts) * 100, 1) if putts else None,
        "penalty_strokes": sum(shot.penalty_strokes for shot in shots),
        "penalty_shot_count": len(penalty_shots),
        "average_distance": round(sum(distances) / len(distances), 1) if distances else None,
    }


def _shot_category(shot: Shot) -> str:
    if shot.penalty_strokes:
        return "penalty_impact"
    if (shot.club_normalized or shot.club or "").upper() in {"P", "PT"}:
        return "putting"
    if shot.shot_number == 1:
        return "off_the_tee"
    if shot.distance is not None and shot.distance <= 50:
        return "short_game"
    return "approach"
