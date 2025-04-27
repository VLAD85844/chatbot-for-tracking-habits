# Habit Tracker Bot

Бот для отслеживания привычек с напоминаниями и статистикой выполнения.

## 📌 Основные возможности

- ✅ Добавление новых привычек
- 📋 Просмотр списка текущих привычек
- ✔️ Отметка выполненных привычек
- ✏️ Редактирование привычек (название, время, активность)
- 🗑️ Удаление привычек
- ⏰ Автоматические напоминания

## 🛠 Технологический стек

- **Backend**: FastAPI, PostgreSQL
- **Bot**: python-telegram-bot
- **Database**: SQLAlchemy, Alembic
- **Scheduling**: APScheduler
- **HTTP Client**: httpx

## 🚀 Установка и запуск

### Требования
- Docker и Docker Compose
- Python 3.9+
- poetry

### Инструкции по запуску

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/VLAD85844/CRM-system-development

2. Создайте файл .env на основе .env и установите зависимости:

   ```bash
   pip install poetry

3. Запустите приложение:

    ```bash
   docker-compose up --build
   

### API Endpoints

Метод	        Путь	             Описание 
POST	/users/	                Создание пользователя
POST	/habits/	            Создание привычки
GET	    /habits/	            Получение списка привычек
PUT	    /habits/{id}	        Обновление привычки
DELETE	/habits/{id}	        Удаление привычки
POST	/habits/{id}/complete	Отметка выполнения

# 🤖 Команды бота

- /start - Начало работы

- /add - Добавить новую привычку

- /list - Показать все привычки

- /done - Отметить выполнение

- /edit - Редактировать привычку

- /delete - Удалить привычку