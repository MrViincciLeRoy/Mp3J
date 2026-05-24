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
        }
        default_rule.update(rule)
        base_url = "https://mp3juice.sc/api/v1/search?"
        page_rule = copy.deepcopy(default_rule)
        search_urls = [{"url": base_url + urlencode(page_rule), "auth_token": auth_token, "param_key": chr(config[6])}]
        self.search_size_per_page = self.search_size_per_source
        return search_urls

    @usesearchheaderscookies
    def _search(self, keyword="", search_url=None, request_overrides=None, song_infos=None, progress=None, progress_id=0):
        song_infos = song_infos if song_infos is not None else []
        request_overrides = request_overrides or {}
        search_meta = copy.deepcopy(search_url)
        search_url_str = search_meta["url"]
        auth_token = search_meta["auth_token"]
        param_key = search_meta["param_key"]

        try:
            resp = self.get(search_url_str, allow_redirects=True, **request_overrides)
            resp.raise_for_status()
            data = resp2json(resp)
            search_results_yt = [{**item, "root_source": "YouTube"} for item in data.get("yt", [])]
            search_results_sc = [{**item, "root_source": "SoundCloud"} for item in data.get("sc", [])]

            for search_result in [x for ab in zip_longest(search_results_yt, search_results_sc) for x in ab if x is not None]:
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page:
                    break
                if not isinstance(search_result, dict) or not (song_id := search_result.get("id")):
                    continue
                if search_result["root_source"] == "SoundCloud" and (
                    "id_base64" not in search_result or "title_base64" not in search_result
                ):
                    continue

                download_result = {}
                if search_result["root_source"] == "SoundCloud":
                    download_url = f"https://thetacloud.org/s/{search_result['id_base64']}/{search_result['title_base64']}/"
                else:
                    with suppress(Exception):
                        init_resp = self.get(
                            "https://theta.thetacloud.org/api/v1/init?",
                            params={param_key: auth_token, "t": str(int(time.time()))},
                            **request_overrides,
                        )
                        init_resp.raise_for_status()
                        download_result["init"] = resp2json(init_resp)
                    if "init" not in download_result or not (convert_url := download_result["init"].get("convertURL", "")):
                        continue
                    with suppress(Exception):
                        convert_resp = self.get(f"{convert_url}&v={search_result['id']}&f=mp3&t={int(time.time())}", **request_overrides)
                        convert_resp.raise_for_status()
                        download_result["convert"] = resp2json(convert_resp)
                    if "convert" not in download_result or not (redirect_url := download_result["convert"].get("redirectURL", "")):
                        continue
                    with suppress(Exception):
                        redirect_resp = self.get(redirect_url, **request_overrides)
                        redirect_resp.raise_for_status()
                        download_result["redirect"] = resp2json(redirect_resp)
                    if "redirect" not in download_result or not (download_url := download_result["redirect"].get("downloadURL", "")):
                        continue

                url_status = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={"search": search_result, "download": download_result, "lyric": {}},
                    source=self.source,
                    root_source=search_result["root_source"],
                    song_name=legalizestring(search_result.get("title")),
                    singers="NULL",
                    album="NULL",
                    ext=url_status["ext"],
                    file_size_bytes=url_status["file_size_bytes"],
                    file_size=url_status["file_size"],
                    identifier=song_id,
                    download_url=url_status["download_url"],
                    download_url_status=url_status,
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS:
                    continue

                song_info.downloaded_contents = self.get(download_url, **request_overrides).content
                song_info.file_size_bytes = song_info.downloaded_contents.__sizeof__()
                song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)

                song_infos.append(song_info)

        except Exception as err:
            self.logger_handle.error(f"{self.source}._search >>> {search_url_str} (Error: {err})", disable_print=self.disable_print)

        return song_infos

    def search(self, keyword, rule=None, request_overrides=None):
        search_urls = self._constructsearchurls(keyword, rule=rule, request_overrides=request_overrides)
        song_infos = []
        for search_url in search_urls:
            song_infos = self._search(
                keyword=keyword,
                search_url=search_url,
                request_overrides=request_overrides,
                song_infos=song_infos,
            )
        return song_infos
