from datetime import datetime

from src.webapp import app
from src.webapp import routes


def _analysis_context(label, round_count, selected_window="all"):
    return {
        "recent_summary": {
            "window": round_count,
            "avg_score": None,
            "avg_score_to_par": None,
            "avg_gir": None,
            "avg_three_putt_rate": None,
            "avg_scrambling_rate": None,
            "avg_penalty_strokes": None,
            "avg_up_and_down_rate": None,
            "avg_driver_penalty_rate": None,
            "avg_driver_result_c_rate": None,
            "avg_gir_from_under_160_rate": None,
            "avg_putts": None,
            "avg_tee_shot_penalty_rate": None,
            "insights": [],
        },
        "recommendations": {
            "practice_priorities": [],
            "strategy_notes": [],
            "strategy_cards": [],
            "sample_note": None,
            "interpretation_guide": None,
        },
        "trend_action_cards": [],
        "analysis_scope": {
            "label": label,
            "round_count": round_count,
            "selected_window": selected_window,
            "window_label": "선택 범위 전체",
            "is_filtered": True,
        },
    }


def test_home_uses_selected_year_and_analysis_window(monkeypatch):
    captured = {}

    monkeypatch.setattr(routes, "init_connection_pool", lambda config: None)
    monkeypatch.setattr(
        routes,
        "get_filtered_rounds",
        lambda **kwargs: [
            {"playdate": datetime(2025, 1, 10), "score": 83, "gir": 44.4},
            {"playdate": datetime(2025, 2, 15), "score": 81, "gir": 50.0},
        ],
    )
    monkeypatch.setattr(routes, "get_unique_years", lambda: [2025, 2024])
    monkeypatch.setattr(routes, "get_yearly_round_statistics", lambda: [])

    def fake_build_analysis_context(selected_year='all', selected_window='all', selected_golf_course='all', selected_companion='all', selected_round_ids=None):
        captured["selected_year"] = selected_year
        captured["selected_window"] = selected_window
        captured["selected_golf_course"] = selected_golf_course
        captured["selected_companion"] = selected_companion
        captured["selected_round_ids"] = selected_round_ids
        return _analysis_context("2025년 / 최근 5라운드", 2, selected_window="5")

    monkeypatch.setattr(routes, "_build_analysis_context", fake_build_analysis_context)

    with app.test_client() as client:
        response = client.get("/?year=2025&analysis_window=5")

    assert response.status_code == 200
    assert captured == {
        "selected_year": "2025",
        "selected_window": "5",
        "selected_golf_course": "all",
        "selected_companion": "all",
        "selected_round_ids": None,
    }
    assert "현재 분석 범위: 2025년 / 최근 5라운드 (2라운드)" in response.get_data(as_text=True)


def test_analysis_uses_list_filters_for_analysis(monkeypatch):
    captured = {}

    monkeypatch.setattr(routes, "init_connection_pool", lambda config: None)
    monkeypatch.setattr(
        routes,
        "get_filtered_rounds",
        lambda **kwargs: [
            {
                "id": 7,
                "playdate": datetime(2025, 3, 1),
                "gcname": "Sky72",
                "coplayers": "Kim",
                "score": 82,
                "gir": 47.1,
            }
        ],
    )
    monkeypatch.setattr(routes, "get_unique_years", lambda: [2025, 2024])
    monkeypatch.setattr(routes, "get_unique_golf_courses", lambda: ["Sky72"])
    monkeypatch.setattr(routes, "get_unique_companions", lambda: ["Kim"])

    def fake_build_analysis_context(selected_year='all', selected_window='all', selected_golf_course='all', selected_companion='all', selected_round_ids=None):
        captured["selected_year"] = selected_year
        captured["selected_window"] = selected_window
        captured["selected_golf_course"] = selected_golf_course
        captured["selected_companion"] = selected_companion
        captured["selected_round_ids"] = selected_round_ids
        return _analysis_context("2025년 / Sky72 / 동반자 Kim / 최근 10라운드", 1, selected_window="10")

    monkeypatch.setattr(routes, "_build_analysis_context", fake_build_analysis_context)

    with app.test_client() as client:
        response = client.get("/analysis?year=2025&golf_course=Sky72&companion=Kim&analysis_window=10")

    assert response.status_code == 200
    assert captured == {
        "selected_year": "2025",
        "selected_window": "10",
        "selected_golf_course": "Sky72",
        "selected_companion": "Kim",
        "selected_round_ids": [],
    }
    body = response.get_data(as_text=True)
    assert "현재 분석 범위: 2025년 / Sky72 / 동반자 Kim / 최근 10라운드 (1라운드)" in body
    assert "analysis_window=10" in body


def test_analysis_uses_selected_round_ids_for_analysis(monkeypatch):
    captured = {}

    monkeypatch.setattr(routes, "init_connection_pool", lambda config: None)
    monkeypatch.setattr(
        routes,
        "get_filtered_rounds",
        lambda **kwargs: [
            {
                "id": 7,
                "playdate": datetime(2025, 3, 1),
                "gcname": "Sky72",
                "coplayers": "Kim",
                "score": 82,
                "gir": 47.1,
            },
            {
                "id": 9,
                "playdate": datetime(2025, 4, 1),
                "gcname": "Sky72",
                "coplayers": "Park",
                "score": 79,
                "gir": 55.0,
            },
        ],
    )
    monkeypatch.setattr(routes, "get_unique_years", lambda: [2025, 2024])
    monkeypatch.setattr(routes, "get_unique_golf_courses", lambda: ["Sky72"])
    monkeypatch.setattr(routes, "get_unique_companions", lambda: ["Kim", "Park"])

    def fake_build_analysis_context(selected_year='all', selected_window='all', selected_golf_course='all', selected_companion='all', selected_round_ids=None):
        captured["selected_year"] = selected_year
        captured["selected_window"] = selected_window
        captured["selected_golf_course"] = selected_golf_course
        captured["selected_companion"] = selected_companion
        captured["selected_round_ids"] = selected_round_ids
        return _analysis_context("선택 라운드 2개 / 최근 5라운드", 2, selected_window="5")

    monkeypatch.setattr(routes, "_build_analysis_context", fake_build_analysis_context)

    with app.test_client() as client:
        response = client.get("/analysis?analysis_window=5&round_ids=7&round_ids=9")

    assert response.status_code == 200
    assert captured == {
        "selected_year": "all",
        "selected_window": "5",
        "selected_golf_course": "all",
        "selected_companion": "all",
        "selected_round_ids": [7, 9],
    }
    body = response.get_data(as_text=True)
    assert "현재 분석 범위: 선택 라운드 2개 / 최근 5라운드 (2라운드)" in body
    assert 'value="7"' in body
    assert 'value="9"' in body


def test_rounds_page_links_to_analysis(monkeypatch):
    monkeypatch.setattr(routes, "init_connection_pool", lambda config: None)
    monkeypatch.setattr(
        routes,
        "get_filtered_rounds",
        lambda **kwargs: [
            {
                "id": 7,
                "playdate": datetime(2025, 3, 1),
                "gcname": "Sky72",
                "coplayers": "Kim",
                "score": 82,
                "gir": 47.1,
            }
        ],
    )
    monkeypatch.setattr(routes, "get_unique_years", lambda: [2025, 2024])
    monkeypatch.setattr(routes, "get_unique_golf_courses", lambda: ["Sky72"])
    monkeypatch.setattr(routes, "get_unique_companions", lambda: ["Kim"])

    with app.test_client() as client:
        response = client.get("/rounds?year=2025&golf_course=Sky72&companion=Kim")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "분석으로 이동" in body
    assert "/analysis?year=2025&amp;golf_course=Sky72&amp;companion=Kim" in body
