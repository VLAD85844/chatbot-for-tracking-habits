import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .database import SessionLocal, engine
from . import models, crud
from dotenv import load_dotenv
from .schemas import HabitCreate, HabitResponse, UserCreate, UserResponse, HabitUpdate

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = FastAPI(redirect_slashes=False)
scheduler = BackgroundScheduler()

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def send_reminder(user_id: int, habit_name: str, reminder_time: str):
    try:
        from telegram import Bot
        bot = Bot(token=TOKEN)
        bot.send_message(
            chat_id=user_id,
            text=f"⏰ Напоминание: время выполнить '{habit_name}'!"
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")


@app.on_event("startup")
def init_scheduler():
    scheduler.start()


@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_telegram_id(db, telegram_id=user.telegram_id)
    if db_user:
        return db_user
    db_user = models.User(telegram_id=user.telegram_id, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/habits/", response_model=HabitResponse)
def create_habit(habit: HabitCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_telegram_id(db, telegram_id=habit.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        hour, minute = map(int, habit.reminder_time.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time format")
    except ValueError:
        raise HTTPException(status_code=400, detail="Time should be in HH:MM format")

    db_habit = models.Habit(
        user_id=db_user.id,
        name=habit.name,
        reminder_time=habit.reminder_time
    )
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)

    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=hour, minute=minute, timezone='Europe/Moscow'),
        args=[db_user.telegram_id, habit.name, habit.reminder_time]
    )

    return db_habit


@app.get("/habits/", response_model=List[HabitResponse])
def read_habits(telegram_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_telegram_id(db, telegram_id=telegram_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    habits = crud.get_habits(db, user_id=db_user.id, skip=skip, limit=limit)
    return habits


@app.post("/habits/{habit_id}/complete")
def complete_habit(
        habit_id: int,
        data: dict,
        db: Session = Depends(get_db)
):
    if not data or "telegram_id" not in data:
        raise HTTPException(status_code=422, detail="telegram_id is required")

    habit = crud.get_habit(db, habit_id=habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    user = crud.get_user_by_telegram_id(db, telegram_id=data["telegram_id"])
    if not user or habit.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your habit")

    completed_habit = crud.mark_habit_completed(db, habit_id=habit_id)
    return {"status": "success", "completion_count": completed_habit.completion_count}


@app.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: int,
    habit_update: HabitUpdate,
    db: Session = Depends(get_db)
):
    if habit_update.reminder_time:
        try:
            hour, minute = map(int, habit_update.reminder_time.split(':'))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("Invalid time format")
        except ValueError:
            raise HTTPException(status_code=400, detail="Time should be in HH:MM format")

    updated_habit = crud.update_habit(
        db,
        habit_id=habit_id,
        name=habit_update.name,
        reminder_time=habit_update.reminder_time,
        is_active=habit_update.is_active
    )
    if not updated_habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return updated_habit


@app.delete("/habits/{habit_id}")
def delete_habit(
        habit_id: int,
        telegram_id: int = Query(..., alias="telegram_id"),
        db: Session = Depends(get_db)
):
    user = crud.get_user_by_telegram_id(db, telegram_id=telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    habit = crud.get_habit(db, habit_id=habit_id)
    if not habit or habit.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your habit")

    success = crud.delete_habit(db, habit_id=habit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return {"status": "success"}