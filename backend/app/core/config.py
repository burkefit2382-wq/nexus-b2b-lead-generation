from ..services import config


class Settings:
    @property
    def DATABASE_URL(self) -> str:
        return config.database_url()


settings = Settings()
