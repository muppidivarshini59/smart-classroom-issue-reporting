# Smart Classroom Issue Reporting System

A working B.Tech DTI prototype: students scan a QR code in a classroom, land on
a mobile-friendly report form, and submit a complaint that's saved with a
unique Complaint ID.

## 1. What's in this project

```
smart-classroom-issue-reporting/
├── app.py                        Flask app: routes, database, complaint ID logic
├── requirements.txt               Python packages needed
├── database.db                    Created automatically the first time you run app.py
├── templates/
│   ├── base.html                  Shared page shell
│   ├── report.html                Student reporting form (the QR destination)
│   ├── success.html               "Complaint Submitted" confirmation page
│   ├── admin_complaints.html      Table of all complaints (proof of storage)
│   └── admin_settings.html        Empty, configurable contact fields
└── static/
    ├── css/style.css              All styling
    └── uploads/                   Uploaded problem photos are saved here
```

## 2. How to run it

You need Python 3.8+ installed.

```bash
cd smart-classroom-issue-reporting
pip install -r requirements.txt
python app.py
```

You'll see something like `Running on http://127.0.0.1:5000`. Leave that
terminal window open while you use the app.

## 3. How to test a complaint

1. With the server running, open a browser to:
   `http://127.0.0.1:5000/report?room=101`
   Notice the page shows **Classroom 101** automatically — that's the part
   the QR code will trigger.
2. Fill in the form (name, student ID, branch, year, section — classroom is
   already locked to 101) and pick an issue category.
3. Optionally attach a photo (on a phone, this opens the camera).
4. Tap **Submit Complaint**. You'll land on a success page showing something
   like `SCR-2026-0001` and a status of **Pending**.
5. To prove it's really stored, open:
   `http://127.0.0.1:5000/admin/complaints`
   You'll see your submission in a table, with the photo thumbnail if you
   added one.
6. Try submitting a second complaint from a different room, e.g.
   `http://127.0.0.1:5000/report?room=102` — the Complaint ID increments to
   `SCR-2026-0002`, and both rows show up in the admin table.
7. From the admin table you can also change a complaint's status
   (Pending → In Progress → Resolved) using the dropdown in the last column
   — handy for showing the full lifecycle in your presentation.

## 4. How the data is stored

Everything is saved in a local SQLite database file, `database.db`, created
automatically the first time you run `app.py`. SQLite needs no separate
server or setup — the whole database is just that one file, which makes it
ideal for a college project demo.

Two tables are created:

- **complaints** — one row per submission: complaint ID, student details,
  classroom, category, description, photo filename, status, and timestamp.
- **settings** — the three configurable contact fields (responsible person,
  phone, email). They start empty on purpose.

Photos are saved as image files in `static/uploads/`, and the database just
stores each photo's filename so it can be shown next to the right complaint.

To peek at the raw data (optional, not required for your demo), you can open
`database.db` with any SQLite viewer, e.g. [DB Browser for SQLite](https://sqlitebrowser.org/).

## 5. Configuring the contact system (later)

Visit `http://127.0.0.1:5000/admin/settings` any time to fill in:

- Responsible Person / Department
- Phone Number
- Email

These are saved to the `settings` table. Right now nothing reads or displays
them yet — that's intentional, since you said the recipient system should
stay configurable and phone numbers shouldn't be in the QR code. When you're
ready to notify someone (e.g. show their name on the success page, or send an
email), the app just needs to start reading these three values — **no QR
code, form, or classroom setup has to change.**

## 6. Creating the QR codes (once the site is working)

Each classroom's QR code just needs to encode a URL in this pattern:

```
https://<your-deployed-domain>/report?room=101
https://<your-deployed-domain>/report?room=102
```

While testing locally, you can use `http://127.0.0.1:5000/report?room=101`,
but that only works on the same computer running the server — for a real
demo, phones need a reachable address (see options below).

**To actually generate the QR image**, any of these work and require no new
libraries in this project:

- Free online generators such as `qrcode-monkey.com` or `goqr.me` — paste the
  URL, download the PNG, print it, stick it in the classroom.
- If you'd rather generate them in Python, install one package
  (`pip install qrcode[pil]`) and run a short script per room — ask me and
  I'll write that script for you if you want it included in this project.

No phone numbers or emails are ever encoded in the QR — it only ever points
to the `/report?room=XXX` link, exactly as required.

## 7. Deploying so classmates/phones can actually reach it

Running on `127.0.0.1` only works on your own laptop. For your presentation
or a real pilot, you have two easy options:

- **Same Wi-Fi demo**: run `python app.py`, find your laptop's local IP
  (e.g. `192.168.1.5`), and use `http://192.168.1.5:5000/report?room=101` in
  the QR codes — any phone on the same Wi-Fi can reach it.
- **Public link**: deploy to a free tier of a host like Render, PythonAnywhere,
  or Railway. Ask me when you're ready and I'll walk you through it.

## 8. A note on the admin pages for your presentation

`/admin/complaints` and `/admin/settings` currently have no login — that's
fine for a prototype demo, but mention in your report that adding an admin
password would be a next step before any real deployment.
