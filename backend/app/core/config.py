from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "EMS Digital Twin API"
    api_backend: str = "fastapi"
    default_duration_min: int = 720
    default_seed: int = 12345


settings = Settings()
