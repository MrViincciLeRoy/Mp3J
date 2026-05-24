import sys
import os
import time
import re
import base64
import copy
import json_repair
import requests
from urllib.parse import quote, urlencode
from contextlib import suppress
from itertools import zip_longest

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://mp3juice.sc/",
    "Origin": "https://mp3juice.sc",
}

session = requests.Session()
session.headers.update(HEADERS)


def getdynamicconfig():
    resp = session.get(f"https://mp3juice.as/?t={int(time.time() * 1000)}")
    resp.raise_for_status()
    match = re.search(r"var\s+json\s*=\s*JSON\.parse\('(.+?)'\);", resp.text)
    if not match:
        match = re.search(r"var\s+json\s*=\s*(\[.+?\]);", resp.text)
    if not match:
        raise RuntimeError("Could not find config in page")
    return json_repair.loads(match.group(1))


def calculateauth(raw_data):
    data_arr, should_reverse, offset_arr = raw_data[0], raw_data[1], raw_data[2]
    result_chars = [chr(data_arr[t] - offset_arr[len(offset_arr) - 1 - t]) for t in range(len(data_arr))]
    full_token = "".join(reversed(result_chars) if should_reverse else result_chars)
    return full_token[:32]


def search(keyword, limit=5):
    config = getdynamicconfig()
    auth_token = calculateauth(config)
    param_key = chr(config[6])

    q = base64.b64encode(quote(keyword, safe="").encode("utf-8")).decode("utf-8")
    params = {"k": auth_token, "y": "s", "q": q, "t": str(int(time.time()))}
    url = "https://mp3juice.sc/api/v1/search?" + urlencode(params)

    resp = session.get(url, allow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    results_yt = [{**i, "root_source": "YouTube"} for i in data.get("yt", [])]
    results_sc = [{**i, "root_source": "SoundCloud"} for i in data.get("sc", [])]
    combined = [x for pair in zip_longest(results_yt, results_sc) for x in pair if x]

    found = []
    for item in combined:
        if len(found) >= limit:
            break
        if not item.get("id"):
            continue

        dl_url = None

        if item["root_source"] == "SoundCloud":
            if "id_base64" not in item or "title_base64" not in item:
                continue
            dl_url = f"https://thetacloud.org/s/{item['id_base64']}/{item['title_base64']}/"
        else:
            try:
                init = session.get(
                    "https://theta.thetacloud.org/api/v1/init?",
                    params={param_key: auth_token, "t": str(int(time.time()))},
                )
                init.raise_for_status()
                convert_url = init.json().get("convertURL", "")
                if not convert_url:
                    continue

                conv = session.get(f"{convert_url}&v={item['id']}&f=mp3&t={int(time.time())}")
                conv.raise_for_status()
                redirect_url = conv.json().get("redirectURL", "")
                if not redirect_url:
                    continue

                redir = session.get(redirect_url)
                redir.raise_for_status()
                dl_url = redir.json().get("downloadURL", "")
            except Exception as e:
                print(f"  [skip] {item.get('title', '?')} — {e}")
                continue

        if dl_url:
            found.append({"title": item.get("title", "unknown"), "source": item["root_source"], "url": dl_url, "id": item["id"]})

    return found


def download(title, url, out_dir="downloads"):
    os.makedirs(out_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\s\-.]', '', title).strip().replace(" ", "_")
    path = os.path.join(out_dir, f"{safe_name}.mp3")

    resp = session.get(url, stream=True, timeout=60)
    resp.raise_for_status()

    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(path) / 1024 / 1024
    return path, size_mb


if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]).strip()
    if not keyword:
        print("Usage: python download.py <song name>")
        sys.exit(1)

    print(f"\nSearching: {keyword}")
    results = search(keyword, limit=10)

    if not results:
        print("No results found.")
        sys.exit(1)

    print(f"Found {len(results)} result(s). Downloading first...")
    first = results[0]
    print(f"  Title  : {first['title']}")
    print(f"  Source : {first['source']}")
    print(f"  URL    : {first['url']}")

    path, size = download(first["title"], first["url"])
    print(f"  Saved  : {path} ({size:.2f} MB)")
    print("\nDone.")