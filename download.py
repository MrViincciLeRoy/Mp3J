import sys
import re
import os
import json
import base64
import requests
from pyDes import ECB, PAD_PKCS5, des

BASE = "https://www.jiosaavn.com/api.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
session = requests.Session()
session.headers.update(HEADERS)


def clean(s):
    return s.encode().decode().replace("&quot;", "'").replace("&amp;", "&").replace("&#039;", "'")


def decrypt_url(enc):
    cipher = des(b"38346591", ECB, b"\0" * 8, pad=None, padmode=PAD_PKCS5)
    dec = cipher.decrypt(base64.b64decode(enc.strip()), padmode=PAD_PKCS5).decode("utf-8")
    return dec.replace("_96.mp4", "_320.mp4")


def search(query):
    url = f"{BASE}?__call=autocomplete.get&_format=json&_marker=0&cc=in&includeMetaTags=1&query={requests.utils.quote(query)}"
    resp = session.get(url, timeout=15)
    text = re.sub(r'\(From "([^"]+)"\)', r"(From '\1')", resp.text.encode().decode("unicode-escape"))
    data = json.loads(text)
    return data.get("songs", {}).get("data", [])


def get_song(song_id):
    url = f"{BASE}?__call=song.getDetails&cc=in&_marker=0&_format=json&pids={song_id}"
    resp = session.get(url, timeout=15)
    data = json.loads(resp.text.encode().decode("unicode-escape"))
    return data.get(song_id)


def download(title, media_url, out_dir="downloads"):
    os.makedirs(out_dir, exist_ok=True)
    safe = re.sub(r'[^\w\s\-.]', '', title).strip().replace(" ", "_")
    # JioSaavn serves .mp4 containers with AAC — rename to .m4a which is correct
    path = os.path.join(out_dir, f"{safe}.m4a")
    resp = session.get(media_url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return path, os.path.getsize(path) / 1024 / 1024


if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]).strip()
    if not keyword:
        print("Usage: python download.py <song name>")
        sys.exit(1)

    print(f"\nSearching: {keyword}")
    results = search(keyword)
    if not results:
        print("No results.")
        sys.exit(1)

    first = results[0]
    song_id = first["id"]
    print(f"Found: {first.get('title', '?')} — {first.get('primary_artists', '?')}")

    print("Fetching song details...")
    song = get_song(song_id)
    if not song:
        print("Could not fetch song details.")
        sys.exit(1)

    title = clean(song.get("song", keyword))
    enc_url = song.get("encrypted_media_url", "")
    if not enc_url:
        print("No encrypted URL found.")
        sys.exit(1)

    media_url = decrypt_url(enc_url)
    if song.get("320kbps") != "true":
        media_url = media_url.replace("_320.mp4", "_160.mp4")

    print(f"Title   : {title}")
    print(f"Quality : {'320kbps' if song.get('320kbps') == 'true' else '160kbps'}")
    print(f"URL     : {media_url}")

    path, size = download(title, media_url)
    print(f"Saved   : {path} ({size:.2f} MB)")