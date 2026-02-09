FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir poetry==1.8.5

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main

COPY . .
RUN poetry install --only main

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
