from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os

app = Flask(__name__)

SONG_FOLDER = "songs"
os.makedirs(SONG_FOLDER, exist_ok=True)


@app.route("/")
def home():
    songs = []

    for filename in os.listdir(SONG_FOLDER):
        if filename.lower().endswith((".mp3", ".wav", ".ogg")):
            songs.append(filename)

    return render_template("index.html", songs=songs)


@app.route("/upload", methods=["POST"])
def upload():
    song = request.files.get("song")

    if song and song.filename:
        song.save(os.path.join(SONG_FOLDER, song.filename))

    return redirect(url_for("home"))


@app.route("/songs/<path:filename>")
def songs(filename):
    return send_from_directory(SONG_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)