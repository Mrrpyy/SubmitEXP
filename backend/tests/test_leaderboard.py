from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.api import leaderboard
from app.api.auth import UserInfo, get_current_user
from app.main import app
STUDENT = UserInfo(user_id=3, username='student', email='student@example.com', role='student')
ADMIN = UserInfo(user_id=1, username='admin', email='admin@example.com', role='admin')
ROWS = [{'user_id': 2, 'username': 'amber', 'total_points': Decimal('300'), 'submissions_recorded': 4},
    {'user_id': 3, 'username': 'blair', 'total_points': 300, 'submissions_recorded': 3},
    {'user_id': 5, 'username': 'casey', 'total_points': 120, 'submissions_recorded': 2},]
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def login_as(user):
    app.dependency_overrides[get_current_user] = lambda: user

def test_login_required(client, monkeypatch):
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: pytest.fail('DB must not be read'))
    assert client.get('/leaderboard').status_code == 401

def test_student_sees_ranks_and_own_position(client, monkeypatch):
    login_as(STUDENT)
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: (7, ROWS, 1, 300))
    result = client.get('/leaderboard')
    assert result.status_code == 200
    body = result.json()
    assert body['total_students'] == 7
    assert [r['rank'] for r in body['leaders']] == [1, 1, 3]
    assert [r['current_level'] for r in body['leaders']] == [4, 4, 2]
    assert body['your_rank'] == 1
    assert body['your_total_points'] == 300
    assert 'email' not in result.text
    assert 'password' not in result.text

def test_student_outside_top_ten_still_has_rank(client, monkeypatch):
    login_as(STUDENT)
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: (42, ROWS, 28, 9))
    body = client.get('/leaderboard').json()
    assert body['your_rank'] == 28
    assert body['your_total_points'] == 9

def test_admin_can_see_leaders_but_not_student_rank(client, monkeypatch):
    login_as(ADMIN)
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: (7, ROWS, None, None))
    body = client.get('/leaderboard').json()
    assert body['your_rank'] is None
    assert body['your_total_points'] is None
    assert len(body['leaders']) == 3

def test_new_users_without_points_can_rank(client, monkeypatch):
    login_as(STUDENT)
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: (1, [dict(user_id=3, username='student', total_points=0, submissions_recorded=0)], 1, 0))
    body = client.get('/leaderboard').json()
    assert body['leaders'][0]['current_level'] == 1
    assert body['leaders'][0]['total_points'] == 0

def test_no_students(client, monkeypatch):
    login_as(ADMIN)
    monkeypatch.setattr(leaderboard, 'load_leaderboard', lambda *args: (0, [], None, None))
    body = client.get('/leaderboard').json()
    assert body['leaders'] == []
    assert body['total_students'] == 0

def test_database_error_returns_503(client, monkeypatch):
    login_as(STUDENT)
    def fail(*args):
        raise SQLAlchemyError('secret db details')
    monkeypatch.setattr(leaderboard, 'load_leaderboard', fail)
    result = client.get('/leaderboard')
    assert result.status_code == 503
    assert 'secret' not in result.text

def test_student_authorization_forwarded_to_loader(client, monkeypatch):
    login_as(STUDENT)
    received = []
    def fake_loader(user_id, role):
        received.append((user_id, role))
        return 0, [], None, None
    monkeypatch.setattr(leaderboard, 'load_leaderboard', fake_loader)
    client.get('/leaderboard')
    assert received == [(3, 'student')]

def test_database_query_filters_to_students_and_computes_own_rank(monkeypatch):
    executed = []
    class Result:
        def __init__(self, n):
            self.n = n

        def scalar_one(self):
            return {0: 5, 3: 2}[self.n]

        def mappings(self):
            return self

        def all(self):
            return ROWS

        def first(self):
            return {'total_points': Decimal('120')}

    class Connection:
        def execute(self, query, params=None):
            executed.append((str(query), params))
            return Result(len(executed) - 1)

    class Engine:
        def connect(self):
            class Context:
                def __enter__(self):
                    return Connection()

                def __exit__(self, *args):
                    return False
            return Context()
    monkeypatch.setattr(leaderboard, 'get_engine', lambda: Engine())
    total, rows, rank, points = leaderboard.load_leaderboard(3, 'student')
    assert (total, rank, points) == (5, 3, 120)
    assert rows == ROWS
    assert "WHERE u.role = 'student'" in executed[1][0]
    assert 'ORDER BY total_points DESC' in executed[1][0]
    assert executed[1][1] == {'limit': 10}
    assert executed[2][1] == {'user_id': 3}
    assert executed[3][1] == {'total_points': 120}
    assert 'email' not in executed[1][0].lower()
    assert 'password' not in executed[1][0].lower()

def test_database_does_not_query_own_rank_for_admin(monkeypatch):
    executed = []
    class Result:
        def __init__(self, n):
            self.n = n

        def scalar_one(self):
            return 2

        def mappings(self):
            return self

        def all(self):
            return ROWS[:2]

    class Connection:
        def execute(self, query, params=None):
            executed.append(str(query))
            return Result(len(executed) - 1)

    class Engine:
        def connect(self):
            class Context:
                def __enter__(self):
                    return Connection()

                def __exit__(self, *args):
                    return False
            return Context()
    monkeypatch.setattr(leaderboard, 'get_engine', lambda: Engine())
    total, rows, rank, points = leaderboard.load_leaderboard(1, 'admin')
    assert (total, rank, points) == (2, None, None)
    assert len(rows) == 2
    assert len(executed) == 2
