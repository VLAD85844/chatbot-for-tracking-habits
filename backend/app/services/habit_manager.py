from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from .database import SessionLocal
from .crud import carry_over_habits

scheduler = BackgroundScheduler()

def init_scheduler():
    scheduler.add_job(
        daily_habits_carryover,
        'cron',
        hour=23,
        minute=59,
        timezone='Europe/Moscow'
    )
    scheduler.start()

def daily_habits_carryover():
    db = SessionLocal()
    try:
        carry_over_habits(db)
    finally:
        db.close()