import httpx
from httpx import ConnectTimeout, ReadTimeout
import logging
import json


BASE_URL = "http://backend:8000"


logger = logging.getLogger(__name__)


async def login_user(auth_data: dict):
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post(
                "/token",
                data={"username": auth_data["username"], "password": auth_data["password"]}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_user(user_data: dict):
    """Создание пользователя с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post("/users/", json=user_data)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_habits(telegram_id: int, token: str = None):
    """Получение списка привычек с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.get(
                "/habits/",
                params={"telegram_id": telegram_id},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error in get_habits: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def create_habit(habit_data: dict, token: str):
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post(
                "/habits/",
                json=habit_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def mark_habit_done(habit_id: int, telegram_id: int):
    """Отметка привычки выполненной"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post(
                f"/habits/{habit_id}/complete",
                json={"telegram_id": telegram_id}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def update_habit(habit_id: int, token: str, **update_data):
    """Обновление привычки"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.put(
                f"/habits/{habit_id}",
                json=update_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_habit(habit_id: int, telegram_id: int, token: str):
    """Удаление привычки с проверкой владельца"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.delete(
                f"/habits/{habit_id}",
                params={"telegram_id": telegram_id},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error in delete_habit: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}