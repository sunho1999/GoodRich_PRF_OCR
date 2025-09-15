# Vercel 배포용 엔트리포인트
import sys
import os

# 프로젝트 루트를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, socketio

# Vercel에서는 WSGI 애플리케이션만 지원되므로 SocketIO 없이 Flask만 사용
if __name__ == "__main__":
    app.run()
else:
    # Vercel 배포용
    application = app
