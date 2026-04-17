#!/usr/bin/env python3
"""Book Cover Swiper - Tinder for book cover design inspiration."""
import json
from flask import Flask, render_template, jsonify, request
from database import init_db, get_unswiped_covers, record_swipe, get_liked_covers, get_analytics, update_cover_designer

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/likes")
def likes_page():
    return render_template("likes.html")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")


# --- API ---

@app.route("/api/covers", methods=["GET"])
def api_covers():
    """Get a batch of unswiped covers."""
    limit = request.args.get("limit", 20, type=int)
    covers = get_unswiped_covers(limit=min(limit, 50))
    return jsonify(covers)


@app.route("/api/swipe", methods=["POST"])
def api_swipe():
    """Record a swipe action."""
    data = request.get_json()
    if not data or "cover_id" not in data or "action" not in data:
        return jsonify({"error": "Missing cover_id or action"}), 400

    action = data["action"]
    if action not in ("like", "dislike", "superlike"):
        return jsonify({"error": "Invalid action"}), 400

    record_swipe(data["cover_id"], action)
    return jsonify({"status": "ok"})


@app.route("/api/likes", methods=["GET"])
def api_likes():
    """Get all liked covers."""
    likes = get_liked_covers()
    return jsonify(likes)


@app.route("/api/covers/<int:cover_id>/designer", methods=["PUT"])
def api_update_designer(cover_id):
    """Update the designer for a cover."""
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
    """Get analytics data."""
    return jsonify(get_analytics())


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
