from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

def get_db():
    return current_app.supabase

# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route("/auth", methods=["GET", "POST"])
def auth():
    """Halaman autentikasi — login atau daftar dengan username + PIN."""
    # Jika sudah login, redirect ke dashboard
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))
    return render_template("auth/auth.html")

@auth_bp.route("/api/cek-username", methods=["POST"])
def cek_username():
    """API: Cek apakah username sudah terdaftar."""
    data = request.get_json()
    username = data.get("username", "").strip().lower()

    if not username:
        return jsonify({"error": "Username tidak boleh kosong."}), 400

    # Validasi panjang username
    if len(username) < 3 or len(username) > 20:
        return jsonify({"error": "Username harus 3–20 karakter."}), 400

    # Validasi karakter username
    import re
    if not re.match(r'^[a-z0-9_]+$', username):
        return jsonify({"error": "Username hanya boleh huruf kecil, angka, dan underscore."}), 400

    db = get_db()
    result = db.table("users").select("id, username").eq("username", username).execute()

    if result.data:
        return jsonify({"exists": True, "message": f"Selamat datang kembali, {username}!"})
    else:
        return jsonify({"exists": False, "message": "Username baru! Buat PIN 4 angka untuk mendaftar."})

@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    """API: Proses login atau registrasi."""
    data = request.get_json()
    username = data.get("username", "").strip().lower()
    pin = data.get("pin", "").strip()

    # Validasi input
    if not username or not pin:
        return jsonify({"error": "Username dan PIN wajib diisi."}), 400

    if len(pin) != 4 or not pin.isdigit():
        return jsonify({"error": "PIN harus tepat 4 angka."}), 400

    db = get_db()
    result = db.table("users").select("*").eq("username", username).execute()

    if result.data:
        # User sudah ada — verifikasi PIN
        user = result.data[0]
        if check_password_hash(user["pin_hash"], pin):
            # Login berhasil
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            return jsonify({"success": True, "redirect": url_for("dashboard.dashboard")})
        else:
            return jsonify({"error": "PIN salah. Coba lagi."}), 401
    else:
        # User baru — daftar
        pin_hash = generate_password_hash(pin)
        try:
            insert_result = db.table("users").insert({
                "username": username,
                "pin_hash": pin_hash,
            }).execute()
            user = insert_result.data[0]
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            return jsonify({"success": True, "redirect": url_for("dashboard.dashboard"), "new_user": True})
        except Exception as e:
            return jsonify({"error": "Gagal membuat akun. Coba lagi."}), 500

@auth_bp.route("/keluar")
def logout():
    """Logout — hapus session."""
    session.clear()
    flash("Kamu berhasil keluar.", "info")
    return redirect(url_for("paste.index"))

@auth_bp.route("/u/<username>")
def profile(username):
    """Halaman profil publik user."""
    db = get_db()

    # Ambil data user
    user_result = db.table("users").select("id, username, created_at").eq("username", username.lower()).execute()
    if not user_result.data:
        flash("User tidak ditemukan.", "error")
        return render_template("404.html"), 404

    user = user_result.data[0]

    # Ambil semua paste publik milik user
    pastes_result = (
        db.table("snippets")
        .select("slug, title, paste_type, language, created_at, view_count, expires_at")
        .eq("user_id", user["id"])
        .eq("visibility", "public")
        .order("created_at", desc=True)
        .execute()
    )

    # Filter yang belum expired
    from routes.paste import is_expired
    pastes = [p for p in pastes_result.data if not is_expired(p)]

    # Hitung total view
    total_views = sum(p.get("view_count", 0) for p in pastes_result.data)

    return render_template(
        "profile.html",
        profile_user=user,
        pastes=pastes,
        total_views=total_views,
        is_own_profile=(session.get("username") == username.lower())
    )
