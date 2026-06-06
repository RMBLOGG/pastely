from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, session, current_app
)
from functools import wraps

dashboard_bp = Blueprint("dashboard", __name__)

def get_db():
    return current_app.supabase

def login_required(f):
    """Decorator: pastikan user sudah login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Kamu harus login untuk mengakses halaman ini.", "error")
            return redirect(url_for("auth.auth"))
        return f(*args, **kwargs)
    return decorated

# ── Routes ────────────────────────────────────────────────────────────────────

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard — daftar semua paste milik user."""
    db = get_db()
    user_id = session["user_id"]

    # Ambil semua paste milik user (semua visibilitas)
    result = (
        db.table("snippets")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    pastes = result.data if result.data else []

    # Statistik
    total_paste = len(pastes)
    total_views = sum(p.get("view_count", 0) for p in pastes)

    # Kelompokkan berdasarkan visibilitas
    public_pastes = [p for p in pastes if p["visibility"] == "public"]
    unlisted_pastes = [p for p in pastes if p["visibility"] == "unlisted"]
    private_pastes = [p for p in pastes if p["visibility"] == "private"]

    return render_template(
        "dashboard.html",
        pastes=pastes,
        total_paste=total_paste,
        total_views=total_views,
        public_count=len(public_pastes),
        unlisted_count=len(unlisted_pastes),
        private_count=len(private_pastes),
    )
