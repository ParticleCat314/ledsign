#!/usr/bin/env python3

from datetime import datetime
from uuid import uuid4

from flask import Flask, request, redirect, url_for, render_template_string, flash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

import os
import logging
from zoneinfo import ZoneInfo

APP_TITLE = "LED Sign Scheduler"
LOCAL_TZ = ZoneInfo(os.environ.get("LED_SIGN_TZ", "Australia/Adelaide"))
JOBS_DB_URL = os.environ.get("LED_SIGN_JOBS_DB", "sqlite:///jobs.sqlite")

app = Flask(__name__)
app.secret_key = os.environ.get("LED_SIGN_SECRET", "dev-only-secret")  # replace in production



# APScheduler with persistent job store
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=JOBS_DB_URL)},
    timezone=LOCAL_TZ,
    daemon=True,
)
scheduler.start()

# -------------------------
# SIGN CONTROL (stub hooks)
# Replace the bodies of these with your real library/program calls
# -------------------------

def sign_on():
    # TODO: integrate your real sign control here
    # e.g., your_library.turn_on() or subprocess.run(["/usr/local/bin/signctl", "on"])
    app.logger.info("SIGN: ON")
    print(f"[{datetime.now(LOCAL_TZ)}] SIGN ON")

def sign_off():
    # TODO: integrate your real sign control here
    app.logger.info("SIGN: OFF")
    print(f"[{datetime.now(LOCAL_TZ)}] SIGN OFF")

def set_sign_content(text: str):
    # TODO: integrate your real sign content update here
    app.logger.info("SIGN: UPDATE CONTENT -> %r", text)
    print(f"[{datetime.now(LOCAL_TZ)}] UPDATE CONTENT: {text}")

# -------------------------
# HELPERS
# -------------------------

def job_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"

def parse_hhmm(s: str):
    # Returns (hour, minute) or raises ValueError
    parts = s.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Time must be HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Hour 0-23 and minute 0-59 required")
    return hour, minute

def list_jobs():
    # Return jobs grouped by type hints in name
    jobs = scheduler.get_jobs()
    return sorted(jobs, key=lambda j: (j.next_run_time or datetime.max))



INDEX_TEMPLATE = open("templates/index.html").read()


@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        INDEX_TEMPLATE,
        title=APP_TITLE,
        tz=str(LOCAL_TZ),
        tzinfo=LOCAL_TZ,
        now=datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        jobs=list_jobs(),
    )

@app.route("/schedule", methods=["POST"])
def save_schedule():
    on_time = request.form.get("on_time", "").strip()
    off_time = request.form.get("off_time", "").strip()
    days = request.form.getlist("days")  # list of 'mon'...'sun'

    if not on_time or not off_time or not days:
        flash("Please provide ON time, OFF time, and at least one day.", "err")
        return redirect(url_for("index"))

    try:
        on_h, on_m = parse_hhmm(on_time)
        off_h, off_m = parse_hhmm(off_time)
    except ValueError as e:
        flash(str(e), "err")
        return redirect(url_for("index"))

    # Map day strings to CronTrigger day_of_week values
    valid_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for d in days:
        if d not in valid_days:
            flash("Invalid day selected.", "err")
            return redirect(url_for("index"))

    # Create ON jobs
    for d in days:
        jid = job_id(f"on-{d}-{on_h:02d}{on_m:02d}")
        scheduler.add_job(
            sign_on,
            trigger=CronTrigger(day_of_week=d, hour=on_h, minute=on_m, timezone=LOCAL_TZ),
            id=jid,
            name=f"on-{d}",
            replace_existing=False,
            misfire_grace_time=60,
            coalesce=True,
        )
    # Create OFF jobs
    for d in days:
        jid = job_id(f"off-{d}-{off_h:02d}{off_m:02d}")
        scheduler.add_job(
            sign_off,
            trigger=CronTrigger(day_of_week=d, hour=off_h, minute=off_m, timezone=LOCAL_TZ),
            id=jid,
            name=f"off-{d}",
            replace_existing=False,
            misfire_grace_time=60,
            coalesce=True,
        )

    flash("Daily ON/OFF jobs saved.", "ok")
    return redirect(url_for("index"))

@app.route("/jobs/<job_id>/delete", methods=["GET"])
def delete_job(job_id):
    try:
        scheduler.remove_job(job_id)
        flash(f"Deleted job {job_id}.", "ok")
    except Exception as e:
        flash(f"Could not delete job: {e}", "err")
    return redirect(url_for("index"))

@app.route("/daily/clear", methods=["GET"])
def clear_daily():
    removed = 0
    for j in list(scheduler.get_jobs()):
        if j.name and (j.name.startswith("on-") or j.name.startswith("off-")):
            try:
                scheduler.remove_job(j.id)
                removed += 1
            except Exception:
                pass
    flash(f"Removed {removed} daily jobs.", "ok")
    return redirect(url_for("index"))

@app.route("/content/update", methods=["POST"])
def update_content():
    text = request.form.get("content", "").strip()
    if not text:
        flash("Please enter some content.", "err")
        return redirect(url_for("index"))
    try:
        set_sign_content(text)
        flash("Content updated on sign.", "ok")
    except Exception as e:
        flash(f"Failed to update content: {e}", "err")
    return redirect(url_for("index"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # On Raspberry Pi, you can bind to 0.0.0.0 to reach from your LAN
    host = os.environ.get("LED_SIGN_HOST", "0.0.0.0")
    port = int(os.environ.get("LED_SIGN_PORT", "8080"))
    app.run(host=host, port=port)
