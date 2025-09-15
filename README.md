# PDF OCR 보험상품 분석 시스템

AI 기반 PDF 문서 OCR 인식과 GPT를 활용한 보험상품 분석 및 비교 웹 애플리케이션입니다.

## 🚀 주요 기능

- **PDF 텍스트 추출**: PyMuPDF, pdfminer를 활용한 고정밀 텍스트 추출
- **OCR 처리**: 이미지 기반 PDF에서 텍스트 인식
- **AI 분석**: GPT-4o-mini를 활용한 보험상품 상세 분석
- **비교 분석**: 두 보험상품 간의 종합 비교 및 추천
- **실시간 웹 인터페이스**: SocketIO 기반 실시간 분석 결과 표시

## 🛠️ 기술 스택

### Backend
- **Python 3.9+**
- **Flask** - 웹 프레임워크
- **Flask-SocketIO** - 실시간 통신
- **OpenAI GPT-4o-mini** - AI 분석
- **PyMuPDF** - PDF 처리
- **OpenCV** - 이미지 처리

### Frontend
- **HTML5/CSS3/JavaScript**
- **Bootstrap 5** - UI 프레임워크
- **Socket.IO** - 실시간 통신

### Infrastructure
- **Docker** - 컨테이너화
- **Vercel** - 배포 플랫폼
- **GitHub Actions** - CI/CD

## 📦 설치 및 실행

### 로컬 개발 환경

1. **저장소 클론**
```bash
git clone <repository-url>
cd PDF_OCR
```

2. **가상환경 설정**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **의존성 설치**
```bash
pip install -r requirements.txt
```

4. **환경변수 설정**
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일에 OpenAI API 키 설정
OPENAI_API_KEY=your_openai_api_key_here
```

5. **애플리케이션 실행**
```bash
python app.py
```

웹 브라우저에서 `http://localhost:8080` 접속

### Docker 실행

1. **Docker 이미지 빌드**
```bash
docker build -t pdf-ocr-app .
```

2. **컨테이너 실행**
```bash
docker run -d -p 8080:8080 --env-file .env --name pdf-ocr-app pdf-ocr-app
```

### Docker Compose 실행

```bash
docker-compose up -d
```

## 🔧 환경변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 | ✅ |
| `FLASK_ENV` | Flask 환경 (development/production) | ❌ |
| `FLASK_DEBUG` | 디버그 모드 (true/false) | ❌ |

## 📖 사용 방법

### 1. 개별 상품 분석
1. "개별 상품 분석" 탭 선택
2. 상품명 입력
3. PDF URL 입력 또는 파일 업로드
4. "분석 시작" 버튼 클릭

### 2. 두 상품 비교
1. "2개 상품 비교" 탭 선택
2. 각각의 상품명과 PDF 정보 입력
3. "비교 분석 시작" 버튼 클릭

### 3. 분석 결과 확인
- 실시간으로 분석 진행 상황 표시
- 완료 후 상세 분석 결과 표시
- 다운로드 기능으로 결과 저장 가능

## 🌳 브랜치 전략

### Git Flow
- **`main`**: 프로덕션 배포용 안정 브랜치
- **`develop`**: 개발 통합 브랜치
- **`feature/*`**: 기능 개발 브랜치

### 워크플로우
1. **개발**: `develop` 브랜치에서 작업
2. **테스트**: Push 시 자동 CI/CD 실행
3. **배포**: `main` 브랜치로 PR → 승인 후 프로덕션 배포

### GitHub Actions
- **Development**: `develop` 브랜치 → 테스트 및 빌드 검증
- **Production**: `main` 브랜치 → Vercel 프로덕션 배포

## 🚀 배포

### Vercel 배포

1. **Vercel 계정 연동**
```bash
npm i -g vercel
vercel login
```

2. **프로젝트 배포**
```bash
vercel --prod
```

3. **환경변수 설정**
- Vercel 대시보드에서 Environment Variables 설정
- `OPENAI_API_KEY` 추가

### GitHub Actions CI/CD

Push to main branch → 자동 배포

필요한 GitHub Secrets:
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID` 
- `VERCEL_PROJECT_ID`

## 📁 프로젝트 구조

```
PDF_OCR/
├── api/                    # Vercel 배포용 API
│   └── index.py
├── core/                   # 핵심 설정
│   ├── config.py
│   └── logging.py
├── llm/                    # AI 모델
│   ├── __init__.py
│   └── gpt_summarizer.py
├── parsing/                # PDF 처리
│   ├── __init__.py
│   ├── pdf_ocr.py
│   └── pdf_text.py
├── static/                 # 정적 파일
│   ├── css/
│   └── js/
├── .github/workflows/      # GitHub Actions
│   └── deploy.yml
├── app.py                  # 메인 애플리케이션
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── vercel.json
└── README.md
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 문제 해결

### 일반적인 문제

**Q: GPT API 오류가 발생합니다**
A: `.env` 파일에 유효한 `OPENAI_API_KEY`가 설정되어 있는지 확인하세요.

**Q: PDF 파일을 읽을 수 없습니다**
A: 지원되는 PDF 형식인지 확인하고, 파일 크기가 너무 크지 않은지 확인하세요.

**Q: Docker 컨테이너가 시작되지 않습니다**
A: Docker 로그를 확인하고 필요한 환경변수가 모두 설정되어 있는지 확인하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면 [Issues](../../issues)에 등록해 주세요.
