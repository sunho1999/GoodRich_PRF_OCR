from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "LLM Link PDF RAG"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # OpenAI Configuration (선택적 - GUI 모드에서는 불필요)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # Storage Configuration
    storage_backend: str = "local"  # local, s3, minio
    storage_path: str = "./data"
    
    # S3/MinIO Configuration
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    s3_region_name: Optional[str] = None
    
    # PDF Processing Limits
    max_pdf_mb: int = 80
    max_pages: int = 1000
    
    # Domain Allowlist
    allowlist_domains: List[str] = ["goodrichplus.kr", "example.com"]
    
    # Chunking Configuration
    chunk_size: int = 1500
    chunk_overlap: int = 200
    
    # Vector Search Configuration
    top_k: int = 8
    enable_rerank: bool = False
    
    # OCR Configuration
    ocr_languages: List[str] = ["ko", "en"]
    enable_gpu: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure data directory exists
os.makedirs(settings.storage_path, exist_ok=True)
os.makedirs(f"{settings.storage_path}/pdfs", exist_ok=True)
os.makedirs(f"{settings.storage_path}/chunks", exist_ok=True)
os.makedirs(f"{settings.storage_path}/embeddings", exist_ok=True)
