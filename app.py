from sign import Sign
from sql import *
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger


### Global stuff because why not

s = Sign("Hello, World!", color=(0, 255, 0), speed=100)


scheduler = BackgroundScheduler(
    job_defaults=dict(coalesce=True, max_instances=1, misfire_grace_time=10)
)



def set_text(text, x=0, y=10, color=(255, 255, 0)):
    s.set_text(text, x, y, color)


def schedule_weekly(day_of_week, hour, minute):
    scheduler.add_job(
        set_text,
        id="weekly_message",
        trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
        kwargs={"text": "Weekly Message!", "x": 1, "y": 10, "color": (0, 0, 255)},
        replace_existing=True,
    )
    ### Now we add to sql db

    insert_job("weekly_message", payload=f"{day_of_week} {hour}:{minute}")


def main():

    print("Initializing database…")
    init_db()


    scheduler.add_job(
        set_text,
        id="goose",
        trigger=DateTrigger(run_date=datetime.now() + timedelta(seconds=10)),
        kwargs={"text": "Honk!", "x": 1, "y": 10, "color": (255, 0, 0)},
        replace_existing=True,
    )

    print("Starting scheduler… (Ctrl+C to exit)")
    scheduler.start()



    while not STOP.is_set():
        STOP.wait(1)


if __name__ == "__main__":
    main()
