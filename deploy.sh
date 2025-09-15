#!/bin/bash

# 🚀 PDF OCR 앱 EC2 배포 스크립트

echo "🚀 PDF OCR 앱 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 에러 처리 함수
error_exit() {
    echo -e "${RED}❌ 오류: $1${NC}"
    exit 1
}

# 성공 메시지 함수
success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 경고 메시지 함수
warning_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. Docker 설치 확인
echo "📦 Docker 설치 확인..."
if ! command -v docker &> /dev/null; then
    warning_msg "Docker가 설치되지 않음. 설치를 진행합니다..."
    
    # Docker 설치
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Docker 서비스 시작
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker $USER
    
    success_msg "Docker 설치 완료 (재로그인 필요)"
    warning_msg "재로그인 후 다시 실행하세요: exit && ssh ubuntu@YOUR_EC2_IP"
    exit 0
else
    success_msg "Docker가 이미 설치됨"
fi

# 2. 프로젝트 디렉토리 설정
echo "📁 프로젝트 디렉토리 설정..."
PROJECT_DIR="/home/ubuntu/pdf-ocr-app"

if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    success_msg "프로젝트 디렉토리 생성: $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 필요한 디렉토리 생성
mkdir -p data logs static/uploads
success_msg "필요한 디렉토리 생성 완료"

# 3. 환경변수 확인
echo "🔑 환경변수 확인..."
if [ -z "$OPENAI_API_KEY" ]; then
    warning_msg "OPENAI_API_KEY 환경변수가 설정되지 않음"
    echo "다음 명령어로 설정하세요:"
    echo "export OPENAI_API_KEY='your_api_key_here'"
    echo ""
    echo "또는 .env 파일을 생성하세요:"
    echo "echo 'OPENAI_API_KEY=your_api_key_here' > .env"
    read -p "API 키를 지금 입력하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "OpenAI API 키를 입력하세요: " api_key
        echo "OPENAI_API_KEY=$api_key" > .env
        export OPENAI_API_KEY="$api_key"
        success_msg "API 키 설정 완료"
    else
        error_exit "API 키가 필요합니다"
    fi
else
    success_msg "OPENAI_API_KEY 환경변수 확인됨"
fi

# 4. 기존 컨테이너 정리
echo "🧹 기존 컨테이너 정리..."
docker stop pdf-ocr-app 2>/dev/null || true
docker rm pdf-ocr-app 2>/dev/null || true
docker rmi pdf-ocr-app:latest 2>/dev/null || true
success_msg "기존 컨테이너 정리 완료"

# 5. Docker 이미지 빌드
echo "🏗️  Docker 이미지 빌드..."
if [ ! -f "Dockerfile" ]; then
    error_exit "Dockerfile을 찾을 수 없습니다. 프로젝트 파일을 확인하세요."
fi

docker build -t pdf-ocr-app:latest . || error_exit "Docker 빌드 실패"
success_msg "Docker 이미지 빌드 완료"

# 6. 컨테이너 실행
echo "🚀 컨테이너 실행..."
docker run -d \
    --name pdf-ocr-app \
    --restart unless-stopped \
    -p 8080:8080 \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e FLASK_DEBUG=False \
    -v "$PROJECT_DIR/data:/app/data" \
    -v "$PROJECT_DIR/logs:/app/logs" \
    -v "$PROJECT_DIR/static/uploads:/app/static/uploads" \
    pdf-ocr-app:latest || error_exit "컨테이너 실행 실패"

success_msg "컨테이너 실행 완료"

# 7. 헬스 체크
echo "🔍 헬스 체크..."
sleep 10

if curl -f http://localhost:8080 > /dev/null 2>&1; then
    success_msg "애플리케이션이 정상적으로 실행 중입니다!"
    echo ""
    echo "🌐 접속 URL:"
    echo "   http://$(curl -s ifconfig.me):8080"
    echo "   또는 http://localhost:8080 (EC2 내부에서)"
    echo ""
    echo "📊 컨테이너 상태:"
    docker ps | grep pdf-ocr-app
    echo ""
    echo "📝 로그 확인:"
    echo "   docker logs -f pdf-ocr-app"
    echo ""
    echo "🛑 컨테이너 중지:"
    echo "   docker stop pdf-ocr-app"
    echo ""
    echo "🔄 컨테이너 재시작:"
    echo "   docker restart pdf-ocr-app"
else
    warning_msg "헬스 체크 실패. 로그를 확인하세요:"
    docker logs pdf-ocr-app
    error_exit "애플리케이션 시작 실패"
fi

success_msg "배포 완료! 🎉"
