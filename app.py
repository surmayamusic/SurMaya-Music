from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "songs"


@app.route("/")
def home():
    songs = []

    try:
        files = supabase.storage.from_(BUCKET_NAME).list()

        for file in files:
            name = file.get("name", "")

            if name.lower().endswith((".mp3", ".wav", ".ogg")):
                songs.append(name)

    except Exception as e:
        print("Error loading songs:", e)

    return render_template("index.html", songs=songs)


@app.route("/upload", methods=["POST"])
def upload():
    song = request.files.get("song")

    if song and song.filename:
        filename = song.filename

        try:
            file_data = song.read()

            supabase.storage.from_(BUCKET_NAME).upload(
                filename,
                file_data,
                {"content-type": song.content_type or "audio/mpeg"}
            )

            print("Song uploaded successfully:", filename)

        except Exception as e:
            print("Upload error:", e)

    return redirect(url_for("home"))


@app.route("/songs/<path:filename>")
def songs(filename):
    try:
        url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return redirect(url)

    except Exception as e:
        print("Song URL error:", e)
        return "Song not found", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))