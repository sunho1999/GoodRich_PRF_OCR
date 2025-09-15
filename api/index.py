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

# GPT 분석 라이브러리
try:
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # OpenAI 클라이언트 초기화
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and not api_key.startswith('your_'):
        try:
            import httpx
            http_client = httpx.Client(timeout=30.0, proxies=None)
            openai_client = OpenAI(api_key=api_key, http_client=http_client)
            GPT_AVAILABLE = True
        except:
            openai_client = OpenAI(api_key=api_key)
            GPT_AVAILABLE = True
    else:
        GPT_AVAILABLE = False
        openai_client = None
except ImportError:
    GPT_AVAILABLE = False
    openai_client = None

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

def analyze_with_gpt(text, product_name="보험상품"):
    """GPT를 사용한 텍스트 분석"""
    if not GPT_AVAILABLE or not openai_client:
        return "GPT 분석 기능이 비활성화되어 있습니다."
    
    try:
        # 텍스트 길이 제한 (토큰 제한 고려)
        max_chars = 8000  # 약 2000 토큰
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""
아래는 '{product_name}' 보험상품의 내용입니다. 이를 분석하여 고객이 이해하기 쉽게 정리해주세요.

## 분석 요청:
1. **상품 기본 정보**: 상품명, 보험회사, 상품 타입
2. **보험료 정보**: 월 보험료, 납입 방식, 납입 기간
3. **주요 보장 내용**: 핵심 보장 항목들과 보장 금액
4. **특징 및 장점**: 이 상품만의 특별한 점

## 보험상품 내용:
{text}

위 내용을 바탕으로 고객 친화적인 분석 결과를 제공해주세요.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 보험 전문가입니다. 복잡한 보험 약관을 고객이 이해하기 쉽게 설명해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"GPT 분석 오류: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test')
def test():
    return jsonify({
        "status": "success", 
        "message": "Vercel deployment working!",
        "features": {
            "pdf_support": PDF_AVAILABLE,
            "gpt_support": GPT_AVAILABLE
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "요청 데이터가 없습니다."}), 400
        
        pdf_url = data.get('pdf_url')
        product_name = data.get('product_name', '보험상품')
        
        if not pdf_url:
            return jsonify({"status": "error", "message": "PDF URL이 필요합니다."}), 400
        
        # PDF 다운로드 및 텍스트 추출
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            urllib.request.urlretrieve(pdf_url, tmp_file.name)
            extracted_text = extract_pdf_text(tmp_file.name)
            os.unlink(tmp_file.name)  # 임시 파일 삭제
        
        # GPT 분석 수행
        if GPT_AVAILABLE and len(extracted_text.strip()) > 50:
            gpt_analysis = analyze_with_gpt(extracted_text, product_name)
        else:
            gpt_analysis = "GPT 분석을 사용할 수 없습니다. 텍스트 추출 결과만 제공됩니다."
        
        return jsonify({
            "status": "success", 
            "message": "PDF 분석 완료",
            "product_name": product_name,
            "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
            "text_length": len(extracted_text),
            "gpt_analysis": gpt_analysis,
            "features_used": {
                "pdf_extraction": PDF_AVAILABLE,
                "gpt_analysis": GPT_AVAILABLE
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"분석 오류: {str(e)}"}), 500

@app.route('/api/compare', methods=['POST'])
def compare():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "요청 데이터가 없습니다."}), 400
        
        pdf_url1 = data.get('pdf_url1')
        pdf_url2 = data.get('pdf_url2')
        product_name1 = data.get('product_name1', '상품 A')
        product_name2 = data.get('product_name2', '상품 B')
        
        if not pdf_url1 or not pdf_url2:
            return jsonify({"status": "error", "message": "두 개의 PDF URL이 모두 필요합니다."}), 400
        
        # 첫 번째 PDF 처리
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file1:
            urllib.request.urlretrieve(pdf_url1, tmp_file1.name)
            text1 = extract_pdf_text(tmp_file1.name)
            os.unlink(tmp_file1.name)
        
        # 두 번째 PDF 처리
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file2:
            urllib.request.urlretrieve(pdf_url2, tmp_file2.name)
            text2 = extract_pdf_text(tmp_file2.name)
            os.unlink(tmp_file2.name)
        
        # 개별 분석
        analysis1 = analyze_with_gpt(text1, product_name1) if GPT_AVAILABLE else "GPT 분석 비활성화"
        analysis2 = analyze_with_gpt(text2, product_name2) if GPT_AVAILABLE else "GPT 분석 비활성화"
        
        return jsonify({
            "status": "success",
            "message": "두 상품 비교 분석 완료",
            "product1": {
                "name": product_name1,
                "text_length": len(text1),
                "analysis": analysis1
            },
            "product2": {
                "name": product_name2,
                "text_length": len(text2),
                "analysis": analysis2
            },
            "features_used": {
                "pdf_extraction": PDF_AVAILABLE,
                "gpt_analysis": GPT_AVAILABLE
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"비교 분석 오류: {str(e)}"}), 500

# Vercel 배포용
application = app

if __name__ == "__main__":
    app.run(debug=True)
