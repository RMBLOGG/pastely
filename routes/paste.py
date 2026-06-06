import secrets
import re
from datetime import datetime, timedelta, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, session, jsonify, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from zoneinfo import ZoneInfo

paste_bp = Blueprint("paste", __name__)

WIB = ZoneInfo("Asia/Jakarta")

# ── Helper ────────────────────────────────────────────────────────────────────

def get_db():
    """Ambil Supabase client dari app context."""
    return current_app.supabase

def generate_slug():
    """Buat slug 6 karakter alphanumeric acak."""
    return secrets.token_urlsafe(4)[:6]

def calculate_expiry(expiry_option):
    """Hitung waktu kedaluwarsa berdasarkan pilihan user."""
    now = datetime.now(timezone.utc)
    options = {
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    if expiry_option in options:
        return (now + options[expiry_option]).isoformat()
    return None  # Tidak pernah kedaluwarsa

def is_expired(paste):
    """Cek apakah paste sudah kedaluwarsa."""
    if not paste.get("expires_at"):
        return False
    expires_at = paste["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) > expires_at

def validate_url(url): return bool(url and url.strip())
    """Validasi apakah string adalah URL yang valid."""
    pattern = re.compile(
        r'^(https?://)'
        r'(\S+)'
    )
    return bool(pattern.match(url))

# ── Routes ────────────────────────────────────────────────────────────────────

@paste_bp.route("/")
def index():
    """Halaman utama — tampilkan 10 paste publik terbaru."""
    db = get_db()
    try:
        result = (
            db.table("snippets")
            .select("slug, title, paste_type, language, created_at, view_count, user_id")
            .eq("visibility", "public")
            .is_("expires_at", "null")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        # Juga ambil yang belum expired
        result2 = (
            db.table("snippets")
            .select("slug, title, paste_type, language, created_at, view_count, user_id")
            .eq("visibility", "public")
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        pastes = result.data + result2.data
        # Urutkan dan ambil 10 terbaru
        pastes.sort(key=lambda x: x["created_at"], reverse=True)
        pastes = pastes[:10]
    except Exception:
        pastes = []

    return render_template("index.html", pastes=pastes)

@paste_bp.route("/buat", methods=["GET", "POST"])
def create():
    """Halaman buat paste baru."""
    if request.method == "POST":
        db = get_db()

        # Ambil data dari form
        paste_type = request.form.get("paste_type", "text")
        title = request.form.get("title", "").strip() or None
        content = request.form.get("content", "").strip()
        language = request.form.get("language", "plaintext") if paste_type == "code" else None
        visibility = request.form.get("visibility", "public")
        expiry = request.form.get("expiry", "never")
        burn_after_read = request.form.get("burn_after_read") == "on"
        password = request.form.get("password", "").strip()

        # Validasi konten wajib ada
        if not content:
            flash("Konten paste tidak boleh kosong.", "error")
            return render_template("create.html")

        # Validasi URL untuk tipe link
        if paste_type == "link":
            if not validate_url(content):
                flash("URL tidak valid. Pastikan diawali dengan http:// atau https://", "error")
                return render_template("create.html")

        # Hash password jika private
        password_hash = None
        if visibility == "private" and password:
            password_hash = generate_password_hash(password)
        elif visibility == "private" and not password:
            flash("Paste privat membutuhkan password.", "error")
            return render_template("create.html")

        # Buat slug unik
        slug = generate_slug()
        # Pastikan slug belum dipakai (coba max 5x)
        for _ in range(5):
            existing = db.table("snippets").select("id").eq("slug", slug).execute()
            if not existing.data:
                break
            slug = generate_slug()

        # Hitung waktu kedaluwarsa
        expires_at = calculate_expiry(expiry)

        # Ambil user_id jika sudah login
        user_id = session.get("user_id")

        # Simpan ke Supabase
        try:
            db.table("snippets").insert({
                "slug": slug,
                "title": title,
                "content": content,
                "paste_type": paste_type,
                "language": language,
                "visibility": visibility,
                "password_hash": password_hash,
                "expires_at": expires_at,
                "burn_after_read": burn_after_read,
                "view_count": 0,
                "user_id": user_id,
            }).execute()
        except Exception as e:
            flash("Gagal menyimpan paste. Coba lagi.", "error")
            return render_template("create.html")

        flash("Paste berhasil dibuat!", "success")
        return redirect(url_for("paste.view_paste", slug=slug))

    return render_template("create.html")

@paste_bp.route("/p/<slug>")
def view_paste(slug):
    """Lihat paste berdasarkan slug."""
    db = get_db()

    # Ambil paste dari database
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        flash("Paste tidak ditemukan.", "error")
        return render_template("404.html"), 404

    paste = result.data[0]

    # Cek kedaluwarsa
    if is_expired(paste):
        return render_template("expired.html", paste=paste)

    # Cek visibilitas private — minta password
    if paste["visibility"] == "private":
        # Cek apakah password sudah diverifikasi di session
        verified_key = f"paste_verified_{slug}"
        is_owner = session.get("user_id") and session["user_id"] == paste.get("user_id")
        if not is_owner and not session.get(verified_key):
            return redirect(url_for("paste.password_check", slug=slug))

    # Ambil info user pembuat (jika ada)
    creator = None
    if paste.get("user_id"):
        user_result = db.table("pastely_users").select("username, created_at").eq("id", paste["user_id"]).execute()
        if user_result.data:
            creator = user_result.data[0]

    # Tangani tipe link — redirect preview
    if paste["paste_type"] == "link":
        # Update view count dulu
        db.table("snippets").update({"view_count": paste["view_count"] + 1}).eq("slug", slug).execute()
        # Burn after read
        if paste["burn_after_read"]:
            db.table("snippets").delete().eq("slug", slug).execute()
        return render_template("redirect_preview.html", paste=paste, url=paste["content"])

    # Update view count
    db.table("snippets").update({"view_count": paste["view_count"] + 1}).eq("slug", slug).execute()
    paste["view_count"] += 1

    # Burn after read — hapus setelah ditampilkan
    burn = paste["burn_after_read"]

    if burn:
        db.table("snippets").delete().eq("slug", slug).execute()

    return render_template("view.html", paste=paste, creator=creator, burned=burn)

@paste_bp.route("/p/<slug>/raw")
def raw_paste(slug):
    """Tampilkan konten paste sebagai teks mentah."""
    db = get_db()
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        return "Paste tidak ditemukan.", 404

    paste = result.data[0]

    if is_expired(paste):
        return "Paste ini sudah kedaluwarsa.", 410

    # Cek private
    if paste["visibility"] == "private":
        verified_key = f"paste_verified_{slug}"
        is_owner = session.get("user_id") and session["user_id"] == paste.get("user_id")
        if not is_owner and not session.get(verified_key):
            return "Paste ini dilindungi password. Buka melalui halaman utama.", 403

    return Response(paste["content"], mimetype="text/plain; charset=utf-8")

@paste_bp.route("/p/<slug>/password", methods=["GET", "POST"])
def password_check(slug):
    """Verifikasi password untuk paste privat."""
    db = get_db()
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        flash("Paste tidak ditemukan.", "error")
        return render_template("404.html"), 404

    paste = result.data[0]

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(paste["password_hash"], password):
            # Simpan status terverifikasi di session
            session[f"paste_verified_{slug}"] = True
            return redirect(url_for("paste.view_paste", slug=slug))
        else:
            flash("Password salah. Coba lagi.", "error")

    return render_template("password.html", paste=paste)

@paste_bp.route("/p/<slug>/hapus", methods=["POST"])
def delete_paste(slug):
    """Hapus paste — hanya owner yang login."""
    if not session.get("user_id"):
        flash("Kamu harus login untuk menghapus paste.", "error")
        return redirect(url_for("paste.view_paste", slug=slug))

    db = get_db()
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        flash("Paste tidak ditemukan.", "error")
        return redirect(url_for("paste.index"))

    paste = result.data[0]
    if paste.get("user_id") != session["user_id"]:
        flash("Kamu tidak punya izin untuk menghapus paste ini.", "error")
        return redirect(url_for("paste.view_paste", slug=slug))

    db.table("snippets").delete().eq("slug", slug).execute()
    flash("Paste berhasil dihapus.", "success")
    return redirect(url_for("dashboard.dashboard"))

@paste_bp.route("/p/<slug>/edit", methods=["GET", "POST"])
def edit_paste(slug):
    """Edit paste — hanya owner yang login."""
    if not session.get("user_id"):
        flash("Kamu harus login untuk mengedit paste.", "error")
        return redirect(url_for("auth.auth"))

    db = get_db()
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        flash("Paste tidak ditemukan.", "error")
        return render_template("404.html"), 404

    paste = result.data[0]
    if paste.get("user_id") != session["user_id"]:
        flash("Kamu tidak punya izin untuk mengedit paste ini.", "error")
        return redirect(url_for("paste.view_paste", slug=slug))

    if request.method == "POST":
        title = request.form.get("title", "").strip() or None
        content = request.form.get("content", "").strip()
        language = request.form.get("language", "plaintext") if paste["paste_type"] == "code" else None
        visibility = request.form.get("visibility", "public")
        password = request.form.get("password", "").strip()

        if not content:
            flash("Konten tidak boleh kosong.", "error")
            return render_template("create.html", paste=paste, edit=True)

        # Validasi URL jika tipe link
        if paste["paste_type"] == "link" and not validate_url(content):
            flash("URL tidak valid.", "error")
            return render_template("create.html", paste=paste, edit=True)

        update_data = {
            "title": title,
            "content": content,
            "language": language,
            "visibility": visibility,
        }

        # Update password jika private
        if visibility == "private":
            if password:
                update_data["password_hash"] = generate_password_hash(password)
            elif not paste.get("password_hash"):
                flash("Paste privat membutuhkan password.", "error")
                return render_template("create.html", paste=paste, edit=True)
        else:
            update_data["password_hash"] = None

        db.table("snippets").update(update_data).eq("slug", slug).execute()
        flash("Paste berhasil diperbarui.", "success")
        return redirect(url_for("paste.view_paste", slug=slug))

    return render_template("create.html", paste=paste, edit=True)

@paste_bp.route("/p/<slug>/fork")
def fork_paste(slug):
    """Clone/fork paste ke halaman buat dengan konten yang sudah terisi."""
    db = get_db()
    result = db.table("snippets").select("*").eq("slug", slug).execute()
    if not result.data:
        flash("Paste tidak ditemukan.", "error")
        return render_template("404.html"), 404

    paste = result.data[0]

    if is_expired(paste):
        flash("Tidak bisa fork paste yang sudah kedaluwarsa.", "error")
        return redirect(url_for("paste.index"))

    # Render halaman buat dengan data paste yang di-fork
    return render_template("create.html", fork=paste)

@paste_bp.route("/cari")
def search():
    """Cari paste publik berdasarkan judul."""
    query = request.args.get("q", "").strip()
    pastes = []

    if query:
        db = get_db()
        try:
            result = (
                db.table("snippets")
                .select("slug, title, paste_type, language, created_at, view_count")
                .eq("visibility", "public")
                .ilike("title", f"%{query}%")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            # Filter expired
            pastes = [p for p in result.data if not is_expired(p)]
        except Exception:
            pastes = []

    return render_template("search.html", pastes=pastes, query=query)
