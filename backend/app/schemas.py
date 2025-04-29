from pydantic import BaseModel, constr
from datetime import datetime
from typing import Optional


class HabitBase(BaseModel):
    name: str


class HabitCreate(HabitBase):
    telegram_id: int


class HabitResponse(HabitBase):
    id: int
    user_id: int
    completion_count: int
    streak: int
    last_completed: Optional[datetime] = None
    is_active: bool
    job_id: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class UserBase(BaseModel):
    username: str


class UserInDB(UserBase):
    hashed_password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: constr(min_length=6)


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None