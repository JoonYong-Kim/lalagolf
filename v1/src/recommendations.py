from collections import defaultdict

from src.analytics_config import (
    RECOMMENDATION_SAMPLE_HIGH_WATERMARK,
    RECOMMENDATION_SAMPLE_MEDIUM_WATERMARK,
)


CATEGORY_LABELS = {
    "off_the_tee": "티샷",
    "approach": "어프로치",
    "short_game": "쇼트게임",
    "putting": "퍼팅",
    "recovery": "리커버리",
    "penalty_impact": "페널티 관리",
}

CLUB_SAFETY_CHOICES = {
    "safer": "우드/유틸리티",
    "neutral": "드라이버 유지",
}


PRACTICE_GUIDES = {
    "off_the_tee": {
        "focus": "티샷 분산 관리",
        "practice": "드라이버와 대체 티샷 클럽으로 페어웨이 폭을 가정한 스타트 라인 훈련을 우선 배치합니다.",
    },
    "approach": {
        "focus": "120-160m 공략",
        "practice": "7번아이언부터 웨지까지 거리별 캐리 편차를 줄이는 표적 훈련을 우선 배치합니다.",
    },
    "short_game": {
        "focus": "30m 이내 업앤다운",
        "practice": "러프와 벙커를 포함한 10-30m 피치/칩 반복으로 파 세이브 확률을 높입니다.",
    },
    "putting": {
        "focus": "3퍼트 억제",
        "practice": "6-12m 래그퍼트와 1-2m 마무리 퍼트를 묶어서 연습 루틴을 구성합니다.",
    },
    "recovery": {
        "focus": "트러블 탈출",
        "practice": "무리한 그린 공략 대신 안전 지역 복귀를 우선하는 리커버리 시나리오를 반복합니다.",
    },
    "penalty_impact": {
        "focus": "페널티 회피",
        "practice": "위험 홀에서는 목표 구역을 넓히고, 1벌타 가능성이 큰 샷 선택을 줄이는 코스 매니지먼트를 점검합니다.",
    },
}


def _sample_status(count):
    if count >= RECOMMENDATION_SAMPLE_HIGH_WATERMARK:
        return {
            "level": "high",
            "label": "표본 충분",
            "message": "최근 샷 수가 충분해 방향성보다 실행 우선순위 판단에 활용할 수 있습니다.",
        }
    if count >= RECOMMENDATION_SAMPLE_MEDIUM_WATERMARK:
        return {
            "level": "medium",
            "label": "표본 보통",
            "message": "방향성은 참고할 수 있지만 다음 몇 라운드에서 계속 추적하는 편이 안전합니다.",
        }
    return {
        "level": "low",
        "label": "표본 적음",
        "message": "샷 수가 적어 최근 몇 번의 실수 영향이 크므로 보조 지표와 함께 해석해야 합니다.",
    }


def _build_loss_reasons(category, recent_summary, row):
    reasons = [
        f"최근 {row['count']}샷에서 평균 shot value가 {row['avg_shot_value']:.2f}타입니다.",
    ]

    if category == "off_the_tee":
        reasons.append(f"드라이버 페널티율 {recent_summary.get('avg_driver_penalty_rate', 0) * 100:.1f}%입니다.")
        reasons.append(f"드라이버 결과 C 비율 {recent_summary.get('avg_driver_result_c_rate', 0) * 100:.1f}%입니다.")
    elif category == "approach":
        reasons.append(f"160m 이내 GIR 전환율 {recent_summary.get('avg_gir_from_under_160_rate', 0) * 100:.1f}%입니다.")
        reasons.append("핀 직접 공략보다 중앙 공략 비중을 먼저 높일 필요가 있습니다.")
    elif category == "short_game":
        reasons.append(f"업앤다운 성공률 {recent_summary.get('avg_up_and_down_rate', 0) * 100:.1f}%입니다.")
        reasons.append(f"스크램블링 {recent_summary.get('avg_scrambling_rate', 0) * 100:.1f}%입니다.")
    elif category == "putting":
        reasons.append(f"3퍼트율 {recent_summary.get('avg_three_putt_rate', 0) * 100:.1f}%입니다.")
        reasons.append(f"평균 퍼트 수 {recent_summary.get('avg_putts', 0):.2f}입니다.")
    elif category == "recovery":
        reasons.append(f"평균 페널티 타수 {recent_summary.get('avg_penalty_strokes', 0):.1f}타입니다.")
        reasons.append("트러블 이후 공격적 선택이 손실을 키웠을 가능성을 점검할 필요가 있습니다.")
    elif category == "penalty_impact":
        reasons.append(f"평균 페널티 타수 {recent_summary.get('avg_penalty_strokes', 0):.1f}타입니다.")
        reasons.append(f"티샷 페널티율 {recent_summary.get('avg_tee_shot_penalty_rate', 0) * 100:.1f}%입니다.")

    return reasons[:3]


def _priority_score(row):
    score = abs(row.get("total_shot_value", 0))
    trend_direction = row.get("trend_direction", "flat")
    if trend_direction == "worsening":
        score += 0.75
    elif trend_direction == "flat":
        score += 0.2
    elif trend_direction == "improving":
        score -= 0.25

    score += min(row.get("count", 0), 20) * 0.02
    return score


def _priority_urgency(row):
    trend_direction = row.get("trend_direction", "flat")
    if trend_direction == "worsening":
        return "즉시 개입"
    if trend_direction == "flat":
        return "우선 점검"
    return "유지 추적"


def _build_priority_reason(row):
    loss = abs(row.get("total_shot_value", 0))
    count = row.get("count", 0)
    trend_label = row.get("trend_label", "보합")
    urgency_label = row.get("urgency_label", _priority_urgency(row))
    sample = _sample_status(count)
    return (
        f"총 손실 {loss:.2f}타, 최근 흐름 {trend_label}, 표본 {sample['label'].replace('표본 ', '')} "
        f"상태라 현재 판단은 {urgency_label}입니다."
    )


def _build_priority_action(row, guide, menu):
    label = CATEGORY_LABELS.get(row.get("category"), row.get("category"))
    trend_direction = row.get("trend_direction", "flat")
    sample = _sample_status(row.get("count", 0))
    if trend_direction == "worsening":
        lead = f"이번 주에는 {label}에서 반복되는 손실을 먼저 끊어야 합니다."
        if sample["level"] == "high":
            intensity = "연습 시작 구간을 이 항목 교정에 가장 먼저 배정하세요."
        elif sample["level"] == "medium":
            intensity = "첫 연습 블록에서 우선 점검하고 다음 라운드까지 계속 추적하세요."
        else:
            intensity = "짧은 교정 루틴으로 먼저 재현 여부를 확인하세요."
    elif trend_direction == "flat":
        lead = f"이번 주에는 {label} 손실이 고정되지 않도록 먼저 점검해야 합니다."
        if sample["level"] == "high":
            intensity = "주력 루틴 직전에 기준선 확인 블록을 넣는 편이 좋습니다."
        elif sample["level"] == "medium":
            intensity = "과한 교정보다 기준선 점검 위주로 연습 순서를 잡으세요."
        else:
            intensity = "짧은 체크 세션으로 현재 패턴이 반복인지 먼저 확인하세요."
    else:
        lead = f"이번 주에는 개선 중인 {label} 감각을 유지하는 연습을 이어가면 됩니다."
        if sample["level"] == "high":
            intensity = "볼륨을 무리하게 늘리기보다 현재 루틴을 압축해 유지하세요."
        elif sample["level"] == "medium":
            intensity = "주간 루틴 후반에 짧게 배치해 흐름만 유지하면 충분합니다."
        else:
            intensity = "짧은 확인 세션만 두고 다른 약점 교정에 시간을 넘기는 편이 좋습니다."

    focus = guide.get("focus")
    first_menu = menu[0] if menu else None
    if first_menu and focus:
        return f"{lead} {intensity} 우선 {focus} 기준으로 `{first_menu['name']}` 드릴부터 시작하세요."
    if first_menu:
        return f"{lead} {intensity} 우선 `{first_menu['name']}` 드릴부터 시작하세요."
    if focus:
        return f"{lead} {intensity} 우선 {focus} 기준으로 연습 루틴을 배치하세요."
    return f"{lead} {intensity}"


def _build_round_priority_reason(row):
    loss = abs(row.get("total_shot_value", 0))
    count = row.get("count", 0)
    return (
        f"이번 라운드 {count}샷 기준 총 손실 {loss:.2f}타입니다. "
        "단일 라운드 신호라 다음 1-2라운드에서 재발 여부를 함께 확인하는 편이 안전합니다."
    )


def _build_round_context_payload(category, round_metrics):
    if category == "putting":
        three_putt_rate = ((round_metrics.get("putting") or {}).get("three_putt_rate"))
        first_putt_avg = ((round_metrics.get("putting") or {}).get("first_putt_distance_avg"))
        if three_putt_rate is not None and three_putt_rate >= 0.15 and first_putt_avg is not None and first_putt_avg >= 6:
            return {
                "subtype": "거리감 손실형",
                "note": f"이번 라운드 3퍼트율이 {three_putt_rate * 100:.1f}%이고 첫 퍼트 평균 거리가 {first_putt_avg:.1f}m라 거리감 회복이 우선입니다.",
                "action_suffix": "장거리 래그퍼트 비중을 먼저 높이고, 마무리 퍼트는 그 다음 블록에 배치하세요.",
            }
        if three_putt_rate is not None and three_putt_rate >= 0.15:
            return {
                "subtype": "마무리 불안형",
                "note": f"이번 라운드 3퍼트율이 {three_putt_rate * 100:.1f}%여서 1-2m 마무리 성공률 회복이 우선입니다.",
                "action_suffix": "래그퍼트보다 짧은 마무리 퍼트 반복을 먼저 두는 편이 좋습니다.",
            }
    if category == "off_the_tee":
        tee_penalty_rate = ((round_metrics.get("penalties") or {}).get("tee_shot_penalty_rate"))
        driver_result_c_rate = ((round_metrics.get("tee_shots") or {}).get("driver_result_c_rate"))
        if tee_penalty_rate is not None and tee_penalty_rate >= 0.10:
            return {
                "subtype": "페널티 리스크형",
                "note": f"이번 라운드 티샷 페널티율이 {tee_penalty_rate * 100:.1f}%라 안전 구역 재설정이 필요합니다.",
                "action_suffix": "드라이버 교정보다 세이프 클럽 기준과 스타트 라인 폭부터 다시 잡으세요.",
            }
        if driver_result_c_rate is not None and driver_result_c_rate >= 0.30:
            return {
                "subtype": "큰 미스 누적형",
                "note": f"이번 라운드 드라이버 결과 C 비율이 {driver_result_c_rate * 100:.1f}%라 큰 미스 억제가 우선입니다.",
                "action_suffix": "비거리보다 가장 넓은 랜딩 구역을 맞히는 루틴을 먼저 반복하세요.",
            }
    if category == "approach":
        gir_rate = ((round_metrics.get("approach") or {}).get("gir_from_under_160_rate"))
        average_error = ((round_metrics.get("approach") or {}).get("under_160_average_error"))
        result_c = (((round_metrics.get("approach") or {}).get("under_160_result_distribution") or {}).get("C"))
        if gir_rate is not None and gir_rate <= 0.45 and average_error is not None and average_error >= 15:
            return {
                "subtype": "거리 오차형",
                "note": f"이번 라운드 160m 이내 GIR 전환율이 {gir_rate * 100:.1f}%이고 평균 오차가 {average_error:.1f}m라 거리 오차 교정이 우선입니다.",
                "action_suffix": "핀 공략보다 클럽별 캐리 기준을 다시 고정하는 드릴을 먼저 두세요.",
            }
        if gir_rate is not None and gir_rate <= 0.45 and result_c is not None and result_c >= 1:
            return {
                "subtype": "미스 누적형",
                "note": f"이번 라운드 160m 이내 GIR 전환율이 {gir_rate * 100:.1f}%이고 큰 미스 샷이 누적돼 중앙 공략 기준이 필요합니다.",
                "action_suffix": "핀보다 그린 중앙 목표를 먼저 고정한 뒤 샷 시작선을 점검하세요.",
            }
        if gir_rate is not None and gir_rate <= 0.45:
            return {
                "subtype": "GIR 전환 저하형",
                "note": f"이번 라운드 160m 이내 GIR 전환율이 {gir_rate * 100:.1f}%라 중앙 공략 기준을 다시 잡아야 합니다.",
                "action_suffix": "버디 공략보다 GIR 확보 루틴을 먼저 반복하는 편이 좋습니다.",
            }
    if category == "short_game":
        up_and_down_rate = ((round_metrics.get("short_game") or {}).get("up_and_down_rate"))
        sand_save_rate = ((round_metrics.get("short_game") or {}).get("sand_save_rate"))
        scrambling_rate = ((round_metrics.get("short_game") or {}).get("scrambling_rate"))
        if sand_save_rate is not None and sand_save_rate == 0:
            return {
                "subtype": "벙커 세이브 저하형",
                "note": "이번 라운드 벙커 세이브가 나오지 않아 벙커 탈출 기본 패턴 점검이 필요합니다.",
                "action_suffix": "러프보다 벙커 기본 탈출 루틴을 먼저 배치하세요.",
            }
        if up_and_down_rate is not None and up_and_down_rate <= 0.30 and scrambling_rate is not None and scrambling_rate <= 0.30:
            return {
                "subtype": "파 세이브 저하형",
                "note": f"이번 라운드 업앤다운 성공률이 {up_and_down_rate * 100:.1f}%이고 스크램블링도 낮아 파 세이브 패턴이 흔들렸습니다.",
                "action_suffix": "어려운 샷보다 한 가지 탄도와 런 비율만 고정하는 연습을 먼저 두세요.",
            }
        if up_and_down_rate is not None and up_and_down_rate <= 0.30:
            return {
                "subtype": "탄도 기준 불안형",
                "note": f"이번 라운드 업앤다운 성공률이 {up_and_down_rate * 100:.1f}%라 기본 탄도 하나를 고정하는 편이 좋습니다.",
                "action_suffix": "낮은 위험의 기본 칩샷 패턴을 먼저 반복하세요.",
            }
    if category in {"recovery", "penalty_impact"}:
        penalty_strokes = ((round_metrics.get("penalties") or {}).get("penalty_strokes_per_round"))
        if penalty_strokes is not None and penalty_strokes >= 2:
            return {
                "subtype": "무리한 만회형",
                "note": f"이번 라운드 페널티 타수가 {penalty_strokes}타라 무리한 만회보다 안전 복귀 루틴이 우선입니다.",
                "action_suffix": "직접 만회보다 한 번에 플레이 가능한 구역 복귀를 먼저 연습하세요.",
            }
    return {"subtype": None, "note": None, "action_suffix": None}


def _build_recent_context_payload(category, recent_summary, row):
    if category == "putting":
        three_putt_rate = recent_summary.get("avg_three_putt_rate")
        avg_putts = recent_summary.get("avg_putts")
        if three_putt_rate is not None and three_putt_rate >= 0.18 and avg_putts is not None and avg_putts >= 2.0:
            return {
                "subtype": "거리감 손실형",
                "note": f"최근 3퍼트율 {three_putt_rate * 100:.1f}%, 평균 퍼트 수 {avg_putts:.2f}라 거리감 관리가 우선입니다.",
                "action_suffix": "래그퍼트 비중을 먼저 두고 마무리 퍼트는 후반 블록으로 넘기세요.",
            }
        if three_putt_rate is not None and three_putt_rate >= 0.15:
            return {
                "subtype": "마무리 불안형",
                "note": f"최근 3퍼트율 {three_putt_rate * 100:.1f}%라 1-2m 마무리 안정화가 필요합니다.",
                "action_suffix": "장거리 퍼트보다 짧은 마무리 퍼트 반복을 먼저 넣으세요.",
            }
    if category == "off_the_tee":
        penalty_rate = recent_summary.get("avg_driver_penalty_rate")
        result_c_rate = recent_summary.get("avg_driver_result_c_rate")
        if penalty_rate is not None and penalty_rate >= 0.12:
            return {
                "subtype": "페널티 리스크형",
                "note": f"최근 드라이버 페널티율 {penalty_rate * 100:.1f}%라 세이프 라인 재설정이 우선입니다.",
                "action_suffix": "드라이버 볼스피드보다 미스 허용 방향과 안전 구역부터 다시 고정하세요.",
            }
        if result_c_rate is not None and result_c_rate >= 0.30:
            return {
                "subtype": "큰 미스 누적형",
                "note": f"최근 드라이버 결과 C 비율이 {result_c_rate * 100:.1f}%라 큰 미스 억제가 핵심입니다.",
                "action_suffix": "가장 넓은 랜딩 구역을 기준으로 스타트 라인만 먼저 안정화하세요.",
            }
    if category == "approach":
        gir_rate = recent_summary.get("avg_gir_from_under_160_rate")
        avg_loss = abs(row.get("avg_shot_value", 0))
        if gir_rate is not None and gir_rate <= 0.40 and avg_loss >= 0.10:
            return {
                "subtype": "거리 오차형",
                "note": f"최근 160m 이내 GIR {gir_rate * 100:.1f}%, 샷당 손실 {avg_loss:.2f}타라 거리 오차 교정이 우선입니다.",
                "action_suffix": "핀 공략보다 클럽별 캐리 기준을 먼저 다시 고정하세요.",
            }
        if gir_rate is not None and gir_rate <= 0.45 and row.get("trend_direction") == "worsening":
            return {
                "subtype": "미스 누적형",
                "note": f"최근 160m 이내 GIR {gir_rate * 100:.1f}%이고 흐름도 악화 중이라 중앙 공략 기준이 필요합니다.",
                "action_suffix": "핀보다 그린 중앙 목표와 샷 시작선 점검을 먼저 두세요.",
            }
        if gir_rate is not None and gir_rate <= 0.45:
            return {
                "subtype": "GIR 전환 저하형",
                "note": f"최근 160m 이내 GIR {gir_rate * 100:.1f}%라 GIR 확보 루틴 점검이 필요합니다.",
                "action_suffix": "버디 공략보다 GIR 확보 반복으로 기준선을 먼저 올리세요.",
            }
    if category == "short_game":
        up_and_down_rate = recent_summary.get("avg_up_and_down_rate")
        scrambling_rate = recent_summary.get("avg_scrambling_rate")
        if up_and_down_rate is not None and up_and_down_rate <= 0.25 and scrambling_rate is not None and scrambling_rate <= 0.35:
            return {
                "subtype": "파 세이브 저하형",
                "note": f"최근 업앤다운 {up_and_down_rate * 100:.1f}%, 스크램블링 {scrambling_rate * 100:.1f}%라 파 세이브 패턴 회복이 우선입니다.",
                "action_suffix": "어려운 샷보다 한 가지 탄도와 런 비율만 반복하세요.",
            }
        if up_and_down_rate is not None and up_and_down_rate <= 0.30:
            return {
                "subtype": "탄도 기준 불안형",
                "note": f"최근 업앤다운 {up_and_down_rate * 100:.1f}%라 기본 탄도 기준이 흔들리고 있습니다.",
                "action_suffix": "낮은 위험의 기본 칩샷 패턴을 먼저 고정하세요.",
            }
    if category in {"recovery", "penalty_impact"}:
        penalty_strokes = recent_summary.get("avg_penalty_strokes")
        if penalty_strokes is not None and penalty_strokes >= 1.5:
            return {
                "subtype": "무리한 만회형",
                "note": f"최근 평균 페널티 타수 {penalty_strokes:.1f}타라 무리한 만회 시도가 손실을 키웠을 수 있습니다.",
                "action_suffix": "직접 만회보다 안전 복귀와 다음 샷 거리 확보를 먼저 연습하세요.",
            }
    return {"subtype": None, "note": None, "action_suffix": None}


def _build_subtype_drill(category, subtype, recent_summary):
    if category == "approach" and subtype == "거리 오차형":
        return {
            "name": "캐리 편차 10m 매트릭스",
            "detail": "같은 클럽으로 10m 간격 목표를 두고 캐리 편차를 기록해 기준 거리를 다시 맞춥니다.",
        }
    if category == "approach" and subtype == "미스 누적형":
        return {
            "name": "그린 중앙 스타트 라인 9구",
            "detail": "핀 대신 그린 중앙만 겨냥해 시작선과 미스 폭을 함께 줄이는 연습입니다.",
        }
    if category == "putting" and subtype == "거리감 손실형":
        return {
            "name": "8-12m 세이프 존 래그 12구",
            "detail": "홀컵이 아니라 1m 안전 원 안에 두는 성공률만 기록해 거리감을 먼저 회복합니다.",
        }
    if category == "putting" and subtype == "마무리 불안형":
        return {
            "name": "1-2m 마무리 연속 성공 20구",
            "detail": "짧은 퍼트를 연속 성공 기준으로 끊어 치며 마무리 불안을 줄입니다.",
        }
    if category == "off_the_tee" and subtype == "페널티 리스크형":
        return {
            "name": "세이프 라인 선언 10구",
            "detail": "샷 전 안전 구역과 미스 허용 방향을 먼저 말하고 티샷을 실행합니다.",
        }
    if category == "off_the_tee" and subtype == "큰 미스 누적형":
        return {
            "name": "와이드 랜딩 10구",
            "detail": "가장 넓은 랜딩 구역만 목표로 두고 탄착군 폭을 먼저 줄입니다.",
        }
    if category == "short_game" and subtype == "파 세이브 저하형":
        return {
            "name": "파 세이브 9볼 챌린지",
            "detail": "9개의 다양한 라이에서 한 가지 탄도와 런 비율로만 파 세이브를 시도합니다.",
        }
    if category == "short_game" and subtype == "탄도 기준 불안형":
        return {
            "name": "기본 칩샷 탄도 고정 15구",
            "detail": "가장 자신 있는 탄도 하나만 반복해 거리별 런아웃을 고정합니다.",
        }
    if category in {"recovery", "penalty_impact"} and subtype == "무리한 만회형":
        return {
            "name": "안전 복귀 우선 8구",
            "detail": "트러블 상황에서 공격보다 한 번에 플레이 가능한 구역 복귀만 반복합니다.",
        }
    return None


def _build_contextual_menu(category, recent_summary, row, context_payload):
    base_menu = _build_training_menu(category, recent_summary)
    subtype_drill = _build_subtype_drill(category, context_payload.get("subtype"), recent_summary)
    if not subtype_drill:
        return base_menu
    return [subtype_drill] + [item for item in base_menu if item["name"] != subtype_drill["name"]]


def build_recent_shot_value_window(raw_trend_data, shot_value_by_round, window=10):
    rounds = {}
    for row in raw_trend_data:
        round_id = row.get("round_id")
        playdate = row.get("playdate")
        if round_id is None or playdate is None:
            continue
        if round_id not in rounds:
            rounds[round_id] = playdate

    selected_round_ids = [
        round_id
        for round_id, _ in sorted(rounds.items(), key=lambda item: item[1], reverse=True)[:window]
    ]
    selected_summaries = [
        shot_value_by_round[round_id]
        for round_id in selected_round_ids
        if round_id in shot_value_by_round
    ]
    split_index = len(selected_summaries) // 2
    newer_summaries = selected_summaries[:split_index]
    older_summaries = selected_summaries[split_index:]

    category_totals = defaultdict(lambda: {"count": 0, "total_shot_value": 0.0})
    newer_totals = defaultdict(lambda: {"count": 0, "total_shot_value": 0.0})
    older_totals = defaultdict(lambda: {"count": 0, "total_shot_value": 0.0})
    covered_shots = 0
    for summary in selected_summaries:
        covered_shots += summary.get("covered_shots", 0)
        for item in summary.get("category_summary", []):
            bucket = category_totals[item["category"]]
            bucket["count"] += item["count"]
            bucket["total_shot_value"] += item["total_shot_value"]
    for summary in newer_summaries:
        for item in summary.get("category_summary", []):
            bucket = newer_totals[item["category"]]
            bucket["count"] += item["count"]
            bucket["total_shot_value"] += item["total_shot_value"]
    for summary in older_summaries:
        for item in summary.get("category_summary", []):
            bucket = older_totals[item["category"]]
            bucket["count"] += item["count"]
            bucket["total_shot_value"] += item["total_shot_value"]

    category_summary = []
    for category, values in category_totals.items():
        count = values["count"]
        total = values["total_shot_value"]
        newer = newer_totals.get(category, {"count": 0, "total_shot_value": 0.0})
        older = older_totals.get(category, {"count": 0, "total_shot_value": 0.0})
        newer_avg = newer["total_shot_value"] / newer["count"] if newer["count"] else 0
        older_avg = older["total_shot_value"] / older["count"] if older["count"] else 0
        trend_delta = newer_avg - older_avg
        if newer["count"] == 0 or older["count"] == 0 or abs(trend_delta) < 0.03:
            trend_direction = "flat"
            trend_label = "보합"
        elif trend_delta > 0:
            trend_direction = "improving"
            trend_label = "개선"
        else:
            trend_direction = "worsening"
            trend_label = "악화"
        category_summary.append(
            {
                "category": category,
                "count": count,
                "total_shot_value": total,
                "avg_shot_value": total / count if count else 0,
                "newer_count": newer["count"],
                "newer_avg_shot_value": newer_avg,
                "older_count": older["count"],
                "older_avg_shot_value": older_avg,
                "trend_delta": trend_delta,
                "trend_direction": trend_direction,
                "trend_label": trend_label,
                "priority_score": _priority_score(
                    {
                        "total_shot_value": total,
                        "trend_direction": trend_direction,
                        "count": count,
                    }
                ),
                "urgency_label": _priority_urgency(
                    {
                        "trend_direction": trend_direction,
                    }
                ),
            }
        )

    category_summary.sort(key=lambda item: item["priority_score"], reverse=True)
    return {
        "window": window,
        "round_count": len(selected_round_ids),
        "covered_shots": covered_shots,
        "category_summary": category_summary,
    }


def build_recommendations(recent_summary, shot_value_window):
    category_rows = shot_value_window.get("category_summary", [])
    losses = [
        row for row in category_rows
        if row["count"] > 0 and row["total_shot_value"] < -0.05
    ]
    losses.sort(key=lambda item: item.get("priority_score", _priority_score(item)), reverse=True)

    priorities = []
    for row in losses[:3]:
        guide = PRACTICE_GUIDES.get(row["category"], {})
        label = CATEGORY_LABELS.get(row["category"], row["category"])
        context_payload = _build_recent_context_payload(row["category"], recent_summary, row)
        menu = _build_contextual_menu(row["category"], recent_summary, row, context_payload)
        priorities.append(
            {
                "category": row["category"],
                "label": label,
                "focus": guide.get("focus", label),
                "loss": row["total_shot_value"],
                "average_loss": row["avg_shot_value"],
                "count": row["count"],
                "message": f"최근 {shot_value_window['window']}라운드 {label} 반복 손실은 {row['total_shot_value']:.2f}타입니다.",
                "practice": guide.get("practice", ""),
                "menu": menu,
                "sample": _sample_status(row["count"]),
                "reasons": _build_loss_reasons(row["category"], recent_summary, row),
                "trend_label": row.get("trend_label", "보합"),
                "trend_direction": row.get("trend_direction", "flat"),
                "priority_score": row.get("priority_score", _priority_score(row)),
                "urgency_label": row.get("urgency_label", _priority_urgency(row)),
                "priority_reason": _build_priority_reason(row),
                "priority_action": (
                    f"{_build_priority_action(row, guide, menu)} {context_payload['action_suffix']}"
                    if context_payload["action_suffix"] else _build_priority_action(row, guide, menu)
                ),
                "context_subtype": context_payload["subtype"],
                "context_note": context_payload["note"],
            }
        )

    strategy_notes = []
    context_notes = []
    strategy_cards = []
    context_strategy_cards = []
    if recent_summary.get("avg_driver_penalty_rate", 0) >= 0.12:
        strategy_notes.append("드라이버 페널티율이 높아 좁은 홀에서는 우드/유틸리티 선택 기준을 같이 운영하는 것이 좋습니다.")
        strategy_cards.append(
            {
                "title": "좁은 홀 티샷 전략",
                "trigger": f"최근 드라이버 페널티율 {recent_summary['avg_driver_penalty_rate'] * 100:.1f}%",
                "decision": f"해저드나 OB가 걸린 홀에서는 {CLUB_SAFETY_CHOICES['safer']} 우선, 넓은 홀만 드라이버 유지",
                "goal": "티샷 미스의 절대 손실을 줄이고 다음 샷을 페어웨이/세미러프에서 시작합니다.",
            }
        )
    if recent_summary.get("avg_driver_result_c_rate", 0) >= 0.30:
        strategy_notes.append("드라이버 결과 C 비율이 높아 티샷 목표를 페어웨이 중앙보다 넓은 안전 구역으로 재설정할 필요가 있습니다.")
        strategy_cards.append(
            {
                "title": "드라이버 목표 구역 재설정",
                "trigger": f"최근 드라이버 결과 C {recent_summary['avg_driver_result_c_rate'] * 100:.1f}%",
                "decision": "페어웨이 중앙 대신 가장 넓은 랜딩 구역을 목표로 정하고, 핀 방향보다 스타트 라인을 먼저 고정합니다.",
                "goal": "큰 미스를 줄여 티샷 후 리커버리 빈도를 낮춥니다.",
            }
        )
    if recent_summary.get("avg_gir_from_under_160_rate", 1) <= 0.45:
        strategy_notes.append("160m 이내 GIR 전환율이 낮아 거리별 캐리 기준을 다시 잡고 핀보다 중앙 공략 빈도를 늘리는 편이 좋습니다.")
        strategy_cards.append(
            {
                "title": "160m 이내 공략 전략",
                "trigger": f"최근 160m 이내 GIR {recent_summary['avg_gir_from_under_160_rate'] * 100:.1f}%",
                "decision": "핀 직공보다 그린 중앙 캐리 기준을 기본값으로 두고, 앞핀일수록 한 클럽 더 안전하게 운영합니다.",
                "goal": "버디 찬스보다 GIR 확보를 우선해 보기 확률을 줄입니다.",
            }
        )
    if recent_summary.get("avg_up_and_down_rate", 1) <= 0.30:
        strategy_notes.append("업앤다운 성공률이 낮아 그린 주변에서 파 세이브용 기본 탄도와 런 비율을 고정하는 연습이 우선입니다.")
        strategy_cards.append(
            {
                "title": "그린 주변 기본 플랜",
                "trigger": f"최근 업앤다운 {recent_summary['avg_up_and_down_rate'] * 100:.1f}%",
                "decision": "어려운 로브샷보다 가장 익숙한 탄도 한 가지와 런 비율 한 가지를 우선 선택합니다.",
                "goal": "미스 폭을 줄여 보기를 막고 파 세이브 시도를 늘립니다.",
            }
        )
    if recent_summary.get("avg_three_putt_rate", 0) >= 0.15:
        strategy_notes.append("3퍼트율이 높아 첫 퍼트 목표 거리를 홀컵보다 짧은 안전 원으로 제한하는 운영이 필요합니다.")
        strategy_cards.append(
            {
                "title": "장거리 퍼트 운영",
                "trigger": f"최근 3퍼트율 {recent_summary['avg_three_putt_rate'] * 100:.1f}%",
                "decision": "첫 퍼트는 홀컵이 아니라 1m 이내 안전 원에 붙이는 것을 목표로 둡니다.",
                "goal": "장거리 퍼트의 하한선을 관리해 3퍼트를 억제합니다.",
            }
        )
    if recent_summary.get("avg_back_minus_front_to_par") is not None and recent_summary.get("avg_back_minus_front_to_par", 0) >= 1.0:
        context_notes.append("후반에 전반보다 타수를 더 잃는 흐름이 보여 에너지 분배와 보수적 마무리 전략을 미리 정해두는 편이 좋습니다.")
        context_strategy_cards.append(
            {
                "title": "후반 운영 플랜",
                "trigger": f"최근 Back - Front {recent_summary['avg_back_minus_front_to_par']:.1f}",
                "decision": "후반 시작 3홀은 공격 핀보다 그린 중앙과 넓은 랜딩 구역을 우선 목표로 두고, 무리한 리스크 테이킹을 줄입니다.",
                "goal": "후반 초반에 리듬이 무너지지 않도록 체력과 판단 손실을 함께 억제합니다.",
            }
        )
    if recent_summary.get("avg_closing_16_18_to_par") is not None and recent_summary.get("avg_closing_16_18_to_par", 0) >= 1.5:
        context_notes.append("16-18번 마무리 구간 손실이 커서 공격 홀과 수비 홀을 사전에 구분하는 종료 플랜이 필요합니다.")
        context_strategy_cards.append(
            {
                "title": "마무리 3홀 플랜",
                "trigger": f"최근 16-18 To Par {recent_summary['avg_closing_16_18_to_par']:.1f}",
                "decision": "16-18번은 티샷 타깃과 세이프 클럽 기준을 라운드 전 미리 정하고, 핀 위치에 따라 공략/수비 홀을 구분합니다.",
                "goal": "종반에 한 번의 큰 실수로 스코어가 무너지는 패턴을 줄입니다.",
            }
        )
    if recent_summary.get("birdie_follow_up_count", 0) >= 2 and recent_summary.get("avg_birdie_follow_up_to_par") is not None and recent_summary.get("avg_birdie_follow_up_to_par", 0) > 0.3:
        context_notes.append("버디 직후 다음 홀 성적이 흔들려 공격 템포를 유지하기보다 다음 홀 첫 샷 목표를 더 보수적으로 두는 편이 좋습니다.")
        context_strategy_cards.append(
            {
                "title": "버디 직후 리셋 루틴",
                "trigger": f"버디 직후 다음 홀 To Par {recent_summary['avg_birdie_follow_up_to_par']:.1f}",
                "decision": "버디 직후 홀에서는 핀 공략보다 첫 샷의 안전 구역 확보를 우선하고, 같은 프리샷 루틴으로 템포를 리셋합니다.",
                "goal": "좋은 흐름 뒤 과속으로 생기는 즉시 리바운드 보기를 줄입니다.",
            }
        )
    if recent_summary.get("penalty_recovery_count", 0) >= 2 and recent_summary.get("avg_penalty_recovery_to_par") is not None and recent_summary.get("avg_penalty_recovery_to_par", 0) > 0.5:
        context_notes.append("페널티 직후 회복 홀이 흔들려 다음 홀은 버디 시도보다 파 세이브 기준으로 운영하는 루틴이 필요합니다.")
        context_strategy_cards.append(
            {
                "title": "페널티 직후 회복 플랜",
                "trigger": f"페널티 직후 다음 홀 To Par {recent_summary['avg_penalty_recovery_to_par']:.1f}",
                "decision": "페널티 직후 홀은 버디 회복보다 페어웨이 복귀와 그린 중앙 확보를 우선해 파 세이브 기준으로 운영합니다.",
                "goal": "실수 직후 추가 손실을 막아 더블 이상의 연속 타격을 줄입니다.",
            }
        )
    if recent_summary.get("target_pressure_count", 0) >= 2 and recent_summary.get("avg_target_closing_delta") is not None and recent_summary.get("avg_target_closing_delta", 0) > 0.5:
        hit_rate = recent_summary.get("target_hit_rate")
        context_notes.append("목표 타수 방어 구간에서 마무리 3홀이 무거워 후반 목표선 관리용 보수 플랜을 미리 정해두는 편이 좋습니다.")
        context_strategy_cards.append(
            {
                "title": "목표 타수 방어 플랜",
                "trigger": (
                    f"최근 목표선 적중률 {hit_rate * 100:.1f}%" if hit_rate is not None
                    else f"최근 Closing Delta {recent_summary['avg_target_closing_delta']:.1f}"
                ),
                "decision": "16번홀 시작 전 남은 허용 타수를 계산하고, 목표선을 넘기지 않는 범위에서 티샷 안전 구역과 그린 중앙 공략을 우선합니다.",
                "goal": "80대 초반이나 80대 중반 방어 상황에서 종반 한 홀의 큰 손실을 줄입니다.",
            }
        )

    sample_note = None
    if shot_value_window.get("covered_shots", 0) < RECOMMENDATION_SAMPLE_HIGH_WATERMARK:
        sample_note = "shot value 표본이 아직 작아서 추천은 방향성 위주로 해석하는 것이 안전합니다."

    return {
        "practice_priorities": priorities,
        "strategy_notes": (context_notes + strategy_notes)[:3],
        "strategy_cards": (context_strategy_cards + strategy_cards)[:6],
        "sample_note": sample_note,
        "interpretation_guide": "shot value는 최근 손실 방향을 보기 위한 지표입니다. 총 손실과 평균 손실, 그리고 샷 수를 함께 봐야 과대해석을 줄일 수 있습니다.",
    }


def build_round_explanation_cards(round_metrics, comparison_stats):
    cards = []

    overall_avg_score = (comparison_stats.get("overall") or {}).get("avg_score")
    same_course_avg_score = (comparison_stats.get("same_course") or {}).get("avg_score")
    recent_avg_score = (comparison_stats.get("recent_5") or {}).get("avg_score")

    round_score = (round_metrics.get("summary") or {}).get("score")
    if round_score is None:
        round_score = None

    score_to_par = round_metrics["summary"]["score_to_par"]
    if overall_avg_score is not None and round_metrics["summary"].get("score") is not None:
        delta = round_metrics["summary"]["score"] - overall_avg_score
        cards.append(
            {
                "title": "Overall Context",
                "summary": f"전체 평균 대비 {delta:+.1f}타입니다.",
                "detail": "이번 라운드의 절대 성적을 전체 평균과 비교한 기준선입니다.",
            }
        )
    elif overall_avg_score is not None:
        cards.append(
            {
                "title": "Overall Context",
                "summary": f"전체 평균 스코어는 {overall_avg_score:.1f}타입니다.",
                "detail": "이번 라운드 위치를 해석할 때 기본 비교선으로 봅니다.",
            }
        )

    if same_course_avg_score is not None:
        cards.append(
            {
                "title": "Course Context",
                "summary": f"같은 코스 평균은 {same_course_avg_score:.1f}타입니다.",
                "detail": "코스 난이도 차이를 제외하고 이번 라운드의 상대 성과를 보는 기준입니다.",
            }
        )

    if recent_avg_score is not None:
        cards.append(
            {
                "title": "Recent Form",
                "summary": f"최근 5라운드 평균은 {recent_avg_score:.1f}타입니다.",
                "detail": "최근 컨디션 흐름과 비교해 이번 라운드가 개선인지 후퇴인지 판단합니다.",
            }
        )

    if round_metrics["putting"]["three_putt_rate"] >= 0.15:
        cards.append(
            {
                "title": "Putting Pressure",
                "summary": f"3퍼트율이 {round_metrics['putting']['three_putt_rate'] * 100:.1f}%입니다.",
                "detail": "스코어 손실이 퍼팅 마무리 구간에서 커졌을 가능성이 높습니다.",
            }
        )

    if round_metrics["penalties"]["penalty_strokes_per_round"] >= 2:
        cards.append(
            {
                "title": "Penalty Impact",
                "summary": f"페널티 타수가 {round_metrics['penalties']['penalty_strokes_per_round']}타입니다.",
                "detail": "이번 라운드 스코어 손실의 큰 축이 위험 관리였는지 빠르게 보여줍니다.",
            }
        )

    if round_metrics["short_game"]["up_and_down_rate"] <= 0.3:
        cards.append(
            {
                "title": "Short Game Save",
                "summary": f"업앤다운 성공률이 {round_metrics['short_game']['up_and_down_rate'] * 100:.1f}%입니다.",
                "detail": "그린 적중 실패 후 파 세이브가 얼마나 지켜졌는지 보여주는 핵심 신호입니다.",
            }
        )

    if round_metrics["approach"]["gir_from_under_160_rate"] <= 0.45:
        cards.append(
            {
                "title": "Approach Conversion",
                "summary": f"160m 이내 GIR 전환율이 {round_metrics['approach']['gir_from_under_160_rate'] * 100:.1f}%입니다.",
                "detail": "스코어를 줄일 수 있는 기회 구간을 실제 타수 절감으로 연결했는지 보여줍니다.",
            }
        )

    if score_to_par is not None:
        cards.append(
            {
                "title": "Round Shape",
                "summary": f"이번 라운드의 score to par는 {score_to_par:+d}입니다.",
                "detail": "세부 지표를 보기 전에 라운드 전체 손익 구조를 한 줄로 요약한 값입니다.",
            }
        )

    return cards[:6]


def build_round_loss_cards(shot_value_summary):
    cards = []
    for item in shot_value_summary.get("category_summary", []):
        if item.get("count", 0) <= 0 or item.get("total_shot_value", 0) >= -0.05:
            continue
        cards.append(
            {
                "category": item["category"],
                "title": f"{item['category'].replace('_', ' ').title()} Loss",
                "summary": f"총 손실 {item['total_shot_value']:.2f}타, 평균 {item['avg_shot_value']:.2f}타입니다.",
                "detail": f"{item['count']}샷 기준이며, 이번 라운드 손실 기여가 큰 영역입니다.",
            }
        )

    cards.sort(key=lambda item: item["category"])
    return cards[:3]


def build_round_next_action_card(shot_value_summary, round_metrics=None):
    losses = [
        item for item in shot_value_summary.get("category_summary", [])
        if item.get("count", 0) > 0 and item.get("total_shot_value", 0) < -0.05
    ]
    if not losses:
        return None

    losses.sort(key=lambda item: item["total_shot_value"])
    top_loss = losses[0]
    category = top_loss["category"]
    label = CATEGORY_LABELS.get(category, category)
    guide = PRACTICE_GUIDES.get(category, {})
    menu = _build_training_menu(category, {})
    first_menu = menu[0] if menu else None
    action_row = {
        "category": category,
        "count": top_loss.get("count", 0),
        "total_shot_value": top_loss.get("total_shot_value", 0),
        "trend_direction": "flat",
    }
    context_payload = _build_round_context_payload(category, round_metrics or {})
    priority_action = _build_priority_action(action_row, guide, menu)
    if context_payload["action_suffix"]:
        priority_action = f"{priority_action} {context_payload['action_suffix']}"

    return {
        "category": category,
        "title": "Next Action",
        "summary": f"이번 라운드 손실 1위는 {label}이며 총 {top_loss['total_shot_value']:.2f}타 손실입니다.",
        "focus": guide.get("focus", label),
        "practice": guide.get("practice", ""),
        "urgency_label": "라운드 우선 과제",
        "priority_reason": _build_round_priority_reason(top_loss),
        "priority_action": priority_action,
        "context_note": context_payload["note"],
        "context_subtype": context_payload["subtype"],
        "menu_name": first_menu["name"] if first_menu else None,
        "menu_detail": first_menu["detail"] if first_menu else None,
    }


def build_round_hybrid_action_card(shot_value_summary, recent_summary, recent_shot_value_window, round_metrics=None):
    round_losses = [
        item for item in shot_value_summary.get("category_summary", [])
        if item.get("count", 0) > 0 and item.get("total_shot_value", 0) < -0.05
    ]
    if not round_losses:
        return None

    round_losses.sort(key=lambda item: item["total_shot_value"])
    top_round_loss = round_losses[0]
    category = top_round_loss["category"]
    label = CATEGORY_LABELS.get(category, category)

    recent_losses = [
        item for item in recent_shot_value_window.get("category_summary", [])
        if item.get("count", 0) > 0 and item.get("total_shot_value", 0) < -0.05
    ]
    recent_losses.sort(key=lambda item: item.get("priority_score", _priority_score(item)), reverse=True)
    matching_recent_loss = next((item for item in recent_losses if item["category"] == category), None)
    recurring = any(item["category"] == category for item in recent_losses[:3])

    menu = _build_training_menu(category, recent_summary)
    first_menu = menu[0] if menu else None
    guide = PRACTICE_GUIDES.get(category, {})

    if recurring:
        summary = f"{label} 손실이 이번 라운드와 최근 10라운드 모두에서 반복되고 있습니다."
        detail = "단발성 실수보다 반복 패턴에 가까워 다음 연습 우선순위로 바로 가져가는 편이 좋습니다."
    else:
        summary = f"{label} 손실이 이번 라운드에서는 가장 컸지만 최근 10라운드의 핵심 패턴은 아닙니다."
        detail = "최근 추세보다 이번 라운드 특이점일 가능성이 있어 다음 2-3라운드에서 재발 여부를 먼저 확인하는 편이 안전합니다."

    priority_row = matching_recent_loss or {
        "category": category,
        "count": top_round_loss.get("count", 0),
        "total_shot_value": top_round_loss.get("total_shot_value", 0),
        "trend_direction": "flat",
        "trend_label": "보합",
    }
    context_payload = _build_round_context_payload(category, round_metrics or {})
    priority_action = _build_priority_action(priority_row, guide, menu)
    if context_payload["action_suffix"]:
        priority_action = f"{priority_action} {context_payload['action_suffix']}"

    return {
        "category": category,
        "title": "Round + Trend Action",
        "summary": summary,
        "detail": detail,
        "urgency_label": "반복 추세 연동" if recurring else "재발 확인 필요",
        "priority_reason": (
            _build_priority_reason(priority_row)
            if matching_recent_loss else _build_round_priority_reason(top_round_loss)
        ),
        "priority_action": priority_action,
        "context_note": context_payload["note"],
        "context_subtype": context_payload["subtype"],
        "menu_name": first_menu["name"] if first_menu else None,
        "menu_detail": first_menu["detail"] if first_menu else None,
        "is_recurring": recurring,
    }


def build_trend_action_cards(recent_summary, recent_shot_value_window, limit=3):
    recent_losses = [
        item for item in recent_shot_value_window.get("category_summary", [])
        if item.get("count", 0) > 0 and item.get("total_shot_value", 0) < -0.05
    ]
    if not recent_losses:
        return []

    recent_losses.sort(key=lambda item: item.get("priority_score", _priority_score(item)), reverse=True)
    cards = []
    for index, loss in enumerate(recent_losses[:limit], start=1):
        category = loss["category"]
        label = CATEGORY_LABELS.get(category, category)
        context_payload = _build_recent_context_payload(category, recent_summary, loss)
        menu = _build_contextual_menu(category, recent_summary, loss, context_payload)
        first_menu = menu[0] if menu else None
        guide = PRACTICE_GUIDES.get(category, {})
        cards.append(
            {
                "category": category,
                "rank": index,
                "title": f"Priority {index}",
                "summary": f"최근 {recent_shot_value_window.get('window', 10)}라운드 반복 손실 {index}위는 {label}이며 총 {loss['total_shot_value']:.2f}타입니다.",
                "detail": "최근 추세 기준으로 먼저 줄여야 할 반복 손실 영역입니다.",
                "trend_direction": loss.get("trend_direction", "flat"),
                "trend_label": loss.get("trend_label", "보합"),
                "trend_delta": loss.get("trend_delta", 0.0),
                "priority_score": loss.get("priority_score", _priority_score(loss)),
                "urgency_label": loss.get("urgency_label", _priority_urgency(loss)),
                "priority_reason": _build_priority_reason(loss),
                "priority_action": (
                    f"{_build_priority_action(loss, guide, menu)} {context_payload['action_suffix']}"
                    if context_payload["action_suffix"] else _build_priority_action(loss, guide, menu)
                ),
                "context_subtype": context_payload["subtype"],
                "context_note": context_payload["note"],
                "menu_name": first_menu["name"] if first_menu else None,
                "menu_detail": first_menu["detail"] if first_menu else None,
            }
        )
    return cards


def _build_training_menu(category, recent_summary):
    if category == "off_the_tee":
        return [
            {
                "name": "스타트 라인 10구",
                "detail": "드라이버 5구, 우드/유틸리티 5구로 동일 타깃에 시작선만 점검합니다.",
            },
            {
                "name": "세이프 클럽 비교",
                "detail": "좁은 홀 가정에서 드라이버와 대체 클럽의 탄착군 폭을 비교합니다.",
            },
        ]
    if category == "approach":
        return [
            {
                "name": "120-160m 캐리 매트릭스",
                "detail": "7번아이언부터 웨지까지 10m 단위 목표에 캐리 편차를 기록합니다.",
            },
            {
                "name": "중앙 공략 9구",
                "detail": f"GIR 전환율 {recent_summary.get('avg_gir_from_under_160_rate', 0) * 100:.1f}%를 기준으로 핀보다 중앙 공략 성공률을 먼저 올립니다.",
            },
        ]
    if category == "short_game":
        return [
            {
                "name": "10-30m 런 비율 고정",
                "detail": "한 가지 탄도와 두 가지 런아웃 패턴만 반복해 업앤다운 루틴을 단순화합니다.",
            },
            {
                "name": "벙커 포함 파 세이브 12구",
                "detail": "벙커 6구, 러프 6구로 2퍼트 이내 마무리 확률을 체크합니다.",
            },
        ]
    if category == "putting":
        return [
            {
                "name": "6-12m 래그 퍼트 12구",
                "detail": "첫 퍼트를 1m 안전 원 안에 두는 성공률을 기록합니다.",
            },
            {
                "name": "1-2m 마무리 퍼트 20구",
                "detail": "장거리 퍼트 이후 남는 거리 기준으로 마무리 확률을 고정합니다.",
            },
        ]
    if category == "recovery":
        return [
            {
                "name": "탈출 우선 시뮬레이션",
                "detail": "트러블 샷 10회에서 그린 공략 대신 안전 복귀 성공률을 먼저 체크합니다.",
            },
            {
                "name": "리커버리 후 3번째 샷 준비",
                "detail": "복귀 위치를 다음 거리 구간이 쉬운 지점으로 설정하는 연습을 합니다.",
            },
        ]
    if category == "penalty_impact":
        return [
            {
                "name": "위험 홀 의사결정 복기",
                "detail": "최근 페널티가 난 홀을 다시 보며 목표 지점과 클럽 선택을 재설계합니다.",
            },
            {
                "name": "세이프 라인 선언 루틴",
                "detail": "샷 전 한 문장으로 안전 구역과 미스 허용 방향을 선언하고 실행합니다.",
            },
        ]
    return []
