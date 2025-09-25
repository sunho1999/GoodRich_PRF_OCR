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

# Git 설치 확인
echo "🔧 Git 설치 확인..."
if ! command -v git &> /dev/null; then
    warning_msg "Git이 설치되지 않음. 설치를 진행합니다..."
    sudo apt-get update
    sudo apt-get install -y git
    success_msg "Git 설치 완료"
else
    success_msg "Git이 이미 설치됨"
fi

# GitHub에서 최신 코드 클론 또는 업데이트
echo "📥 GitHub에서 최신 코드 가져오기..."
if [ -d ".git" ]; then
    echo "기존 저장소 업데이트 중..."
    git pull origin main || error_exit "Git pull 실패"
    success_msg "기존 저장소 업데이트 완료"
else
    echo "새 저장소 클론 중..."
    git clone https://github.com/sunho1999/GoodRich_PRF_OCR.git . || error_exit "Git clone 실패"
    success_msg "저장소 클론 완료"
fi

# 현재 디렉토리 확인
echo "📂 현재 디렉토리: $(pwd)"
echo "📋 디렉토리 내용:"
ls -la

# 필요한 디렉토리 생성
mkdir -p data logs static/uploads data/pdfs data/chunks data/embeddings
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

# 4. 기존 컨테이너 정리 및 디스크 공간 확보
echo "🧹 기존 컨테이너 정리..."
docker stop pdf-ocr-app 2>/dev/null || true
docker rm pdf-ocr-app 2>/dev/null || true
docker rmi pdf-ocr-app:latest 2>/dev/null || true

echo "💾 디스크 공간 확보..."
docker system prune -a -f --volumes 2>/dev/null || true
docker builder prune -a -f 2>/dev/null || true
docker volume prune -f 2>/dev/null || true
sudo apt-get clean 2>/dev/null || true
sudo apt-get autoremove -y 2>/dev/null || true
sudo apt-get autoclean 2>/dev/null || true
sudo rm -rf /tmp/* 2>/dev/null || true
sudo rm -rf /var/tmp/* 2>/dev/null || true
sudo rm -rf /var/cache/apt/archives/* 2>/dev/null || true
sudo journalctl --vacuum-time=1d 2>/dev/null || true
sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} \; 2>/dev/null || true

# 디스크 사용량 확인
echo "📊 현재 디스크 사용량:"
df -h | head -2

# 디스크 공간이 부족하면 경고
AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
if [ "$AVAILABLE_SPACE" -lt 2000000 ]; then
    warning_msg "디스크 공간이 부족합니다 (${AVAILABLE_SPACE}KB). EC2 인스턴스 스토리지를 확장하세요."
fi

success_msg "기존 컨테이너 정리 및 디스크 공간 확보 완료"

# 5. Docker 이미지 빌드
echo "🏗️  Docker 이미지 빌드..."
echo "📂 빌드 디렉토리: $(pwd)"
echo "📋 빌드 디렉토리 내용:"
ls -la

if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile을 찾을 수 없습니다!"
    echo "📋 현재 디렉토리의 파일들:"
    ls -la
    echo "🔍 Dockerfile 검색 중..."
    find . -name "Dockerfile" -type f 2>/dev/null || echo "Dockerfile을 찾을 수 없습니다."
    error_exit "Dockerfile을 찾을 수 없습니다. 프로젝트 파일을 확인하세요."
fi

echo "✅ Dockerfile 발견: $(pwd)/Dockerfile"
echo "📄 Dockerfile 내용 확인:"
head -10 Dockerfile

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
    -v "$PROJECT_DIR/data/pdfs:/app/data/pdfs" \
    -v "$PROJECT_DIR/data/chunks:/app/data/chunks" \
    -v "$PROJECT_DIR/data/embeddings:/app/data/embeddings" \
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
    echo "🆕 새로운 기능:"
    echo "   ✅ 사용자 정의 프롬프트 입력 기능"
    echo "   ✅ 금액 단위 자동 통일 (천원, 만원, 억원 → 원 단위)"
    echo "   ✅ 개별 상품 분석 및 2개 상품 비교 분석"
    echo "   ✅ AI 챗봇 상담 기능"
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
