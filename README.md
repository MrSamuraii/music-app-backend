# Music App Backend

Каркас backend'а на FastAPI: регистрация, вход, JWT-авторизация.

## Запуск локально (Windows)

1. Установи PostgreSQL (или подними через Docker: `docker run --name musicapp-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=musicapp -p 5432:5432 -d postgres`)

2. Создай виртуальное окружение и установи зависимости:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Создай файл `.env` в корне проекта (можно скопировать значения из `app/core/config.py` и поменять):
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/musicapp
   SECRET_KEY=сделай-длинный-случайный-ключ-тут
   ```

   Без строк ниже приложение тоже работает — просто Google-логин будет выдавать понятную ошибку:
   ```
   # Вход через Google — создать в console.cloud.google.com/apis/credentials
   # OAuth Client ID типа "Desktop app"
   GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxxxxxx
   ```

4. Запусти сервер:
   ```
   uvicorn app.main:app --reload
   ```

5. Открой http://localhost:8000/docs — там будет автоматическая Swagger-документация со всеми эндпоинтами, можно сразу тестировать регистрацию и вход через браузер.

## Что уже готово

- `POST /auth/register` — регистрация (email, username, password)
- `POST /auth/login` — вход, возвращает JWT access_token
- `GET /auth/me` — данные текущего юзера (нужен Bearer-токен)

## Структура проекта

```
app/
  core/
    config.py      — настройки (из .env)
    database.py     — подключение к БД
    security.py     — хэширование паролей, JWT
    deps.py          — dependency для получения текущего юзера
  models/
    user.py          — модель User
    track.py         — модель Track
    playlist.py       — модели Playlist и PlaylistTrack
  schemas/
    user.py           — Pydantic-схемы для запросов/ответов
  routers/
    auth.py            — роуты регистрации/входа
  main.py               — точка входа приложения
```

## Что дальше

- Роутер для загрузки и стриминга треков (`/tracks`)
- Роутер для плейлистов (`/playlists`)
- Миграции через Alembic вместо `create_all`
