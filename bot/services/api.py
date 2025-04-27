import httpx
from httpx import ConnectTimeout, ReadTimeout
import logging
import json


BASE_URL = "http://backend:8000"

logger = logging.getLogger(__name__)

async def create_user(user_data: dict):
    """Создание пользователя с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post(
                "/users/",
                json=user_data
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def get_habits(telegram_id: int):
    """Получение списка привычек с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.get(
                "/habits/",
                params={"telegram_id": telegram_id}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def create_habit(habit_data: dict):
    """Создание привычки с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.post(
                "/habits/",
                json=habit_data
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

async def update_habit(habit_id: int, **update_data):
    """Обновление привычки"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.put(
                f"/habits/{habit_id}",
                json=update_data
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_habit(habit_id: int, telegram_id: int):
    """Удаление привычки с проверкой владельца"""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            response = await client.delete(
                f"/habits/{habit_id}",
                params={"telegram_id": telegram_id}
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error in delete_habit: {e.response.text}")
        return {"status": "error", "message": f"Ошибка: {e.response.text}"}
    except Exception as e:
        logger.error(f"Unexpected error in delete_habit: {str(e)}", exc_info=True)
        return {"status": "error", "message": "Не удалось удалить привычку"}