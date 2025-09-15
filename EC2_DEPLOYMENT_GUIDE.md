# 🚀 EC2 배포 가이드

## 📋 **필요한 준비사항**

### 1. **EC2 인스턴스 설정**
```bash
# Ubuntu 20.04+ 인스턴스 권장
# 인스턴스 타입: t3.medium 이상 (메모리 4GB+)
# 보안 그룹: 8080 포트 오픈
```

### 2. **EC2 초기 설정**
```bash
# EC2 접속 후 실행
sudo apt update
sudo apt install -y docker.io docker-compose git

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# ubuntu 사용자를 docker 그룹에 추가
sudo usermod -aG docker ubuntu

# 로그아웃 후 재접속 필요
```

### 3. **프로젝트 디렉토리 설정**
```bash
# 홈 디렉토리에 프로젝트 폴더 생성
mkdir -p /home/ubuntu/pdf-ocr-app
cd /home/ubuntu/pdf-ocr-app

# 데이터 디렉토리 생성
mkdir -p data logs static/uploads
```

## 🔧 **GitHub Secrets 설정**

GitHub 저장소 → Settings → Secrets and variables → Actions에서 다음 secrets 추가:

### **필수 Secrets:**
- `EC2_HOST`: EC2 인스턴스 퍼블릭 IP (예: 13.124.123.45)
- `EC2_USER`: EC2 사용자명 (보통 ubuntu)
- `EC2_SSH_KEY`: EC2 SSH 개인키 내용
- `EC2_PORT`: SSH 포트 (보통 22)
- `OPENAI_API_KEY`: OpenAI API 키

### **SSH 키 설정 방법:**
```bash
# 로컬에서 SSH 키 생성 (이미 있다면 생략)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# EC2에 공개키 추가
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@YOUR_EC2_IP

# 개인키 내용을 GitHub Secrets에 추가
cat ~/.ssh/id_rsa
# 전체 내용을 EC2_SSH_KEY로 복사
```

## 🚀 **배포 과정**

### 1. **자동 배포 (권장)**
```bash
# main 브랜치에 푸시하면 자동으로 배포됨
git add .
git commit -m "배포 테스트"
git push origin main
```

### 2. **수동 배포**
```bash
# EC2에서 직접 실행
cd /home/ubuntu/pdf-ocr-app

# GitHub에서 클론 (최초 1회)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# Docker 컨테이너 실행
docker-compose up -d --build
```

## 🔍 **배포 확인**

### 1. **컨테이너 상태 확인**
```bash
# EC2에서 실행
docker ps
docker logs pdf-ocr-app
```

### 2. **웹 접속 테스트**
```bash
# 브라우저에서 접속
http://YOUR_EC2_IP:8080

# 또는 curl로 테스트
curl http://YOUR_EC2_IP:8080
```

## 📊 **모니터링 및 로그**

### **로그 확인**
```bash
# 애플리케이션 로그
docker logs -f pdf-ocr-app

# 시스템 로그
sudo journalctl -u docker
```

### **리소스 모니터링**
```bash
# CPU/메모리 사용량
htop

# 디스크 사용량
df -h

# Docker 리소스 사용량
docker stats pdf-ocr-app
```

## 🔧 **문제 해결**

### **컨테이너가 시작되지 않는 경우**
```bash
# 로그 확인
docker logs pdf-ocr-app

# 환경변수 확인
docker exec pdf-ocr-app env | grep OPENAI

# 컨테이너 재시작
docker restart pdf-ocr-app
```

### **메모리 부족 오류**
```bash
# 더 큰 인스턴스로 변경하거나
# Docker 메모리 제한 설정
docker run --memory=4g pdf-ocr-app
```

### **포트 충돌**
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep :8080

# 다른 포트로 변경
docker run -p 8081:8080 pdf-ocr-app
```

## 📈 **성능 최적화**

### **Docker 최적화**
```bash
# 불필요한 이미지 정리
docker system prune -a

# 볼륨 최적화
docker volume prune
```

### **시스템 최적화**
```bash
# 스왑 파일 설정 (메모리 부족 시)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 🔒 **보안 설정**

### **방화벽 설정**
```bash
# UFW 설정
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 8080  # 애플리케이션
```

### **SSL 인증서 (선택사항)**
```bash
# Let's Encrypt 사용
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
```

## 📞 **지원**

문제가 발생하면 다음을 확인하세요:
1. EC2 인스턴스 상태
2. Docker 컨테이너 로그
3. GitHub Actions 배포 로그
4. 네트워크 연결 상태

---

**배포 완료 후 접속 URL:**
`http://YOUR_EC2_IP:8080`
