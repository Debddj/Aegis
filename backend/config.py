from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_api_key: str
    database_url: str
    redis_url: str
    chroma_persist_dir: str = "./chroma_db"
    backend_port: int = 8000
    grpc_port: int = 50051
    auto_remediation_enabled: bool = True
    risk_threshold_auto: str = "low"

    class Config:
        env_file = ".env"

settings = Settings()
