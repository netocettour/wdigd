import os


class Settings:
    def __init__(self) -> None:
        self.secret_key: str = os.environ.get("SECRET_KEY", "dev-secret-cambiame-en-produccion")
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./wdigd.db")
        # Railway entrega postgres://; SQLAlchemy 2.x exige postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.database_url: str = db_url


settings = Settings()
