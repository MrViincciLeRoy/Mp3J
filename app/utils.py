import logging
from dataclasses import dataclass, field
from typing import Optional


def legalizestring(s):
    if not s:
        return "unknown"
    return "".join(c for c in s if c.isalnum() or c in " _-.")


def usesearchheaderscookies(fn):
    return fn


def resp2json(resp):
    return resp.json()


class AudioLinkTester:
    VALID_AUDIO_EXTS = {"mp3", "m4a", "ogg", "wav", "flac", "aac"}

    def test(self, url, request_overrides=None, renew_session=False):
        return {
            "ext": "mp3",
            "file_size_bytes": 0,
            "file_size": "0 MB",
            "download_url": url,
            "is_valid": True,
        }


@dataclass
class SongInfo:
    source: str = ""
    root_source: str = ""
    song_name: str = ""
    singers: str = "NULL"
    album: str = "NULL"
    ext: str = "mp3"
    file_size_bytes: int = 0
    file_size: str = "0 MB"
    identifier: str = ""
    duration_s: Optional[float] = None
    duration: str = "-:-:-"
    lyric: str = "NULL"
    cover_url: Optional[str] = None
    download_url: str = ""
    download_url_status: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)
    downloaded_contents: Optional[bytes] = None
    with_valid_download_url: bool = False

    def __post_init__(self):
        self.with_valid_download_url = bool(self.download_url)


class SongInfoUtils:
    @staticmethod
    def byte2mb(b):
        return f"{b / 1024 / 1024:.2f} MB"


class LoggerHandle:
    def __init__(self):
        self.logger = logging.getLogger("mp3juice")

    def error(self, msg, disable_print=False):
        self.logger.error(msg)
        if not disable_print:
            print(f"[ERROR] {msg}")
