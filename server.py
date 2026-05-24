from flask import Flask, request, jsonify
from app.client import MP3JuiceMusicClient

app = Flask(__name__)
client = MP3JuiceMusicClient(search_size_per_source=5)


@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "q param required"}), 400
    try:
        results = client.search(keyword)
        return jsonify([
            {
                "song_name": s.song_name,
                "source": s.root_source,
                "ext": s.ext,
                "file_size": s.file_size,
                "download_url": s.download_url,
                "identifier": s.identifier,
            }
            for s in results
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
