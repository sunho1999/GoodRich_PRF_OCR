#!/usr/bin/env python3
"""
GPT API에 전달되는 실제 내용을 디버깅하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsing.pdf_text import PDFTextExtractor
from llm.gpt_summarizer import GPTSummarizer

def debug_gpt_input():
    """GPT API에 전달되는 내용을 디버깅"""
    
    # 테스트 URL
    test_url = "http://goodrichplus.kr/gvKNg"
    
    print("🔍 GPT API 전달 내용 디버깅 시작")
    print("=" * 50)
    
    # 1. PDF 텍스트 추출
    print("1. PDF 텍스트 추출 중...")
    extractor = PDFTextExtractor()
    success, pages = extractor.extract_text_from_url(test_url)
    
    if not success:
        print("❌ PDF 텍스트 추출 실패")
        return
    
    print(f"✅ PDF 텍스트 추출 성공: {len(pages)} 페이지")
    
    # 2. 페이지별 상세 정보
    print("\n2. 페이지별 상세 정보:")
    for i, page in enumerate(pages):
        page_num = page.get('page_number', i+1)
        text_length = len(page.get('text', ''))
        has_surrender = any(keyword in page.get('text', '') for keyword in ['해약환급금', '환급금', '경과기간'])
        table_data_count = len(page.get('table_data', []))
        
        print(f"  페이지 {page_num}: 텍스트 길이 {text_length}, 해약환급금 관련: {has_surrender}, 표 데이터: {table_data_count}개")
        
        if has_surrender:
            print(f"    📊 해약환급금 관련 페이지 {page_num} 감지!")
            print(f"    📝 텍스트 샘플: {page.get('text', '')[:200]}...")
            
            # 표 데이터 상세 확인
            table_data = page.get('table_data', [])
            if table_data:
                print(f"    📋 표 데이터 {len(table_data)}개:")
                for j, item in enumerate(table_data[:5]):  # 처음 5개만
                    print(f"      {j+1}. {item.get('text_raw', '')} -> {item.get('amount_raw', '')}")
    
    # 3. GPT 텍스트 조합 확인 (API 키 없이)
    print("\n3. GPT 텍스트 조합 확인:")
    try:
        summarizer = GPTSummarizer()
        combined_text = summarizer._combine_extracted_text(pages)
    except Exception as e:
        print(f"⚠️ GPT 초기화 실패 (API 키 문제): {e}")
        # API 키 없이도 텍스트 조합은 가능
        from llm.gpt_summarizer import GPTSummarizer
        summarizer = GPTSummarizer.__new__(GPTSummarizer)  # 인스턴스 생성만
        combined_text = summarizer._combine_extracted_text(pages)
    
    print(f"✅ GPT 텍스트 조합 완료: {len(combined_text)} 자")
    
    # 해약환급금 관련 부분 확인
    surrender_sections = []
    lines = combined_text.split('\n')
    for i, line in enumerate(lines):
        if '해약환급금' in line or '환급금' in line:
            surrender_sections.append(f"라인 {i+1}: {line}")
    
    print(f"📊 해약환급금 관련 라인 {len(surrender_sections)}개 발견:")
    for section in surrender_sections[:10]:  # 처음 10개만
        print(f"  {section}")
    
    # 4. 표 데이터 추출 확인
    print("\n4. 표 데이터 추출 확인:")
    table_data1 = summarizer._extract_table_data_from_pages(pages)
    print(f"📋 추출된 표 데이터: {table_data1}")
    
    # 5. 실제 GPT 프롬프트 생성 (비교 분석용)
    print("\n5. 실제 GPT 프롬프트 생성:")
    
    # 표 데이터 추출
    table_data1 = summarizer._extract_table_data_from_pages(pages)
    table_data2 = "표 데이터 없음"  # 단일 상품이므로
    
    # 텍스트 스마트 절단
    smart_text1 = summarizer._smart_truncate_text(combined_text, max_input_tokens=40000)
    
    # 프롬프트 생성
    prompt = f"""
아래에는 보험 상품의 보장 내역이 있습니다.
이 상품을 고객의 입장에서 쉽게 분석할 수 있도록 정리해 주세요.

**📊 표 데이터 (정확한 수치 비교용)**:
상품 표 데이터: {table_data1}

**상품**: 한화 시그니처 여성 건강보험3.0
페이지 수: {len(pages)}
추출된 텍스트:
{smart_text1}
"""
    
    print(f"📝 GPT 프롬프트 길이: {len(prompt)} 자")
    print(f"📊 표 데이터 포함: {'예' if table_data1 != '표 데이터 없음' else '아니오'}")
    
    # 6. 해약환급금 관련 부분 하이라이트
    print("\n6. 해약환급금 관련 부분 하이라이트:")
    if '해약환급금' in combined_text:
        print("✅ 해약환급금 키워드가 GPT 텍스트에 포함됨")
        
        # 해약환급금 관련 부분 추출
        surrender_start = combined_text.find('해약환급금')
        surrender_section = combined_text[surrender_start:surrender_start+1000]
        print(f"📋 해약환급금 관련 텍스트 샘플:")
        print(f"   {surrender_section[:500]}...")
    else:
        print("❌ 해약환급금 키워드가 GPT 텍스트에 포함되지 않음")
    
    print("\n" + "=" * 50)
    print("🔍 디버깅 완료")

if __name__ == "__main__":
    debug_gpt_input()
