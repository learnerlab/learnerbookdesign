#!/usr/bin/env python3
"""Book Cover Swiper - Tinder for book cover design inspiration."""
from flask import Flask, render_template, jsonify, request, redirect
from database import (
    init_db, get_unswiped_covers, record_swipe, get_liked_covers,
    get_analytics, update_cover_designer,
    create_user, get_user_by_token, get_user_by_id, list_users,
)

app = Flask(__name__)

COOKIE_NAME = "swiper_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def current_user():
    return get_user_by_token(request.cookies.get(COOKIE_NAME))


def _set_profile_cookie(resp, user):
    resp.set_cookie(COOKIE_NAME, user["token"], max_age=COOKIE_MAX_AGE,
                    httponly=True, samesite="Lax")
    return resp


# Lightweight endpoint for uptime pings — keeps Render's free tier from
# spinning down without touching the database.
@app.route("/health")
def health():
    return "ok", 200


# --- Pages ---

@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect("/profiles")
    return render_template("index.html", user=user)


@app.route("/likes")
def likes_page():
    user = current_user()
    if not user:
        return redirect("/profiles")
    return render_template("likes.html", user=user)


@app.route("/analytics")
def analytics_page():
    user = current_user()
    if not user:
        return redirect("/profiles")
    return render_template("analytics.html", user=user)


@app.route("/profiles")
def profiles_page():
    return render_template("profiles.html", user=current_user())


# --- Profile API ---

@app.route("/api/profiles", methods=["GET"])
def api_list_profiles():
    return jsonify(list_users())


@app.route("/api/profiles", methods=["POST"])
def api_create_profile():
    data = request.get_json()
    name = (data.get("name") or "").strip() if data else ""
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if len(name) > 40:
        return jsonify({"error": "Name too long (40 chars max)"}), 400
    user = create_user(name)
    if not user:
        return jsonify({"error": "That name is taken — pick it from the list instead"}), 409
    resp = jsonify({"status": "ok", "id": user["id"], "name": user["name"]})
    return _set_profile_cookie(resp, user)


@app.route("/api/profiles/<int:user_id>/select", methods=["POST"])
def api_select_profile(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Profile not found"}), 404
    resp = jsonify({"status": "ok", "id": user["id"], "name": user["name"]})
    return _set_profile_cookie(resp, user)


# --- Swiping API (all scoped to the current profile) ---

@app.route("/api/covers", methods=["GET"])
def api_covers():
    """Get a batch of covers the current profile hasn't swiped yet."""
    user = current_user()
    if not user:
        return jsonify({"error": "No profile selected"}), 401
    limit = request.args.get("limit", 20, type=int)
    covers = get_unswiped_covers(user["id"], limit=min(limit, 50))
    return jsonify(covers)


@app.route("/api/swipe", methods=["POST"])
def api_swipe():
    """Record a swipe action for the current profile."""
    user = current_user()
    if not user:
        return jsonify({"error": "No profile selected"}), 401
    data = request.get_json()
    if not data or "cover_id" not in data or "action" not in data:
        return jsonify({"error": "Missing cover_id or action"}), 400

    action = data["action"]
    if action not in ("like", "dislike", "superlike"):
        return jsonify({"error": "Invalid action"}), 400

    record_swipe(data["cover_id"], action, user["id"])
    return jsonify({"status": "ok"})


@app.route("/api/likes", methods=["GET"])
def api_likes():
    """Get the current profile's liked covers."""
    user = current_user()
    if not user:
        return jsonify({"error": "No profile selected"}), 401
    return jsonify(get_liked_covers(user["id"]))


@app.route("/api/covers/<int:cover_id>/designer", methods=["PUT"])
def api_update_designer(cover_id):
    """Update the designer for a cover (shared across all profiles)."""
    data = request.get_json()
    if not data or "designer" not in data:
        return jsonify({"error": "Missing designer"}), 400
    designer = data["designer"].strip()
    if not designer:
        return jsonify({"error": "Designer cannot be empty"}), 400
    if update_cover_designer(cover_id, designer):
        return jsonify({"status": "ok", "designer": designer})
    return jsonify({"error": "Cover not found"}), 404


@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    """Get analytics for the current profile."""
    user = current_user()
    if not user:
        return jsonify({"error": "No profile selected"}), 401
    return jsonify(get_analytics(user["id"]))


if __name__ == "__main__":
    init_db()

    # Run scraper in background so the app binds to the port immediately
    # (Render will kill the process if it doesn't bind within ~60 seconds)
    import threading
    import subprocess

    def run_scraper():
        subprocess.run(["python", "scrape.py"])

    threading.Thread(target=run_scraper, daemon=True).start()

    print("Starting Book Cover Swiper...")
    print("Scraper running in background — covers will appear as they're fetched.")
    app.run(host='0.0.0.0', port=5000, debug=False)
