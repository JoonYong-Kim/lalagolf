from src.recommendations import (
    build_recommendations,
    build_recent_shot_value_window,
    build_round_explanation_cards,
    build_round_hybrid_action_card,
    build_round_loss_cards,
    build_round_next_action_card,
    build_trend_action_cards,
)


def test_build_recent_shot_value_window():
    raw_trend_data = [
        {"round_id": 1, "playdate": "2026-04-01"},
        {"round_id": 2, "playdate": "2026-04-10"},
        {"round_id": 3, "playdate": "2026-04-15"},
    ]
    shot_value_by_round = {
        1: {
            "covered_shots": 10,
            "category_summary": [
                {"category": "putting", "count": 4, "total_shot_value": -0.5, "avg_shot_value": -0.125},
            ],
        },
        2: {
            "covered_shots": 12,
            "category_summary": [
                {"category": "approach", "count": 5, "total_shot_value": -1.2, "avg_shot_value": -0.24},
            ],
        },
        3: {
            "covered_shots": 8,
            "category_summary": [
                {"category": "putting", "count": 3, "total_shot_value": -0.15, "avg_shot_value": -0.05},
            ],
        },
    }

    window = build_recent_shot_value_window(raw_trend_data, shot_value_by_round, window=3)

    assert window["round_count"] == 3
    assert window["covered_shots"] == 30
    assert window["category_summary"][0]["category"] == "approach"
    assert window["category_summary"][0]["trend_direction"] == "flat"
    assert window["category_summary"][1]["category"] == "putting"
    assert window["category_summary"][1]["trend_direction"] == "improving"
    assert window["category_summary"][1]["trend_label"] == "개선"


def test_build_recommendations():
    recent_summary = {
        "avg_driver_penalty_rate": 0.15,
        "avg_driver_result_c_rate": 0.33,
        "avg_gir_from_under_160_rate": 0.40,
        "avg_up_and_down_rate": 0.25,
        "avg_three_putt_rate": 0.18,
        "avg_back_minus_front_to_par": 1.2,
        "avg_closing_16_18_to_par": 1.8,
        "birdie_follow_up_count": 3,
        "avg_birdie_follow_up_to_par": 0.6,
        "penalty_recovery_count": 2,
        "avg_penalty_recovery_to_par": 0.8,
        "target_pressure_count": 4,
        "target_hit_rate": 0.5,
        "avg_target_closing_delta": 1.2,
    }
    shot_value_window = {
        "window": 10,
        "covered_shots": 28,
        "category_summary": [
            {"category": "approach", "count": 20, "total_shot_value": -2.4, "avg_shot_value": -0.12, "trend_direction": "worsening", "trend_label": "악화", "priority_score": 3.55, "urgency_label": "즉시 개입"},
            {"category": "putting", "count": 18, "total_shot_value": -1.5, "avg_shot_value": -0.08, "trend_direction": "improving", "trend_label": "개선", "priority_score": 1.61, "urgency_label": "유지 추적"},
            {"category": "off_the_tee", "count": 14, "total_shot_value": -1.0, "avg_shot_value": -0.07, "trend_direction": "flat", "trend_label": "보합", "priority_score": 1.48, "urgency_label": "우선 점검"},
            {"category": "short_game", "count": 10, "total_shot_value": 0.2, "avg_shot_value": 0.02, "trend_direction": "improving", "trend_label": "개선", "priority_score": 0.15, "urgency_label": "유지 추적"},
        ],
    }

    recommendations = build_recommendations(recent_summary, shot_value_window)

    assert len(recommendations["practice_priorities"]) == 3
    assert recommendations["practice_priorities"][0]["category"] == "approach"
    assert recommendations["practice_priorities"][0]["urgency_label"] == "즉시 개입"
    assert recommendations["practice_priorities"][0]["context_subtype"] == "거리 오차형"
    assert "현재 판단은 즉시 개입입니다." in recommendations["practice_priorities"][0]["priority_reason"]
    assert "160m 이내 GIR 40.0%" in recommendations["practice_priorities"][0]["context_note"]
    assert "이번 주에는" in recommendations["practice_priorities"][0]["priority_action"]
    assert "드릴부터 시작하세요." in recommendations["practice_priorities"][0]["priority_action"]
    assert "첫 연습 블록에서 우선 점검하고 다음 라운드까지 계속 추적하세요." in recommendations["practice_priorities"][0]["priority_action"]
    assert "클럽별 캐리 기준을 먼저 다시 고정하세요." in recommendations["practice_priorities"][0]["priority_action"]
    assert recommendations["practice_priorities"][0]["menu"][0]["name"] == "캐리 편차 10m 매트릭스"
    assert recommendations["practice_priorities"][0]["menu"]
    assert recommendations["practice_priorities"][0]["sample"]["level"] in {"low", "medium", "high"}
    assert recommendations["practice_priorities"][0]["reasons"]
    assert recommendations["strategy_notes"]
    assert recommendations["strategy_cards"]
    assert recommendations["sample_note"] is not None
    assert any("후반" in note or "버디 직후" in note or "페널티 직후" in note for note in recommendations["strategy_notes"])
    assert any("후반 운영 플랜" == card["title"] for card in recommendations["strategy_cards"])
    assert any("버디 직후 리셋 루틴" == card["title"] for card in recommendations["strategy_cards"])
    assert any("페널티 직후 회복 플랜" == card["title"] for card in recommendations["strategy_cards"])
    assert any("목표 타수 방어 플랜" == card["title"] for card in recommendations["strategy_cards"])


def test_build_recommendations_prioritizes_worsening_trend():
    recent_summary = {"avg_driver_result_c_rate": 0.35}
    shot_value_window = {
        "window": 10,
        "covered_shots": 24,
        "category_summary": [
            {"category": "putting", "count": 12, "total_shot_value": -1.4, "avg_shot_value": -0.12, "trend_direction": "improving", "trend_label": "개선", "priority_score": 1.39, "urgency_label": "유지 추적"},
            {"category": "off_the_tee", "count": 10, "total_shot_value": -1.0, "avg_shot_value": -0.10, "trend_direction": "worsening", "trend_label": "악화", "priority_score": 1.95, "urgency_label": "즉시 개입"},
        ],
    }

    recommendations = build_recommendations(recent_summary, shot_value_window)

    assert recommendations["practice_priorities"][0]["category"] == "off_the_tee"
    assert recommendations["practice_priorities"][0]["trend_direction"] == "worsening"
    assert recommendations["practice_priorities"][0]["context_subtype"] == "큰 미스 누적형"
    assert "최근 흐름 악화" in recommendations["practice_priorities"][0]["priority_reason"]
    assert "최근 10라운드 티샷 반복 손실은 -1.00타입니다." == recommendations["practice_priorities"][0]["message"]
    assert "반복되는 손실을 먼저 끊어야 합니다." in recommendations["practice_priorities"][0]["priority_action"]
    assert "짧은 교정 루틴으로 먼저 재현 여부를 확인하세요." in recommendations["practice_priorities"][0]["priority_action"]
    assert "가장 넓은 랜딩 구역을 기준으로 스타트 라인만 먼저 안정화하세요." in recommendations["practice_priorities"][0]["priority_action"]
    assert recommendations["practice_priorities"][0]["menu"][0]["name"] == "와이드 랜딩 10구"


def test_build_recommendations_personalizes_flat_and_improving_actions():
    recent_summary = {
        "avg_driver_penalty_rate": 0.0,
        "avg_driver_result_c_rate": 0.0,
        "avg_three_putt_rate": 0.2,
        "avg_putts": 2.1,
    }
    shot_value_window = {
        "window": 10,
        "covered_shots": 26,
        "category_summary": [
            {"category": "off_the_tee", "count": 14, "total_shot_value": -1.1, "avg_shot_value": -0.08, "trend_direction": "flat", "trend_label": "보합", "priority_score": 1.58, "urgency_label": "우선 점검"},
            {"category": "putting", "count": 22, "total_shot_value": -0.9, "avg_shot_value": -0.04, "trend_direction": "improving", "trend_label": "개선", "priority_score": 1.09, "urgency_label": "유지 추적"},
        ],
    }

    recommendations = build_recommendations(recent_summary, shot_value_window)

    flat_item = recommendations["practice_priorities"][0]
    improving_item = recommendations["practice_priorities"][1]

    assert flat_item["category"] == "off_the_tee"
    assert "짧은 체크 세션으로 현재 패턴이 반복인지 먼저 확인하세요." in flat_item["priority_action"]
    assert improving_item["category"] == "putting"
    assert improving_item["context_subtype"] == "거리감 손실형"
    assert "주간 루틴 후반에 짧게 배치해 흐름만 유지하면 충분합니다." in improving_item["priority_action"]
    assert improving_item["menu"][0]["name"] == "8-12m 세이프 존 래그 12구"


def test_build_round_explanation_cards():
    round_metrics = {
        "summary": {"score": 84, "score_to_par": 12},
        "putting": {"three_putt_rate": 0.2},
        "penalties": {"penalty_strokes_per_round": 3},
        "short_game": {"up_and_down_rate": 0.2},
        "approach": {"gir_from_under_160_rate": 0.35},
    }
    comparison_stats = {
        "overall": {"avg_score": 87.5},
        "same_course": {"avg_score": 85.0},
        "recent_5": {"avg_score": 86.2},
    }

    cards = build_round_explanation_cards(round_metrics, comparison_stats)

    assert cards
    assert len(cards) >= 5
    assert any(card["title"] == "Overall Context" for card in cards)
    assert any(card["title"] == "Penalty Impact" for card in cards)


def test_build_round_loss_cards():
    shot_value_summary = {
        "category_summary": [
            {"category": "approach", "count": 12, "total_shot_value": -1.8, "avg_shot_value": -0.15},
            {"category": "putting", "count": 10, "total_shot_value": -0.8, "avg_shot_value": -0.08},
            {"category": "off_the_tee", "count": 8, "total_shot_value": -0.4, "avg_shot_value": -0.05},
            {"category": "short_game", "count": 6, "total_shot_value": 0.1, "avg_shot_value": 0.02},
        ]
    }

    cards = build_round_loss_cards(shot_value_summary)

    assert len(cards) == 3
    assert any(card["category"] == "approach" for card in cards)
    assert any(card["category"] == "putting" for card in cards)


def test_build_round_next_action_card():
    shot_value_summary = {
        "category_summary": [
            {"category": "approach", "count": 12, "total_shot_value": -1.8, "avg_shot_value": -0.15},
            {"category": "putting", "count": 10, "total_shot_value": -0.8, "avg_shot_value": -0.08},
        ]
    }
    round_metrics = {
        "approach": {"gir_from_under_160_rate": 0.35, "under_160_average_error": 18.0},
        "putting": {"three_putt_rate": 0.22},
        "short_game": {"up_and_down_rate": 0.25},
        "tee_shots": {"driver_result_c_rate": 0.2},
        "penalties": {"penalty_strokes_per_round": 2},
    }

    card = build_round_next_action_card(shot_value_summary, round_metrics)

    assert card is not None
    assert card["category"] == "approach"
    assert card["title"] == "Next Action"
    assert card["urgency_label"] == "라운드 우선 과제"
    assert card["context_subtype"] == "거리 오차형"
    assert "이번 라운드 12샷 기준 총 손실 1.80타입니다." in card["priority_reason"]
    assert "160m 이내 GIR 전환율이 35.0%" in card["context_note"]
    assert "이번 주에는" in card["priority_action"]
    assert "클럽별 캐리 기준을 다시 고정하는 드릴을 먼저 두세요." in card["priority_action"]
    assert card["menu_name"]


def test_build_round_hybrid_action_card():
    shot_value_summary = {
        "category_summary": [
            {"category": "approach", "count": 12, "total_shot_value": -1.8, "avg_shot_value": -0.15},
            {"category": "putting", "count": 10, "total_shot_value": -0.8, "avg_shot_value": -0.08},
        ]
    }
    recent_summary = {"avg_gir_from_under_160_rate": 0.4}
    recent_shot_value_window = {
        "category_summary": [
            {"category": "approach", "count": 30, "total_shot_value": -3.0, "avg_shot_value": -0.10},
            {"category": "putting", "count": 20, "total_shot_value": -1.0, "avg_shot_value": -0.05},
        ]
    }
    round_metrics = {
        "approach": {"gir_from_under_160_rate": 0.35, "under_160_average_error": 18.0},
        "putting": {"three_putt_rate": 0.22},
        "short_game": {"up_and_down_rate": 0.25},
        "tee_shots": {"driver_result_c_rate": 0.2},
        "penalties": {"penalty_strokes_per_round": 2},
    }

    card = build_round_hybrid_action_card(shot_value_summary, recent_summary, recent_shot_value_window, round_metrics)

    assert card is not None
    assert card["category"] == "approach"
    assert card["title"] == "Round + Trend Action"
    assert card["is_recurring"] is True
    assert card["urgency_label"] == "반복 추세 연동"
    assert card["context_subtype"] == "거리 오차형"
    assert "현재 판단은" in card["priority_reason"]
    assert "160m 이내 GIR 전환율이 35.0%" in card["context_note"]
    assert "이번 주에는" in card["priority_action"]
    assert "클럽별 캐리 기준을 다시 고정하는 드릴을 먼저 두세요." in card["priority_action"]


def test_build_trend_action_cards():
    recent_summary = {"avg_gir_from_under_160_rate": 0.4}
    recent_shot_value_window = {
        "window": 10,
        "category_summary": [
            {"category": "approach", "count": 30, "total_shot_value": -3.0, "avg_shot_value": -0.10, "trend_direction": "worsening", "trend_label": "악화", "trend_delta": -0.06},
            {"category": "putting", "count": 20, "total_shot_value": -1.0, "avg_shot_value": -0.05, "trend_direction": "improving", "trend_label": "개선", "trend_delta": 0.04},
            {"category": "off_the_tee", "count": 18, "total_shot_value": -0.8, "avg_shot_value": -0.04, "trend_direction": "flat", "trend_label": "보합", "trend_delta": 0.0},
        ]
    }

    cards = build_trend_action_cards(recent_summary, recent_shot_value_window)

    assert len(cards) == 3
    assert cards[0]["category"] == "approach"
    assert cards[0]["title"] == "Priority 1"
    assert cards[0]["trend_direction"] == "worsening"
    assert cards[0]["trend_label"] == "악화"
    assert cards[0]["urgency_label"] == "즉시 개입"
    assert cards[0]["context_subtype"] == "거리 오차형"
    assert "현재 판단은 즉시 개입입니다." in cards[0]["priority_reason"]
    assert "이번 주에는" in cards[0]["priority_action"]
    assert "연습 시작 구간을 이 항목 교정에 가장 먼저 배정하세요." in cards[0]["priority_action"]
    assert "클럽별 캐리 기준을 먼저 다시 고정하세요." in cards[0]["priority_action"]
    assert "160m 이내 GIR 40.0%" in cards[0]["context_note"]
    assert cards[0]["menu_name"] == "캐리 편차 10m 매트릭스"
    assert cards[0]["menu_name"]


def test_build_trend_action_cards_prioritize_worsening_over_improving():
    recent_summary = {}
    recent_shot_value_window = {
        "window": 10,
        "category_summary": [
            {"category": "approach", "count": 22, "total_shot_value": -1.8, "avg_shot_value": -0.08, "trend_direction": "improving", "trend_label": "개선", "trend_delta": 0.05, "priority_score": 1.95, "urgency_label": "유지 추적"},
            {"category": "off_the_tee", "count": 12, "total_shot_value": -1.4, "avg_shot_value": -0.12, "trend_direction": "worsening", "trend_label": "악화", "trend_delta": -0.06, "priority_score": 2.39, "urgency_label": "즉시 개입"},
        ],
    }

    cards = build_trend_action_cards(recent_summary, recent_shot_value_window)

    assert cards[0]["category"] == "off_the_tee"
    assert cards[0]["urgency_label"] == "즉시 개입"
