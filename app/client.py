
import re
import copy
import time
import base64
import json_repair
from urllib.parse import quote, urlencode
from contextlib import suppress
from itertools import zip_longest

from .sources import BaseMusicClient
from .utils import (
    legalizestring, usesearchheaderscookies, resp2json,
    SongInfo, SongInfoUtils, AudioLinkTester, LoggerHandle,
)


class MP3JuiceMusicClient(BaseMusicClient):
    source = "MP3JuiceMusicClient"

    def __init__(self, **kwargs):
        kwargs["search_size_per_source"] = kwargs.get("search_size_per_source", 10) * 2
        super().__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp3juice.sc/",
            "Origin": "https://mp3juice.sc",
        }
        self.default_download_headers = self.default_search_headers
        self.default_headers = self.default_search_headers
        self.audio_link_tester = AudioLinkTester()
        self.logger_handle = LoggerHandle()
        self._initsession()

    def _getdynamicconfig(self, request_overrides=None):
        resp = self.get(
            f"https://mp3juice.as/?t={int(time.time() * 1000)}",
            **(request_overrides or {}),
        )
        resp.raise_for_status()
        match = re.search(r"var\s+json\s*=\s*JSON\.parse\('(.+?)'\);", resp.text)
        if not match:
            match = re.search(r"var\s+json\s*=\s*(\[.+?\]);", resp.text)
        return json_repair.loads(match.group(1))

    def _calculateauth(self, raw_data):
        data_arr, should_reverse, offset_arr = raw_data[0], raw_data[1], raw_data[2]
        result_chars = [chr(data_arr[t] - offset_arr[len(offset_arr) - 1 - t]) for t in range(len(data_arr))]
        full_token = "".join(reversed(result_chars) if should_reverse else result_chars)
        return full_token[:32]

    def _constructsearchurls(self, keyword, rule=None, request_overrides=None):
        rule = rule or {}
        request_overrides = request_overrides or {}
        config = self._getdynamicconfig()
        auth_token = self._calculateauth(config)
        default_rule = {
            "k": auth_token,
            "y": "s",
            "q": base64.b64encode(quote(keyword, safe="").encode("utf-8")).decode("utf-8"),
            "t": str(int(time.time())),