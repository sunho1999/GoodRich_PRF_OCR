FROM python:3.9-slim

WORKDIR /app

# WeasyPrint 의존성 설치 (Ubuntu 공식 권장사항)
RUN apt-get update && apt-get install -y \
    # WeasyPrint 필수 의존성 (Ubuntu ≥ 20.04)
    libpango-1.0-0 \
    libpango1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    # Pango 개발 라이브러리
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    # 추가 의존성 (wheels 없이 설치 시)
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    # 기타 시스템 의존성
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libx11-6 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libcairo2 \
    libcairo-gobject2 \
    libpangocairo-1.0-0 \
    # 한글 폰트
    fonts-noto-cjk \
    fonts-dejavu-core \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Python 패키지 설치 (캐시 없이, 의존성 포함)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge \
    && rm -rf /root/.cache/pip \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 애플리케이션 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p data logs static/uploads data/pdfs data/chunks data/embeddings

# 포트 노출
EXPOSE 8080

# 실행
CMD ["python", "app.py"]