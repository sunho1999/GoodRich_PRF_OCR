#!/bin/bash

# 🚀 PDF OCR 앱 EC2 자동 배포 및 관리 스크립트

echo "🚀 PDF OCR 앱 자동 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정 변수
APP_NAME="pdf-ocr-app"
SERVICE_NAME="pdf-ocr-service"
PROJECT_DIR="/home/ubuntu/pdf-ocr-app"
BACKUP_DIR="/home/ubuntu/backups"
LOG_DIR="/var/log/pdf-ocr"
SERVICE_USER="ubuntu"

# 에러 처리 함수
error_exit() {
    echo -e "${RED}❌ 오류: $1${NC}"
    # 로그 파일에 오류 기록
    echo "$(date): ERROR - $1" >> "$LOG_DIR/deploy.log"
    exit 1
}

# 성공 메시지 함수
success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "$(date): SUCCESS - $1" >> "$LOG_DIR/deploy.log"
}

# 경고 메시지 함수
warning_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    echo "$(date): WARNING - $1" >> "$LOG_DIR/deploy.log"
}

# 정보 메시지 함수
info_msg() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    echo "$(date): INFO - $1" >> "$LOG_DIR/deploy.log"
}

# 초기 설정 및 디렉토리 생성
echo "🔧 초기 설정..."
sudo mkdir -p "$LOG_DIR" "$BACKUP_DIR"
sudo chown -R $SERVICE_USER:$SERVICE_USER "$LOG_DIR" "$BACKUP_DIR"
success_msg "로그 및 백업 디렉토리 생성 완료"

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
    echo "🔍 해약환급금 표 인식 디버깅 실행..."
    docker exec pdf-ocr-app python debug_ec2_surrender.py || echo "디버깅 스크립트 실행 실패"
    echo ""
    echo "🌐 접속 URL:"
    echo "   http://$(curl -s ifconfig.me):8080"
    echo "   또는 http://localhost:8080 (EC2 내부에서)"
    echo ""
    echo "🆕 새로운 기능:"
    echo "   ✅ 사용자 정의 프롬프트 입력 기능"
    echo "   ✅ 금액 단위 자동 통일 (천원, 만원, 억원 → 원 단위)"
    echo "   ✅ 해약환급금 표 정확한 인식 및 분석"
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

# 8. systemd 서비스 생성 및 등록
echo "🔧 systemd 서비스 설정..."
create_systemd_service() {
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=PDF OCR Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker start $APP_NAME
ExecStop=/usr/bin/docker stop $APP_NAME
ExecReload=/usr/bin/docker restart $APP_NAME
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    success_msg "systemd 서비스 등록 완료"
}

create_systemd_service

# 9. 자동 재시작 스크립트 생성
echo "🔄 자동 재시작 스크립트 생성..."
sudo tee /usr/local/bin/pdf-ocr-restart.sh > /dev/null <<EOF
#!/bin/bash
# PDF OCR 앱 자동 재시작 스크립트

LOG_FILE="$LOG_DIR/restart.log"
APP_NAME="$APP_NAME"

echo "\$(date): 자동 재시작 시작" >> \$LOG_FILE

# 컨테이너 상태 확인
if ! docker ps | grep -q \$APP_NAME; then
    echo "\$(date): 컨테이너가 실행되지 않음. 재시작 시도..." >> \$LOG_FILE
    docker start \$APP_NAME
    
    # 재시작 후 헬스 체크
    sleep 10
    if curl -f http://localhost:8080 > /dev/null 2>&1; then
        echo "\$(date): 재시작 성공" >> \$LOG_FILE
    else
        echo "\$(date): 재시작 실패" >> \$LOG_FILE
        # 전체 재배포 실행
        cd $PROJECT_DIR
        ./deploy.sh
    fi
else
    echo "\$(date): 컨테이너가 정상 실행 중" >> \$LOG_FILE
fi
EOF

sudo chmod +x /usr/local/bin/pdf-ocr-restart.sh
success_msg "자동 재시작 스크립트 생성 완료"

# 10. cron 작업 설정 (5분마다 헬스 체크)
echo "⏰ cron 작업 설정..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/pdf-ocr-restart.sh") | crontab -
success_msg "cron 작업 설정 완료 (5분마다 헬스 체크)"

# 11. 로그 로테이션 설정
echo "📝 로그 로테이션 설정..."
sudo tee /etc/logrotate.d/pdf-ocr > /dev/null <<EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        docker restart $APP_NAME > /dev/null 2>&1 || true
    endscript
}
EOF
success_msg "로그 로테이션 설정 완료"

# 12. 백업 스크립트 생성
echo "💾 백업 스크립트 생성..."
sudo tee /usr/local/bin/pdf-ocr-backup.sh > /dev/null <<EOF
#!/bin/bash
# PDF OCR 앱 백업 스크립트

BACKUP_DIR="$BACKUP_DIR"
PROJECT_DIR="$PROJECT_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="pdf-ocr-backup-\$DATE.tar.gz"

echo "\$(date): 백업 시작" >> $LOG_DIR/backup.log

# 데이터 디렉토리 백업
tar -czf "\$BACKUP_DIR/\$BACKUP_FILE" -C "\$PROJECT_DIR" data logs static/uploads

# 7일 이상 된 백업 파일 삭제
find "\$BACKUP_DIR" -name "pdf-ocr-backup-*.tar.gz" -mtime +7 -delete

echo "\$(date): 백업 완료 - \$BACKUP_FILE" >> $LOG_DIR/backup.log
EOF

sudo chmod +x /usr/local/bin/pdf-ocr-backup.sh
success_msg "백업 스크립트 생성 완료"

# 13. 모니터링 스크립트 생성
echo "📊 모니터링 스크립트 생성..."
sudo tee /usr/local/bin/pdf-ocr-monitor.sh > /dev/null <<EOF
#!/bin/bash
# PDF OCR 앱 모니터링 스크립트

LOG_FILE="$LOG_DIR/monitor.log"
APP_NAME="$APP_NAME"

# 시스템 리소스 확인
CPU_USAGE=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | cut -d'%' -f1)
MEMORY_USAGE=\$(free | grep Mem | awk '{printf("%.2f"), \$3/\$2 * 100.0}')
DISK_USAGE=\$(df / | tail -1 | awk '{print \$5}' | cut -d'%' -f1)

# Docker 컨테이너 상태 확인
CONTAINER_STATUS=\$(docker ps | grep \$APP_NAME | wc -l)

echo "\$(date): CPU: \${CPU_USAGE}%, Memory: \${MEMORY_USAGE}%, Disk: \${DISK_USAGE}%, Container: \${CONTAINER_STATUS}" >> \$LOG_FILE

# 임계값 체크 및 알림
if (( \$(echo "\$CPU_USAGE > 80" | bc -l) )); then
    echo "\$(date): WARNING - CPU 사용률이 높습니다: \${CPU_USAGE}%" >> \$LOG_FILE
fi

if (( \$(echo "\$MEMORY_USAGE > 80" | bc -l) )); then
    echo "\$(date): WARNING - 메모리 사용률이 높습니다: \${MEMORY_USAGE}%" >> \$LOG_FILE
fi

if [ "\$DISK_USAGE" -gt 80 ]; then
    echo "\$(date): WARNING - 디스크 사용률이 높습니다: \${DISK_USAGE}%" >> \$LOG_FILE
fi

if [ "\$CONTAINER_STATUS" -eq 0 ]; then
    echo "\$(date): ERROR - 컨테이너가 실행되지 않습니다" >> \$LOG_FILE
    /usr/local/bin/pdf-ocr-restart.sh
fi
EOF

sudo chmod +x /usr/local/bin/pdf-ocr-monitor.sh
success_msg "모니터링 스크립트 생성 완료"

# 14. cron 작업 추가 (모니터링 및 백업)
echo "⏰ 추가 cron 작업 설정..."
(crontab -l 2>/dev/null; echo "*/10 * * * * /usr/local/bin/pdf-ocr-monitor.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/pdf-ocr-backup.sh") | crontab -
success_msg "추가 cron 작업 설정 완료"

# 15. 서비스 시작
echo "🚀 서비스 시작..."
sudo systemctl start $SERVICE_NAME
success_msg "서비스 시작 완료"

# 16. 최종 상태 확인
echo "🔍 최종 상태 확인..."
sleep 5

if systemctl is-active --quiet $SERVICE_NAME; then
    success_msg "서비스가 정상적으로 실행 중입니다!"
else
    warning_msg "서비스 시작에 문제가 있습니다. 로그를 확인하세요:"
    sudo systemctl status $SERVICE_NAME
fi

success_msg "자동 배포 및 관리 시스템 구축 완료! 🎉"

echo ""
echo "📋 관리 명령어:"
echo "   서비스 상태 확인: sudo systemctl status $SERVICE_NAME"
echo "   서비스 시작: sudo systemctl start $SERVICE_NAME"
echo "   서비스 중지: sudo systemctl stop $SERVICE_NAME"
echo "   서비스 재시작: sudo systemctl restart $SERVICE_NAME"
echo "   로그 확인: docker logs -f $APP_NAME"
echo "   수동 재시작: /usr/local/bin/pdf-ocr-restart.sh"
echo "   백업 실행: /usr/local/bin/pdf-ocr-backup.sh"
echo "   모니터링: /usr/local/bin/pdf-ocr-monitor.sh"
echo ""
echo "📊 로그 파일 위치:"
echo "   배포 로그: $LOG_DIR/deploy.log"
echo "   재시작 로그: $LOG_DIR/restart.log"
echo "   백업 로그: $LOG_DIR/backup.log"
echo "   모니터링 로그: $LOG_DIR/monitor.log"
echo ""
echo "🌐 접속 URL:"
echo "   http://$(curl -s ifconfig.me):8080"
echo ""
echo "🔄 자동 관리 기능:"
echo "   ✅ 5분마다 헬스 체크 및 자동 재시작"
echo "   ✅ 10분마다 시스템 리소스 모니터링"
echo "   ✅ 매일 새벽 2시 자동 백업"
echo "   ✅ 로그 자동 로테이션 (7일 보관)"
echo "   ✅ systemd 서비스 등록으로 부팅 시 자동 시작"
