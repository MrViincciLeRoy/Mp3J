import pytest
from unittest.mock import patch, MagicMock
from app.utils import SongInfo


@pytest.fixture
def flask_client():
    import server
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def test_health(flask_client):
    resp = flask_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_search_missing_query(flask_client):
    resp = flask_client.get("/search")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@patch("server.client.search")
def test_search_returns_results(mock_search, flask_client):
    mock_search.return_value = [
        SongInfo(
            song_name="lofi study",
            root_source="YouTube",
            ext="mp3",
            file_size="3.2 MB",
            download_url="https://example.com/track.mp3",
            identifier="abc123",
        )
    ]
    resp = flask_client.get("/search?q=lofi")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["song_name"] == "lofi study"
    assert data[0]["source"] == "YouTube"


@patch("server.client.search")
def test_search_handles_exception(mock_search, flask_client):
    mock_search.side_effect = Exception("api down")
    resp = flask_client.get("/search?q=test")
    assert resp.status_code == 500
    assert "error" in resp.get_json()
