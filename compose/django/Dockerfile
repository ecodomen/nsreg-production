# syntax=docker/dockerfile:1
FROM python:3.12
EXPOSE 8000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . /app/
WORKDIR /app
RUN apt-get update
RUN apt-get install -y gettext-base
RUN pip install poetry && poetry install --no-root
CMD ["sh", "compose/django/dev-django.sh"]
