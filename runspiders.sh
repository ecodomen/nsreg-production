#!/usr/bin/env bash

if [ -f .env ]; then
  export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

ERROR_LOG="$(cd "$(dirname "logs/grabber_errors.log")"; pwd)/$(basename "logs/grabber_errors.log")"
LOG_LEVEL=ERROR
DATE=$(date +"%d-%b-%Y_%H:%M")

echo "truncating error file:  $ERROR_LOG"
echo -n '' > $ERROR_LOG

cd src/grabber/nsreg

poetry run scrapy crawl monitor --logfile $ERROR_LOG --loglevel $LOG_LEVEL
poetry run scrapy list | awk '$1 != "monitor" {print $1}' | xargs -n 1 poetry run scrapy crawl --logfile $ERROR_LOG --loglevel $LOG_LEVEL