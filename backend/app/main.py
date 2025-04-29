import os
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .database import SessionLocal, engine
from . import models, crud
from dotenv import load_dotenv
from .schemas import HabitCreate, HabitResponse, UserCreate, UserResponse, HabitUpdate
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("apscheduler")
logger.setLevel(logging.DEBUG)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = FastAPI(redirect_slashes=False)
scheduler = AsyncIOScheduler()


models.Base.metadata.create_all(bind=engine)


SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    user = crud.get_user_by_username(db, username=username)
    if not user:
        logger.error(f"User {username} not found in DB")
        return False
    if not verify_password(password, user.hashed_password):
        logger.error(f"Invalid password for user {username}")
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=UserResponse)
async def read_users_me(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def send_reminder(user_id: int, habit_name: str):
    try:
        from telegram import Bot
        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=user_id,
            text=f"⏰ Не забудьте выполнить привычку: '{habit_name}'!"
        )
        logger.info(f"Сообщение отправлено: user_id={user_id}, habit={habit_name}")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}", exc_info=True)


@app.on_event("startup")
def init_scheduler():
    scheduler.start()
    logger.info(f"Планировщик запущен: {scheduler.running}")
    logger.info(f"Активные задачи: {scheduler.get_jobs()}")


@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


from datetime import datetime
from fastapi import HTTPException, status
from apscheduler.triggers.interval import IntervalTrigger


@app.put("/users/{username}/link_telegram")
def link_telegram(
        username: str,
        data: dict = Body(...),
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("sub") != username:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = crud.update_user_telegram_id(db, username=username, telegram_id=data["telegram_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/habits/", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(habit: HabitCreate, db: Session = Depends(get_db)):
    try:
        db_user = crud.get_user_by_telegram_id(db, telegram_id=habit.telegram_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_habit = (
            db.query(models.Habit)
            .filter(
                models.Habit.user_id == db_user.id,
                models.Habit.name == habit.name
            )
            .first()
        )
        if existing_habit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Habit with this name already exists"
            )

        job = scheduler.add_job(
            send_reminder,
            trigger=IntervalTrigger(hours=1),
            args=[db_user.telegram_id, habit.name],
            id=f"habit_{db_user.id}_{habit.name}"
        )
        logger.info(f"Добавлена задача: ID={job.id}, Интервал={job.trigger}")

        db_habit = models.Habit(
            user_id=db_user.id,
            name=habit.name,
            is_active=True,
            job_id=job.id
        )

        db.add(db_habit)
        db.commit()
        db.refresh(db_habit)

        return {
            **db_habit.__dict__,
            "telegram_id": db_user.telegram_id
        }


    except HTTPException:
        raise
    except Exception as e:
        if 'job' in locals():
            scheduler.remove_job(job.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating habit: {str(e)}"
        )


@app.get("/habits/", response_model=List[HabitResponse])
def read_habits(telegram_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_telegram_id(db, telegram_id=telegram_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.get_habits(db, user_id=db_user.id, skip=skip, limit=limit)


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
    habit = crud.get_habit(db, habit_id=habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    if habit_update.is_active is False and habit.job_id:
        try:
            scheduler.remove_job(habit.job_id)
        except Exception as e:
            logger.warning(f"Ошибка удаления задачи: {e}")

    return crud.update_habit(db, habit_id=habit_id, **habit_update.dict())


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

    if habit.job_id:
        try:
            scheduler.remove_job(habit.job_id)
        except Exception as e:
            logger.warning(f"Failed to delete job {habit.job_id}: {str(e)}")

    success = crud.delete_habit(db, habit_id=habit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return {"status": "success"}


@app.post("/test_reminder/{user_id}/{habit_name}")
def trigger_reminder(user_id: int, habit_name: str):
    send_reminder(user_id, habit_name)
    return {"status": "reminder_triggered"}