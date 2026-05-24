# mp3juice-test

Flask wrapper + test suite for `MP3JuiceMusicClient`.

## Structure

```
mp3juice-test/
├── app/
│   ├── client.py       # MP3JuiceMusicClient
│   ├── sources.py      # BaseMusicClient stub
│   └── utils.py        # SongInfo, AudioLinkTester, helpers
├── tests/
│   ├── test_client.py  # Unit tests for client logic
│   └── test_routes.py  # Flask route tests
├── server.py           # Flask app
├── requirements.txt
└── .github/workflows/ci.yml
```

## Setup

```bash
pip install -r requirements.txt
python server.py
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/search?q=<keyword>` | Search for tracks |

## Tests

```bash
pytest tests/ -v --cov=app
```

## CI

GitHub Actions runs on every push to `main`/`dev` and on PRs targeting `main`. See `.github/workflows/ci.yml`.

## Notes

- `sources.py` and `utils.py` are stubs that replace the original package dependencies so the client can run standalone.
- The real `MP3JuiceMusicClient` hits live mp3juice APIs — tests mock network calls so no real requests are made.
