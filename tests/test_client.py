import pytest
from unittest.mock import MagicMock, patch
from app.client import MP3JuiceMusicClient
from app.utils import legalizestring, SongInfo, AudioLinkTester


def test_legalizestring_strips_invalid():
    assert legalizestring("Hello! World#") == "Hello World"


def test_legalizestring_none():
    assert legalizestring(None) == "unknown"


def test_song_info_valid_url():
    s = SongInfo(download_url="https://example.com/track.mp3")
    assert s.with_valid_download_url is True


def test_song_info_empty_url():
    s = SongInfo(download_url="")
    assert s.with_valid_download_url is False


def test_audio_link_tester_valid_exts():
    assert "mp3" in AudioLinkTester.VALID_AUDIO_EXTS
    assert "flac" in AudioLinkTester.VALID_AUDIO_EXTS


def test_calculateauth_basic():
    client = MP3JuiceMusicClient.__new__(MP3JuiceMusicClient)
    # raw_data: [data_arr, should_reverse, offset_arr]
    # char = chr(data_arr[i] - offset_arr[len-1-i])
    # data_arr[0] - offset_arr[3] = 72 - 4 = 68 = 'D' ... etc
    data_arr = [72, 101, 108, 108]
    offset_arr = [4, 3, 2, 1]
    # i=0: chr(72 - offset[3]) = chr(72-1)=chr(71)='G'
    # i=1: chr(101 - offset[2]) = chr(101-2)=chr(99)='c'
    # i=2: chr(108 - offset[1]) = chr(108-3)=chr(105)='i'
    # i=3: chr(108 - offset[0]) = chr(108-4)=chr(104)='h'
    result = client._calculateauth([data_arr, False, offset_arr])
    assert isinstance(result, str)
    assert len(result) <= 32


def test_calculateauth_reversed():
    client = MP3JuiceMusicClient.__new__(MP3JuiceMusicClient)
    data_arr = [72, 101, 108, 108]
    offset_arr = [4, 3, 2, 1]
    normal = client._calculateauth([data_arr, False, offset_arr])
    reversed_result = client._calculateauth([data_arr, True, offset_arr])
    assert normal != reversed_result


@patch("app.client.MP3JuiceMusicClient._getdynamicconfig")
@patch("app.client.MP3JuiceMusicClient._calculateauth")
def test_constructsearchurls_returns_list(mock_auth, mock_config):
    mock_config.return_value = [0] * 10 + [65]  # config[6] = 65 = 'A'
    mock_auth.return_value = "testtoken123"

    client = MP3JuiceMusicClient.__new__(MP3JuiceMusicClient)
    client.search_size_per_source = 10
    client.session = MagicMock()

    urls = client._constructsearchurls("lofi beats")
    assert isinstance(urls, list)
    assert len(urls) == 1
    assert "mp3juice.sc" in urls[0]["url"]
    assert urls[0]["auth_token"] == "testtoken123"


@patch("app.client.MP3JuiceMusicClient._getdynamicconfig")
@patch("app.client.MP3JuiceMusicClient._calculateauth")
def test_constructsearchurls_keyword_encoded(mock_auth, mock_config):
    mock_config.return_value = [0] * 10 + [65]
    mock_auth.return_value = "tok"

    client = MP3JuiceMusicClient.__new__(MP3JuiceMusicClient)
    client.search_size_per_source = 5
    client.session = MagicMock()

    urls = client._constructsearchurls("drake")
    assert "q=" in urls[0]["url"]


def test_search_returns_empty_on_bad_response():
    client = MP3JuiceMusicClient.__new__(MP3JuiceMusicClient)
    client.search_size_per_source = 10
    client.search_size_per_page = 10
    client.strict_limit_search_size_per_page = True
    client.disable_print = True
    client.audio_link_tester = AudioLinkTester()

    from app.utils import LoggerHandle
    client.logger_handle = LoggerHandle()

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("connection refused")
    mock_session.get.return_value = mock_resp
    client.session = mock_session

    results = client._search(
        keyword="test",
        search_url={"url": "https://fake.url", "auth_token": "tok", "param_key": "k"},
        song_infos=[],
    )
    assert results == []
