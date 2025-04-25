import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_forum(client):
    # Adjust course_id as needed based on what's in your DB
    res = client.post('/forums', json={
        "course_id": 101,
        "forum_title": "Test Forum"
    })
    assert res.status_code == 201
    assert "forum_id" in res.get_json()

def test_get_forums(client):
    res = client.get('/forums/101')
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)
