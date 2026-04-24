from src import db_loader


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params or []))

    def fetchall(self):
        return list(self.rows)

    def close(self):
        return None


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self, dictionary=True):
        return _FakeCursor(self.rows)

    def close(self):
        return None


def test_split_companions_supports_comma_and_space_separated_names():
    assert db_loader._split_companions("Kim, Park Lee") == ["Kim", "Park", "Lee"]
    assert db_loader._split_companions("김철수 박영희") == ["김철수", "박영희"]
    assert db_loader._split_companions(None) == []


def test_get_unique_companions_returns_individual_names(monkeypatch):
    rows = [
        {"coplayers": "Kim, Park"},
        {"coplayers": "Lee Park"},
        {"coplayers": "Kim"},
    ]
    monkeypatch.setattr(db_loader, "get_db_connection", lambda: _FakeConnection(rows))

    companions = db_loader.get_unique_companions()

    assert companions == ["Kim", "Lee", "Park"]


def test_get_filtered_rounds_filters_by_exact_companion_token(monkeypatch):
    rows = [
        {"id": 1, "coplayers": "Kim Park", "playdate": None, "gcname": "A", "score": 80, "gir": 50},
        {"id": 2, "coplayers": "Kimura", "playdate": None, "gcname": "B", "score": 82, "gir": 45},
        {"id": 3, "coplayers": "Park, Choi", "playdate": None, "gcname": "C", "score": 84, "gir": 40},
    ]
    monkeypatch.setattr(db_loader, "get_db_connection", lambda: _FakeConnection(rows))

    filtered = db_loader.get_filtered_rounds(companion="Kim")

    assert [row["id"] for row in filtered] == [1]


def test_get_rounds_for_trend_analysis_filters_by_exact_companion_token(monkeypatch):
    rows = [
        {"round_id": 1, "coplayers": "Kim Park", "playdate": "2026-01-01"},
        {"round_id": 2, "coplayers": "Kimura", "playdate": "2026-01-02"},
        {"round_id": 3, "coplayers": "Park, Choi", "playdate": "2026-01-03"},
    ]
    monkeypatch.setattr(db_loader, "get_db_connection", lambda: _FakeConnection(rows))

    filtered = db_loader.get_rounds_for_trend_analysis(companion="Park")

    assert [row["round_id"] for row in filtered] == [1, 3]
