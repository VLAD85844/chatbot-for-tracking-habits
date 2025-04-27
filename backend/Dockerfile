FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.2

COPY ./backend/pyproject.toml ./backend/poetry.lock ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

COPY . .

CMD sh -c "until pg_isready -h db -U habit_user -d habit_db; do sleep 2; done && \
           cd /app && \
           alembic upgrade head && \
           poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000"