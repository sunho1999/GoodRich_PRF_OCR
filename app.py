#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session, send_file
from flask_socketio import SocketIO, emit
import os
import json
import tempfile
import threading
from datetime import datetime
import logging
from werkzeug.utils import secure_filename

# 기존 모듈들 import
from parsing.pdf_text import PDFTextExtractor
from llm.gpt_summarizer import GPTSummarizer
from core.config import settings

# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = 'pdf_ocr_analysis_secret_key_2024'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 제한

# SocketIO 초기화 (실시간 채팅용)
socketio = SocketIO(app, cors_allowed_origins="*")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class WebAnalyzer:
    """웹 기반 PDF 분석기"""
    
    def __init__(self):
        self.config = settings
        self.pdf_extractor = PDFTextExtractor()
        
        # 사용자별 분석 데이터 저장 (메모리 기반)
        self.user_data = {}
        
        # GPT 초기화 (더 강력한 에러 처리)
        try:
            # .env 파일에서 API 키 우선 로드
            from dotenv import load_dotenv
            load_dotenv()  # .env 파일 강제 로드
            
            # .env 파일 -> config -> 시스템 환경변수 순서로 우선순위
            api_key = self.config.openai_api_key or os.getenv('OPENAI_API_KEY')
            logger.info(f"API 키 확인: {'있음' if api_key else '없음'}")
            
            if not api_key:
                raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되지 않음")
            
            self.gpt_summarizer = GPTSummarizer(api_key=api_key)
            self.gpt_available = True
            logger.info("✅ GPT API 초기화 성공")
        except Exception as e:
            self.gpt_summarizer = None
            self.gpt_available = False
            logger.error(f"❌ GPT API 초기화 실패: {e}")
            logger.info("🔄 기본 텍스트 파싱 모드로 동작합니다")
    
    def allowed_file(self, filename):
        """허용된 파일 확장자 확인"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def get_user_id(self, request):
        """사용자 ID 생성 (IP + User-Agent 기반)"""
        import hashlib
        user_info = f"{request.remote_addr}_{request.headers.get('User-Agent', '')}"
        return hashlib.md5(user_info.encode()).hexdigest()[:16]
    
    def get_user_data(self, user_id):
        """사용자 데이터 가져오기"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'analyzed_products': [],
                'last_activity': datetime.now()
            }
        return self.user_data[user_id]
    
    def save_analysis_result(self, user_id, product_info):
        """분석 결과 저장"""
        user_data = self.get_user_data(user_id)
        user_data['analyzed_products'].append(product_info)
        user_data['last_activity'] = datetime.now()
        
        # 최대 5개까지만 저장
        if len(user_data['analyzed_products']) > 5:
            user_data['analyzed_products'] = user_data['analyzed_products'][-5:]
        
        logger.info(f"사용자 {user_id}의 분석 결과 저장됨: {product_info['name']}")
    
    def get_analyzed_products(self, user_id):
        """분석된 상품 목록 가져오기"""
        user_data = self.get_user_data(user_id)
        return user_data['analyzed_products']
    
    def cleanup_old_data(self):
        """오래된 사용자 데이터 정리 (1시간 이상)"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        old_users = [
            user_id for user_id, data in self.user_data.items()
            if data['last_activity'] < cutoff_time
        ]
        
        for user_id in old_users:
            del self.user_data[user_id]
            
        if old_users:
            logger.info(f"오래된 사용자 데이터 정리: {len(old_users)}명")
    
    def extract_pdf_content(self, file_path_or_url, is_url=False, use_ocr=True):
        """PDF에서 텍스트 추출 (OCR 향상 포함)"""
        try:
            if is_url:
                success, pages = self.pdf_extractor.extract_text_from_url(file_path_or_url)
            else:
                success, pages = self.pdf_extractor.extract_text_from_pdf(file_path_or_url, use_ocr=use_ocr)
            
            if not success:
                return {
                    'success': False, 
                    'error': 'PDF 텍스트 추출에 실패했습니다.'
                }
            
            # 기본 텍스트 결합 및 추출 통계 생성
            combined_text = ""
            extraction_stats = {
                'total_pages': len(pages),
                'pages_with_text': 0,
                'ocr_enhanced_pages': 0,
                'hybrid_pages': 0,
                'extraction_methods': {}
            }
            
            for page in pages:
                if isinstance(page, dict):
                    text = page.get('text', '')
                    page_num = page.get('page_number', 0)
                    extraction_method = page.get('extraction_method', 'unknown')
                    
                    # 텍스트 결합
                    if text.strip():
                        extraction_stats['pages_with_text'] += 1
                        combined_text += f"\n--- 페이지 {page_num} ---\n{text}\n"
                    
                    # 추출 방법 통계
                    if extraction_method in extraction_stats['extraction_methods']:
                        extraction_stats['extraction_methods'][extraction_method] += 1
                    else:
                        extraction_stats['extraction_methods'][extraction_method] = 1
                    
                    # OCR 통계
                    if page.get('has_ocr', False):
                        extraction_stats['ocr_enhanced_pages'] += 1
                    if extraction_method == 'hybrid':
                        extraction_stats['hybrid_pages'] += 1
            
            return {
                'success': True,
                'pages': pages,
                'content': combined_text,
                'page_count': len(pages),
                'extraction_stats': extraction_stats
            }
            
        except Exception as e:
            logger.error(f"PDF 추출 오류: {e}")
            return {
                'success': False,
                'error': f'PDF 처리 중 오류가 발생했습니다: {str(e)}'
            }
    
    def analyze_product_detail(self, pages, file_name):
        """상품 상세 분석"""
        if not self.gpt_available:
            return "❌ GPT API를 사용할 수 없습니다. 기본 텍스트만 제공됩니다."
        
        try:
            return self.gpt_summarizer.analyze_for_detail(pages, file_name)
        except Exception as e:
            logger.error(f"GPT 상세 분석 오류: {e}")
            return f"❌ 분석 중 오류가 발생했습니다: {str(e)}"
    
    def analyze_product_comparison(self, pages, file_name):
        """상품 비교 분석"""
        if not self.gpt_available:
            return "❌ GPT API를 사용할 수 없습니다. 기본 텍스트만 제공됩니다."
        
        try:
            return self.gpt_summarizer.analyze_for_comparison(pages, file_name)
        except Exception as e:
            logger.error(f"GPT 비교 분석 오류: {e}")
            return f"❌ 분석 중 오류가 발생했습니다: {str(e)}"
    
    def generate_chatbot_response(self, question, context):
        """챗봇 응답 생성"""
        if not self.gpt_available:
            return "죄송합니다. GPT API를 사용할 수 없어 AI 상담 기능이 제한됩니다."
        
        try:
            prompt = f"""
당신은 전문 보험 상담사입니다. 분석된 상품 정보를 바탕으로 답변해주세요.

{context}

질문: {question}

답변:"""
            
            messages = [
                {"role": "system", "content": "당신은 전문적이고 친근한 보험 상담사입니다."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.gpt_summarizer._safe_api_call(
                messages=messages, 
                max_tokens=1000, 
                retries=2, 
                delay=1
            )
            
            if response is None:
                return "죄송합니다. 현재 AI 응답 생성에 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"챗봇 응답 생성 오류: {e}")
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"

# 전역 분석기 인스턴스
analyzer = WebAnalyzer()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html', gpt_available=analyzer.gpt_available)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """파일 업로드 API"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'})
        
        if not analyzer.allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'PDF 파일만 업로드 가능합니다.'})
        
        # 안전한 파일명으로 저장
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(file_path)
        
        return jsonify({
            'success': True, 
            'file_path': file_path,
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"파일 업로드 오류: {e}")
        return jsonify({'success': False, 'error': f'업로드 중 오류가 발생했습니다: {str(e)}'})

@app.route('/api/analyze/individual', methods=['POST'])
def analyze_individual():
    """개별 상품 분석 API"""
    try:
        data = request.get_json()
        source_type = data.get('source_type')  # 'file' or 'url'
        source = data.get('source')
        product_name = data.get('product_name', '상품')
        
        if not source:
            return jsonify({'success': False, 'error': '분석할 소스가 제공되지 않았습니다.'})
        
        # PDF 텍스트 추출
        is_url = (source_type == 'url')
        result = analyzer.extract_pdf_content(source, is_url=is_url)
        
        if not result['success']:
            return jsonify(result)
        
        # GPT 상세 분석 (가능한 경우)
        analysis = ""
        gpt_analysis_success = False
        
        if analyzer.gpt_available:
            analysis = analyzer.analyze_product_detail(result['pages'], product_name)
            # GPT 분석이 실제로 성공했는지 확인
            gpt_analysis_success = (
                analysis and 
                not analysis.startswith("❌") and 
                not "분석 중 오류 발생" in analysis and
                not "API 호출에 실패" in analysis
            )
            logger.info(f"GPT 분석 성공: {gpt_analysis_success}")
        
        # 메모리에 분석 결과 저장 (챗봇용)
        user_id = analyzer.get_user_id(request)
        analyzer.save_analysis_result(user_id, {
            'name': product_name,
            'content': result['content'],
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'content': result['content'],
            'analysis': analysis,
            'page_count': result['page_count'],
            'gpt_used': gpt_analysis_success,  # 실제 성공 여부로 변경
            'extraction_stats': result.get('extraction_stats', {})
        })
        
    except Exception as e:
        logger.error(f"개별 분석 오류: {e}")
        return jsonify({'success': False, 'error': f'분석 중 오류가 발생했습니다: {str(e)}'})

@app.route('/api/get_raw_text', methods=['POST'])
def get_raw_text():
    """원본 텍스트 추출 API (디버깅용)"""
    try:
        data = request.get_json()
        source = data.get('source')
        source_type = data.get('source_type', 'file')
        
        if not source:
            return jsonify({'success': False, 'error': '소스가 제공되지 않았습니다.'})
        
        is_url = (source_type == 'url')
        result = analyzer.extract_pdf_content(source, is_url=is_url)
        
        if not result['success']:
            return jsonify(result)
        
        return jsonify({
            'success': True,
            'raw_text': result['content'],
            'page_count': result['page_count'],
            'extraction_stats': result.get('extraction_stats', {})
        })
        
    except Exception as e:
        logger.error(f"원본 텍스트 추출 오류: {e}")
        return jsonify({'success': False, 'error': f'원본 텍스트 추출 중 오류가 발생했습니다: {str(e)}'})

@app.route('/api/analyze/compare', methods=['POST'])
def analyze_compare():
    """2개 상품 비교 분석 API"""
    try:
        data = request.get_json()
        
        # 첫 번째 상품
        source1_type = data.get('source1_type')
        source1 = data.get('source1')
        product1_name = data.get('product1_name', '상품 A')
        
        # 두 번째 상품
        source2_type = data.get('source2_type')
        source2 = data.get('source2')
        product2_name = data.get('product2_name', '상품 B')
        
        if not source1 or not source2:
            return jsonify({'success': False, 'error': '비교할 두 개의 소스가 모두 필요합니다.'})
        
        # 첫 번째 상품 분석
        result1 = analyzer.extract_pdf_content(source1, is_url=(source1_type == 'url'))
        if not result1['success']:
            return jsonify({'success': False, 'error': f'첫 번째 상품 분석 실패: {result1["error"]}'})
        
        # 두 번째 상품 분석
        result2 = analyzer.extract_pdf_content(source2, is_url=(source2_type == 'url'))
        if not result2['success']:
            return jsonify({'success': False, 'error': f'두 번째 상품 분석 실패: {result2["error"]}'})
        
        # 비교 분석 수행 (Rate Limit 방지)
        comparison_analysis = ""
        analysis1 = ""
        analysis2 = ""
        gpt_comparison_success = False
        
        if analyzer.gpt_available:
            logger.info("🤖 GPT 종합 비교 분석 시작...")
            
            try:
                # 새로운 종합 비교 분석 함수 사용
                comparison_analysis = analyzer.gpt_summarizer.analyze_products_comparison(
                    result1['pages'], product1_name,
                    result2['pages'], product2_name
                )
                logger.info(f"📊 종합 비교 분석 결과 길이: {len(comparison_analysis) if comparison_analysis else 0}")
            except Exception as e:
                logger.error(f"❌ 종합 비교 분석 중 오류: {e}")
                comparison_analysis = f"❌ 종합 비교 분석 오류: {str(e)}"
            
            # 분석 성공 여부 확인
            gpt_comparison_success = (
                comparison_analysis and 
                not comparison_analysis.startswith("❌") and 
                not "분석 중 오류 발생" in comparison_analysis and
                not "API 호출에 실패" in comparison_analysis
            )
            
            logger.info(f"GPT 종합 비교 분석 성공: {gpt_comparison_success}")
            
            if gpt_comparison_success:
                logger.info("✅ 종합 비교 분석 완료")
            else:
                logger.warning("⚠️ GPT 종합 비교 분석 실패, 기본 텍스트 사용")
                
            # 개별 분석도 메모리 저장용으로 수행 (성공한 경우에만)
            if gpt_comparison_success:
                logger.info("🔄 개별 분석 시작 (메모리 저장용)...")
                analysis1 = analyzer.analyze_product_comparison(result1['pages'], product1_name)
                time.sleep(1)  # Rate Limit 방지
                analysis2 = analyzer.analyze_product_comparison(result2['pages'], product2_name)
            else:
                analysis1 = ""
                analysis2 = ""
        
        # 메모리에 분석 결과 저장
        user_id = analyzer.get_user_id(request)
        analyzer.save_analysis_result(user_id, {
            'name': product1_name,
            'content': result1['content'],
            'analysis': analysis1 if analyzer.gpt_available else "",
            'timestamp': datetime.now().isoformat()
        })
        analyzer.save_analysis_result(user_id, {
            'name': product2_name,
            'content': result2['content'],
            'analysis': analysis2 if analyzer.gpt_available else "",
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'product1': {
                'name': product1_name,
                'content': result1['content'],
                'page_count': result1['page_count']
            },
            'product2': {
                'name': product2_name,
                'content': result2['content'],
                'page_count': result2['page_count']
            },
            'comparison_analysis': comparison_analysis,
            'gpt_used': gpt_comparison_success  # 실제 성공 여부로 변경
        })
        
    except Exception as e:
        logger.error(f"비교 분석 오류: {e}")
        return jsonify({'success': False, 'error': f'비교 분석 중 오류가 발생했습니다: {str(e)}'})

# WebSocket 이벤트 (챗봇용)
@socketio.on('connect')
def handle_connect():
    """클라이언트 연결"""
    logger.info(f"클라이언트 연결: {request.sid}")
    emit('status', {'message': 'AI 상담 서비스에 연결되었습니다.', 'type': 'info'})

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제"""
    logger.info(f"클라이언트 연결 해제: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """채팅 메시지 처리"""
    try:
        question = data.get('message', '').strip()
        if not question:
            emit('chat_response', {'error': '메시지를 입력해주세요.'})
            return
        
        # 분석된 상품 정보 가져오기 (메모리에서)
        from flask import request as flask_request
        user_id = analyzer.get_user_id(flask_request)
        analyzed_products = analyzer.get_analyzed_products(user_id)
        
        if not analyzed_products:
            emit('chat_response', {
                'response': '아직 분석된 상품이 없습니다. 먼저 상품을 분석해주세요.',
                'type': 'warning'
            })
            return
        
        # 컨텍스트 구성
        context = "분석된 상품 정보:\n\n"
        for i, product in enumerate(analyzed_products[-3:], 1):  # 최근 3개만 사용
            content_preview = product['content'][:1500]
            context += f"상품 {i}: {product['name']}\n{content_preview}\n\n"
        
        # 로딩 상태 전송
        emit('chat_response', {'loading': True, 'message': 'AI가 응답을 생성하고 있습니다...'})
        
        # 현재 request sid 저장
        current_sid = request.sid
        
        # 별도 스레드에서 AI 응답 생성
        def generate_response():
            try:
                response = analyzer.generate_chatbot_response(question, context)
                socketio.emit('chat_response', {
                    'response': response,
                    'type': 'success',
                    'loading': False
                }, room=current_sid)
            except Exception as e:
                logger.error(f"챗봇 응답 생성 오류: {e}")
                socketio.emit('chat_response', {
                    'error': f'응답 생성 중 오류가 발생했습니다: {str(e)}',
                    'loading': False
                }, room=current_sid)
        
        thread = threading.Thread(target=generate_response)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        emit('chat_response', {'error': f'처리 중 오류가 발생했습니다: {str(e)}'})

def start_app():
    """앱 시작 함수 - Vercel과 로컬 환경 모두 지원"""
    logger.info("🚀 PDF OCR 웹 애플리케이션 시작...")
    logger.info(f"GPT API 상태: {'✅ 사용 가능' if analyzer.gpt_available else '❌ 사용 불가'}")
    
    # 주기적 데이터 정리 스케줄링
    import threading
    import time
    
    def cleanup_task():
        while True:
            time.sleep(300)  # 5분마다 실행
            analyzer.cleanup_old_data()
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    
    # 환경에 따라 실행 방식 결정
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    if debug_mode:
        # 개발 환경
        socketio.run(app, host='0.0.0.0', port=8080, debug=True)
    else:
        # 프로덕션 환경
        socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)

# Vercel 환경에서는 import만 되고 실행되지 않음
# 로컬 환경에서만 실행
if __name__ == '__main__':
    start_app()

# Vercel용 WSGI 앱 export
application = app
