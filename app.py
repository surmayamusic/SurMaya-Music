from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from supabase import create_client
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
BASE_URL = os.environ.get("BASE_URL", "https://surmaya-music.onrender.com").rstrip("/")

# Public/publishable key is used for user authentication.
supabase_auth = create_client(SUPABASE_URL, SUPABASE_KEY)
# Service key is used only for trusted server-side database/storage operations.
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
BUCKET_NAME = "songs"


def current_user():
    if "user_id" not in session:
        return None
    return {"id": session.get("user_id"), "email": session.get("user_email"), "is_admin": session.get("is_admin", False)}


def admin_required():
    return "user_id" in session and session.get("is_admin") is True


@app.after_request
def add_google_button(response):
    if response.content_type and "text/html" in response.content_type and not current_user():
        body = response.get_data(as_text=True)
        marker = '<div class="auth-tabs">'
        button = '''<div class="google-wrap"><div class="or-line"><span>OR</span></div><a class="google-btn" href="/auth/google"><span class="google-g">G</span><span>Continue with Google</span></a></div>'''
        cinematic_css = '''<style id="surmaya-cinematic-overrides">
:root{--sm-bg:#05040b;--sm-card:rgba(17,15,29,.72);--sm-line:rgba(255,255,255,.14);--sm-muted:#a9a8b8}
html{background:#05040b}body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(900px 500px at 8% 12%,rgba(255,35,160,.16),transparent 55%),radial-gradient(800px 520px at 92% 18%,rgba(0,205,255,.14),transparent 55%),radial-gradient(700px 600px at 52% 88%,rgba(125,70,255,.13),transparent 58%),#05040b!important;color:#f7f4ff}
body:after{content:"";position:fixed;inset:0;z-index:-3;pointer-events:none;background:linear-gradient(120deg,rgba(255,0,153,.055),transparent 30%,rgba(0,229,255,.045) 68%,rgba(255,191,0,.045));mix-blend-mode:screen}
.cinematic{background:radial-gradient(ellipse at 50% -8%,rgba(255,47,178,.22),transparent 34%),radial-gradient(circle at 15% 48%,rgba(0,215,255,.11),transparent 27%),radial-gradient(circle at 85% 62%,rgba(255,190,50,.09),transparent 25%),linear-gradient(135deg,#04030a 0%,#0b0716 42%,#05050c 100%)!important}
header{background:rgba(6,5,13,.78)!important;border-bottom:1px solid rgba(255,255,255,.10)!important;box-shadow:0 10px 45px rgba(0,0,0,.28)}.brand img{filter:drop-shadow(0 0 12px rgba(255,44,180,.55)) drop-shadow(0 0 22px rgba(0,210,255,.22))}.brand span{letter-spacing:.2px}
nav a{transition:.2s;color:#d9d6e6}nav a:hover{color:#fff;text-shadow:0 0 18px rgba(255,48,183,.7)}.nav-btn{background:linear-gradient(100deg,rgba(255,40,174,.12),rgba(77,109,255,.12),rgba(0,213,255,.10));border-color:rgba(255,255,255,.18)}
.hero{padding-top:100px}.hero:after{content:"";position:absolute;left:50%;bottom:25px;transform:translateX(-50%);width:420px;height:2px;background:linear-gradient(90deg,transparent,#ff2cae,#7958ff,#13d8ff,#ffd166,transparent);filter:blur(1px);opacity:.75}.hero-logo{filter:drop-shadow(0 0 20px rgba(255,37,171,.45)) drop-shadow(0 0 38px rgba(0,210,255,.20))}.kicker{color:#f1d8ff;border-color:rgba(255,255,255,.14)!important;background:linear-gradient(100deg,rgba(255,37,174,.10),rgba(106,76,255,.10),rgba(0,205,255,.08))!important}.gradient{background:linear-gradient(90deg,#ff36b4,#ff8a32,#ffd166,#9b65ff,#21d9ff,#ff36b4)!important;background-size:300% auto!important}
.btn,.primary{background:linear-gradient(100deg,#ff249f 0%,#a74cff 48%,#16cfff 100%)!important;box-shadow:0 14px 42px rgba(139,53,255,.28),0 0 30px rgba(255,32,165,.10)}
.section{position:relative}.section h2{letter-spacing:-.7px}.song-card{background:linear-gradient(145deg,rgba(255,255,255,.105),rgba(255,255,255,.035))!important;border-color:rgba(255,255,255,.14)!important;box-shadow:0 20px 55px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.05)!important}.song-card:hover{border-color:rgba(255,57,181,.55)!important;box-shadow:0 25px 65px rgba(0,0,0,.45),0 0 35px rgba(255,44,174,.12)!important}.cover{background:radial-gradient(circle at 15% 20%,#ff2ba6,transparent 32%),radial-gradient(circle at 85% 25%,#19d7ff,transparent 35%),radial-gradient(circle at 55% 90%,#8060ff,transparent 40%),#10101d!important}.download{background:linear-gradient(100deg,rgba(255,255,255,.06),rgba(121,88,255,.10),rgba(0,207,255,.07))!important}.fav.active{box-shadow:0 0 18px rgba(255,55,181,.18)}
.panel,.about,.upload{background:linear-gradient(145deg,rgba(255,255,255,.095),rgba(255,255,255,.035))!important;border-color:rgba(255,255,255,.14)!important;box-shadow:0 24px 70px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.05)!important}.form input,.search{background:rgba(0,0,0,.18)!important}.form input:focus,.search:focus{border-color:#b76aff!important;box-shadow:0 0 0 3px rgba(183,106,255,.13),0 0 25px rgba(255,46,177,.08)!important}.tab.active{background:linear-gradient(100deg,#ff2cae,#7b52ff,#13cfff)!important}.upload button{background:linear-gradient(100deg,#ff2cae,#7b52ff,#13cfff)!important}
.google-wrap{margin:0 0 15px}.or-line{display:flex;align-items:center;gap:10px;margin:2px 0 12px;color:#858397;font-size:10px;letter-spacing:2px}.or-line:before,.or-line:after{content:"";height:1px;flex:1;background:rgba(255,255,255,.12)}.google-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:12px 14px;border-radius:12px;background:rgba(255,255,255,.96);color:#15131b!important;text-decoration:none;font-weight:800;border:1px solid rgba(255,255,255,.7);box-shadow:0 10px 30px rgba(0,0,0,.22);transition:.2s}.google-btn:hover{transform:translateY(-1px);box-shadow:0 14px 35px rgba(0,0,0,.3)}.google-g{font-size:19px;font-weight:900;background:linear-gradient(45deg,#4285f4 20%,#34a853 42%,#fbbc05 65%,#ea4335 84%);-webkit-background-clip:text;background-clip:text;color:transparent}
footer{background:#030308!important;border-top:1px solid rgba(255,255,255,.10)!important}
@media(max-width:600px){.hero{padding-top:70px}.google-btn{font-size:13px}}
</style>'''
        if marker in body and "Continue with Google" not in body:
            body = body.replace(marker, button + marker, 1)
        if "surmaya-cinematic-overrides" not in body and "</head>" in body:
            body = body.replace("</head>", cinematic_css + "</head>", 1)
        response.set_data(body)
    return response


@app.route("/")
def home():
    songs = []
    try:
        files = supabase_admin.storage.from_(BUCKET_NAME).list()
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
        response = supabase_auth.auth.sign_up({"email": email, "password": password})
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
        response = supabase_auth.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            session["user_id"] = str(response.user.id)
            session["user_email"] = email
            session["is_admin"] = False
            return redirect(url_for("home"))
        return redirect(url_for("home", auth_error="Invalid email or password"))
    except Exception as e:
        print("Login error:", e)
        return redirect(url_for("home", auth_error="Invalid email or password. Please check your email/password and Supabase Auth settings."))


@app.route("/auth/google")
def google_login():
    try:
        redirect_to = f"{BASE_URL}/auth/callback"
        response = supabase_auth.auth.sign_in_with_oauth({"provider": "google", "options": {"redirect_to": redirect_to}})
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
        response = supabase_auth.auth.exchange_code_for_session(code)
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
        result = supabase_admin.table("favourites").select("song_name").eq("user_id", session["user_id"]).execute()
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
        supabase_admin.table("favourites").upsert({"user_id": session["user_id"], "song_name": song_name}).execute()
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
        supabase_admin.table("favourites").delete().eq("user_id", session["user_id"]).eq("song_name", song_name).execute()
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
        supabase_admin.storage.from_(BUCKET_NAME).upload(filename, song.read(), {"content-type": song.content_type or "audio/mpeg"})
    except Exception as e:
        print("Upload error:", e)
    return redirect(url_for("home"))


@app.route("/delete/<path:filename>", methods=["POST"])
def delete_song(filename):
    if not admin_required():
        return "Access denied. Admin only.", 403
    try:
        supabase_admin.storage.from_(BUCKET_NAME).remove([filename])
        supabase_admin.table("favourites").delete().eq("song_name", filename).execute()
        return redirect(url_for("home"))
    except Exception as e:
        print("Delete error:", e)
        return "Unable to delete song.", 500


@app.route("/songs/<path:filename>")
def songs(filename):
    try:
        return redirect(supabase_admin.storage.from_(BUCKET_NAME).get_public_url(filename))
    except Exception as e:
        print("Song URL error:", e)
        return "Song not found", 404


@app.route("/download/<path:filename>")
def download_song(filename):
    try:
        data = supabase_admin.storage.from_(BUCKET_NAME).download(filename)
        ext = filename.lower().rsplit(".", 1)[-1]
        mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}.get(ext, "application/octet-stream")
        return send_file(io.BytesIO(data), as_attachment=True, download_name=os.path.basename(filename), mimetype=mime)
    except Exception as e:
        print("Download error:", e)
        return "Download failed", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
