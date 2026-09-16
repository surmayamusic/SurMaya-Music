from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
import os

app = Flask(__name__)

# -------------------------
# SECURITY
# -------------------------

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

BUCKET_NAME = "songs"


# -------------------------
# HOME
# -------------------------

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

    user = None

    if "user_id" in session:
        user = {
            "id": session.get("user_id"),
            "email": session.get("user_email"),
            "is_admin": session.get("is_admin", False)
        }

    return render_template(
        "index.html",
        songs=songs,
        user=user
    )


# -------------------------
# USER SIGNUP
# -------------------------

@app.route("/signup", methods=["POST"])
def signup():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return "Email and password are required", 400

    try:

        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if response.user:

            session["user_id"] = str(response.user.id)
            session["user_email"] = email
            session["is_admin"] = False

            return redirect(url_for("home"))

        return "Signup failed", 400

    except Exception as e:

        print("Signup error:", e)

        return "Signup failed. This email may already be registered.", 400


# -------------------------
# USER / ADMIN LOGIN
# -------------------------

@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return "Email and password are required", 400

    # ADMIN LOGIN
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:

        session["user_id"] = "admin"
        session["user_email"] = email
        session["is_admin"] = True

        return redirect(url_for("home"))

    # NORMAL USER LOGIN
    try:

        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.user:

            session["user_id"] = str(response.user.id)
            session["user_email"] = email
            session["is_admin"] = False

            return redirect(url_for("home"))

        return "Invalid login", 401

    except Exception as e:

        print("Login error:", e)

        return "Invalid email or password", 401


# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# -------------------------
# FAVOURITES - GET
# -------------------------

@app.route("/api/favourites")
def get_favourites():

    if "user_id" not in session or session.get("is_admin"):
        return jsonify([])

    user_id = session["user_id"]

    try:

        result = (
            supabase
            .table("favourites")
            .select("song_name")
            .eq("user_id", user_id)
            .execute()
        )

        favourites = [
            row["song_name"]
            for row in result.data
        ]

        return jsonify(favourites)

    except Exception as e:

        print("Favourite load error:", e)

        return jsonify([])


# -------------------------
# ADD FAVOURITE
# -------------------------

@app.route("/api/favourite", methods=["POST"])
def add_favourite():

    if "user_id" not in session or session.get("is_admin"):
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    data = request.get_json()

    song_name = data.get("song_name", "").strip()

    if not song_name:
        return jsonify({
            "success": False
        }), 400

    user_id = session["user_id"]

    try:

        supabase.table("favourites").upsert({
            "user_id": user_id,
            "song_name": song_name
        }).execute()

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("Favourite add error:", e)

        return jsonify({
            "success": False
        }), 500


# -------------------------
# REMOVE FAVOURITE
# -------------------------

@app.route("/api/favourite/remove", methods=["POST"])
def remove_favourite():

    if "user_id" not in session or session.get("is_admin"):
        return jsonify({
            "success": False
        }), 401

    data = request.get_json()

    song_name = data.get("song_name", "").strip()

    user_id = session["user_id"]

    try:

        (
            supabase
            .table("favourites")
            .delete()
            .eq("user_id", user_id)
            .eq("song_name", song_name)
            .execute()
        )

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("Favourite remove error:", e)

        return jsonify({
            "success": False
        }), 500


# -------------------------
# ADMIN CHECK
# -------------------------

def admin_required():

    return (
        "user_id" in session
        and session.get("is_admin") is True
    )


# -------------------------
# ADMIN UPLOAD
# -------------------------

@app.route("/upload", methods=["POST"])
def upload():

    if not admin_required():
        return "Access denied. Admin only.", 403

    song = request.files.get("song")

    if not song or not song.filename:
        return redirect(url_for("home"))

    filename = song.filename

    allowed = (".mp3", ".wav", ".ogg")

    if not filename.lower().endswith(allowed):
        return "Only MP3, WAV and OGG files are allowed.", 400

    try:

        file_data = song.read()

        supabase.storage.from_(BUCKET_NAME).upload(
            filename,
            file_data,
            {
                "content-type": song.content_type or "audio/mpeg"
            }
        )

        print("Song uploaded successfully:", filename)

    except Exception as e:

        print("Upload error:", e)

    return redirect(url_for("home"))


# -------------------------
# ADMIN DELETE SONG
# -------------------------

@app.route("/delete/<path:filename>", methods=["POST"])
def delete_song(filename):

    if not admin_required():
        return "Access denied. Admin only.", 403

    try:

        supabase.storage.from_(BUCKET_NAME).remove([
            filename
        ])

        # Remove song from everyone's favourites too
        (
            supabase
            .table("favourites")
            .delete()
            .eq("song_name", filename)
            .execute()
        )

        print("Song deleted:", filename)

        return redirect(url_for("home"))

    except Exception as e:

        print("Delete error:", e)

        return "Unable to delete song.", 500


# -------------------------
# SONG PLAYBACK
# -------------------------

@app.route("/songs/<path:filename>")
def songs(filename):

    try:

        url = (
            supabase
            .storage
            .from_(BUCKET_NAME)
            .get_public_url(filename)
        )

        return redirect(url)

    except Exception as e:

        print("Song URL error:", e)

        return "Song not found", 404


# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
