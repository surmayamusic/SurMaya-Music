from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from supabase import create_client
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
BASE_URL = os.environ.get("BASE_URL", "https://surmaya-music.onrender.com").rstrip("/")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
BUCKET_NAME = "songs"


def current_user():
    if "user_id" not in session:
        return None
    return {"id": session.get("user_id"), "email": session.get("user_email"), "is_admin": session.get("is_admin", False)}


def admin_required():
    return "user_id" in session and session.get("is_admin") is True


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
    return render_template("index.html", songs=songs, user=current_user())


@app.route("/logo")
def logo():
    return send_file("surmaya-logo.png", mimetype="image/png", max_age=3600)


@app.route("/signup", methods=["POST"])
def signup():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        return redirect(url_for("home", auth_error="Email and password are required", auth_tab="signup"))
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            session["user_id"] = str(response.user.id)
            session["user_email"] = email
            session["is_admin"] = False
            return redirect(url_for("home"))
        return redirect(url_for("home", auth_error="Signup could not be completed. Check Supabase email confirmation settings.", auth_tab="signup"))
    except Exception as e:
        print("Signup error:", e)
        return redirect(url_for("home", auth_error="Signup failed. The email may already be registered.", auth_tab="signup"))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        return redirect(url_for("home", auth_error="Email and password are required"))
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["user_id"] = "admin"
        session["user_email"] = email
        session["is_admin"] = True
        return redirect(url_for("home"))
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            session["user_id"] = str(response.user.id)
            session["user_email"] = email
            session["is_admin"] = False
            return redirect(url_for("home"))
        return redirect(url_for("home", auth_error="Invalid email or password"))
    except Exception as e:
        print("Login error:", e)
        return redirect(url_for("home", auth_error="Invalid email or password"))


@app.route("/auth/google")
def google_login():
    try:
        redirect_to = f"{BASE_URL}/auth/callback"
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_to}
        })
        oauth_url = getattr(response, "url", None)
        if oauth_url:
            return redirect(oauth_url)
        return redirect(url_for("home", auth_error="Google sign in is not configured yet."))
    except Exception as e:
        print("Google OAuth error:", e)
        return redirect(url_for("home", auth_error="Google sign in is not configured yet."))


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("home", auth_error="Google sign in was cancelled or failed."))
    try:
        response = supabase.auth.exchange_code_for_session(code)
        user = getattr(response, "user", None)
        if user:
            session["user_id"] = str(user.id)
            session["user_email"] = user.email or ""
            session["is_admin"] = False
            return redirect(url_for("home"))
        return redirect(url_for("home", auth_error="Google sign in could not be completed."))
    except Exception as e:
        print("OAuth callback error:", e)
        return redirect(url_for("home", auth_error="Google sign in could not be completed."))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/api/favourites")
def get_favourites():
    if "user_id" not in session or session.get("is_admin"):
        return jsonify([])
    try:
        result = supabase.table("favourites").select("song_name").eq("user_id", session["user_id"]).execute()
        return jsonify([row["song_name"] for row in result.data])
    except Exception as e:
        print("Favourite load error:", e)
        return jsonify([])


@app.route("/api/favourite", methods=["POST"])
def add_favourite():
    if "user_id" not in session or session.get("is_admin"):
        return jsonify({"success": False, "message": "Login required"}), 401
    data = request.get_json(silent=True) or {}
    song_name = str(data.get("song_name", "")).strip()
    if not song_name:
        return jsonify({"success": False}), 400
    try:
        supabase.table("favourites").upsert({"user_id": session["user_id"], "song_name": song_name}).execute()
        return jsonify({"success": True})
    except Exception as e:
        print("Favourite add error:", e)
        return jsonify({"success": False}), 500


@app.route("/api/favourite/remove", methods=["POST"])
def remove_favourite():
    if "user_id" not in session or session.get("is_admin"):
        return jsonify({"success": False}), 401
    data = request.get_json(silent=True) or {}
    song_name = str(data.get("song_name", "")).strip()
    try:
        supabase.table("favourites").delete().eq("user_id", session["user_id"]).eq("song_name", song_name).execute()
        return jsonify({"success": True})
    except Exception as e:
        print("Favourite remove error:", e)
        return jsonify({"success": False}), 500


@app.route("/upload", methods=["POST"])
def upload():
    if not admin_required():
        return "Access denied. Admin only.", 403
    song = request.files.get("song")
    if not song or not song.filename:
        return redirect(url_for("home"))
    filename = song.filename
    if not filename.lower().endswith((".mp3", ".wav", ".ogg")):
        return "Only MP3, WAV and OGG files are allowed.", 400
    try:
        supabase.storage.from_(BUCKET_NAME).upload(filename, song.read(), {"content-type": song.content_type or "audio/mpeg"})
    except Exception as e:
        print("Upload error:", e)
    return redirect(url_for("home"))


@app.route("/delete/<path:filename>", methods=["POST"])
def delete_song(filename):
    if not admin_required():
        return "Access denied. Admin only.", 403
    try:
        supabase.storage.from_(BUCKET_NAME).remove([filename])
        supabase.table("favourites").delete().eq("song_name", filename).execute()
        return redirect(url_for("home"))
    except Exception as e:
        print("Delete error:", e)
        return "Unable to delete song.", 500


@app.route("/songs/<path:filename>")
def songs(filename):
    try:
        return redirect(supabase.storage.from_(BUCKET_NAME).get_public_url(filename))
    except Exception as e:
        print("Song URL error:", e)
        return "Song not found", 404


@app.route("/download/<path:filename>")
def download_song(filename):
    try:
        data = supabase.storage.from_(BUCKET_NAME).download(filename)
        ext = filename.lower().rsplit(".", 1)[-1]
        mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}.get(ext, "application/octet-stream")
        return send_file(io.BytesIO(data), as_attachment=True, download_name=os.path.basename(filename), mimetype=mime)
    except Exception as e:
        print("Download error:", e)
        return "Download failed", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
