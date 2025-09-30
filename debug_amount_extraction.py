#!/usr/bin/env python3
"""
금액 추출 로직 디버깅 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsing.pdf_text import PDFTextExtractor

def debug_amount_extraction():
    """금액 추출 로직 디버깅"""
    
    # 테스트 URL
    test_url = "http://goodrichplus.kr/gvKNg"
    
    print("🔍 금액 추출 로직 디버깅 시작")
    print("=" * 50)
    
    # PDF 텍스트 추출
    extractor = PDFTextExtractor()
    success, pages = extractor.extract_text_from_url(test_url)
    
    if not success:
        print("❌ PDF 텍스트 추출 실패")
        return
    
    print(f"✅ PDF 텍스트 추출 성공: {len(pages)} 페이지")
    
    # 9페이지 (해약환급금 표) 상세 분석
    page_9 = pages[8]  # 9페이지 (인덱스 8)
    print(f"\n📊 9페이지 상세 분석:")
    print(f"텍스트 길이: {len(page_9.get('text', ''))}")
    print(f"표 데이터 개수: {len(page_9.get('table_data', []))}")
    
    # 9페이지 텍스트에서 금액 패턴 찾기
    text_9 = page_9.get('text', '')
    print(f"\n📝 9페이지 텍스트 샘플:")
    print(text_9[:1000])
    
    # 금액 패턴 테스트
    import re
    
    print(f"\n🔍 금액 패턴 테스트:")
    
    # 기존 패턴들
    patterns = [
        r'([0-9,]+원)',      # 85,804원
        r'([0-9]+원)',       # 85804원
        r'([0-9,]+천원)',    # 1,000천원
        r'([0-9,]+만원)',    # 1,000만원
        r'([0-9.]+억원)'     # 1.5억원
    ]
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, text_9)
        print(f"  패턴 {i+1} ({pattern}): {len(matches)}개 발견")
        if matches:
            print(f"    예시: {matches[:5]}")
    
    # 표 데이터에서 금액 추출 테스트
    print(f"\n📋 표 데이터 금액 추출 테스트:")
    table_data = page_9.get('table_data', [])
    
    for i, item in enumerate(table_data[:10]):  # 처음 10개만
        text_raw = item.get('text_raw', '')
        amount_raw = item.get('amount_raw', '')
        amount_norm = item.get('amount_norm_krw', 0)
        
        print(f"  {i+1}. '{text_raw}' -> amount_raw: '{amount_raw}', amount_norm: {amount_norm}")
        
        # 수동으로 금액 추출 테스트
        manual_amounts = re.findall(r'([0-9,]+원)', text_raw)
        if manual_amounts:
            print(f"     수동 추출: {manual_amounts}")
    
    # 해약환급금 표 특정 부분 찾기
    print(f"\n🎯 해약환급금 표 특정 부분:")
    surrender_lines = []
    for line in text_9.split('\n'):
        if any(keyword in line for keyword in ['해약환급금', '경과기간', '납입보험료', '환급금']):
            surrender_lines.append(line.strip())
    
    print(f"해약환급금 관련 라인 {len(surrender_lines)}개:")
    for line in surrender_lines[:10]:  # 처음 10개만
        print(f"  '{line}'")
        
        # 각 라인에서 금액 추출
        amounts = re.findall(r'([0-9,]+원)', line)
        if amounts:
            print(f"    -> 금액 발견: {amounts}")

if __name__ == "__main__":
    debug_amount_extraction()
