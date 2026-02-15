# syntax=docker/dockerfile:1
FROM python:3.12
COPY . /app/
COPY .env /app/
WORKDIR /app
RUN apt-get update
RUN apt-get install -y gettext-base
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root
CMD ["python", "src/telegram_bot"]
