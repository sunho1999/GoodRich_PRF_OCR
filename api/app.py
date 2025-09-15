# Vercel용 app.py 엔트리포인트
import sys
import os

# 프로젝트 루트를 Python 패스에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"🔧 프로젝트 루트: {project_root}")
print(f"🔧 Python 경로: {sys.path[:3]}")

# 메인 app.py에서 Flask 앱 import
try:
    print("📦 메인 app.py 모듈 로드 시작...")
    
    # 환경변수 설정 (Vercel 환경)
    os.environ.setdefault('VERCEL_ENV', 'true')
    
    from app import app, analyzer
    
    print("✅ 전체 app.py 로드 성공!")
    print(f"✅ Flask 앱: {app}")
    print(f"✅ GPT 상태: {'활성화' if analyzer.gpt_available else '비활성화'}")
    
    # Vercel에서는 SocketIO 없이 Flask만 사용
    application = app
    
except ImportError as e:
    print(f"❌ app.py import 실패: {e}")
    import traceback
    traceback.print_exc()
    
    # 폴백: 기본 Flask 앱
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return f"❌ 메인 앱 로드 실패: {str(e)}"
    
    @app.route('/health')
    def health():
        return {"status": "error", "message": f"메인 앱 로드 실패: {str(e)}"}
    
    application = app

except Exception as e:
    print(f"❌ 예상치 못한 오류: {e}")
    import traceback
    traceback.print_exc()
    
    # 폴백: 기본 Flask 앱
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return f"❌ 시스템 오류: {str(e)}"
    
    application = app

# Vercel WSGI 호환성
def application_handler(environ, start_response):
    """Vercel WSGI 핸들러"""
    return application(environ, start_response)

if __name__ == "__main__":
    # 로컬 테스트용
    print("🧪 로컬 테스트 모드")
    application.run(debug=True, port=8080)
