from flask import Flask, render_template
from config import Config
from supabase import create_client, Client
from zoneinfo import ZoneInfo
from datetime import datetime

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inisialisasi klien Supabase
supabase: Client = create_client(
    app.config["SUPABASE_URL"],
    app.config["SUPABASE_KEY"]
)

# Timezone WIB untuk digunakan di seluruh aplikasi
WIB = ZoneInfo("Asia/Jakarta")

# Simpan supabase client di app untuk diakses route
app.supabase = supabase
app.WIB = WIB

# Register blueprint dari masing-masing modul route
from routes.paste import paste_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp

app.register_blueprint(paste_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)

# ── Template filters ──────────────────────────────────────────────────────────

@app.template_filter("format_wib")
def format_wib(dt):
    """Konversi datetime UTC ke format tampilan WIB."""
    if dt is None:
        return "—"
    # Jika string, parse dulu
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    # Konversi ke WIB
    dt_wib = dt.astimezone(WIB)
    # Format: "6 Juni 2025, 14:30 WIB"
    bulan = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{dt_wib.day} {bulan[dt_wib.month]} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"

@app.template_filter("relative_time")
def relative_time(dt):
    """Tampilkan waktu relatif seperti '2 jam yang lalu'."""
    if dt is None:
        return "—"
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    now = datetime.now(WIB)
    dt_wib = dt.astimezone(WIB)
    diff = now - dt_wib
    seconds = int(diff.total_seconds())
    if seconds < 0:
        # Waktu di masa depan (expiry)
        seconds = abs(seconds)
        if seconds < 60:
            return f"dalam {seconds} detik"
        elif seconds < 3600:
            return f"dalam {seconds // 60} menit"
        elif seconds < 86400:
            return f"dalam {seconds // 3600} jam"
        elif seconds < 2592000:
            return f"dalam {seconds // 86400} hari"
        else:
            return f"dalam {seconds // 2592000} bulan"
    else:
        if seconds < 60:
            return "baru saja"
        elif seconds < 3600:
            return f"{seconds // 60} menit yang lalu"
        elif seconds < 86400:
            return f"{seconds // 3600} jam yang lalu"
        elif seconds < 2592000:
            return f"{seconds // 86400} hari yang lalu"
        else:
            return f"{seconds // 2592000} bulan yang lalu"

# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# ── Jalankan aplikasi ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
