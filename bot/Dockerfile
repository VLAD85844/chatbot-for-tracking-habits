FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.2

COPY ./bot/pyproject.toml ./bot/poetry.lock ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

COPY ./bot/ .

CMD ["poetry", "run", "python", "main.py"]