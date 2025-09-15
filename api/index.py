# Vercel 배포용 PDF 처리 엔트리포인트
import sys
import os
from flask import Flask, render_template, request, jsonify
import tempfile
import urllib.request

# 프로젝트 루트를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PDF 처리 라이브러리
try:
    import fitz  # PyMuPDF
    from pdfminer.high_level import extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Vercel 환경에서는 간소화된 Flask 앱 사용
app = Flask(__name__, 
           template_folder='../templates',
           static_folder='../static')

def extract_pdf_text(pdf_path):
    """PDF에서 텍스트 추출"""
    if not PDF_AVAILABLE:
        return "PDF 처리 라이브러리가 설치되지 않았습니다."
    
    try:
        # PyMuPDF로 먼저 시도
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if text.strip():
            return text
        
        # PyMuPDF로 텍스트가 없으면 pdfminer 시도
        return extract_text(pdf_path)
        
    except Exception as e:
        return f"PDF 텍스트 추출 오류: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test')
def test():
    return jsonify({
        "status": "success", 
        "message": "Vercel deployment working!",
        "pdf_support": PDF_AVAILABLE
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "요청 데이터가 없습니다."}), 400
        
        pdf_url = data.get('pdf_url')
        if not pdf_url:
            return jsonify({"status": "error", "message": "PDF URL이 필요합니다."}), 400
        
        # PDF 다운로드 및 텍스트 추출
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            urllib.request.urlretrieve(pdf_url, tmp_file.name)
            extracted_text = extract_pdf_text(tmp_file.name)
            os.unlink(tmp_file.name)  # 임시 파일 삭제
        
        return jsonify({
            "status": "success", 
            "message": "PDF 텍스트 추출 완료",
            "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            "text_length": len(extracted_text)
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"분석 오류: {str(e)}"}), 500

# Vercel 배포용
application = app

if __name__ == "__main__":
    app.run(debug=True)
