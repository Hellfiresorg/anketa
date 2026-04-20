# Деплой Аудио-анкеты

> **Архитектура деплоя**
>
> | Компонент | Где живёт | Как обновлять |
> |-----------|-----------|---------------|
> | Frontend-client (клиентская анкета) | SpaceWeb — статика | FTP / файловый менеджер cPanel |
> | Frontend-admin (панель менеджера) | SpaceWeb — статика | FTP / файловый менеджер cPanel |
> | Backend API (FastAPI) | Ваш VPS | systemd + uvicorn |
> | Transcription worker (arq) | Тот же VPS | systemd |
> | PostgreSQL | Тот же VPS | apt / managed DB |
> | Redis | Тот же VPS | apt |
> | Аудиофайлы | Диск VPS | `/var/anketa/audio` |

---

## Содержание

1. [Подготовка: что нужно знать заранее](#1-подготовка)
2. [Деплой фронтендов на SpaceWeb](#2-деплой-фронтендов-на-spaceweb)
3. [Деплой бэкенда на VPS](#3-деплой-бэкенда-на-vps)
4. [Первый запуск: миграции и создание аккаунтов](#4-первый-запуск)
5. [Обновление после изменений в коде](#5-обновление)
6. [Диагностика](#6-диагностика)

---

## 1. Подготовка

### Домены / субдомены

Заранее решите, какие URL будут у каждого компонента. Пример:

| Компонент | URL |
|-----------|-----|
| Клиентская анкета | `https://anketa.yourdomain.ru` |
| Панель администратора | `https://admin.yourdomain.ru` |
| API бэкенда | `https://api.yourdomain.ru` |

Для SpaceWeb (фронтенды): создайте субдомены в cPanel → **Subdomains**.  
Для VPS (API): пропишите A-запись `api.yourdomain.ru → IP вашего VPS` в DNS-панели.

### Что нужно иметь

- [ ] Доступ к cPanel SpaceWeb (логин/пароль)
- [ ] SSH-доступ к VPS (root или sudo-пользователь)
- [ ] Groq API Key (https://console.groq.com/)
- [ ] Сгенерированный JWT_SECRET: `openssl rand -hex 32`

---

## 2. Деплой фронтендов на SpaceWeb

SpaceWeb — виртуальный хостинг, Python там не запускается. Загружаем только скомпилированные статические файлы.

### 2.1 Сборка frontend-client (клиентская анкета)

Выполнить на своём компьютере:

```bash
cd frontend-client

# Создать файл с переменными для production
cp .env.production.example .env.production
# Открыть .env.production и заменить URL на реальный:
#   VITE_API_BASE_URL=https://api.yourdomain.ru

npm install
npm run build
```

После сборки папка `frontend-client/dist/` содержит готовые файлы.

### 2.2 Сборка frontend-admin (панель администратора)

```bash
cd frontend-admin

cp .env.production.example .env.production
# Открыть .env.production:
#   VITE_API_BASE_URL=https://api.yourdomain.ru

npm install
npm run build
```

Готовые файлы в `frontend-admin/dist/`.

### 2.3 Загрузка файлов на SpaceWeb

**Вариант А — через файловый менеджер cPanel:**

1. Зайдите в cPanel → **Файловый менеджер**
2. Перейдите в `public_html/` (или в папку субдомена, например `public_html/anketa/`)
3. Нажмите **Загрузить** → загрузите ZIP-архив папки `dist/`
4. Разархивируйте прямо в cPanel (правой кнопкой → Extract)
5. Убедитесь, что `index.html` лежит в корне папки субдомена

**Вариант Б — через FTP (FileZilla или аналог):**

1. В cPanel → **Аккаунты FTP** — создайте FTP-аккаунт для субдомена (или используйте основной)
2. Подключитесь в FileZilla: хост `ftp.yourdomain.ru`, порт 21
3. Скопируйте содержимое `dist/` в папку субдомена

> **Важно:** загружайте именно **содержимое** `dist/` (файлы `index.html`, `assets/`, `brand/` и т.д.),
> а не саму папку `dist/`.

### 2.4 Настройка роутинга SPA (обязательно!)

React-приложение — Single Page Application. При прямом переходе по URL типа `/invitations/123` сервер вернёт 404, если не настроен редирект на `index.html`.

Создайте файл `.htaccess` в корне каждого субдомена:

```apache
Options -MultiViews
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [QSA,L]
```

Загрузите этот файл через файловый менеджер или FTP рядом с `index.html`.

### 2.5 Проверка

Откройте в браузере:
- `https://anketa.yourdomain.ru` — должна открыться страница анкеты
- `https://admin.yourdomain.ru` — должна открыться страница входа
- `https://admin.yourdomain.ru/invitations/test-id` — должен загрузиться интерфейс (пусть и с ошибкой 404 от API), а **не** страница 404 хостинга

---

## 3. Деплой бэкенда на VPS

> Все команды выполняются на VPS через SSH. Предполагается Ubuntu 22.04 / 24.04.

### 3.1 Системные зависимости

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential git \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    # weasyprint требует системные шрифты и библиотеки:
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libcairo-gobject2 \
    fonts-liberation fonts-freefont-ttf
```

### 3.2 PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE USER voice_survey WITH PASSWORD 'STRONG_PASSWORD_HERE';
CREATE DATABASE voice_survey OWNER voice_survey;
GRANT ALL PRIVILEGES ON DATABASE voice_survey TO voice_survey;
SQL
```

> Запомните пароль — он пойдёт в `DATABASE_URL` в `.env`.

### 3.3 Redis

Redis уже запущен после `apt install`. Проверьте:

```bash
redis-cli ping   # должен вернуть PONG
```

По умолчанию Redis слушает `127.0.0.1:6379` — этого достаточно.

### 3.4 Системный пользователь для приложения

```bash
sudo useradd --system --shell /bin/bash --create-home --home-dir /opt/anketa anketa
```

### 3.5 Копирование кода на сервер

**Вариант А — git:**

```bash
sudo -u anketa git clone https://github.com/YOUR/anketa.git /opt/anketa
```

**Вариант Б — rsync с локальной машины** (запускать локально):

```bash
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
    ./backend/ user@YOUR_VPS_IP:/opt/anketa/backend/
```

### 3.6 Python-окружение и зависимости

```bash
sudo -u anketa bash -c "
    python3.11 -m venv /opt/anketa/backend/.venv
    /opt/anketa/backend/.venv/bin/pip install --upgrade pip
    /opt/anketa/backend/.venv/bin/pip install -e /opt/anketa/backend
"
```

### 3.7 Конфигурация (.env)

```bash
sudo cp /opt/anketa/backend/.env.example /opt/anketa/backend/.env
sudo nano /opt/anketa/backend/.env
```

Заполните все поля. Минимум для работы:

```env
DATABASE_URL=postgresql+asyncpg://voice_survey:STRONG_PASSWORD_HERE@localhost:5432/voice_survey
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=<вывод openssl rand -hex 32>
GROQ_API_KEY=gsk_...
AUDIO_ROOT=/var/anketa/audio
CORS_ORIGINS=https://anketa.yourdomain.ru,https://admin.yourdomain.ru
FRONTEND_URL=https://anketa.yourdomain.ru
APP_ENV=production
SEED_MANAGERS=admin@yourdomain.ru:STRONG_PASSWORD:Администратор
```

Ограничьте права на файл:

```bash
sudo chown anketa:anketa /opt/anketa/backend/.env
sudo chmod 600 /opt/anketa/backend/.env
```

### 3.8 Папка для аудиофайлов

```bash
sudo mkdir -p /var/anketa/audio
sudo chown -R anketa:anketa /var/anketa
```

### 3.9 Systemd-сервисы

```bash
# Скопировать юниты
sudo cp /opt/anketa/deploy/anketa-api.service    /etc/systemd/system/
sudo cp /opt/anketa/deploy/anketa-worker.service /etc/systemd/system/

sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable anketa-api anketa-worker

# Запустить
sudo systemctl start anketa-api anketa-worker

# Проверить статус
sudo systemctl status anketa-api
sudo systemctl status anketa-worker
```

### 3.10 nginx

```bash
sudo cp /opt/anketa/deploy/nginx.conf /etc/nginx/sites-available/anketa

# Отредактируйте — замените api.yourdomain.ru на ваш реальный домен
sudo nano /etc/nginx/sites-available/anketa

# Активировать сайт
sudo ln -s /etc/nginx/sites-available/anketa /etc/nginx/sites-enabled/anketa

# Удалить дефолтный сайт (если он мешает)
sudo rm -f /etc/nginx/sites-enabled/default

# Проверить конфиг
sudo nginx -t

# Перезапустить nginx
sudo systemctl reload nginx
```

### 3.11 SSL-сертификат (Let's Encrypt)

```bash
sudo certbot --nginx -d api.yourdomain.ru
```

Certbot автоматически пропишет сертификат в nginx-конфиге. Проверьте, что автообновление работает:

```bash
sudo certbot renew --dry-run
```

---

## 4. Первый запуск

### 4.1 Применить миграции базы данных

```bash
sudo -u anketa bash -c "
    cd /opt/anketa/backend
    .venv/bin/python -m alembic upgrade head
"
```

Ожидаемый вывод: `Running upgrade ... -> ..., <описание>` для каждой миграции.

### 4.2 Создать первого администратора

Если в `.env` заполнен `SEED_MANAGERS`:

```bash
sudo -u anketa bash -c "
    cd /opt/anketa/backend
    .venv/bin/python -c \"
import asyncio, os
from app.db import AsyncSessionLocal
from app.models.manager import Manager
from passlib.context import CryptContext

pwd = CryptContext(schemes=['bcrypt'])

async def seed():
    entries = os.getenv('SEED_MANAGERS', '').split(',')
    async with AsyncSessionLocal() as s:
        for entry in entries:
            if not entry.strip(): continue
            email, password, name = entry.strip().split(':')
            m = Manager(email=email, hashed_password=pwd.hash(password), full_name=name, role='supervisor')
            s.add(m)
        await s.commit()
        print('Done')

asyncio.run(seed())
\"
"
```

> После первого запуска рекомендуется убрать `SEED_MANAGERS` из `.env` и перезапустить сервис.

### 4.3 Проверка API

```bash
curl https://api.yourdomain.ru/health
# Ожидаемый ответ: {"status":"ok","db":"ok","redis":"ok"}
```

### 4.4 Проверка входа через браузер

1. Откройте `https://admin.yourdomain.ru`
2. Войдите с email/паролем из `SEED_MANAGERS`
3. Убедитесь, что дашборд загружается без ошибок

---

## 5. Обновление

### Обновить бэкенд

```bash
# На VPS:
cd /opt/anketa
sudo -u anketa git pull   # или rsync с локальной машины

# Установить новые зависимости (если изменился pyproject.toml)
sudo -u anketa /opt/anketa/backend/.venv/bin/pip install -e /opt/anketa/backend

# Применить новые миграции (если появились)
sudo -u anketa bash -c "cd /opt/anketa/backend && .venv/bin/python -m alembic upgrade head"

# Перезапустить сервисы
sudo systemctl restart anketa-api anketa-worker
```

### Обновить фронтенд

1. На локальной машине: пересобрать (`npm run build`) нужный фронтенд
2. Загрузить содержимое `dist/` на SpaceWeb через файловый менеджер / FTP (заменить старые файлы)

---

## 6. Диагностика

### Логи сервисов

```bash
# API (последние 100 строк, live)
journalctl -u anketa-api -n 100 -f

# Worker
journalctl -u anketa-worker -n 100 -f

# nginx
tail -f /var/log/nginx/anketa-api.error.log
```

### Перезапуск сервисов

```bash
sudo systemctl restart anketa-api
sudo systemctl restart anketa-worker
```

### Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| CORS-ошибка в браузере | `CORS_ORIGINS` не содержит URL фронтенда | Добавить в `.env`, перезапустить `anketa-api` |
| 502 Bad Gateway | uvicorn не запущен или упал | `systemctl status anketa-api`, смотреть логи |
| Пустой список шаблонов в admin | Просрочен JWT / API недоступен | Открыть DevTools → Network, проверить статус `/api/templates` |
| Транскрипция не работает | GROQ_API_KEY не задан или неверный | Проверить `.env`, перезапустить `anketa-worker` |
| Аудио не загружается | Папка `/var/anketa/audio` не существует или нет прав | `mkdir -p /var/anketa/audio && chown anketa:anketa /var/anketa/audio` |
| Ошибка миграции | БД недоступна или `DATABASE_URL` неверный | `sudo -u anketa psql $DATABASE_URL -c "SELECT 1"` |
| `.htaccess` не работает | `AllowOverride` отключён на SpaceWeb | Обратитесь в поддержку SpaceWeb — обычно включён по умолчанию |

### Проверка подключения к БД вручную

```bash
sudo -u anketa /opt/anketa/backend/.venv/bin/python -c "
import asyncio
from app.db import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text('SELECT version()'))
        print(r.scalar())

asyncio.run(check())
"
```

---

## Переменные окружения — справочник

| Переменная | Обязательная | Описание |
|------------|:---:|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | ✅ | Redis connection string (`redis://...`) |
| `JWT_SECRET` | ✅ | Случайная строка ≥32 символа. Генерировать: `openssl rand -hex 32` |
| `GROQ_API_KEY` | ✅ | API-ключ для транскрипции аудио (groq.com) |
| `AUDIO_ROOT` | ✅ | Абсолютный путь к папке хранения аудиофайлов |
| `CORS_ORIGINS` | ✅ | Через запятую: все URL фронтендов (с `https://`) |
| `FRONTEND_URL` | ✅ | URL клиентской анкеты — вставляется в ссылки-приглашения |
| `JWT_ALGORITHM` | — | По умолчанию `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | По умолчанию `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | По умолчанию `7` |
| `MAX_AUDIO_SIZE_MB` | — | По умолчанию `25` |
| `MAX_AUDIO_DURATION_SEC` | — | По умолчанию `300` |
| `APP_ENV` | — | `production` / `development` |
| `LOG_LEVEL` | — | `INFO` / `DEBUG` / `WARNING` |
| `SENTRY_DSN` | — | DSN Sentry; пусто = мониторинг отключён |
| `SEED_MANAGERS` | — | `email:pass:name,...` — только для первого запуска |
