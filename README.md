# Голосовые анкеты (voice-survey)

Инструмент для сбора голосовых ответов клиентов перед поступлением в заведение. Клиент получает персональную ссылку, отвечает на вопросы голосом в браузере, ответы автоматически транскрибируются через Groq Whisper. Менеджеры просматривают анкеты в удобной панели управления.

---

## Быстрый старт (локальная разработка)

### Предварительные требования

- Docker + Docker Compose
- Node.js 20+
- Python 3.11+

### 1. Клонировать и настроить переменные окружения

```bash
cp backend/.env.example backend/.env
# Отредактировать backend/.env: добавить GROQ_API_KEY и JWT_SECRET
```

### 2. Запустить всё одной командой

```bash
docker compose up
```

Сервисы будут доступны:
- API: http://localhost:8000/docs
- Клиентская форма: http://localhost:5173
- Панель управления: http://localhost:5174
- Health: http://localhost:8000/health

### 3. Первоначальный сид (создать менеджеров и шаблон)

```bash
docker compose run --rm backend python scripts/seed.py
```

Менеджеры указываются в `SEED_MANAGERS` в `.env`:
```
SEED_MANAGERS=manager@example.com:password123:Имя Менеджера
```

---

## Переменные окружения

| Переменная | Обязательная | Описание | Пример |
|---|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL URL с asyncpg | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | ✅ | Redis URL | `redis://localhost:6379/0` |
| `JWT_SECRET` | ✅ | Секрет для JWT (мин. 32 байта) | `openssl rand -hex 32` |
| `GROQ_API_KEY` | ✅ | API ключ Groq | `gsk_...` |
| `AUDIO_ROOT` | ✅ | Путь для хранения аудиофайлов | `/var/voice-survey/audio` |
| `FRONTEND_URL` | ✅ | URL клиентского фронтенда | `https://client.example.com` |
| `SEED_MANAGERS` | Для сида | Менеджеры через запятую | `email:pass:Имя` |
| `SENTRY_DSN` | ❌ | DSN для Sentry (опционально) | `https://...@sentry.io/...` |
| `MAX_AUDIO_SIZE_MB` | ❌ | Макс. размер аудио в МБ | `25` |
| `MAX_AUDIO_DURATION_SEC` | ❌ | Макс. длительность аудио в сек | `300` |
| `CORS_ORIGINS` | ❌ | Разрешённые CORS origins | `https://app.example.com` |

> ⚠️ **JWT_SECRET**: нельзя менять без инвалидации всех сессий. При ротации нужно явно разлогинить всех пользователей.

---

## Как добавить или изменить вопросы шаблона

1. Отредактировать `backend/scripts/default_questions.yaml`
2. Запустить сид-скрипт (идемпотентно, обновит существующие вопросы):

```bash
docker compose run --rm backend python scripts/seed.py
# или локально:
cd backend && python scripts/seed.py
```

---

## Как добавить менеджера

Добавить запись в `SEED_MANAGERS` и перезапустить сид:

```
SEED_MANAGERS=existing@example.com:pass:Существующий,new@example.com:newpass:Новый Менеджер
```

Или напрямую через SQL:
```sql
INSERT INTO managers (id, email, password_hash, full_name)
VALUES (gen_random_uuid(), 'new@example.com', '<bcrypt_hash>', 'Имя');
```

---

## Бэкапы аудиофайлов

Аудиофайлы хранятся в `AUDIO_ROOT`. Пример резервного копирования через rsync:

```bash
rsync -avz --progress /var/voice-survey/audio/ backup@backup-server:/backups/voice-survey/
```

Или через restic:
```bash
restic -r s3:s3.amazonaws.com/my-bucket/voice-survey backup /var/voice-survey/audio
```

---

## Деплой

Деплой выполняется внешним исполнителем. Подробное описание системы — в [DOC.md](DOC.md).

---

## Troubleshooting

### iOS Safari не записывает аудио

Safari на iOS требует явного взаимодействия пользователя (тап) перед `getUserMedia`. Кнопка "Начать" должна быть нажата самим пользователем — не программно. Также убедитесь, что сайт открыт по HTTPS.

### Groq возвращает 429 (Rate limit)

Worker автоматически повторит задачу с экспоненциальным backoff (5с, 30с, 2мин, 10мин, 30мин). Статус в панели управления изменится на `done` автоматически. Если проблема не решается — проверьте лимиты на https://console.groq.com.

### Диск кончился

API вернёт `503` на загрузку аудио если свободно менее 1GB. В логах появится `WARNING: disk space low`. Освободите место или увеличьте диск.

### Worker не стартует

Проверьте подключение к Redis:
```bash
docker compose logs worker
redis-cli -u $REDIS_URL ping
```

### Транскрипция зависла в `processing`

Worker мог упасть во время обработки. Используйте кнопку "Перетранскрибировать" в панели управления или:
```sql
UPDATE responses SET transcription_status='pending', transcription_attempts=0 WHERE transcription_status='processing';
```
