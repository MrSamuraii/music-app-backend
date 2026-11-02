from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/musicapp"

    # JWT
    SECRET_KEY: str = "change-me-in-.env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # Хранилище файлов
    STORAGE_DIR: str = "storage/tracks"

    # Вход через Google (нужно создать OAuth Client ID типа "Desktop app"
    # в Google Cloud Console: console.cloud.google.com/apis/credentials)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Проверка обновлений приложения. Когда выпускаешь новую версию —
    # поменяй APP_LATEST_VERSION и ссылку на установщик в .env и перезапусти сервер.
    APP_LATEST_VERSION: str = "0.2.0"
    APP_MIN_VERSION: str = "0.0.0"  # версии ниже этой обязаны обновиться
    APP_DOWNLOAD_URL: str = ""
    APP_RELEASE_NOTES: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
