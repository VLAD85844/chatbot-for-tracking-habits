from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timedelta
from .schemas import HabitCreate


def create_habit(db: Session, habit: HabitCreate):
    db_habit = models.Habit(**habit.dict())
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
    return db_habit


def update_user_telegram_id(db: Session, username: str, telegram_id: int):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        user.telegram_id = telegram_id
        db.commit()
        db.refresh(user)
    return user


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()


def get_habit(db: Session, habit_id: int):
    return db.query(models.Habit).filter(models.Habit.id == habit_id).first()


def get_habits(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Habit).filter(
        models.Habit.user_id == user_id,
        models.Habit.is_active == True
    ).offset(skip).limit(limit).all()


def mark_habit_completed(db: Session, habit_id: int):
    habit = db.query(models.Habit).filter(
        models.Habit.id == habit_id,
        models.Habit.is_active == True
    ).first()
    if not habit:
        return None
    if habit:
        now = datetime.utcnow()
        today = now.date()
        last_completed = habit.last_completed.date() if habit.last_completed else None

        if last_completed:
            if last_completed == today - timedelta(days=1):
                habit.streak += 1
            elif last_completed != today:
                habit.streak = 1
        else:
            habit.streak = 1

        habit.completion_count += 1
        habit.last_completed = now
        db.commit()
    return habit


def carry_over_habits(db: Session):
    yesterday = datetime.utcnow() - timedelta(days=1)
    habits = db.query(models.Habit).filter(
        models.Habit.last_completed < yesterday.date(),
        models.Habit.completion_count < 21
    ).all()

    for habit in habits:
        habit.streak = 0
    db.commit()


def update_habit(
        db: Session,
        habit_id: int,
        name: str = None,
        is_active: bool = None
):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        return None

    if name:
        habit.name = name
    if is_active is not None:
        habit.is_active = is_active

    db.commit()
    db.refresh(habit)
    return habit



def delete_habit(db: Session, habit_id: int):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        return False

    db.delete(habit)
    db.commit()
    return True


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()