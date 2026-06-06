from datetime import datetime, timezone
from flask import Blueprint, jsonify, session, request, render_template, current_app

social_bp = Blueprint("social", __name__)

def get_db():
    return current_app.supabase

# ── Like / Unlike paste ───────────────────────────────────────────────────────

@social_bp.route("/api/like/<slug>", methods=["POST"])
def toggle_like(slug):
    if not session.get("user_id"):
        return jsonify({"error": "Login dulu"}), 401

    db = get_db()
    user_id = session["user_id"]

    # Cari paste
    paste = db.table("snippets").select("id, like_count").eq("slug", slug).single().execute()
    if not paste.data:
        return jsonify({"error": "Paste tidak ditemukan"}), 404

    paste_id = paste.data["id"]
    like_count = paste.data.get("like_count") or 0

    # Cek apakah sudah like
    existing = db.table("paste_likes") \
        .select("id") \
        .eq("user_id", user_id) \
        .eq("paste_id", paste_id) \
        .execute()

    if existing.data:
        # Unlike
        db.table("paste_likes") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("paste_id", paste_id) \
            .execute()
        new_count = max(0, like_count - 1)
        liked = False
    else:
        # Like
        db.table("paste_likes").insert({
            "user_id": user_id,
            "paste_id": paste_id,
        }).execute()
        new_count = like_count + 1
        liked = True

    # Update cache like_count
    db.table("snippets").update({"like_count": new_count}).eq("id", paste_id).execute()

    return jsonify({"liked": liked, "like_count": new_count})


# ── Komentar ──────────────────────────────────────────────────────────────────

@social_bp.route("/api/comment/<slug>", methods=["POST"])
def add_comment(slug):
    if not session.get("user_id"):
        return jsonify({"error": "Login dulu"}), 401

    db = get_db()
    content = request.json.get("content", "").strip()

    if not content:
        return jsonify({"error": "Komentar tidak boleh kosong"}), 400
    if len(content) > 1000:
        return jsonify({"error": "Komentar maksimal 1000 karakter"}), 400

    paste = db.table("snippets").select("id, visibility").eq("slug", slug).single().execute()
    if not paste.data or paste.data["visibility"] != "public":
        return jsonify({"error": "Paste tidak ditemukan"}), 404

    comment = db.table("paste_comments").insert({
        "paste_id": paste.data["id"],
        "user_id": session["user_id"],
        "content": content,
    }).execute()

    return jsonify({
        "id": comment.data[0]["id"],
        "username": session["username"],
        "content": content,
        "created_at": comment.data[0]["created_at"],
    })


@social_bp.route("/api/comment/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    if not session.get("user_id"):
        return jsonify({"error": "Login dulu"}), 401

    db = get_db()
    comment = db.table("paste_comments") \
        .select("id, user_id") \
        .eq("id", comment_id) \
        .single().execute()

    if not comment.data:
        return jsonify({"error": "Komentar tidak ditemukan"}), 404
    if comment.data["user_id"] != session["user_id"]:
        return jsonify({"error": "Bukan komentar kamu"}), 403

    db.table("paste_comments").delete().eq("id", comment_id).execute()
    return jsonify({"deleted": True})


# ── Follow / Unfollow ─────────────────────────────────────────────────────────

@social_bp.route("/api/follow/<username>", methods=["POST"])
def toggle_follow(username):
    if not session.get("user_id"):
        return jsonify({"error": "Login dulu"}), 401

    db = get_db()
    follower_id = session["user_id"]

    # Cari target user
    target = db.table("users").select("id").eq("username", username).single().execute()
    if not target.data:
        return jsonify({"error": "User tidak ditemukan"}), 404

    following_id = target.data["id"]
    if follower_id == following_id:
        return jsonify({"error": "Tidak bisa follow diri sendiri"}), 400

    # Cek existing follow
    existing = db.table("user_follows") \
        .select("id") \
        .eq("follower_id", follower_id) \
        .eq("following_id", following_id) \
        .execute()

    if existing.data:
        db.table("user_follows") \
            .delete() \
            .eq("follower_id", follower_id) \
            .eq("following_id", following_id) \
            .execute()
        following = False
    else:
        db.table("user_follows").insert({
            "follower_id": follower_id,
            "following_id": following_id,
        }).execute()
        following = True

    # Hitung followers terbaru
    count = db.table("user_follows") \
        .select("id", count="exact") \
        .eq("following_id", following_id) \
        .execute()

    return jsonify({"following": following, "follower_count": count.count or 0})


# ── Feed: paste dari orang yang lo follow ─────────────────────────────────────

@social_bp.route("/following")
def following_feed():
    if not session.get("user_id"):
        from flask import redirect, url_for, flash
        flash("Login dulu untuk melihat feed.", "info")
        return redirect(url_for("auth.auth"))

    db = get_db()
    user_id = session["user_id"]

    # Ambil list following
    follows = db.table("user_follows") \
        .select("following_id") \
        .eq("follower_id", user_id) \
        .execute()

    following_ids = [f["following_id"] for f in follows.data]

    pastes = []
    if following_ids:
        # Ambil paste publik dari user yang difollow
        result = db.table("snippets") \
            .select("slug, title, paste_type, language, created_at, view_count, like_count, user_id, users(username)") \
            .eq("visibility", "public") \
            .in_("user_id", following_ids) \
            .order("created_at", desc=True) \
            .limit(30) \
            .execute()
        pastes = result.data or []

    return render_template("following.html", pastes=pastes, following_count=len(following_ids))
