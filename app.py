"""
Smart Classroom Issue Reporting System
----------------------------------------
A beginner-friendly Flask web app that lets students scan a classroom QR code,
report a problem (with an optional photo), and get a unique Complaint ID.

Run with: python app.py
Then open: http://127.0.0.1:5000/report?room=101
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename


# ---------------------------------------------------------------------------
# Basic configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PostgreSQL connection URL comes from Render Environment Variables
DATABASE_URL = os.environ.get("DATABASE_URL")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "change-this-secret-key-later"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB max upload size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Issue categories
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Complaint status values
# ---------------------------------------------------------------------------

STATUS_OPTIONS = ["Pending", "In Progress", "Resolved"]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open a new PostgreSQL database connection."""

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """Create the tables if they don't exist yet."""

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id              SERIAL PRIMARY KEY,
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    # Default contact settings
    defaults = {
        "responsible_person": "",
        "contact_phone": "",
        "contact_email": "",
    }

    for key, value in defaults.items():
        cursor.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO NOTHING
            """,
            (key, value),
        )

    conn.commit()
    cursor.close()
    conn.close()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def generate_complaint_id():
    """
    Builds an ID like SCR-2026-0001.
    It looks at the highest number already used this year and adds 1.
    """

    year = datetime.now().year

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT complaint_id
        FROM complaints
        WHERE complaint_id LIKE %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (f"SCR-{year}-%",),
    )

    row = cursor.fetchone()

    cursor.close()
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
    return render_template("index.html")


@app.route("/report", methods=["GET"])
def report_form():
    """
    This is the page the QR code points to.
    Example: /report?room=101
    """

    classroom = request.args.get("room", "")

    return render_template(
        "report.html",
        categories=ISSUE_CATEGORIES,
        classroom=classroom
    )


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

    required = [
        name,
        student_id,
        branch,
        year,
        section,
        classroom,
        category,
        description
    ]

    if not all(required):
        return render_template(
            "report.html",
            categories=ISSUE_CATEGORIES,
            classroom=classroom,
            error="Please fill in every field before submitting.",
            form_data=request.form,
        )

    # ---------------------------------------------------------
    # Handle optional photo upload
    # ---------------------------------------------------------

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

        unique_name = (
            f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        )

        photo.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_name
            )
        )

        photo_filename = unique_name

    # ---------------------------------------------------------
    # Create complaint
    # ---------------------------------------------------------

    complaint_id = generate_complaint_id()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO complaints
            (
                complaint_id,
                name,
                student_id,
                branch,
                year,
                section,
                classroom,
                category,
                description,
                photo_filename,
                status,
                created_at
            )
        VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Pending',
                %s
            )
        """,
        (
            complaint_id,
            name,
            student_id,
            branch,
            year,
            section,
            classroom,
            category,
            description,
            photo_filename,
            created_at,
        ),
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for(
            "success",
            complaint_id=complaint_id
        )
    )


@app.route("/success/<complaint_id>")
def success(complaint_id):

    conn = get_db()

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM complaints
        WHERE complaint_id = %s
        """,
        (complaint_id,),
    )

    complaint = cursor.fetchone()

    cursor.close()
    conn.close()

    if not complaint:
        return redirect(url_for("report_form"))

    return render_template(
        "success.html",
        complaint=complaint
    )

# ---------------------------------------------------------------------------
# Student complaint tracking
# ---------------------------------------------------------------------------

@app.route("/track", methods=["GET", "POST"])
def track_complaint():
    complaint = None
    error = None

    if request.method == "POST":
        complaint_id = request.form.get("complaint_id", "").strip().upper()

        if not complaint_id:
            error = "Please enter your Complaint ID."
        else:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                SELECT complaint_id, name, classroom, category,
                       description, status, created_at
                FROM complaints
                WHERE complaint_id = %s
                """,
                (complaint_id,)
            )

            complaint = cursor.fetchone()

            cursor.close()
            conn.close()

            if not complaint:
                error = "Complaint ID not found."

    return render_template(
        "track.html",
        complaint=complaint,
        error=error
    )
# ---------------------------------------------------------------------------
# Admin login and admin routes
# ---------------------------------------------------------------------------

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_complaints")
            )

        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(
        url_for("admin_login")
    )


def admin_required():
    return session.get("admin_logged_in") is True


@app.route("/admin/complaints")
def admin_complaints():

    conn = get_db()

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM complaints
        ORDER BY id DESC
        """
    )

    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_complaints.html",
        complaints=complaints,
        status_options=STATUS_OPTIONS
    )


@app.route("/admin/update_status/<complaint_id>", methods=["POST"])
def update_status(complaint_id):

    new_status = request.form.get(
        "status",
        "Pending"
    )

    if new_status not in STATUS_OPTIONS:
        new_status = "Pending"

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE complaints
        SET status = %s
        WHERE complaint_id = %s
        """,
        (
            new_status,
            complaint_id
        ),
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(
        url_for("admin_complaints")
    )


@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():

    conn = get_db()

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    saved = False

    if request.method == "POST":

        responsible_person = request.form.get(
            "responsible_person",
            ""
        ).strip()

        contact_phone = request.form.get(
            "contact_phone",
            ""
        ).strip()

        contact_email = request.form.get(
            "contact_email",
            ""
        ).strip()

        cursor.execute(
            """
            UPDATE settings
            SET value = %s
            WHERE key = 'responsible_person'
            """,
            (responsible_person,),
        )

        cursor.execute(
            """
            UPDATE settings
            SET value = %s
            WHERE key = 'contact_phone'
            """,
            (contact_phone,),
        )

        cursor.execute(
            """
            UPDATE settings
            SET value = %s
            WHERE key = 'contact_email'
            """,
            (contact_email,),
        )

        conn.commit()

        saved = True

    cursor.execute(
        """
        SELECT key, value
        FROM settings
        """
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    settings = {
        row["key"]: row["value"]
        for row in rows
    }

    return render_template(
        "admin_settings.html",
        settings=settings,
        saved=saved
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

init_db()


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )