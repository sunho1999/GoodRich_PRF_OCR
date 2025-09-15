"""
GUI 전용 설정 파일
서버 기능 없이 PDF 처리만 필요한 경우 사용
"""

import os
from typing import List


class GUISettings:
    """GUI 애플리케이션 전용 설정"""
    
    def __init__(self):
        # 기본 설정
        self.app_name = "PDF 요약기"
        self.version = "1.0.1"
        
        # 저장소 설정
        self.storage_path = "./data"
        
        # PDF 처리 제한
        self.max_pdf_mb = 80
        self.max_pages = 1000
        
        # OCR 설정
        self.ocr_languages = ["ko", "en"]
        self.enable_gpu = False
        
        # OpenAI 설정 (선택적)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = "gpt-4"
        
        # 청킹 설정 (사용되지 않을 수 있지만 호환성을 위해)
        self.chunk_size = 1500
        self.chunk_overlap = 200
        
        # 도메인 허용 목록
        self.allowlist_domains = ["goodrichplus.kr", "example.com"]
        
        # 디렉토리 생성
        self._ensure_directories()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(f"{self.storage_path}/pdfs", exist_ok=True)
        os.makedirs(f"{self.storage_path}/chunks", exist_ok=True)
        os.makedirs(f"{self.storage_path}/embeddings", exist_ok=True)


# GUI 전용 설정 인스턴스
gui_settings = GUISettings()

