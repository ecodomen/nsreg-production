# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Domain registrar price monitoring system ("Ecodomen") that scrapes pricing from ~41 Russian domain registrar websites, stores data in PostgreSQL, and displays comparative pricing through a Django web interface. A Telegram bot triggers scraping runs and sends notifications.

**Stack:** Python 3.12+, Scrapy 2.11, Django 4.1.7, PostgreSQL, Aiogram 3.0 (Telegram bot), Docker, Poetry

## Common Commands

### Local Development Setup
```bash
pip install poetry                 # Install Poetry (if not installed)
poetry install                     # Install all dependencies
cp .env.template .env              # Create env file, then edit values
export $(cat .env | sed 's/#.*//g' | xargs | envsubst)
docker-compose up                  # Start PostgreSQL + Adminer (port 8085)
```

### Run Django Dev Server
```bash
bash runsite.sh                    # Runs migrations + starts server on :8000
```

### Run All Spiders
```bash
bash runspiders.sh                 # Runs monitor spider first, then all others sequentially
```

### Run a Single Spider
```bash
cd src/grabber/nsreg
poetry run scrapy crawl nsreg_domainshop.py   # Spider name = filename (e.g., nsreg_domainshop.py)
```

### Run Telegram Bot
```bash
poetry run python src/telegram_bot
```

### Linting (matches CI)
```bash
poetry run flake8 --max-line-length 1000 src/
```

### Docker (Full Stack Deployment)
```bash
docker compose -f dev.yml up --build   # PostgreSQL + Scrapy/Bot + Django
```

### Django Management
```bash
poetry run python src/website/manage.py migrate
poetry run python src/website/manage.py runserver
poetry run python src/website/manage.py createsuperuser   # Admin at /admin/
```

### Adding Dependencies
```bash
poetry add <package>               # Add a runtime dependency
poetry add --group dev <package>   # Add a dev dependency (e.g., flake8)
```

## Architecture

### Three Independent Subsystems

```
src/
├── grabber/nsreg/          # Scrapy project - web scraping engine
├── website/                # Django project - web UI and data models
└── telegram_bot/           # Aiogram bot - triggers spiders, sends notifications
```

All three share the same PostgreSQL database and `.env` configuration.

### Scrapy Spiders (`src/grabber/nsreg/spiders/`)

Spiders follow a **composition pattern** using `BaseSpiderComponent` from `base_site_spider.py`:

1. Spider defines XPath paths for `price_reg`, `price_prolong`, `price_change` and a regex pattern
2. `BaseSpiderComponent` handles extraction and price parsing via `find_price()`
3. `NsregPipeline` (`pipelines.py`) saves results to PostgreSQL, linking to the latest `ParseHistory`

**Spider naming:** Files must be named `nsreg_[sitename].py`. The spider `name` attribute matches the filename.

**Multi-site spiders** (`multi_site_spider*.py`) parse 2-3 related registrar sites in one spider.

For complex cases requiring multi-page scraping, spiders override `parse()` directly and use `scrapy.Request` callbacks.

### Django App (`src/website/`)

**Models** (in `catalog/models.py`):
- `Registrator` - registrar info (name, website, city, NIC handles)
- `Price` - scraped prices with status flags (V=valid, A=absent), linked to Registrator and ParseHistory
- `ParseHistory` - timestamps for scraping runs
- `Parser` - contributor tracking
- `ParseError` - error logging

**Views:** Main page at `/list/` shows latest price per registrar with search/sort. Detail page at `/partner/<id>/` shows price history.

### Data Flow

Scrapy spiders yield `NsregItem` (name + prices dict) → `NsregPipeline` matches registrar by name → creates `Price` record linked to current `ParseHistory` → Django views query latest prices per registrar for display.

## Key Configuration

- **Scrapy settings** (`src/grabber/nsreg/settings.py`): `CONCURRENT_REQUESTS=1`, `DOWNLOAD_DELAY=0.25`, `ROBOTSTXT_OBEY=False`, async Twisted reactor
- **Django settings** (`src/website/website/settings.py`): locale `ru-RU`, `CSRF_TRUSTED_ORIGINS` includes `ecodomen.ru`
- **Database connection** uses env vars: `HOSTNAME_DB`, `USERNAME_DB`, `PASSWORD_DB`, `DATABASE_NAME`, `PORT_DB`

## CI/CD

- **Linter** (push/PR to main/dev): `flake8 --max-line-length 1000 src/`
- **Deploy** (push to dev): SSH to server, pulls latest, rebuilds `dev.yml` Docker containers

## Conventions

- Documentation and code comments are in **Russian**
- New spiders should use `BaseSpiderComponent` composition (reference: `nsreg_domainshop.py`)
- Legacy spiders using old `utils.py` pattern are being deprecated
- `site_names` must be a tuple with trailing comma (e.g., `("Name",)`) or Scrapy iterates characters