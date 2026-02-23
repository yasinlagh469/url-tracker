from flask import Flask, redirect, request, jsonify, make_response
import sqlite3
import json
import hashlib
from datetime import datetime
import os
import uuid

app = Flask(__name__)

DB = "clicks.db"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # create table if not exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS clicks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_name TEXT,
        visitor_hash TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOAD LINKS ----------------
def load_links():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading products.json:", e)
        return {}

# ---------------- UNIQUE VISITOR ----------------
def get_visitor_id():
    # check if visitor_id cookie exists
    visitor_id = request.cookies.get("visitor_id")
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
    return visitor_id

# ---------------- TRACK + REDIRECT ----------------
@app.route("/go/<name>")
def go(name):
    links = load_links()
    if name not in links:
        return "Link not found", 404

    visitor = get_visitor_id()
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # check unique
    c.execute("""
        SELECT 1 FROM clicks
        WHERE link_name=? AND visitor_hash=?
    """, (name, visitor))

    exists = c.fetchone()

    if not exists:
        c.execute("""
            INSERT INTO clicks(link_name, visitor_hash, timestamp)
            VALUES (?, ?, ?)
        """, (name, visitor, datetime.utcnow()))
        conn.commit()

    conn.close()

    response = make_response(redirect(links[name]))

    # set cookie for uniqueness (1 year)
    response.set_cookie(
        "visitor_id",
        visitor,
        max_age=60*60*24*365
    )

    return response

# ---------------- STATS ----------------
@app.route("/stats")
def stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT link_name, COUNT(*) as unique_clicks
        FROM clicks
        GROUP BY link_name
    """)

    rows = c.fetchall()
    conn.close()

    result = {row[0]: row[1] for row in rows}
    return jsonify(result)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
