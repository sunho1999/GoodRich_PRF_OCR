FROM python:3.9-slim

WORKDIR /app

# 최소한의 시스템 패키지만 설치
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p data logs static/uploads data/pdfs data/chunks data/embeddings

# 포트 노출
EXPOSE 8080

# 실행
CMD ["python", "app.py"]