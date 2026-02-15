# Развертывание nsreg-watcher

## Содержание

- [Требования](#требования)
- [Локальное развертывание](#локальное-развертывание)
  - [1. Клонирование репозитория](#1-клонирование-репозитория)
  - [2. Настройка окружения](#2-настройка-окружения)
  - [3. Запуск PostgreSQL](#3-запуск-postgresql)
  - [4. Запуск Django](#4-запуск-django)
  - [5. Запуск спайдеров](#5-запуск-спайдеров)
  - [6. Запуск Telegram-бота](#6-запуск-telegram-бота)
- [Развертывание на сервере (Docker + Nginx)](#развертывание-на-сервере-docker--nginx)
  - [1. Подготовка сервера](#1-подготовка-сервера)
  - [2. Клонирование и настройка проекта](#2-клонирование-и-настройка-проекта)
  - [3. Настройка .env для сервера](#3-настройка-env-для-сервера)
  - [4. Запуск контейнеров](#4-запуск-контейнеров)
  - [5. Сборка статики Django](#5-сборка-статики-django)
  - [6. Настройка Nginx](#6-настройка-nginx)
  - [7. Установка SSL-сертификата (Let's Encrypt)](#7-установка-ssl-сертификата-lets-encrypt)
  - [8. Проверка работоспособности](#8-проверка-работоспособности)
- [Управление контейнерами](#управление-контейнерами)
- [CI/CD (автоматический деплой)](#cicd-автоматический-деплой)
- [Управление зависимостями](#управление-зависимостями)
- [Переменные окружения](#переменные-окружения)
- [Устранение неполадок](#устранение-неполадок)

---

## Требования

### Для локальной разработки

- Python 3.12+
- Poetry (менеджер зависимостей)
- Docker и Docker Compose (для PostgreSQL)
- Git

### Для серверного развертывания

- Linux-сервер (Ubuntu 22.04+ / Debian 12+)
- Docker и Docker Compose
- Nginx
- Certbot (для SSL)
- Git
- Домен, направленный A-записью на IP сервера

---

## Локальное развертывание

### 1. Клонирование репозитория

```bash
git clone https://github.com/ecodomen/nsreg-watcher.git
cd nsreg-watcher
git checkout dev
```

> **Windows:** используйте WSL (Windows Subsystem for Linux). При проблемах с окончаниями строк выполните: `sudo apt-get install dos2unix && dos2unix *`

### 2. Настройка окружения

Установите Poetry (если ещё не установлен) и зависимости проекта:

```bash
pip install poetry
poetry install
```

Этот процесс:
- создаст виртуальное окружение (управляется Poetry)
- установит все зависимости из `pyproject.toml`

Создайте файл `.env` на основе шаблона:

```bash
cp .env.template .env
```

Откройте `.env` и при необходимости измените значения:

```env
# DOCKER-COMPOSE POSTGRES SETTINGS
HOSTNAME_DB=localhost
USERNAME_DB=nsreg
PASSWORD_DB=Nsreg123
DATABASE_NAME=nsreg
PORT_DB=50432

# SENDMAIL SETTINGS
EMAIL_FROM=nsregproject@gmail.com
EMAIL_TO=nsregproject@gmail.com
EMAIL_SMTP=smtp.gmail.com:587
EMAIL_LOGIN=nsregproject@gmail.com
EMAIL_PASS=<пароль>

# DJANGO SETTINGS
DJANGO_SECRET_KEY='<сгенерируйте секретный ключ>'

# TELEGRAM BOT
BOT_TOKEN=<токен от @BotFather>
CHAT_ID=<ID чата>
TOPIC_SUPPORT_ID=<ID топика в чате>
```

Загрузите переменные окружения в текущую сессию терминала:

```bash
export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
```

> Эту команду нужно выполнять в каждом новом терминале. Скрипты `runsite.sh` и `runspiders.sh` делают это автоматически.

### 3. Запуск PostgreSQL

Локально БД запускается через Docker Compose (`docker-compose.yml`):

```bash
docker-compose up -d
```

Это поднимает:
- **PostgreSQL** — порт задается переменной `PORT_DB` (по умолчанию `50432`)
- **Adminer** — веб-интерфейс для БД на порту `8085` (http://localhost:8085)

Проверьте подключение к базе:

```bash
docker-compose ps
```

### 4. Запуск Django

```bash
bash runsite.sh
```

Скрипт `runsite.sh` автоматически:
1. Загружает переменные из `.env`
2. Применяет миграции (`manage.py migrate`)
3. Запускает dev-сервер на http://localhost:8000

Для создания суперпользователя (доступ к http://localhost:8000/admin/):

```bash
export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
poetry run python src/website/manage.py createsuperuser
```

### 5. Запуск спайдеров

```bash
bash runspiders.sh
```

Скрипт `runspiders.sh` автоматически:
1. Загружает переменные из `.env`
2. Очищает лог ошибок `logs/grabber_errors.log`
3. Запускает spider `monitor` (создает запись `ParseHistory`)
4. Последовательно запускает все остальные спайдеры

Для запуска **одного конкретного спайдера**:

```bash
export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
cd src/grabber/nsreg
poetry run scrapy crawl nsreg_domainshop.py
```

Для просмотра списка всех доступных спайдеров:

```bash
cd src/grabber/nsreg
poetry run scrapy list
```

### 6. Запуск Telegram-бота

Для работы бота необходимо заполнить в `.env` переменные `BOT_TOKEN`, `CHAT_ID` и `TOPIC_SUPPORT_ID`.

```bash
export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
poetry run python src/telegram_bot
```

Бот при старте:
1. Отправляет сообщение в Telegram-чат о начале парсинга
2. Запускает все спайдеры через `compose/scrapy/scrapy-dev.sh`
3. По завершении отправляет результат с логом ошибок

---

## Развертывание на сервере (Docker + Nginx)

Архитектура на сервере:

```
Клиент (браузер)
    │
    │ HTTPS :443
    ▼
┌─────────┐
│  Nginx  │ ── статика (CSS/JS/images) отдается напрямую
│         │ ── /admin/, /list/, /partner/ → проксируется ──┐
└─────────┘                                                │
                                                           ▼
                                              ┌────────────────────┐
                                              │  Django :8000      │
                                              │  (Docker-контейнер)│
                                              └────────┬───────────┘
                                                       │
                                              ┌────────▼───────────┐
                                              │  PostgreSQL :5432  │
                                              │  (Docker-контейнер)│
                                              └────────────────────┘
```

### 1. Подготовка сервера

Обновите систему и установите необходимые пакеты:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx git ufw
```

Добавьте текущего пользователя в группу `docker`, чтобы не использовать `sudo`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Настройте файрвол:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Проверьте, что Docker запущен:

```bash
sudo systemctl enable docker
sudo systemctl start docker
docker --version
```

### 2. Клонирование и настройка проекта

```bash
cd ~
git clone https://github.com/ecodomen/nsreg-watcher.git
cd nsreg-watcher
git checkout dev
```

### 3. Настройка .env для сервера

```bash
cp .env.template .env
nano .env
```

**Важные отличия от локальной конфигурации:**

```env
# DOCKER-COMPOSE POSTGRES SETTINGS
# В Docker-сети контейнеры обращаются к PostgreSQL по имени сервиса, не по localhost
HOSTNAME_DB=postgres
USERNAME_DB=nsreg
PASSWORD_DB=<надежный_пароль>
DATABASE_NAME=nsreg
PORT_DB=5432

# DJANGO SETTINGS
# Сгенерируйте уникальный ключ: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_SECRET_KEY='<уникальный_секретный_ключ>'

# TELEGRAM BOT
BOT_TOKEN=<токен от @BotFather>
CHAT_ID=<ID чата>
TOPIC_SUPPORT_ID=<ID топика в чате>
```

> **`HOSTNAME_DB=postgres`** — внутри Docker-сети контейнеры обращаются к PostgreSQL по имени сервиса `postgres` из `dev.yml`, а не по `localhost`.

> **`PORT_DB=5432`** — внутри Docker-сети контейнеры подключаются к внутреннему порту PostgreSQL (5432), а не к внешнему маппингу (5433).

### 4. Запуск контейнеров

```bash
cd ~/nsreg-watcher
docker compose -f dev.yml up --build -d
```

Compose-файл `dev.yml` создает три сервиса:

| Сервис | Описание | Порт |
|--------|----------|------|
| `postgres` | PostgreSQL база данных | 5433 (внешний) → 5432 (внутренний) |
| `scrapy_telbot` | Scrapy-спайдеры + Telegram-бот | — |
| `django` | Django веб-интерфейс | 8000 |

Проверьте, что контейнеры запустились:

```bash
docker compose -f dev.yml ps
```

Ожидаемый результат — все три сервиса в статусе `Up`.

Создайте суперпользователя Django:

```bash
docker compose -f dev.yml exec django python src/website/manage.py createsuperuser
```

Убедитесь, что Django отвечает:

```bash
curl -I http://localhost:8000/list/
```

### 5. Сборка статики Django

Django в production-режиме не раздает статику самостоятельно — это делает Nginx. Нужно собрать статические файлы.

Создайте директорию для статики на хосте:

```bash
sudo mkdir -p /var/www/ecodomen.ru/static
```

Соберите статику внутри контейнера:

```bash
docker compose -f dev.yml exec django python src/website/manage.py collectstatic --noinput
```

Скопируйте статику из контейнера на хост:

```bash
docker compose -f dev.yml cp django:/app/src/website/staticfiles/. /var/www/ecodomen.ru/static/
```

> **Примечание:** если `collectstatic` ещё не настроен в проекте, Nginx будет проксировать запросы к статике через Django. Это работает, но медленнее. Для настройки `collectstatic` добавьте в `settings.py`:
> ```python
> STATIC_ROOT = BASE_DIR / "staticfiles"
> ```

### 6. Настройка Nginx

Создайте конфигурационный файл для сайта:

```bash
sudo nano /etc/nginx/sites-available/ecodomen.ru
```

Вставьте конфигурацию:

```nginx
server {
    listen 80;
    server_name ecodomen.ru www.ecodomen.ru;

    # Статические файлы — отдаются Nginx напрямую
    location /static/ {
        alias /var/www/ecodomen.ru/static/;
        expires 30d;
        access_log off;
    }

    # Все остальные запросы — проксируются в Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Таймауты для длительных запросов
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

Активируйте конфигурацию и проверьте синтаксис:

```bash
sudo ln -s /etc/nginx/sites-available/ecodomen.ru /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
```

Если `nginx -t` выводит `syntax is ok` — перезапустите Nginx:

```bash
sudo systemctl restart nginx
```

Проверьте, что сайт доступен по HTTP:

```bash
curl -I http://ecodomen.ru
```

### 7. Установка SSL-сертификата (Let's Encrypt)

> **Предварительно:** убедитесь, что DNS A-запись домена `ecodomen.ru` (и `www.ecodomen.ru`, если нужен) указывает на IP вашего сервера.

Получите SSL-сертификат через Certbot:

```bash
sudo certbot --nginx -d ecodomen.ru -d www.ecodomen.ru
```

Certbot:
1. Запросит email для уведомлений о продлении сертификата
2. Автоматически модифицирует конфигурацию Nginx, добавив SSL
3. Настроит редирект с HTTP на HTTPS

Проверьте автоматическое продление:

```bash
sudo certbot renew --dry-run
```

После установки SSL итоговая конфигурация Nginx будет выглядеть примерно так (Certbot создаст её автоматически):

```nginx
server {
    server_name ecodomen.ru www.ecodomen.ru;

    location /static/ {
        alias /var/www/ecodomen.ru/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/ecodomen.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ecodomen.ru/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name ecodomen.ru www.ecodomen.ru;

    if ($host = www.ecodomen.ru) {
        return 301 https://ecodomen.ru$request_uri;
    }

    if ($host = ecodomen.ru) {
        return 301 https://$host$request_uri;
    }
}
```

### 8. Проверка работоспособности

После настройки выполните чек-лист:

```bash
# 1. Контейнеры работают
docker compose -f dev.yml ps

# 2. Django отвечает локально
curl -I http://localhost:8000/list/

# 3. Nginx проксирует
curl -I http://ecodomen.ru/list/

# 4. SSL работает
curl -I https://ecodomen.ru/list/

# 5. Статика отдается
curl -I https://ecodomen.ru/static/catalog/style.css

# 6. Админка доступна
curl -I https://ecodomen.ru/admin/
```

---

## Управление контейнерами

Все команды выполняются из директории проекта (`~/nsreg-watcher`).

Просмотр статуса:
```bash
docker compose -f dev.yml ps
```

Просмотр логов:
```bash
docker compose -f dev.yml logs -f              # все сервисы
docker compose -f dev.yml logs -f django        # только Django
docker compose -f dev.yml logs -f scrapy_telbot # только Scrapy/бот
docker compose -f dev.yml logs -f postgres      # только PostgreSQL
```

Перезапуск:
```bash
docker compose -f dev.yml restart               # все сервисы
docker compose -f dev.yml restart django         # только Django
```

Полная пересборка:
```bash
docker compose -f dev.yml down
docker compose -f dev.yml up --build -d
```

Выполнение команд внутри контейнера Django:
```bash
docker compose -f dev.yml exec django python src/website/manage.py createsuperuser
docker compose -f dev.yml exec django python src/website/manage.py migrate
docker compose -f dev.yml exec django python src/website/manage.py shell
```

---

## CI/CD (автоматический деплой)

Настроен GitHub Actions workflow (`.github/workflows/deploy.yml`):

- **Триггер:** push в ветку `dev`
- **Действия:**
  1. Подключается к серверу по SSH
  2. Выполняет `git pull origin dev` на сервере
  3. Пересобирает и перезапускает контейнеры через `dev.yml`

### Необходимые GitHub Secrets

| Secret | Описание |
|--------|----------|
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ для доступа к серверу |
| `SSH_KNOWN_HOSTS` | Отпечаток SSH-ключа сервера (`ssh-keyscan <host>`) |
| `SSH_SERVER_ADRESS` | Адрес в формате `user@host` |

### Настройка SSH-ключа на сервере

```bash
# На локальной машине — сгенерируйте ключ
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy

# Скопируйте публичный ключ на сервер
ssh-copy-id -i ~/.ssh/github_deploy.pub user@<IP_сервера>

# Получите отпечаток сервера для KNOWN_HOSTS
ssh-keyscan <IP_сервера>
```

Затем добавьте в GitHub Secrets:
- `SSH_PRIVATE_KEY` — содержимое файла `~/.ssh/github_deploy`
- `SSH_KNOWN_HOSTS` — вывод `ssh-keyscan`
- `SSH_SERVER_ADRESS` — `user@<IP_сервера>`

### Требования к серверу для CI/CD

1. Репозиторий клонирован в директорию `~/nsreg-watcher`
2. Docker и Docker Compose установлены
3. Файл `.env` настроен в корне репозитория
4. SSH-пользователь имеет права на запуск Docker (в группе `docker`)
5. Nginx настроен и запущен

### Линтер

Workflow `.github/workflows/linter.yml` запускается при push/PR в `main` или `dev`:

```bash
poetry run flake8 --max-line-length 1000 src/
```

Перед отправкой PR проверьте код локально той же командой.

---

## Управление зависимостями

Проект использует **Poetry** для управления зависимостями. Конфигурация находится в `pyproject.toml`.

### Добавление зависимости

```bash
poetry add <package>                # runtime-зависимость
poetry add --group dev <package>    # dev-зависимость (линтеры, тесты)
```

### Обновление зависимостей

```bash
poetry update                       # обновить все зависимости
poetry update <package>             # обновить конкретный пакет
```

### Просмотр установленных пакетов

```bash
poetry show                         # все пакеты
poetry show --tree                  # дерево зависимостей
```

---

## Переменные окружения

Полный список переменных из `.env.template`:

| Переменная | Описание | Локально | На сервере (Docker) |
|------------|----------|----------|---------------------|
| `HOSTNAME_DB` | Хост PostgreSQL | `localhost` | `postgres` |
| `USERNAME_DB` | Имя пользователя БД | `nsreg` | `nsreg` |
| `PASSWORD_DB` | Пароль БД | `Nsreg123` | надежный пароль |
| `DATABASE_NAME` | Имя базы данных | `nsreg` | `nsreg` |
| `PORT_DB` | Порт PostgreSQL | `50432` | `5432` |
| `EMAIL_FROM` | Email отправителя | — | — |
| `EMAIL_TO` | Email получателя | — | — |
| `EMAIL_SMTP` | SMTP-сервер с портом | — | — |
| `EMAIL_LOGIN` | Логин SMTP | — | — |
| `EMAIL_PASS` | Пароль SMTP | — | — |
| `DJANGO_SECRET_KEY` | Секретный ключ Django | любой | уникальный |
| `BOT_TOKEN` | Токен Telegram-бота | — | токен |
| `CHAT_ID` | ID Telegram-чата | — | ID чата |
| `TOPIC_SUPPORT_ID` | ID топика в Telegram-чате | — | ID топика |

---

## Устранение неполадок

### Django не подключается к БД

1. Убедитесь, что PostgreSQL запущен: `docker-compose ps` (локально) или `docker compose -f dev.yml ps` (сервер)
2. Проверьте переменные окружения: `docker compose -f dev.yml exec django env | grep DB`
3. Локально `HOSTNAME_DB=localhost` + `PORT_DB=50432`, на сервере `HOSTNAME_DB=postgres` + `PORT_DB=5432`

### Nginx возвращает 502 Bad Gateway

1. Убедитесь, что Django-контейнер запущен и слушает порт 8000:
```bash
docker compose -f dev.yml ps
curl http://localhost:8000/list/
```
2. Проверьте логи Django:
```bash
docker compose -f dev.yml logs django
```
3. Проверьте, что порт 8000 не занят другим процессом:
```bash
sudo ss -tlnp | grep 8000
```

### Статика не загружается (404 на CSS/JS)

1. Проверьте, что файлы существуют:
```bash
ls /var/www/ecodomen.ru/static/
```
2. Если пусто — соберите статику:
```bash
docker compose -f dev.yml exec django python src/website/manage.py collectstatic --noinput
docker compose -f dev.yml cp django:/app/src/website/staticfiles/. /var/www/ecodomen.ru/static/
```
3. Проверьте права доступа:
```bash
sudo chown -R www-data:www-data /var/www/ecodomen.ru/static/
```

### SSL-сертификат не выдается

1. Убедитесь, что DNS A-запись указывает на IP сервера:
```bash
dig ecodomen.ru +short
```
2. Убедитесь, что порты 80 и 443 открыты:
```bash
sudo ufw status
```
3. Nginx должен быть запущен до вызова `certbot`:
```bash
sudo systemctl status nginx
```

### Спайдер не сохраняет данные в БД

1. Spider `monitor` должен быть запущен первым — он создает запись `ParseHistory`, к которой привязываются цены
2. Имя регистратора в поле `site_names` спайдера должно **точно** совпадать с `name` в таблице `Registrator`
3. Проверьте лог: `docker compose -f dev.yml logs scrapy_telbot`

### Контейнер scrapy_telbot падает

Скрипт `compose/scrapy/scrapy-dev.sh` включает `sleep 10` для ожидания готовности PostgreSQL. Если БД стартует дольше — контейнер может упасть. Проверьте логи:
```bash
docker compose -f dev.yml logs scrapy_telbot
```

### Ошибки окончаний строк (Windows/WSL)

```bash
sudo apt-get install dos2unix
dos2unix *
dos2unix compose/scrapy/* compose/django/*
```

### Adminer недоступен

Adminer доступен только при локальном развертывании (`docker-compose.yml`) на http://localhost:8085. В серверном `dev.yml` он не включен.

### Обновление SSL-сертификата

Certbot настраивает автоматическое продление через systemd-таймер. Проверить:
```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

Сертификаты обновляются автоматически каждые 60-90 дней.