"""
GPT API를 사용한 PDF 텍스트 정리 및 요약 모듈
"""
import os
import time
from typing import Dict, List, Any, Optional
from openai import OpenAI
import logging

# 토큰 계산을 위한 import (선택적)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken 라이브러리가 없습니다. 근사치 토큰 계산을 사용합니다.")

try:
    from core.gui_config import gui_settings as settings
except ImportError:
    try:
        from core.config import settings
    except ImportError:
        class MinimalSettings:
            openai_api_key = None
            openai_model = "gpt-4"
        settings = MinimalSettings()

try:
    from core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class GPTSummarizer:
    def __init__(self, api_key: Optional[str] = None):
        """
        GPT 요약기 초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 자동 로드)
        """
        # API 키 설정 (.env 파일 우선)
        from dotenv import load_dotenv
        load_dotenv()  # .env 파일 강제 로드
        
        # .env 파일 -> 설정 -> 파라미터 -> 시스템 환경변수 순서로 우선순위
        self.api_key = (api_key or 
                       settings.openai_api_key or 
                       os.getenv('OPENAI_API_KEY'))
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. 다음 중 하나의 방법으로 설정해주세요:\n"
                "1. 환경변수: OPENAI_API_KEY=your_key\n"
                "2. 파라미터로 직접 전달\n"
                "3. core/config.py에서 openai_api_key 설정"
            )
        
        # API 키 디버깅 정보
        key_preview = f"{self.api_key[:10]}...{self.api_key[-4:]}" if len(self.api_key) > 14 else "****"
        logger.info(f"OpenAI API 키 로드됨: {key_preview}")
        
        # OpenAI 클라이언트 초기화 (proxy 설정 명시적 비활성화)
        try:
            import httpx
            # HTTP 클라이언트를 명시적으로 생성하여 proxy 설정 제어
            http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                # proxy 설정을 명시적으로 None으로 설정
                proxies=None
            )
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=http_client
            )
        except Exception as e:
            logger.warning(f"HTTP 클라이언트 설정 실패, 기본 설정 사용: {e}")
            # 기본 설정으로 재시도
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e2:
                # 환경 변수에서 proxy 설정 제거 후 재시도
                import os
                old_http_proxy = os.environ.pop('HTTP_PROXY', None)
                old_https_proxy = os.environ.pop('HTTPS_PROXY', None)
                old_http_proxy_lower = os.environ.pop('http_proxy', None)
                old_https_proxy_lower = os.environ.pop('https_proxy', None)
                
                try:
                    self.client = OpenAI(api_key=self.api_key)
                    logger.info("proxy 환경변수 제거 후 OpenAI 클라이언트 초기화 성공")
                except Exception as e3:
                    logger.error(f"모든 방법 실패: {e3}")
                    raise e3
                finally:
                    # 환경변수 복원
                    if old_http_proxy: os.environ['HTTP_PROXY'] = old_http_proxy
                    if old_https_proxy: os.environ['HTTPS_PROXY'] = old_https_proxy
                    if old_http_proxy_lower: os.environ['http_proxy'] = old_http_proxy_lower
                    if old_https_proxy_lower: os.environ['https_proxy'] = old_https_proxy_lower
        # 가장 저렴한 모델 사용 (gpt-4o-mini)
        self.model = 'gpt-4o-mini'
        
        # API 키 유효성 검증
        try:
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logger.info(f"✅ OpenAI API 키 검증 성공")
        except Exception as e:
            logger.error(f"❌ OpenAI API 키 검증 실패: {e}")
            raise ValueError(f"OpenAI API 키가 유효하지 않습니다: {e}")
        
        logger.info(f"GPT Summarizer initialized with model: {self.model}")
    
    def _estimate_tokens(self, text: str) -> int:
        """텍스트의 토큰 수를 추정합니다."""
        if TIKTOKEN_AVAILABLE:
            try:
                encoding = tiktoken.encoding_for_model(self.model)
                return len(encoding.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken 인코딩 실패: {e}")
        
        # 근사치 계산 (한국어: 2자당 1토큰, 영어: 4자당 1토큰)
        korean_chars = len([c for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3])
        other_chars = len(text) - korean_chars
        return int(korean_chars / 2 + other_chars / 4)
    
    def _normalize_currency_units(self, text: str) -> str:
        """
        금액 단위를 통일하여 정확한 비교가 가능하도록 정규화합니다.
        
        Args:
            text: 정규화할 텍스트
            
        Returns:
            금액 단위가 통일된 텍스트
        """
        import re
        
        # 금액 패턴 매칭 및 단위 통일
        # 1. 천원 단위 (예: 1,000천원, 1000천원)
        thousand_pattern = r'([0-9,]+)\s*천원'
        def replace_thousand(match):
            amount = match.group(1).replace(',', '')
            try:
                value = int(amount) * 1000
                return f"{value:,}원"
            except:
                return match.group(0)
        text = re.sub(thousand_pattern, replace_thousand, text)
        
        # 2. 만원 단위 (예: 1,000만원, 1000만원)
        ten_thousand_pattern = r'([0-9,]+)\s*만원'
        def replace_ten_thousand(match):
            amount = match.group(1).replace(',', '')
            try:
                value = int(amount) * 10000
                return f"{value:,}원"
            except:
                return match.group(0)
        text = re.sub(ten_thousand_pattern, replace_ten_thousand, text)
        
        # 3. 억원 단위 (예: 1억원, 1.5억원)
        hundred_million_pattern = r'([0-9.]+)\s*억원'
        def replace_hundred_million(match):
            amount = match.group(1)
            try:
                value = float(amount) * 100000000
                return f"{int(value):,}원"
            except:
                return match.group(0)
        text = re.sub(hundred_million_pattern, replace_hundred_million, text)
        
        # 4. 숫자만 있는 경우 (원이 없는 경우) - 문맥에 따라 판단
        # 보험료 관련 문맥에서 숫자만 있으면 원 단위로 가정
        premium_context_pattern = r'(월보험료|보험료|납입|보장금액|지급금액)[:：]\s*([0-9,]+)(?![원천만억])'
        def add_won_unit(match):
            prefix = match.group(1)
            amount = match.group(2)
            return f"{prefix}: {amount}원"
        text = re.sub(premium_context_pattern, add_won_unit, text)
        
        return text
    
    def _smart_truncate_text(self, text: str, max_input_tokens: int = 100000) -> str:
        """토큰 제한을 고려하여 텍스트를 스마트하게 절단합니다. (GPT-4o-mini 128K 활용)"""
        current_tokens = self._estimate_tokens(text)
        
        # GPT-4o-mini는 128K 토큰 지원하므로 대부분의 PDF는 전체 처리 가능
        if current_tokens <= max_input_tokens:
            logger.info(f"✅ 전체 텍스트 보존: {current_tokens} 토큰 (제한: {max_input_tokens})")
            return text
        
        # 토큰 비율 계산
        ratio = max_input_tokens / current_tokens
        target_length = int(len(text) * ratio * 0.9)  # 10% 여유분
        
        # 문장 단위로 절단 시도
        sentences = text.split('.')
        truncated = ""
        for sentence in sentences:
            if self._estimate_tokens(truncated + sentence + ".") > max_input_tokens:
                break
            truncated += sentence + "."
        
        if truncated.strip():
            logger.info(f"텍스트를 문장 단위로 절단: {current_tokens} → {self._estimate_tokens(truncated)} 토큰")
            return truncated
        
        # 문장 단위 절단 실패 시 문자 단위로 절단
        truncated = text[:target_length]
        logger.info(f"텍스트를 문자 단위로 절단: {current_tokens} → {self._estimate_tokens(truncated)} 토큰")
        return truncated

    def _safe_api_call(self, messages, max_tokens=1000, retries=3, delay=2):
        """
        Rate Limit을 고려한 안전한 API 호출
        
        Args:
            messages: 채팅 메시지 리스트
            max_tokens: 최대 토큰 수
            retries: 재시도 횟수
            delay: 재시도 간격 (초)
            
        Returns:
            OpenAI API response object or None if failed
        """
        # 토큰 수 사전 검증
        total_input_tokens = sum(self._estimate_tokens(msg.get('content', '')) for msg in messages)
        total_tokens = total_input_tokens + max_tokens
        
        if total_tokens > 125000:  # GPT-4o-mini 안전 마진 (128k - 3k)
            logger.warning(f"토큰 수 초과 위험: {total_tokens} tokens (입력: {total_input_tokens}, 출력: {max_tokens})")
            # 출력 토큰 자동 조정
            max_tokens = min(max_tokens, 125000 - total_input_tokens)
            logger.info(f"출력 토큰 자동 조정: {max_tokens}")
        
        logger.info(f"API 호출 예상 토큰: 입력 {total_input_tokens} + 출력 {max_tokens} = {total_tokens}")
        for attempt in range(retries):
            try:
                # Rate Limit 방지를 위한 지연
                if attempt > 0:
                    wait_time = delay * (2 ** attempt)  # 지수적 백오프
                    logger.info(f"API 재시도 대기: {wait_time}초")
                    time.sleep(wait_time)
                elif hasattr(self, '_last_api_call'):
                    # 연속 호출 간 최소 간격 보장 (Rate Limit 방지)
                    elapsed = time.time() - self._last_api_call
                    min_interval = 0.5  # 500ms 최소 간격
                    if elapsed < min_interval:
                        sleep_time = min_interval - elapsed
                        logger.info(f"Rate Limit 방지 대기: {sleep_time:.2f}초")
                        time.sleep(sleep_time)
                
                # API 호출 시간 기록
                self._last_api_call = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=max_tokens
                )
                
                # 성공 로깅
                logger.info(f"✅ API 호출 성공 (시도 {attempt + 1}/{retries})")
                
                # 성공 시 다음 요청을 위한 짧은 지연
                time.sleep(1)
                return response
                
            except Exception as e:
                error_str = str(e)
                logger.warning(f"API 호출 시도 {attempt + 1}/{retries} 실패: {error_str}")
                
                # 다양한 에러 타입별 처리
                if "429" in error_str or "rate" in error_str.lower():
                    if attempt < retries - 1:
                        wait_time = delay * (2 ** (attempt + 1))
                        logger.warning(f"🚨 Rate Limit 감지, {wait_time}초 대기 후 재시도...")
                        time.sleep(wait_time)
                        continue
                elif "context_length_exceeded" in error_str.lower() or ("token" in error_str.lower() and "exceed" in error_str.lower()):
                    logger.error(f"🚨 토큰 수 초과 감지: {error_str}")
                    logger.error(f"📊 예상 토큰: 입력 {sum(self._estimate_tokens(msg.get('content', '')) for msg in messages)} + 출력 {max_tokens}")
                    # 토큰 수 초과 시 더 이상 재시도하지 않음
                    break
                elif "invalid_api_key" in error_str.lower() or "401" in error_str:
                    logger.error(f"🚨 API 키 오류 감지: {error_str}")
                    # API 키 오류 시 재시도 무의미
                    break
                
                # 마지막 시도에서도 실패하면 None 반환 (예외 발생 대신)
                if attempt == retries - 1:
                    logger.error(f"❌ API 호출 최종 실패: {error_str}")
                    return None
        
        logger.error("API 호출 최대 재시도 횟수 초과")
        return None
    
    def format_extracted_text(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        OCR로 추출된 원본 텍스트를 GPT API로 보기 좋게 정리
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            GPT로 정리된 텍스트
        """
        try:
            # 1. 원본 텍스트 합치기 (요약하지 않음)
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 추출된 텍스트가 없습니다."
            
            # 2. GPT 프롬프트 생성
            prompt = self._create_formatting_prompt(raw_text, file_name, len(pages))
            
            # 3. GPT API 호출
            logger.info("GPT API 호출 중...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 PDF 문서 텍스트를 깔끔하게 정리하는 전문가입니다. 내용을 요약하지 말고, 읽기 쉽게 구조화하고 포맷팅해주세요."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            formatted_text = response.choices[0].message.content.strip()
            
            # 4. 기본 정보 추가
            final_result = self._add_document_metadata(formatted_text, file_name, len(pages))
            
            logger.info("GPT 텍스트 정리 완료")
            return final_result
            
        except Exception as e:
            logger.error(f"GPT 텍스트 정리 중 오류: {e}")
            # GPT 실패 시 기본 포맷 반환
            return self._fallback_formatting(pages, file_name)
    
    def summarize_extracted_text(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        추출된 텍스트를 GPT로 요약 (원하는 프로세스)
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            GPT로 생성된 요약
        """
        try:
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 요약할 텍스트가 없습니다."
            
            # 내용 전체 인식 프롬프트 (요약하지 않음)
            prompt = f"""
다음은 PDF 문서 "{file_name}"에서 OCR로 추출한 텍스트입니다.
이 내용을 요약하지 말고, 전체 내용을 그대로 깔끔하게 정리해주세요.

추출된 텍스트:
{raw_text}  # 전체 텍스트 포함

정리 요구사항:
1. ❌ 내용을 절대 요약하지 마세요 - 모든 페이지의 모든 정보를 보존해주세요
2. ✅ 전체 페이지 전체 내용을 빠뜨리지 말고 모두 포함해주세요
3. ✅ 각 페이지별로 구조화된 형태로 재구성 (제목, 목록, 표 등)
4. ✅ **모든 표(테이블) 데이터는 반드시 마크다운 표 형식으로 정리해주세요**
5. ✅ **다음 표들을 특히 정확하게 추출해주세요:**
   - 위험보장 및 보험금 지급 표
   - 해약환급금 예시표 (경과기간별) - **반드시 연도별/경과기간별 상세 데이터 포함**
   - 갱신담보 보험료 예시표
   - 모든 숫자, 금액, 비율 데이터가 포함된 표
   - **해약환급금 관련 모든 표와 수치 데이터**
6. ✅ OCR 오류나 오타는 자연스럽게 수정해주세요
7. ✅ 페이지별로 섹션을 명확히 구분해주세요
8. ✅ 마크다운 형식 사용 (## 제목, ** 강조, - 목록, | 표 |)
9. ✅ 한국어는 자연스럽게, 영어/숫자는 원문 유지
10. ✅ 중요한 정보는 굵게 표시해주세요
11. ✅ 모든 페이지의 내용을 순서대로 나열해주세요
12. ⚠️  **중요**: 전체 페이지 끝까지 모든 내용을 완성해주세요. 중간에 끊지 마세요!

표 데이터 예시:

**위험보장표:**
| 담보명 | 보장금액 | 보험료(출생전) | 보험료(출생후) | 비고 |
|--------|----------|----------------|----------------|------|
| 상해후유장해 | 1억원 | 350원 | 1,820원 | 3~100% |
| 암진단 | 1억원 | 2,230원 | 5,230원 | - |

**해약환급금 예시표:**
| 경과기간 | 납입보험료 | 해약환급금 | 환급률 |
|----------|------------|------------|-------|
| 03개월 | 246,870원 | 0원 | 0.0% |
| 01년 | 987,480원 | 0원 | 0.0% |
| 30년01개월 | 30,065,340원 | 14,806,968원 | 49.3% |

**⚠️ 해약환급금 표 추출 시 주의사항:**
- 연도별/경과기간별 모든 데이터를 빠뜨리지 말고 포함
- 표 구조가 깨져도 숫자 데이터는 반드시 보존
- "해약환급금", "환급금", "해약" 관련 모든 표와 수치 추출

**갱신담보 보험료 예시표:**
| 담보명 | 갱신주기 | 0차(현재) | 1차 보험료 | 증가율 | 2차 보험료 | 증가율 |
|--------|----------|-----------|------------|--------|------------|--------|
| 독감치료담보 | 20년 | 1,770원 | 313원 | -82.3% | 270원 | -13.7% |
| 표적항암약물 | 10년 | 469원 | 511원 | 9.0% | 875원 | 71.2% |

결과 형식:
# PDF 전체 내용: {file_name}

## 📋 문서 정보
[문서의 기본 정보]

## 📄 전체 내용
[모든 내용을 구조화하여 표시 - 절대 요약하지 않음]

### 📊 위험보장 및 보험금 지급 표
[위험보장 관련 모든 표를 마크다운 형식으로 정리]

### 💰 해약환급금 예시표
[경과기간별 해약환급금 표를 완전히 정리]

### 🔄 갱신담보 보험료 예시표  
[갱신차수별 보험료 변동 표를 완전히 정리]

### 📋 기타 모든 표 데이터
[문서 내 모든 표 형태 데이터를 빠뜨리지 않고 정리]
"""

            # Rate Limit을 고려한 안전한 API 호출
            messages = [
                {
                    "role": "system",
                    "content": "당신은 PDF 문서 정리 전문가입니다. 내용을 요약하지 말고, 모든 정보를 보존하면서 읽기 쉽게 구조화해주세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self._safe_api_call(
                messages=messages, 
                max_tokens=8000,  # 19페이지 전체 출력을 위해 대폭 확대
                retries=3,
                delay=2
            )
            
            if response is None:
                # GPT 실패 시 기본 텍스트 정리 시도
                logger.warning("GPT API 실패, 기본 텍스트 포맷팅 사용")
                return self._fallback_formatting(pages, file_name)
            
            summary = response.choices[0].message.content.strip()
            
            # 문서 메타데이터 추가
            from datetime import datetime
            metadata = f"""📄 PDF 요약 결과
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {len(pages)}
⏰ 요약 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 요약 방식: GPT API 사용

{'='*50}

"""
            
            return metadata + summary
            
        except Exception as e:
            logger.error(f"GPT 요약 중 오류: {e}")
            return f"❌ 요약 생성 중 오류 발생: {str(e)}"
    
    def summarize_content(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        추출된 텍스트를 요약 (선택적 기능)
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            GPT로 생성된 요약
        """
        try:
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 요약할 텍스트가 없습니다."
            
            # 요약 프롬프트
            prompt = f"""
다음 PDF 문서의 내용을 한국어로 요약해주세요:

문서명: {file_name}
페이지 수: {len(pages)}

내용:
{raw_text}  # 전체 텍스트 포함

요구사항:
1. 핵심 내용만 간결하게 요약
2. 중요한 키워드와 개념 포함
3. 구조화된 형태로 작성
4. 한국어 사용
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 문서 요약 전문가입니다. 핵심 내용을 놓치지 않고 간결하게 요약해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"GPT 요약 중 오류: {e}")
            return f"❌ 요약 생성 중 오류 발생: {str(e)}"
    
    def _combine_extracted_text(self, pages: List[Dict[str, Any]]) -> str:
        """모든 페이지의 텍스트를 합치기 (전체 내용 보존)"""
        all_text = ""
        
        # 타입 안전성 확인
        if not isinstance(pages, list):
            logger.error(f"Expected list, got {type(pages)}")
            return ""
        
        total_pages = len(pages)
        logger.info(f"GPT 텍스트 조합 시작: 총 {total_pages} 페이지")
        
        for i, page in enumerate(pages):
            # 각 페이지가 딕셔너리인지 확인
            if not isinstance(page, dict):
                logger.error(f"Page {i} is not dict: {type(page)}")
                continue
                
            page_num = page.get('page_number', i+1)
            text = page.get('text', '')
            ocr_text = page.get('ocr_text', '')
            
            # 해약환급금 관련 페이지 특별 표시
            is_surrender_page = any(keyword in text for keyword in ['해약환급금', '환급금', '경과기간'])
            page_marker = f"\n\n=== 페이지 {page_num}/{total_pages} {'[해약환급금 관련]' if is_surrender_page else ''} ===\n"
            all_text += page_marker
            
            if is_surrender_page:
                logger.info(f"해약환급금 관련 페이지 {page_num} GPT 텍스트에 포함")
            
            # 기본 텍스트 추가 (더 많은 내용 포함)
            if text.strip():
                all_text += text.strip() + "\n"
            
            # OCR 텍스트 추가 (구분하여 표시)
            if ocr_text.strip():
                if text.strip():
                    all_text += "\n[OCR로 추가 추출된 텍스트]\n"
                all_text += ocr_text.strip() + "\n"
            
            # 페이지에 텍스트가 없는 경우 표시
            if not text.strip() and not ocr_text.strip():
                all_text += "[이 페이지에서 텍스트를 추출할 수 없습니다]\n"
        
        logger.info(f"전체 텍스트 길이: {len(all_text)} 자, 총 {total_pages} 페이지")
        return all_text
    
    def _create_formatting_prompt(self, raw_text: str, file_name: str, page_count: int) -> str:
        """GPT 포맷팅용 프롬프트 생성"""
        return f"""
다음은 PDF "{file_name}"에서 OCR로 추출한 원본 텍스트입니다.
내용을 요약하지 말고, 읽기 쉽게 정리만 해주세요.

문서 정보:
- 파일명: {file_name}
- 페이지 수: {page_count}

원본 텍스트:
{raw_text}  # 전체 텍스트 포함

정리 요구사항:
1. 내용을 절대 요약하지 마세요 - 모든 정보를 보존
2. 구조화된 형태로 재구성 (제목, 목록, 표 등)
3. 오타나 OCR 오류는 자연스럽게 수정
4. 문단과 섹션을 명확히 구분
5. 마크다운 형식 사용 (제목: ##, 목록: -, 강조: **)
6. 중요한 정보는 굵게 표시
7. 한국어는 자연스럽게, 영어는 원문 유지

결과 형식:
# 문서 제목 (파일명 기반)

## 개요
[문서의 기본 정보]

## 주요 내용
[구조화된 전체 내용]
"""
    
    def _add_document_metadata(self, formatted_text: str, file_name: str, page_count: int) -> str:
        """문서 메타데이터 추가"""
        from datetime import datetime
        
        metadata = f"""📄 PDF 문서 정리 결과
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {page_count}
⏰ 처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 정리 방식: GPT API 사용

{'='*50}

"""
        return metadata + formatted_text
    
    def _fallback_formatting(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """GPT 실패 시 기본 포맷팅"""
        from datetime import datetime
        
        result = f"""📄 PDF 텍스트 추출 결과 (기본 모드)
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {len(pages)}
⏰ 처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚠️  GPT API 사용 불가 - 기본 포맷 적용

{'='*50}

"""
        
        # 페이지별 텍스트 추가
        for i, page in enumerate(pages):
            # 각 페이지가 딕셔너리인지 확인
            if not isinstance(page, dict):
                continue
                
            page_num = page.get('page_number', i+1)
            text = page.get('text', '')
            ocr_text = page.get('ocr_text', '')
            
            result += f"\n## 페이지 {page_num}\n"
            result += "-" * 20 + "\n"
            
            if text.strip():
                result += text.strip() + "\n\n"
            
            if ocr_text.strip():
                result += "**[OCR 텍스트]**\n"
                result += ocr_text.strip() + "\n\n"
        
        return result
    
    def analyze_for_comparison(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        상품 비교용 핵심 정보 추출 및 분석
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            비교 분석에 특화된 구조화된 정보
        """
        try:
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 분석할 텍스트가 없습니다."
            
            # 토큰 제한 고려한 스마트 절단 (비교 분석용 - 전체 보존)
            smart_text = self._smart_truncate_text(raw_text, max_input_tokens=80000)
            
            # 비교 분석용 특화 프롬프트
            prompt = f"""
다음은 보험 상품 문서 "{file_name}"에서 추출한 텍스트입니다.
이 상품을 다른 상품과 비교하기 위한 핵심 정보를 체계적으로 분석해주세요.

추출된 텍스트:
{smart_text}

분석 요구사항:
1. **상품 기본 정보**
   - 상품명, 상품 코드
   - 상품 타입 (어린이보험, 종합보험, 암보험 등)
   - 보험 회사명

2. **보험료 정보** 🚨 중요: 모든 금액은 원본 문서의 정확한 숫자를 그대로 사용하세요
   - 월 보험료 (예: 92,540원처럼 원본 그대로, 절대 반올림하거나 수정하지 마세요)
   - 납입 방식 (월납, 연납 등)
   - 납입 기간
   
   ⚠️ 금액 표기 주의사항:
   - 92,540원은 그대로 92,540원으로 표기
   - 절대 92,000원이나 93,000원으로 반올림하지 않기
   - 모든 숫자는 원본 텍스트에서 발견한 그대로 정확히 복사

3. **핵심 보장 내용**
   - 기본 보장 (주계약)
   - 주요 특약 보장 (상위 5개)
   - 보장 금액 및 범위

4. **비교 우위 요소**
   - 이 상품만의 독특한 보장
   - 타 상품 대비 유리한 점
   - 보험료 경쟁력

5. **해약/환급 정보**
   - 환급 방식 (무해지환급형, 저해지환급형 등)
   - 만기 환급률 또는 조건

6. **대상 고객**
   - 주요 타겟 연령층
   - 추천 상황

결과 형식:
# 🏷️ 상품 비교 분석: {file_name}

## 📋 기본 정보
- **상품명**: [정확한 상품명]
- **상품코드**: [코드]
- **상품타입**: [카테고리]
- **회사**: [보험사명]

## 💰 보험료 정보 🚨 숫자 변경 절대 금지
- **월보험료**: [원본 문서의 정확한 금액 - 예: 92,540원]
- **납입방식**: [방식]
- **납입기간**: [기간]

💡 **금액 표기 원칙**: 
- 문서에서 찾은 정확한 금액을 그대로 표기
- 절대 반올림하지 않음 (예: 92,540원 → 92,000원 변경 금지)

## 🛡️ 핵심 보장
### 기본보장 (주계약)
- [주계약 내용 및 금액]

### 주요 특약 TOP 5
1. [특약명] - [보장금액] - [특징]
2. [특약명] - [보장금액] - [특징]
3. [특약명] - [보장금액] - [특징]
4. [특약명] - [보장금액] - [특징]
5. [특약명] - [보장금액] - [특징]

## ⭐ 경쟁 우위
- **독특한 보장**: [차별화 요소]
- **보험료 경쟁력**: [비용 대비 효과]
- **특화 영역**: [강점 분야]

## 💎 해약/환급
- **환급방식**: [방식]
- **만기조건**: [조건]

## 🎯 추천 대상
- **주요 고객**: [타겟층]
- **추천 상황**: [언제 유리한지]

## 📊 비교 점수 (5점 만점)
- **보험료 경쟁력**: ⭐⭐⭐⭐⭐
- **보장 다양성**: ⭐⭐⭐⭐⭐  
- **보장 충실도**: ⭐⭐⭐⭐⭐
- **해약 조건**: ⭐⭐⭐⭐⭐
"""

            messages = [
                {
                    "role": "system",
                    "content": "당신은 보험상품 비교 분석 전문가입니다. 상품의 핵심 경쟁력과 차별화 요소를 정확히 파악하여 비교에 최적화된 정보를 제공해주세요. 🚨 중요: 모든 금액과 숫자는 원본 문서의 정확한 값을 그대로 사용하고, 절대 반올림하거나 수정하지 마세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self._safe_api_call(
                messages=messages,
                max_tokens=6000,  # 더 상세한 분석을 위해 증가
                retries=3,
                delay=2
            )
            
            if response is None:
                # GPT 실패 시 기본 텍스트 정리 시도
                logger.warning("GPT API 실패, 기본 텍스트 포맷팅 사용")
                return self._fallback_formatting(pages, file_name)
            
            analysis = response.choices[0].message.content.strip()
            
            # 메타데이터 추가
            from datetime import datetime
            metadata = f"""📊 상품 비교 분석 결과
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {len(pages)}
⏰ 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 분석 목적: 상품 비교용 핵심 정보 추출

{'='*50}

"""
            
            return metadata + analysis
            
        except Exception as e:
            logger.error(f"상품 비교 분석 중 오류: {e}")
            return f"❌ 비교 분석 생성 중 오류 발생: {str(e)}"
    
    def analyze_products_comparison(self, pages1: List[Dict[str, Any]], file1_name: str, 
                                    pages2: List[Dict[str, Any]], file2_name: str, 
                                    custom_prompt: str = "") -> str:
        """
        두 보험상품의 직접적인 비교 분석을 수행합니다.
        
        Args:
            pages1: 첫 번째 상품 페이지 데이터
            file1_name: 첫 번째 상품 파일명
            pages2: 두 번째 상품 페이지 데이터
            file2_name: 두 번째 상품 파일명
            
        Returns:
            두 상품의 종합적인 비교 분석 결과
        """
        try:
            # 두 상품의 텍스트 추출
            text1 = self._combine_extracted_text(pages1)
            text2 = self._combine_extracted_text(pages2)
            
            if not text1.strip() or not text2.strip():
                return "❌ 비교할 텍스트가 충분하지 않습니다."
            
            # 금액 단위 정규화 (두 상품 모두)
            normalized_text1 = self._normalize_currency_units(text1)
            normalized_text2 = self._normalize_currency_units(text2)
            
            # 토큰 제한 고려한 스마트 절단 (두 상품 모두)
            smart_text1 = self._smart_truncate_text(normalized_text1, max_input_tokens=40000)
            smart_text2 = self._smart_truncate_text(normalized_text2, max_input_tokens=40000)
            
            pages1_count = len(pages1)
            pages2_count = len(pages2)
            
            # 표 데이터 추출 및 주입
            table_data1 = self._extract_table_data_from_pages(pages1)
            table_data2 = self._extract_table_data_from_pages(pages2)
            
            # 종합 비교 분석 프롬프트
            user_instruction = ""
            if custom_prompt:
                user_instruction = f"""
🚨 **사용자 특별 요청사항**:
{custom_prompt}

위 요청사항을 반드시 우선적으로 고려하여 분석을 진행해주세요.
"""
            
            prompt = f"""
아래에는 두 가지 보험 상품의 보장 내역이 있습니다. 
이 두 상품을 고객의 입장에서 쉽게 비교할 수 있도록 정리해 주세요.
{user_instruction}

**📊 표 데이터 (정확한 수치 비교용)**:
상품 A 표 데이터: {table_data1}
상품 B 표 데이터: {table_data2}

**상품 A**: {file1_name}
페이지 수: {pages1_count}
추출된 텍스트:
{smart_text1}

**상품 B**: {file2_name}  
페이지 수: {pages2_count}
추출된 텍스트:
{smart_text2}

[출력 지침]

1. **기본 정보 추출**
   - 상품명, 상품코드, 상품타입, 보험회사를 정확히 추출하세요
   - 🚨 **보험료 정보**: 모든 금액은 원본 문서의 정확한 숫자를 그대로 사용하세요
     (예: 92,540원은 절대 92,000원으로 반올림하지 마세요)
   - 💰 **금액 단위 통일**: 모든 금액은 원 단위로 통일하여 비교하세요
     (천원, 만원, 억원 등은 모두 원 단위로 변환하여 표시)

2. **보장 항목 자동 식별 및 매칭**
   - 두 문서에서 '보장 항목'을 스스로 식별하세요 
     (예: 수술보장, 특정질병보장, 입원보장, 납입면제, 비급여치료, 암보장, 뇌혈관질환보장 등)
   - 문서마다 항목 이름이나 구성이 달라도 같은 의미라면 같은 카테고리로 묶어 비교하세요
   - 한쪽 상품에만 존재하는 항목은 '해당 없음'으로 표시하세요

3. **전문용어 고객 친화적 해석**
   - 전문 용어가 있으면 간단한 설명을 괄호 안에 추가해 주세요
     (예: '납입면제(특정 조건 충족 시 보험료 납입을 면제받는 제도)')
   - 보험 비전문가도 이해할 수 있도록 간결하고 명확하게 작성하세요

결과 형식:

# 🏷️ 2개 상품 비교 분석

## 📊 상품 A 분석

### 📋 기본 정보
- **상품명**: [정확한 상품명]
- **상품코드**: [코드]
- **상품타입**: [카테고리]
- **회사**: [보험사명]

### 💰 보험료 정보 🚨 숫자 변경 절대 금지
- **월보험료**: [원본 문서의 정확한 금액 - 예: 92,540원]
- **납입방식**: [방식]
- **납입기간**: [기간]

### 🛡️ 핵심 보장 내용
| 보장 항목 | 보장 내용 | 보장 금액/횟수 |
|-----------|-----------|----------------|
| [항목1] | [구체적 내용] | [금액/횟수] |
| [항목2] | [구체적 내용] | [금액/횟수] |
| [항목3] | [구체적 내용] | [금액/횟수] |

### ⭐ 경쟁 우위 요소
- **독특한 보장**: [차별화 요소]
- **보험료 경쟁력**: [비용 대비 효과]
- **특화 영역**: [강점 분야]

---

## 📊 상품 B 분석

### 📋 기본 정보
- **상품명**: [정확한 상품명]
- **상품코드**: [코드]  
- **상품타입**: [카테고리]
- **회사**: [보험사명]

### 💰 보험료 정보 🚨 숫자 변경 절대 금지
- **월보험료**: [원본 문서의 정확한 금액 - 예: 69,000원]
- **납입방식**: [방식]
- **납입기간**: [기간]

### 🛡️ 핵심 보장 내용
| 보장 항목 | 보장 내용 | 보장 금액/횟수 |
|-----------|-----------|----------------|
| [항목1] | [구체적 내용] | [금액/횟수] |
| [항목2] | [구체적 내용] | [금액/횟수] |
| [항목3] | [구체적 내용] | [금액/횟수] |

### ⭐ 경쟁 우위 요소
- **독특한 보장**: [차별화 요소]
- **보험료 경쟁력**: [비용 대비 효과]
- **특화 영역**: [강점 분야]

---

## 🔍 핵심 비교 분석

### 📊 보장 항목별 상세 비교표
| 보장 항목 | 상품 A | 상품 B | 차이점 및 우위 |
|-----------|--------|--------|----------------|
| [공통항목1] | [A의 보장내용] | [B의 보장내용] | [구체적 차이점] |
| [공통항목2] | [A의 보장내용] | [B의 보장내용] | [구체적 차이점] |
| [A만의 항목] | [A의 보장내용] | 해당 없음 | [A의 독점 장점] |
| [B만의 항목] | 해당 없음 | [B의 보장내용] | [B의 독점 장점] |

### 💡 고객 관점 핵심 차이점
1. **보험료 비교**: [구체적인 월보험료 차이 및 가성비 분석]
2. **보장 범위**: [어느 상품이 더 폭넓게/깊이 있게 보장하는지]
3. **독점 보장**: [각 상품만의 특별한 보장 내용]
4. **고객 유형별 추천**: [어떤 고객에게 어떤 상품이 더 적합한지]

### 🎯 상황별 추천 가이드
- **20-30대 젊은층**: [추천 상품과 이유]
- **30-40대 가족층**: [추천 상품과 이유]  
- **50대+ 중장년층**: [추천 상품과 이유]
- **보험료 절약 우선**: [추천 상품과 이유]
- **보장 충실도 우선**: [추천 상품과 이유]

⚠️ **중요 주의사항**: 
- 모든 금액은 원본 문서의 정확한 숫자를 그대로 표기
- 절대 반올림하거나 수정하지 않음
- 전문용어는 괄호 안에 쉬운 설명 추가
- 항목 누락 없이 모든 보장 내역 반영
"""

            messages = [
                {
                    "role": "system",
                    "content": "당신은 보험상품 비교 분석 전문가입니다. 두 상품을 고객 관점에서 쉽게 이해할 수 있도록 체계적으로 비교 분석해주세요. 🚨 중요: 모든 금액과 숫자는 원본 문서의 정확한 값을 그대로 사용하고, 절대 반올림하거나 수정하지 마세요. 전문용어는 고객이 이해하기 쉽게 설명을 추가해주세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self._safe_api_call(
                messages=messages,
                max_tokens=8000,  # 종합 비교 분석을 위해 더 큰 토큰 할당
                retries=3,
                delay=2
            )
            
            if response is None:
                # GPT 실패 시 기본 텍스트 조합
                logger.warning("GPT API 실패, 기본 개별 분석 조합 사용")
                return self._fallback_comparison(pages1, file1_name, pages2, file2_name)
            
            analysis = response.choices[0].message.content.strip()
            
            # 디버깅: GPT 응답 로깅
            logger.info(f"📊 GPT 응답 샘플 (처음 500자): {analysis[:500]}")
            
            # 메타데이터 추가
            from datetime import datetime
            metadata = f"""🔍 보험상품 종합 비교 분석 결과
{'='*60}

📁 상품 A: {file1_name} ({pages1_count}페이지)
📁 상품 B: {file2_name} ({pages2_count}페이지)
⏰ 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 분석 목적: 고객 친화적 종합 비교 분석

{'='*60}

"""
            
            return metadata + analysis
            
        except Exception as e:
            logger.error(f"종합 비교 분석 중 오류: {e}")
            return f"❌ 종합 비교 분석 생성 중 오류 발생: {str(e)}"
    
    def _fallback_comparison(self, pages1: List[Dict[str, Any]], file1_name: str,
                           pages2: List[Dict[str, Any]], file2_name: str) -> str:
        """GPT 분석 실패 시 기본 비교 형태로 조합"""
        try:
            # 개별 분석 수행
            analysis1 = self.analyze_for_comparison(pages1, file1_name)
            analysis2 = self.analyze_for_comparison(pages2, file2_name)
            
            return f"""# 🔍 기본 비교 분석 (GPT 분석 실패 시 대체)

## 📊 상품 A 분석
{analysis1}

---

## 📊 상품 B 분석  
{analysis2}

---

## ⚠️ 알림
GPT 비교 분석에 실패하여 기본 개별 분석을 제공합니다.
상세한 비교를 위해서는 다시 시도해주세요.
"""
            
        except Exception as e:
            logger.error(f"Fallback 비교 분석 중 오류: {e}")
            return f"❌ 비교 분석 생성 실패: {str(e)}"

    def analyze_surrender_value(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        해약환급금 정보를 특화하여 분석합니다.
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            해약환급금 관련 상세 정보
        """
        try:
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 분석할 텍스트가 없습니다."
            
            # 해약환급금 관련 텍스트만 필터링
            surrender_keywords = ['해약환급금', '환급금', '해약', '환급', '경과기간', '납입보험료']
            surrender_text = self._extract_surrender_related_text(raw_text, surrender_keywords)
            
            if not surrender_text.strip():
                return "❌ 해약환급금 관련 정보를 찾을 수 없습니다."
            
            # 토큰 제한 고려한 스마트 절단
            smart_text = self._smart_truncate_text(surrender_text, max_input_tokens=40000)
            
            # 해약환급금 특화 프롬프트
            prompt = f"""
다음은 보험 상품 "{file_name}"에서 추출한 해약환급금 관련 텍스트입니다.
해약환급금에 대한 구체적이고 정확한 정보를 제공해주세요.

추출된 텍스트:
{smart_text}

분석 요구사항:
1. **해약환급금 표 데이터 완전 추출**
   - 경과기간별 해약환급금액
   - 납입보험료 대비 환급률
   - 연도별 상세 데이터

2. **표 구조 복원**
   - 깨진 표 구조라도 숫자 데이터는 반드시 보존
   - 마크다운 표 형식으로 정리
   - 모든 수치 데이터 포함

3. **누락된 정보 확인**
   - 해약환급금 관련 모든 표와 수치
   - 경과기간별 상세 정보
   - 환급 조건 및 제한사항

결과 형식:
# 💰 해약환급금 상세 분석: {file_name}

## 📊 해약환급금 표 (경과기간별)
| 경과기간 | 납입보험료 | 해약환급금 | 환급률 | 비고 |
|----------|------------|------------|-------|------|
| [구체적 데이터] | [구체적 금액] | [구체적 금액] | [구체적 %] | [조건] |

## 📈 해약환급금 분석
- **최초 환급 시점**: [구체적 경과기간]
- **최대 환급률**: [구체적 %]
- **환급 조건**: [구체적 조건]

## ⚠️ 주의사항
- [환급 제한 조건]
- [해약 시 주의사항]
"""

            messages = [
                {
                    "role": "system",
                    "content": "당신은 보험 해약환급금 분석 전문가입니다. 해약환급금 관련 모든 표와 수치 데이터를 정확히 추출하고 분석해주세요. 표 구조가 깨져도 숫자 데이터는 반드시 보존하여 제공해주세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self._safe_api_call(
                messages=messages,
                max_tokens=6000,
                retries=3,
                delay=2
            )
            
            if response is None:
                return "❌ 해약환급금 분석에 실패했습니다."
            
            analysis = response.choices[0].message.content.strip()
            
            # 메타데이터 추가
            from datetime import datetime
            metadata = f"""💰 해약환급금 특화 분석 결과
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {len(pages)}
⏰ 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 분석 목적: 해약환급금 상세 정보 추출

{'='*50}

"""
            
            return metadata + analysis
            
        except Exception as e:
            logger.error(f"해약환급금 분석 중 오류: {e}")
            return f"❌ 해약환급금 분석 생성 중 오류 발생: {str(e)}"
    
    def _extract_surrender_related_text(self, text: str, keywords: List[str]) -> str:
        """해약환급금 관련 텍스트만 추출"""
        lines = text.split('\n')
        surrender_lines = []
        
        for line in lines:
            if any(keyword in line for keyword in keywords):
                surrender_lines.append(line)
                # 주변 컨텍스트도 포함 (표 구조 보존)
                if '|' in line or any(char.isdigit() for char in line):
                    surrender_lines.append(line)
        
        return '\n'.join(surrender_lines)
    
    def _extract_table_data_from_pages(self, pages: List[Dict[str, Any]]) -> str:
        """페이지에서 표 데이터 추출 (개선된 해약환급금 표 파싱)"""
        try:
            from parsing.table_parser import TableParser
            
            table_data = []
            parser = TableParser()
            
            for page in pages:
                page_text = page.get('text', '')
                if page_text:
                    # 해약환급금 표 파싱
                    surrender_table = parser.parse_surrender_value_table(page_text)
                    if surrender_table:
                        table_data.extend(surrender_table)
            
            if not table_data:
                return "표 데이터 없음"
            
            # 표 데이터를 구조화된 형태로 변환
            formatted_data = []
            for item in table_data:
                if item.get('type') == 'data':
                    columns = item.get('columns', [])
                    amounts = item.get('amounts', [])
                    
                    if len(columns) >= 6:  # 경과기간, 납입보험료, 적립부분환급금, 보장부분환급금, 환급금(합계), 환급률
                        formatted_data.append({
                            "period": columns[0] if len(columns) > 0 else "",
                            "premium": columns[1] if len(columns) > 1 else "",
                            "surrender_amount": columns[4] if len(columns) > 4 else "",
                            "surrender_rate": columns[5] if len(columns) > 5 else "",
                            "amounts": amounts
                        })
            
            return str(formatted_data)
            
        except Exception as e:
            logger.error(f"표 데이터 추출 실패: {e}")
            return "표 데이터 추출 실패"

    def analyze_for_detail(self, pages: List[Dict[str, Any]], file_name: str) -> str:
        """
        상품 상세 정보 제공용 심층 분석
        
        Args:
            pages: PDF 페이지 데이터 리스트
            file_name: PDF 파일명
            
        Returns:
            상세 정보 제공에 특화된 종합 분석
        """
        try:
            raw_text = self._combine_extracted_text(pages)
            
            if not raw_text.strip():
                return "❌ 분석할 텍스트가 없습니다."
            
            # 토큰 제한 고려한 스마트 절단 (상세 분석용 - 전체 보존)
            smart_text = self._smart_truncate_text(raw_text, max_input_tokens=80000)
            
            # 상세 분석용 특화 프롬프트
            prompt = f"""
다음은 보험 상품 문서 "{file_name}"에서 추출한 전체 텍스트입니다.
고객이 이 상품을 자세히 이해할 수 있도록 상세하고 실용적인 정보를 제공해주세요.

추출된 텍스트:
{smart_text}

상세 분석 요구사항:
1. **종합 상품 개요**
   - 상품의 핵심 가치와 목적
   - 누구를 위한 상품인지
   - 이 상품의 철학과 설계 개념

2. **완전한 보장 구조**
   - 기본 보장 상세 설명
   - 모든 특약 보장 내용 (중요도 순)
   - 보장 제외 사항 및 주의사항
   - 각 보장별 실제 활용 예시

3. **보험료 구조 분석** 🚨 모든 금액은 원본 그대로 표기
   - 보험료 산출 기준 (정확한 금액으로 예: 92,540원)
   - 연령별, 성별 차이 (구체적 금액)
   - 보험료 할인/할증 요인
   - 갱신 조건 및 보험료 변동
   
   💡 **금액 표기 원칙**: 원본에서 92,540원이면 92,540원 그대로, 절대 반올림 금지

4. **가입 조건 및 절차**
   - 가입 가능 연령 및 조건
   - 건강 고지 의무 사항
   - 필요 서류 및 절차
   - 가입 후 주의사항

5. **실전 활용 가이드**
   - 보험금 청구 절차
   - 자주 발생하는 사고별 보상 범위
   - 보험금 지급 제외 사례
   - 고객이 알아두면 좋은 팁

6. **장단점 심층 분석**
   - 이 상품의 명확한 장점
   - 한계나 아쉬운 점
   - 다른 상품과의 차별점
   - 개선 제안

7. **생애주기별 활용법**
   - 연령대별 활용 전략
   - 가족 상황별 최적 설계
   - 다른 보험과의 조합 방법

8. **수치 정보 완전 정리**
   - 모든 보험료 정보 테이블
   - 해약환급금 상세 표
   - 갱신 보험료 변동 예시
   - 보장 금액별 비교표

결과 형식:
# 📖 [{file_name}] 완전 분석 가이드

## 🎯 상품 철학 및 핵심 가치
[이 상품이 추구하는 가치와 설계 철학]

## 🏗️ 완전한 보장 구조
### 🛡️ 기본 보장 (주계약)
[상세한 기본 보장 설명]

### ⭐ 특약 보장 완전 가이드
[모든 특약을 중요도순으로 상세 설명]

### ⚠️ 보장 제외 및 주의사항
[고객이 반드시 알아야 할 제외 사항]

## 💰 보험료 구조 완전 분석
### 📊 보험료 산출 기준
[보험료 결정 요소들]

### 📈 갱신 및 변동 조건
[보험료 변동 가능성]

## 📋 가입 가이드
### ✅ 가입 조건
[상세한 가입 자격 및 조건]

### 📝 필요 절차
[단계별 가입 과정]

## 🔧 실전 활용 매뉴얼
### 💊 보험금 청구 가이드
[실제 청구 시 필요한 모든 정보]

### 📚 사례별 보상 범위
[구체적인 상황별 보상 예시]

## ⚖️ 장단점 완전 분석
### ✅ 명확한 장점
[이 상품의 확실한 강점들]

### ⚠️ 한계 및 개선점
[솔직한 아쉬운 점들]

## 🎯 생애주기별 활용 전략
### 👶 연령대별 전략
[각 연령에서의 최적 활용법]

### 👨‍👩‍👧‍👦 가족 상황별 설계
[가족 구성에 따른 맞춤 전략]

## 📊 완전한 수치 정보
### 💰 보험료 상세표
[모든 보험료 정보를 표로 정리]

### 📈 해약환급금 표
[경과 기간별 상세 환급 정보]

### 🔄 갱신 보험료 예시
[갱신 시 보험료 변동 예측]

## 💡 전문가 조언
[이 상품을 고려할 때 반드시 알아둘 점들]
"""

            messages = [
                {
                    "role": "system",
                    "content": "당신은 보험상품 상세 분석 전문가입니다. 고객이 상품을 완전히 이해하고 현명한 선택을 할 수 있도록 상세하고 실용적인 정보를 제공해주세요. 모든 내용을 포함하되 이해하기 쉽게 설명해주세요. 🚨 중요: 모든 금액과 숫자는 원본 문서의 정확한 값을 그대로 사용하고, 절대 반올림하거나 수정하지 마세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self._safe_api_call(
                messages=messages,
                max_tokens=8000,  # 상세 분석이므로 더 많은 토큰 할당
                retries=3,
                delay=2
            )
            
            if response is None:
                # GPT 실패 시 기본 텍스트 정리 시도
                logger.warning("GPT API 실패, 기본 텍스트 포맷팅 사용")
                return self._fallback_formatting(pages, file_name)
            
            analysis = response.choices[0].message.content.strip()
            
            # 메타데이터 추가
            from datetime import datetime
            metadata = f"""📖 상품 상세 분석 결과
{'='*50}

📁 파일명: {file_name}
📑 페이지 수: {len(pages)}
⏰ 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎯 분석 목적: 상품 상세 정보 제공

{'='*50}

"""
            
            return metadata + analysis
            
        except Exception as e:
            logger.error(f"상품 상세 분석 중 오류: {e}")
            return f"❌ 상세 분석 생성 중 오류 발생: {str(e)}"
