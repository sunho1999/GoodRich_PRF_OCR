# Vercel 배포용 간소화 엔트리포인트
import sys
import os
from flask import Flask, render_template, request, jsonify

# 프로젝트 루트를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel 환경에서는 간소화된 Flask 앱 사용
app = Flask(__name__, 
           template_folder='../templates',
           static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test')
def test():
    return jsonify({"status": "success", "message": "Vercel deployment working!"})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        # 기본 분석 응답 (GPT 없이)
        return jsonify({
            "status": "success", 
            "message": "PDF 분석 기능이 곧 활성화됩니다.",
            "analysis": "현재 Vercel 배포 테스트 중입니다."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Vercel 배포용
application = app

if __name__ == "__main__":
    app.run(debug=True)
