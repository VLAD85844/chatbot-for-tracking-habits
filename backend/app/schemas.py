from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HabitBase(BaseModel):
    name: str
    reminder_time: str


class HabitCreate(HabitBase):
    user_id: int


class HabitResponse(HabitCreate):
    id: int
    completion_count: int
    streak: int
    last_completed: Optional[datetime] = None


class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class CompleteHabitRequest(BaseModel):
    telegram_id: int


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    reminder_time: Optional[str] = None
    is_active: Optional[bool] = None