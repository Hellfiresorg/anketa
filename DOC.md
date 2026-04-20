# DOC.md — Техническая документация: Голосовые анкеты

## Оглавление

1. [Обзор системы](#1-обзор-системы)
2. [Архитектура](#2-архитектура)
3. [Стек технологий](#3-стек-технологий)
4. [Модель данных](#4-модель-данных)
5. [API Reference](#5-api-reference)
6. [Ключевые процессы](#6-ключевые-процессы)
7. [Переменные окружения](#7-переменные-окружения)
8. [Локальный запуск](#8-локальный-запуск)
9. [Тесты](#9-тесты)
10. [Безопасность](#10-безопасность)
11. [Troubleshooting](#11-troubleshooting)
12. [TODO / Следующие шаги](#12-todo--следующие-шаги)

---

## 1. Обзор системы

**Голосовые анкеты** — веб-приложение для сбора голосовых ответов клиентов перед поступлением в заведение. Менеджер создаёт персональную ссылку и отправляет её клиенту. Клиент заходит на сайт, записывает ответы голосом прямо в браузере. Аудио автоматически транскрибируется в текст (Groq Whisper). Менеджер видит транскрипции в панели управления и может экспортировать данные.

**Пользователи:**
- **Клиент** — получает ссылку, заполняет анкету голосом, без регистрации
- **Менеджер** — создаёт приглашения, просматривает анкеты, экспортирует данные
- **Администратор** — управление через SQL/сид-скрипт (UI не предусмотрен в MVP)

**Масштаб:** до 50 анкет/месяц, 4 менеджера.

---

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        Клиент                               │
│  [Браузер] ──► Vercel (frontend-client) ──► /s/{id}         │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                        Менеджер                             │
│  [Браузер] ──► Vercel (frontend-admin) ──► /login, /        │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/HTTPS
┌────────────────────────────▼────────────────────────────────┐
│                  VPS (nginx → FastAPI)                       │
│                                                             │
│  nginx (HTTPS, proxy_pass) ──► FastAPI (uvicorn)            │
│                                    │                        │
│                      ┌─────────────┼──────────────┐        │
│                      ▼             ▼              ▼        │
│               PostgreSQL        Redis        /var/voice-   │
│               (данные)        (очередь)      survey/audio  │
│                                    │          (аудио)      │
│                                    ▼                       │
│                             arq worker ──► Groq API        │
│                             (транскрипция)  (Whisper)      │
└─────────────────────────────────────────────────────────────┘
```

**Потоки данных:**

1. **Заполнение анкеты**: Клиент → GET /api/public/invitations/{id} → запись аудио в браузере → POST /api/public/invitations/{id}/responses (multipart) → файл сохраняется атомарно → задача enqueue в Redis → POST /submit
2. **Транскрипция**: arq worker → dequeue → ffprobe валидация → Groq API → сохранение текста
3. **Просмотр**: Менеджер → GET /api/invitations/{id} → список ответов с транскрипциями + аудио player

**Ключевые архитектурные решения:**

| Решение | Обоснование |
|---|---|
| arq вместо Celery | Минимум зависимостей, native asyncio, Redis уже используется |
| Groq Whisper вместо OpenAI | У пользователя есть ключ, дешевле, быстрее |
| Два отдельных Vite-проекта | Разные security-поверхности, разные бандлы, разные Vercel деплои |
| Soft delete для приглашений | Аудиофайлы не удаляются автоматически, история сохраняется |
| Все менеджеры видят все анкеты | Взаимозаменяемость, подстраховка при отсутствии коллеги |

---

## 3. Стек технологий

### Backend
| Компонент | Версия | Роль |
|---|---|---|
| Python | 3.11+ | Язык |
| FastAPI | ≥0.111 | Web framework |
| SQLAlchemy | ≥2.0 (async) | ORM |
| asyncpg | ≥0.29 | PostgreSQL async driver |
| Alembic | ≥1.13 | Миграции БД |
| Pydantic v2 | ≥2.0 | Валидация данных |
| pydantic-settings | ≥2.0 | Конфигурация из env |
| python-jose | ≥3.3 | JWT |
| passlib[bcrypt] | ≥1.7 | Хеширование паролей |
| arq | ≥0.25 | Очередь задач (Redis) |
| Groq SDK | ≥0.9 | Транскрипция Whisper |
| openpyxl | ≥3.1 | Генерация XLSX |
| weasyprint | ≥62 | Генерация PDF |
| nanoid | ≥2.0 | Генерация invitation ID |
| structlog | ≥24 | Структурированные логи |

### Frontend
| Компонент | Версия | Роль |
|---|---|---|
| React | 18 | UI framework |
| TypeScript | 5 | Типизация |
| Vite | 5 | Сборщик |
| TailwindCSS | 3 | Стили |
| React Router | 6 | Маршрутизация |
| MediaRecorder API | — | Запись аудио |
| Web Audio API | — | Визуализация амплитуды |

### Инфраструктура
| Компонент | Роль |
|---|---|
| PostgreSQL 15 | Основная БД |
| Redis 7 | Очередь задач (arq) |
| nginx | Reverse proxy, HTTPS termination |
| Vercel | Хостинг frontend (2 проекта) |
| VPS (SpaceWeb) | Бэкенд + БД + Redis |

---

## 4. Модель данных

### managers
Менеджеры системы. Создаются через сид-скрипт.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| email | TEXT UNIQUE | Логин |
| password_hash | TEXT | bcrypt, cost=12 |
| full_name | TEXT | Отображаемое имя |
| is_active | BOOLEAN | Для деактивации без удаления |
| created_at | TIMESTAMPTZ | |

### survey_templates
Шаблоны анкет. На старте — один дефолтный.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| name | TEXT | Название шаблона |
| is_active | BOOLEAN | Только активные шаблоны доступны менеджерам |
| created_at | TIMESTAMPTZ | |

### survey_questions
Вопросы шаблона. Порядок задаётся `order_index`.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| template_id | UUID FK | → survey_templates |
| order_index | INT | Порядок (0-based). UNIQUE(template_id, order_index) |
| text | TEXT | Текст вопроса |
| hint | TEXT nullable | Подсказка под вопросом |
| is_required | BOOLEAN | Обязателен ли ответ для submit |

### invitations
Персональные приглашения. ID — nanoid(12), используется в URL.

| Поле | Тип | Описание |
|---|---|---|
| id | VARCHAR(20) PK | nanoid(12) |
| template_id | UUID FK | → survey_templates |
| manager_id | UUID FK | → managers (кто создал) |
| client_name | TEXT | Имя клиента |
| client_phone | TEXT nullable | Телефон |
| client_note | TEXT nullable | Внутренняя заметка менеджера |
| status | VARCHAR(20) | `pending` → `in_progress` → `completed` |
| created_at | TIMESTAMPTZ | |
| started_at | TIMESTAMPTZ nullable | Первое открытие ссылки |
| completed_at | TIMESTAMPTZ nullable | Момент submit |
| expires_at | TIMESTAMPTZ nullable | Зарезервировано для будущего |
| deleted_at | TIMESTAMPTZ nullable | Soft delete |

**Индексы:** `created_at`, `status`, `manager_id`

### responses
Ответы клиентов (по одному на вопрос в рамках приглашения).

| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | |
| invitation_id | VARCHAR(20) FK | → invitations |
| question_id | UUID FK | → survey_questions |
| audio_path | TEXT | Относительный путь в AUDIO_ROOT |
| audio_duration_sec | REAL nullable | Заполняется после ffprobe |
| audio_size_bytes | BIGINT nullable | |
| audio_mime | VARCHAR(50) nullable | `audio/webm`, `audio/mp4`, etc. |
| transcription | TEXT nullable | Готовый текст от Groq |
| transcription_status | VARCHAR(20) | `pending` → `processing` → `done`/`failed` |
| transcription_error | TEXT nullable | Текст последней ошибки |
| transcription_attempts | INT | Счётчик попыток |
| created_at | TIMESTAMPTZ | |
| transcribed_at | TIMESTAMPTZ nullable | Момент успешной транскрипции |

**Индекс:** partial index на `transcription_status IN ('pending', 'processing', 'failed')`

### audit_log
Минимальный аудит действий менеджеров.

| Поле | Тип | Описание |
|---|---|---|
| id | BIGSERIAL PK | |
| manager_id | UUID nullable FK | → managers |
| action | VARCHAR(50) | `login`, `create_invitation`, `delete_invitation`, `export` |
| target_id | TEXT nullable | ID целевого объекта |
| meta | JSONB nullable | Дополнительные данные |
| created_at | TIMESTAMPTZ | |

---

## 5. API Reference

### Публичные endpoints (без авторизации)

#### GET /api/public/invitations/{invitation_id}
Загрузка анкеты по ID приглашения.

**Responses:**
- `200` — анкета найдена. Побочный эффект: если статус `pending`, меняет на `in_progress`, проставляет `started_at`.
- `404` — приглашение не найдено
- `410` — приглашение удалено (`deleted_at` не null)

```json
{
  "invitation": { "id": "abc123", "client_name": "Иван", "status": "in_progress", ... },
  "questions": [{ "id": "uuid", "order_index": 0, "text": "...", "hint": null, "is_required": true }],
  "existing_responses": [{ "question_id": "uuid", "transcription_status": "done", "audio_url": "/api/public/responses/uuid/audio", "transcription": "..." }]
}
```

#### POST /api/public/invitations/{invitation_id}/responses
Загрузка аудио-ответа. `multipart/form-data`: `question_id` (UUID), `audio` (file).

**Responses:**
- `200` — загружено. Если ответ на этот вопрос уже есть — перезаписывается (старый файл удаляется).
- `409` — приглашение в статусе `completed`
- `422` — невалидный mime-тип или файл слишком большой
- `503` — недостаточно места на диске

```json
{ "response_id": "uuid", "transcription_status": "pending" }
```

#### POST /api/public/invitations/{invitation_id}/submit
Финализация анкеты.

**Responses:**
- `200` — успешно
- `400` — не все обязательные вопросы закрыты: `{ "detail": { "missing_question_ids": ["uuid1", "uuid2"] } }`
- `409` — уже завершена

#### GET /api/public/responses/{response_id}/audio
Стриминг аудиофайла. Поддерживает `Range` requests (HTTP 206).

---

### Авторизация

#### POST /api/auth/login
```json
// body
{ "email": "manager@example.com", "password": "secret" }
// response 200
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
// response 401
{ "detail": "Invalid credentials" }
```
Побочный эффект: refresh_token устанавливается в httpOnly cookie.

#### POST /api/auth/refresh
Обновление access token. Читает refresh_token из httpOnly cookie.
```json
// response 200
{ "access_token": "...", "token_type": "bearer" }
```

#### POST /api/auth/logout
Удаляет cookie. `200 { "ok": true }`

#### GET /api/auth/me
Требует `Authorization: Bearer {token}`.
```json
{ "id": "uuid", "email": "...", "full_name": "...", "is_active": true }
```

---

### Менеджерские endpoints (требуют JWT)

Все endpoints требуют заголовок `Authorization: Bearer {access_token}`.

#### GET /api/templates
Список активных шаблонов.

#### GET /api/templates/{id}
Шаблон с вопросами (ordered by order_index).

#### GET /api/invitations
Список всех (не удалённых) приглашений. Query params:
- `status` — фильтр по статусу
- `search` — поиск по `client_name` / `client_phone`
- `page`, `page_size` — пагинация
- `my_only=true` — только мои приглашения

```json
{
  "items": [{ "id": "...", "client_name": "...", "manager_full_name": "...", "status": "completed", "transcription_ready": 8, "transcription_total": 10, ... }],
  "total": 42, "page": 1, "page_size": 20
}
```

#### POST /api/invitations
Создать приглашение.
```json
// body
{ "template_id": "uuid", "client_name": "Иван", "client_phone": "+7...", "client_note": "..." }
// response 201
{ "id": "abc123def456", "url": "https://client.example.com/s/abc123def456" }
```

#### GET /api/invitations/{id}
Детали: информация + вопросы + ответы с транскрипциями.

#### DELETE /api/invitations/{id}
Soft delete. Пишет в audit_log. `204 No Content`.

#### GET /api/invitations/{id}/export?format=...
Форматы: `csv_summary`, `csv_rows`, `xlsx_summary`, `xlsx_rows`, `pdf`.
Возвращает файл с `Content-Disposition: attachment`.

#### GET /api/invitations/export
Заглушка массового экспорта. Всегда `501 Not Implemented`.

#### GET /api/admin/responses/{response_id}/audio
Стриминг аудио с проверкой JWT.

#### POST /api/admin/responses/{response_id}/retranscribe
Сброс и повторная постановка в очередь. `200 { "ok": true }`.

#### POST /api/me/password
Смена пароля.
```json
// body
{ "current_password": "...", "new_password": "..." }
```

---

### Системные

#### GET /health
```json
{ "status": "ok", "db": "ok", "redis": "ok" }
```
`db` — результат `SELECT 1`. `redis` — результат `PING`.

#### GET /metrics
Заглушка Prometheus. `200 text/plain`.

---

## 6. Ключевые процессы

### Создание и заполнение приглашения

```
Менеджер                    Backend                      Клиент
   │                           │                            │
   ├── POST /api/invitations ──►│                            │
   │◄── { id, url } ───────────┤                            │
   │                           │                            │
   │    [отправляет ссылку] ──────────────────────────────►│
   │                           │                            │
   │                           │◄── GET /public/inv/{id} ──┤
   │                           ├─── { invitation, questions, existing_responses } ──►│
   │                           │   (status: pending→in_progress)
   │                           │                            │
   │                           │◄── POST /public/inv/{id}/responses ──┤
   │                           │    (multipart: question_id + audio file)
   │                           ├── сохранить файл атомарно ─┤
   │                           ├── enqueue transcribe_response ──► Redis
   │                           ├─── { response_id, status: pending } ──►│
   │                           │                            │
   │                           │◄── POST /public/inv/{id}/submit ──┤
   │                           ├── проверить все required ──┤
   │                           ├─── { status: completed } ──►│
```

### Транскрипция (arq worker)

```
Redis (arq queue)
    │
    ▼
transcribe_response(response_id)
    │
    ├── SELECT response FROM DB
    ├── SET status = 'processing', attempts += 1
    │
    ├── ffprobe(audio_path)
    │     ├── duration < 0.5s → status='failed', STOP
    │     ├── duration > 300s → status='failed', STOP
    │     └── ffprobe not found → WARNING, continue
    │
    ├── Groq API: whisper-large-v3-turbo, language=ru
    │     ├── OK → transcription=text, status='done', transcribed_at=now()
    │     │
    │     ├── 429 / 5xx / ConnectionError (retryable):
    │     │     ├── attempts < 5 → enqueue with backoff (5s,30s,2m,10m,30m)
    │     │     └── attempts >= 5 → status='failed'
    │     │
    │     └── 4xx non-429 (не retryable):
    │           └── status='failed', error=message
    │
    └── COMMIT
```

### Экспорт данных

Менеджер выбирает формат из дропдауна → GET /api/invitations/{id}/export?format=... → backend генерирует файл → StreamingResponse с Content-Disposition → браузер скачивает файл.

**Форматы:**
- `csv_summary` / `xlsx_summary` — одна строка на приглашение, колонки = вопросы
- `csv_rows` / `xlsx_rows` — одна строка на ответ (удобно для анализа)
- `pdf` — отформатированный документ через weasyprint (HTML → PDF)

---

## 7. Переменные окружения

| Переменная | Тип | Дефолт | Описание |
|---|---|---|---|
| `DATABASE_URL` | str | — | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | str | `redis://localhost:6379/0` | Redis URL |
| `JWT_SECRET` | str | `change-me` | Секрет HS256. Мин. 32 байта |
| `JWT_ALGORITHM` | str | `HS256` | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `15` | TTL access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | TTL refresh token |
| `GROQ_API_KEY` | str | — | Groq API ключ (`gsk_...`) |
| `AUDIO_ROOT` | str | `/var/voice-survey/audio` | Корневая папка аудиофайлов |
| `MAX_AUDIO_SIZE_MB` | int | `25` | Макс. размер файла в МБ |
| `MAX_AUDIO_DURATION_SEC` | int | `300` | Макс. длительность в секундах |
| `DISK_SPACE_MIN_BYTES` | int | `1073741824` | Мин. свободное место (1 GB) |
| `FRONTEND_URL` | str | `http://localhost:5173` | URL клиентского фронта (для ссылок) |
| `CORS_ORIGINS` | str | `http://localhost:5173,...` | Разрешённые origins через запятую |
| `SENTRY_DSN` | str | `""` | Sentry DSN (пусто = отключено) |
| `APP_ENV` | str | `development` | Среда |
| `LOG_LEVEL` | str | `INFO` | Уровень логов |
| `SEED_MANAGERS` | str | — | `email:pass:Имя,...` для сид-скрипта |

---

## 8. Локальный запуск

### Через Docker Compose (рекомендуется)

```bash
# 1. Настроить переменные
cp backend/.env.example backend/.env
# Добавить GROQ_API_KEY и JWT_SECRET в backend/.env

# 2. Запустить
docker compose up

# 3. Применить сид
docker compose run --rm backend python scripts/seed.py
```

### Без Docker (для разработки backend)

```bash
# Запустить Postgres и Redis (через Docker или нативно)
docker run -d -p 5432:5432 -e POSTGRES_USER=voice_survey -e POSTGRES_PASSWORD=password -e POSTGRES_DB=voice_survey postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Установить зависимости
cd backend
pip install -e ".[dev]"

# Настроить .env
cp .env.example .env

# Применить миграции
python -m alembic upgrade head

# Сид
python scripts/seed.py

# Запустить API
uvicorn app.main:app --reload

# В другом терминале — worker
python -m arq app.workers.arq_worker.WorkerSettings
```

### Frontend

```bash
# Клиентская форма
cd frontend-client
cp .env.example .env
npm install
npm run dev  # http://localhost:5173

# Панель управления
cd frontend-admin
cp .env.example .env
npm install
npm run dev  # http://localhost:5174
```

---

## 9. Тесты

### Запуск

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```

### С coverage

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Что покрыто

| Файл | Что тестируется |
|---|---|
| `tests/test_auth.py` | Login success/fail, /me, logout, invalid token |
| `tests/test_public_api.py` | GET invitation (pending→in_progress, 404, 410), submit (missing required, 409) |
| `tests/test_invitations.py` | Create, list, search, delete (soft), get detail, bulk export stub (501) |
| `tests/test_transcription.py` | ffprobe not found (graceful), too short, too long, rate limit (retryable), 4xx (not retryable) |

### Стек тестирования

- **pytest** + **pytest-asyncio** (anyio backend)
- **httpx.AsyncClient** с **ASGITransport** для тестов API
- **SQLite (aiosqlite)** вместо Postgres для изоляции
- **unittest.mock** для Groq API

---

## 10. Безопасность

### Аутентификация

- **JWT HS256** с коротким TTL access token (15 мин) и длинным refresh (7 дней)
- **Refresh rotation**: каждый вызов `/refresh` создаёт новый refresh token
- **httpOnly cookie** для refresh token — недоступен JavaScript
- **bcrypt** cost=12 для паролей — достаточно медленный для brute force защиты

> ⚠️ При компрометации JWT_SECRET все токены нужно инвалидировать сменой секрета + разлогином.

### API Protection

- **CORS whitelist** — только разрешённые origins
- **Rate limiting** на публичные endpoints через slowapi
- **Pydantic strict mode** на всех входных данных
- **Nanoid(12)** для invitation ID — 71 бит энтропии, подбором не взять
- **Magic bytes validation** на загружаемые аудиофайлы
- **Mime type whitelist**: только `audio/webm`, `audio/mp4`, `audio/wav`, `audio/ogg`

### Хранение файлов

- Аудиофайлы: owner = пользователь бэкенда, mode 0640
- Директории: mode 0750
- Атомарная запись: tmp → rename (предотвращает частичные файлы)

### Аудит

Все значимые действия записываются в `audit_log`:
- `login` — каждый вход
- `create_invitation` — создание приглашения
- `delete_invitation` — мягкое удаление
- `export` — экспорт данных

### Секреты

- Все секреты через переменные окружения
- `.env` файл в `.gitignore`
- Sentry DSN опционален (пустой = отключён)

---

## 11. Troubleshooting

### iOS Safari не записывает

Safari требует явного user gesture перед `getUserMedia`. Запись должна инициироваться только по нажатию кнопки. Также:
- Убедитесь что сайт открыт по HTTPS
- iOS Safari поддерживает только `audio/mp4` (не webm) — это учтено в MediaRecorder fallback

### Groq 429 (Rate limit)

Worker автоматически повторит с backoff. Проверить статус:
```sql
SELECT id, transcription_status, transcription_attempts, transcription_error
FROM responses WHERE transcription_status IN ('pending', 'processing', 'failed');
```

### Диск кончился

```bash
# Проверить место
df -h /var/voice-survey/audio

# Логи
journalctl -u voice-survey-api | grep "disk space"

# Экстренно: найти большие файлы
find /var/voice-survey/audio -name "*.webm" -size +10M -ls
```

### Worker завис

```bash
# Посмотреть очередь в Redis
redis-cli -u $REDIS_URL LLEN arq:queue:default

# Сбросить зависшие задачи
redis-cli -u $REDIS_URL DEL arq:queue:default

# Вручную сбросить статус
psql $DATABASE_URL -c "UPDATE responses SET transcription_status='pending', transcription_attempts=0 WHERE transcription_status='processing';"
```

### Транскрипция не работает

```bash
# Проверить ключ
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models

# Проверить ffprobe
ffprobe -version
```

---

## 12. TODO / Следующие шаги

Следующие функции намеренно исключены из MVP:

| Функция | Причина | Сложность |
|---|---|---|
| Уведомления менеджеру (email/Telegram) | Не критично для старта | Средняя |
| AI-анализ транскрипций (sentiment, ключевые слова) | Требует продуктового решения | Высокая |
| Роль "Администратор" (UI для управления менеджерами и шаблонами) | Пока хватает seed + SQL | Средняя |
| Шифрование аудио at-rest | Не требуется регулятором | Средняя |
| Мультиязычность интерфейса | Только русский в MVP | Низкая |
| CI/CD pipeline | Ручной деплой достаточен | Низкая |
| Автоматическая очистка удалённых аудиофайлов | Soft delete + ручная очистка | Низкая |
| Массовый экспорт (все анкеты за период) | Эндпоинт заглушен как 501 | Средняя |
| Настройка лимита длительности через UI шаблона | Сейчас константа 300 сек | Низкая |
| Refresh token blacklist (немедленный logout) | Сейчас refresh action до истечения TTL | Средняя |
