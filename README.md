# Голосовые анкеты (voice-survey) — техническая документация

> Последнее обновление: 2026-04-20

## Оглавление

1. [Обзор системы](#1-обзор-системы)
2. [Архитектура](#2-архитектура)
3. [Стек технологий](#3-стек-технологий)
4. [Модель данных](#4-модель-данных)
5. [API Reference](#5-api-reference)
6. [Ключевые процессы](#6-ключевые-процессы)
7. [Переменные окружения](#7-переменные-окружения)
8. [Деплой и CI/CD](#8-деплой-и-cicd)
9. [Локальный запуск](#9-локальный-запуск)
10. [Тесты](#10-тесты)
11. [Безопасность](#11-безопасность)
12. [Troubleshooting](#12-troubleshooting)
13. [Частые задачи](#13-частые-задачи)

---

## 1. Обзор системы

**Голосовые анкеты** — веб-приложение для сбора голосовых и текстовых ответов клиентов. Менеджер создаёт персональную ссылку и отправляет её клиенту. Клиент заходит на сайт, записывает ответы голосом или вводит текст. Аудио транскрибируется через Groq Whisper. Менеджер видит ответы в панели управления, может оставлять заметки и экспортировать данные.

**Пользователи:**
- **Клиент** — получает ссылку, заполняет анкету, без регистрации
- **Менеджер** — создаёт приглашения, просматривает анкеты, экспортирует данные
- **Администратор** — управление через seed-скрипт (UI не предусмотрен)

**Масштаб:** до 50 анкет/месяц, до 6 менеджеров.

**Продакшен URL:**
- Клиентская анкета: https://anketa.akademia-budushego.ru
- Панель управления: https://admin.akademia-budushego.ru

---

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        Клиент                               │
│  [Браузер] ──► anketa.akademia-budushego.ru                 │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                        Менеджер                             │
│  [Браузер] ──► admin.akademia-budushego.ru                  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────┐
│           VPS 104.165.244.132 (Caddy → Docker Compose)      │
│                                                             │
│  Caddy (80/443, auto SSL)                                   │
│    ├── anketa.akademia-budushego.ru → static frontend-client│
│    ├── admin.akademia-budushego.ru  → static frontend-admin │
│    └── /api/* → 127.0.0.1:8002 (FastAPI)                   │
│                                                             │
│  Docker Compose:                                            │
│    anketa-api (FastAPI, порт 8002) ─────────────────────┐  │
│    anketa-worker (arq) ─────────────────────────────────┤  │
│    anketa-postgres (PostgreSQL 15) ◄────────────────────┘  │
│    anketa-redis (Redis 7) ◄─────────────────────────────┘  │
│                                                             │
│  Volumes:                                                   │
│    postgres_data  ← данные БД                               │
│    audio_data     ← /var/voice-survey/audio                 │
└─────────────────────────────────────────────────────────────┘
```

**Ключевые архитектурные решения:**

| Решение | Обоснование |
|---|---|
| Caddy вместо nginx | Автоматический SSL, минималистичный конфиг |
| Статика на VPS вместо Vercel | Всё в одном месте, не нужен внешний хостинг |
| arq вместо Celery | Native asyncio, Redis уже используется |
| Groq Whisper | Быстро, дёшево, есть ключ |
| Два Vite-проекта | Разные security-поверхности, разные бандлы |
| Бэкенд в Docker image | `docker compose build` обязателен при изменении кода |
| MediaRecorder + sync transcribe | Надёжнее Web Speech API, работает на всех устройствах |

---

## 3. Стек технологий

### Backend
| Компонент | Роль |
|---|---|
| Python 3.11+ | Язык |
| FastAPI | Web framework |
| SQLAlchemy 2.0 (async) | ORM |
| asyncpg | PostgreSQL async driver |
| Alembic | Миграции БД (применяются автоматически при старте контейнера) |
| Pydantic v2 | Валидация данных |
| pydantic-settings | Конфигурация из env |
| python-jose | JWT |
| passlib[bcrypt] | Хеширование паролей |
| arq | Очередь задач (Redis) |
| Groq SDK | Транскрипция Whisper (async фоновая + sync публичная) |
| openpyxl | Генерация XLSX |
| nanoid | Генерация invitation ID |

### Frontend
| Компонент | Роль |
|---|---|
| React 18 + TypeScript | UI |
| Vite 5 | Сборщик |
| TailwindCSS | Стили |
| React Router 6 | Маршрутизация |
| MediaRecorder API | Запись аудио (кросс-браузерный) |

### Инфраструктура
| Компонент | Роль |
|---|---|
| PostgreSQL 15 | Основная БД (БД называется `voice_survey`) |
| Redis 7 | Очередь задач (arq) |
| Caddy | Reverse proxy + автоматический SSL (Let's Encrypt) |
| Docker Compose | Оркестрация контейнеров |
| GitHub Actions | CI/CD (авто-деплой при push в main) |
| VPS HIPHOSTING | Сервер, IP 104.165.244.132 |

---

## 4. Модель данных

### managers

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| email | TEXT UNIQUE | Логин |
| password_hash | TEXT | bcrypt |
| full_name | TEXT | Отображаемое имя. `""` = не заполнено → редирект на /setup-name |
| is_active | BOOLEAN | Деактивация без удаления |
| created_at | TIMESTAMPTZ | |

### survey_templates

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| name | TEXT | Название шаблона |
| is_active | BOOLEAN | Только активные доступны менеджерам |
| created_at | TIMESTAMPTZ | |

> ⚠️ В папке `backend/scripts/` должен быть **только один** YAML файл: `akademiya_questions.yaml`. Каждый yaml создаёт отдельный шаблон при seed.

### survey_questions

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| template_id | UUID FK | → survey_templates |
| order_index | INT | Порядок (1-based). UNIQUE(template_id, order_index) |
| text | TEXT | Текст вопроса |
| hint | TEXT nullable | Подсказка |
| is_required | BOOLEAN | Обязателен для submit |

### invitations

| Поле | Тип | Описание |
|---|---|---|
| id | VARCHAR(20) PK | nanoid(12) — используется в URL |
| template_id | UUID FK | → survey_templates |
| manager_id | UUID FK | → managers |
| client_name | TEXT | Имя клиента |
| client_phone | TEXT nullable | Телефон |
| client_note | TEXT nullable | Внутренняя заметка менеджера |
| status | VARCHAR(20) | `pending` → `in_progress` → `completed` |
| created_at | TIMESTAMPTZ | |
| started_at | TIMESTAMPTZ nullable | Первое открытие ссылки |
| completed_at | TIMESTAMPTZ nullable | Момент submit |
| deleted_at | TIMESTAMPTZ nullable | Soft delete |

### responses

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| invitation_id | VARCHAR(20) FK | → invitations |
| question_id | UUID FK | → survey_questions |
| audio_path | TEXT nullable | Путь в AUDIO_ROOT (если голосовой ответ) |
| audio_duration_sec | REAL nullable | |
| audio_size_bytes | BIGINT nullable | |
| audio_mime | VARCHAR(50) nullable | |
| transcription | TEXT nullable | Готовый текст |
| transcription_status | VARCHAR(20) | `pending` → `processing` → `done`/`failed` |
| transcription_error | TEXT nullable | |
| transcription_attempts | INT | |
| created_at | TIMESTAMPTZ | |
| transcribed_at | TIMESTAMPTZ nullable | |

---

## 5. API Reference

### Публичные endpoints (без авторизации)

#### GET /api/public/invitations/{invitation_id}
Загрузка анкеты. Побочный эффект: `pending` → `in_progress`, проставляет `started_at`.

```json
{
  "invitation": { "id": "abc123", "client_name": "Иван", "status": "in_progress" },
  "questions": [{ "id": "uuid", "order_index": 1, "text": "...", "is_required": true }],
  "existing_responses": [{ "question_id": "uuid", "transcription_status": "done", "transcription": "..." }]
}
```

#### POST /api/public/invitations/{invitation_id}/responses/text
Сохранение текстового ответа. Body: `{ "question_id": "uuid", "text": "..." }`.

#### POST /api/public/invitations/{invitation_id}/submit
Финализация. `400` если не все обязательные вопросы отвечены.

#### GET /api/public/responses/{response_id}/audio
Стриминг аудио. Поддерживает Range requests (HTTP 206).

#### POST /api/public/transcribe
**Синхронная** транскрипция аудио через Groq Whisper. Вызывается фронтендом сразу после записи.

- Body: `multipart/form-data`, поле `audio` — файл (webm/mp4/wav/ogg)
- Response: `{ "text": "расшифрованный текст" }`
- Используется в клиентской анкете вместо Web Speech API

---

### Авторизация

#### POST /api/auth/login
```json
// body
{ "email": "manager@example.com", "password": "secret" }
// response 200
{ "access_token": "...", "token_type": "bearer", "manager": { "id": "...", "full_name": "...", ... } }
```
Refresh token устанавливается в httpOnly cookie.

После логина: если `manager.full_name === ""` → фронтенд редиректит на `/setup-name`.

#### POST /api/auth/refresh
Обновляет access token из httpOnly cookie. `200 { "access_token": "..." }`

#### POST /api/auth/logout
Удаляет cookie. `200 { "ok": true }`

#### GET /api/auth/me
`Authorization: Bearer {token}` → `{ "id", "email", "full_name", "is_active" }`

#### PATCH /api/me/name
Обновление имени менеджера. Вызывается однократно после первого логина.
```json
// body
{ "full_name": "Иванов И.И." }
// response 200
{ "full_name": "Иванов И.И." }
```

---

### Менеджерские endpoints (требуют JWT)

#### GET /api/templates
Список активных шаблонов.

#### GET /api/templates/{id}
Шаблон с вопросами (ordered by order_index).

#### GET /api/invitations
Список приглашений. Query: `status`, `search`, `page`, `page_size`, `my_only`.

#### POST /api/invitations
```json
// body
{ "template_id": "uuid", "client_name": "Иван", "client_phone": "+7...", "client_note": "..." }
// response 201
{ "id": "abc123def456", "url": "https://anketa.akademia-budushego.ru/s/abc123def456" }
```

#### GET /api/invitations/{id}
Детали: информация + вопросы + ответы с транскрипциями.

#### DELETE /api/invitations/{id}
Soft delete. `204 No Content`.

#### GET /api/invitations/{id}/export?format=...
Форматы: `csv_summary`, `csv_rows`, `xlsx_summary`, `xlsx_rows`, `pdf`.

> ⚠️ CSV использует разделитель `;` (стандарт для русского Excel/LibreOffice).

#### GET /api/invitations/{id}/notes
Заметки менеджера по приглашению.

#### POST /api/admin/responses/{response_id}/retranscribe
Сброс и повторная транскрипция. `200 { "ok": true }`

#### POST /api/me/password
```json
{ "current_password": "...", "new_password": "..." }
```

---

### Системные

#### GET /health
```json
{ "status": "ok", "db": "ok", "redis": "ok" }
```

---

## 6. Ключевые процессы

### Заполнение анкеты (клиент)

1. Клиент открывает ссылку → `GET /api/public/invitations/{id}` → экран приветствия
2. Нажимает "Начать" → экран с вопросами
3. На каждом вопросе — кнопка записи (MediaRecorder):
   - Запись → `MediaRecorder` пишет в chunks
   - Стоп → blob отправляется на `POST /api/public/transcribe` → Groq → текст
   - Текст вставляется в поле ответа
4. Ответы сохраняются в `localStorage` (ключ `survey_{invitationId}`) — не теряются при рефреше
5. Навигация: точки вверху экрана (синяя = отвечено, голубая = текущий, серая = пусто)
6. Из экрана review можно вернуться к любому вопросу кнопкой "Изменить"
7. `POST /submit` → финализация

### Транскрипция (arq worker — для аудио-ответов)

```
Redis (arq queue)
    │
    ▼
transcribe_response(response_id)
    ├── ffprobe валидация (< 0.5s или > 300s → failed)
    ├── Groq whisper-large-v3-turbo, language=ru
    │     ├── OK → status='done'
    │     ├── 429/5xx → retry с backoff (5s, 30s, 2m, 10m, 30m)
    │     └── 4xx → status='failed'
    └── COMMIT
```

### Первый логин менеджера

1. `POST /api/auth/login` → получает токен
2. Если `full_name === ""` → фронтенд редиректит на `/setup-name`
3. Менеджер вводит имя → `PATCH /api/me/name`
4. После сохранения — редирект на `/` (главная панели)
5. Повторно `/setup-name` не показывается

### Экспорт данных

Менеджер выбирает формат → `GET /api/invitations/{id}/export?format=...` → StreamingResponse.

**Форматы:**
- `csv_summary` / `xlsx_summary` — одна строка на приглашение, колонки = вопросы
- `csv_rows` / `xlsx_rows` — одна строка на ответ
- `pdf` — форматированный документ

**Кнопка "Скопировать"** в панели детали приглашения — копирует все ответы в буфер обмена в читаемом формате (имя, телефон, менеджер, дата, Q&A).

---

## 7. Переменные окружения

Файл: `backend/.env`. **Не коммитить в git.**

| Переменная | Дефолт | Описание |
|---|---|---|
| `DATABASE_URL` | — | `postgresql+asyncpg://voice_survey:pass@postgres:5432/voice_survey` |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL |
| `JWT_SECRET` | — | Секрет HS256, мин. 32 байта |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | 7 дней |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `GROQ_API_KEY` | — | `gsk_...` |
| `AUDIO_ROOT` | `/var/voice-survey/audio` | Папка аудиофайлов |
| `MAX_AUDIO_SIZE_MB` | `25` | |
| `MAX_AUDIO_DURATION_SEC` | `300` | |
| `DISK_SPACE_MIN_BYTES` | `1073741824` | 1 GB минимум |
| `FRONTEND_URL` | — | URL клиентского фронта (для ссылок в ответах) |
| `CORS_ORIGINS` | — | Разрешённые origins через запятую |
| `APP_ENV` | `production` | |
| `LOG_LEVEL` | `INFO` | |
| `SEED_MANAGERS` | — | `email:pass:Имя Фамилия,...` |
| `SENTRY_DSN` | `""` | Опционально |

---

## 8. Деплой и CI/CD

### Репозиторий
**https://github.com/Hellfiresorg/anketa** (org: Hellfiresorg)

### Автодеплой
Каждый `git push origin main` → GitHub Actions (`.github/workflows/deploy.yml`):

1. Сборка `frontend-admin` (npm ci + npm run build)
2. Сборка `frontend-client` (npm ci + npm run build)
3. rsync `frontend-admin/dist/` → `/opt/services/anketa/frontend-admin/`
4. rsync `frontend-client/dist/` → `/opt/services/anketa/frontend-client/`
5. rsync `backend/` → `/opt/services/anketa/backend/` (исключает `.env`, `__pycache__`, `*.pyc`, `*.db`)
6. SSH: `docker compose build api worker && docker compose up -d`
7. SSH: `docker exec anketa-api python scripts/seed.py`

Ручной запуск: GitHub → Actions → Deploy → "Run workflow".

### ⚠️ КРИТИЧНО: бэкенд запечён в Docker image

Нет bind mount для кода. `Dockerfile` копирует источник в образ при сборке.

**Прямое редактирование файлов на сервере НЕ влияет на запущенные контейнеры.**

Для применения изменений бэкенда всегда нужен rebuild:
```bash
cd /opt/services/anketa
docker compose build api worker && docker compose up -d
```

Исключение: `backend/.env` — читается при старте контейнера, не в образе.

### Ручное управление на сервере

```bash
# Перезапуск без rebuild (только если .env изменился)
cd /opt/services/anketa && docker compose up -d

# Полный rebuild
cd /opt/services/anketa && docker compose build api worker && docker compose up -d

# Логи
docker logs anketa-api -f --tail 50
docker logs anketa-worker -f --tail 50

# Re-seed вручную
docker exec anketa-api python scripts/seed.py

# Доступ к БД
docker exec -it anketa-postgres psql -U voice_survey -d voice_survey
```

### Seed: правила шаблонов

- `seed.py` загружает **все** `*.yaml` из `scripts/` внутри контейнера
- В `scripts/` должен быть **только** `akademiya_questions.yaml`
- Лишний yaml → лишний шаблон в БД
- Удалить лишний шаблон:
  ```bash
  docker exec anketa-postgres psql -U voice_survey -d voice_survey \
    -c "DELETE FROM survey_templates WHERE name='Лишний шаблон';"
  ```

### GitHub Secrets (org-level, Hellfiresorg)

| Secret | Значение |
|---|---|
| `SSH_HOST` | `104.165.244.132` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | ed25519 приватный ключ (`~/.ssh/github_actions` на dev-машине) |

---

## 9. Локальный запуск

### Backend

```bash
# Запустить Postgres и Redis
docker run -d -p 5432:5432 -e POSTGRES_USER=voice_survey -e POSTGRES_PASSWORD=password -e POSTGRES_DB=voice_survey postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

cd backend
pip install -e ".[dev]"
cp .env.example .env  # добавить GROQ_API_KEY и JWT_SECRET

python -m alembic upgrade head
python scripts/seed.py

uvicorn app.main:app --reload        # API на :8000
python -m arq app.workers.arq_worker.WorkerSettings  # worker
```

### Frontend

```bash
cd frontend-client && npm install && npm run dev  # :5173
cd frontend-admin  && npm install && npm run dev  # :5174
```

---

## 10. Тесты

```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

| Файл | Покрытие |
|---|---|
| `tests/test_auth.py` | Login, /me, logout, invalid token |
| `tests/test_public_api.py` | GET invitation, submit |
| `tests/test_invitations.py` | CRUD, search, soft delete, export |
| `tests/test_transcription.py` | ffprobe, rate limit, retries |

**Стек:** pytest-asyncio, httpx.AsyncClient + ASGITransport, SQLite (aiosqlite), unittest.mock для Groq.

---

## 11. Безопасность

- **JWT HS256**, access token 7 дней, refresh token 7 дней (httpOnly cookie)
- **bcrypt** для паролей
- **CORS whitelist** — только разрешённые origins
- **Nanoid(12)** для invitation ID — 71 бит энтропии
- **Pydantic strict mode** на всех входных данных
- **Mime type whitelist**: `audio/webm`, `audio/mp4`, `audio/wav`, `audio/ogg`
- Аудиофайлы: атомарная запись (tmp → rename)
- Все секреты через `.env`, не в git

> ⚠️ При компрометации `JWT_SECRET` — сменить секрет в `.env` и перезапустить контейнер. Все токены инвалидируются.

---

## 12. Troubleshooting

### iOS Safari не записывает
Safari поддерживает только `audio/mp4`. Это учтено в `getSupportedMimeType()` — функция перебирает форматы и берёт первый поддерживаемый. Убедитесь что сайт открыт по HTTPS.

### Groq 429 (Rate limit)
Worker автоматически повторит с backoff. Проверить:
```sql
SELECT id, transcription_status, transcription_attempts, transcription_error
FROM responses WHERE transcription_status IN ('pending', 'processing', 'failed');
```

### Транскрипция не работает (sync endpoint)
Проверить логи API: `docker logs anketa-api --tail 50`.
Проверить ключ Groq: значение `GROQ_API_KEY` в `backend/.env`.

### Ответы потеряны при рефреше
В норме не должно происходить — ответы сохраняются в `localStorage` (ключ `survey_{invitationId}`).
Если всё же потерялись: проверить в devtools → Application → Local Storage.

### Диск кончился
```bash
df -h
find /var/voice-survey/audio -name "*.webm" -size +10M -ls
```

### Worker завис
```bash
docker exec anketa-redis redis-cli LLEN arq:queue:default
# Сброс зависших задач в БД:
docker exec anketa-postgres psql -U voice_survey -d voice_survey \
  -c "UPDATE responses SET transcription_status='pending', transcription_attempts=0 WHERE transcription_status='processing';"
```

### Изменения в коде не применились
Бэкенд запечён в Docker image. Нужен rebuild:
```bash
cd /opt/services/anketa && docker compose build api worker && docker compose up -d
```

---

## 13. Частые задачи

### Добавить или изменить вопросы шаблона

1. Отредактировать `backend/scripts/default_questions.yaml`
2. Запустить сид-скрипт (идемпотентно, обновит существующие вопросы):

```bash
docker compose run --rm backend python scripts/seed.py
# или локально:
cd backend && python scripts/seed.py
```

### Добавить менеджера

Добавить запись в `SEED_MANAGERS` и перезапустить сид:

```
SEED_MANAGERS=existing@example.com:pass:Существующий,new@example.com:newpass:Новый Менеджер
```

Или напрямую через SQL:
```sql
INSERT INTO managers (id, email, password_hash, full_name)
VALUES (gen_random_uuid(), 'new@example.com', '<bcrypt_hash>', 'Имя');
```

### Бэкапы аудиофайлов

Аудиофайлы хранятся в `AUDIO_ROOT`. Пример резервного копирования через rsync:

```bash
rsync -avz --progress /var/voice-survey/audio/ backup@backup-server:/backups/voice-survey/
```

Или через restic:
```bash
restic -r s3:s3.amazonaws.com/my-bucket/voice-survey backup /var/voice-survey/audio
```
