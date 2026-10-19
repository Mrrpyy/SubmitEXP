from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_metadata_validation():
    response = client.post('/integration/validate', json={
        'assignment_title': 'Demo assignment',
        'course_name': 'CS 101',
        'submission_type': 'assignment',
    })
    assert response.status_code == 200
    assert response.json()['accepted'] is True
    assert response.json()['submission_type'] == 'assignment'


def test_reject_screenshots():
    response = client.post('/integration/validate', json={
        'assignment_title': 'Demo',
        'submission_type': 'assignment',
        'screenshot': 'should not be accepted',
    })
    assert response.status_code == 422


def test_reject_invalid_types():
    response = client.post('/integration/validate', json={
        'assignment_title': 'Demo',
        'submission_type': 'invalid',
    })
    assert response.status_code == 422


def test_accept_quizzes():
    response = client.post('/integration/validate', json={
        'assignment_title': 'Demo Quiz',
        'submission_type': 'quiz',
    })
    assert response.status_code == 200
    assert response.json()['accepted'] is True
    assert response.json()['submission_type'] == 'quiz'


def test_cors_for_chrome_extension():
    origin = 'chrome-extension://' + 'a' * 32
    response = client.options('/integration/validate', headers={
        'Origin': origin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin
