"""
Smart Classroom Issue Reporting System
----------------------------------------
A beginner-friendly Flask web app that lets students scan a classroom QR code,
report a problem (with an optional photo), and get a unique Complaint ID.

Run with:  python app.py
Then open: http://127.0.0.1:5000/report?room=101
"""

import os
import sqlite3
from datetime import datetime

from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Basic configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "change-this-secret-key-later"  # only needed if you add flash messages/sessions
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB max upload size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# The categories shown as a dropdown on the report form
ISSUE_CATEGORIES = [
    "Cleanliness",
    "Broken Desk/Bench",
    "Fan Problem",
    "Light Problem",
    "Electrical Problem",
    "Projector Problem",
    "Computer/IT Problem",
    "Water Problem",
    "Door/Window Problem",
    "Infrastructure Damage",
    "Other",
]

# The status values a complaint can move through
STATUS_OPTIONS = ["Pending", "In Progress", "Resolved"]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Open a new database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["name"]
    return conn


def init_db():
    """Create the tables if they don't exist yet, and seed empty contact settings."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id    TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            student_id      TEXT NOT NULL,
            branch          TEXT NOT NULL,
            year            TEXT NOT NULL,
            section         TEXT NOT NULL,
            classroom       TEXT NOT NULL,
            category        TEXT NOT NULL,
            description     TEXT NOT NULL,
            photo_filename  TEXT,
            status          TEXT NOT NULL DEFAULT 'Pending',
            created_at      TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    # These are the "configurable later" contact fields. They start empty on purpose.
    defaults = {
        "responsible_person": "",
        "contact_phone": "",
        "contact_email": "",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_complaint_id():
    """
    Builds an ID like SCR-2026-0001.
    It looks at the highest number already used this year and adds 1.
    """
    year = datetime.now().year
    conn = get_db()
    row = conn.execute(
        "SELECT complaint_id FROM complaints WHERE complaint_id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"SCR-{year}-%",),
    ).fetchone()
    conn.close()

    if row:
        last_number = int(row["complaint_id"].split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"SCR-{year}-{new_number:04d}"


# ---------------------------------------------------------------------------
# Student-facing routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    # Anyone hitting the bare site gets sent to the report form
    return redirect(url_for("report_form"))


@app.route("/report", methods=["GET"])
def report_form():
    """
    This is the page the QR code points to.
    The classroom number comes from the URL, e.g. /report?room=101
    """
    classroom = request.args.get("room", "")
    return render_template("report.html", categories=ISSUE_CATEGORIES, classroom=classroom)


@app.route("/submit", methods=["POST"])
def submit_complaint():
    name = request.form.get("name", "").strip()
    student_id = request.form.get("student_id", "").strip()
    branch = request.form.get("branch", "").strip()
    year = request.form.get("year", "").strip()
    section = request.form.get("section", "").strip()
    classroom = request.form.get("classroom", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    required = [name, student_id, branch, year, section, classroom, category, description]
    if not all(required):
        return render_template(
            "report.html",
            categories=ISSUE_CATEGORIES,
            classroom=classroom,
            error="Please fill in every field before submitting.",
            form_data=request.form,
        )

    # Handle the optional photo upload
    photo_filename = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        if not allowed_file(photo.filename):
            return render_template(
                "report.html",
                categories=ISSUE_CATEGORIES,
                classroom=classroom,
                error="Photo must be an image file (png, jpg, jpeg, gif, or webp).",
                form_data=request.form,
            )
        safe_name = secure_filename(photo.filename)
        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
        photo_filename = unique_name

    complaint_id = generate_complaint_id()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    conn.execute(
        """
        INSERT INTO complaints
            (complaint_id, name, student_id, branch, year, section, classroom,
             category, description, photo_filename, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        """,
        (
            complaint_id, name, student_id, branch, year, section, classroom,
            category, description, photo_filename, created_at,
        ),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("success", complaint_id=complaint_id))


@app.route("/success/<complaint_id>")
def success(complaint_id):
    conn = get_db()
    complaint = conn.execute(
        "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()
    conn.close()

    if not complaint:
        return redirect(url_for("report_form"))

    return render_template("success.html", complaint=complaint)


# ---------------------------------------------------------------------------
# Simple admin/demo routes (no login yet — see README for notes on this)
# ---------------------------------------------------------------------------
@app.route("/admin/complaints")
def admin_complaints():
    conn = get_db()
    complaints = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_complaints.html", complaints=complaints, status_options=STATUS_OPTIONS)


@app.route("/admin/update_status/<complaint_id>", methods=["POST"])
def update_status(complaint_id):
    new_status = request.form.get("status", "Pending")
    if new_status not in STATUS_OPTIONS:
        new_status = "Pending"
    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status = ? WHERE complaint_id = ?",
        (new_status, complaint_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_complaints"))


@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    conn = get_db()
    saved = False

    if request.method == "POST":
        responsible_person = request.form.get("responsible_person", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()
        contact_email = request.form.get("contact_email", "").strip()

        conn.execute("UPDATE settings SET value = ? WHERE key = 'responsible_person'", (responsible_person,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'contact_phone'", (contact_phone,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'contact_email'", (contact_email,))
        conn.commit()
        saved = True

    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    settings = {row["key"]: row["value"] for row in rows}

    return render_template("admin_settings.html", settings=settings, saved=saved)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
