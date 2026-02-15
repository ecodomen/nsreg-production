#!/usr/bin/env bash

if [ -f .env ]; then
  set -a
  source <(grep -v '^\s*#' .env | grep -v '^\s*$')
  set +a
fi

poetry run python src/website/manage.py migrate
poetry run python src/website/manage.py runserver