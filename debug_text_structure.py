#!/usr/bin/env python3
"""
텍스트 구조 디버깅 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsing.pdf_text import PDFTextExtractor

def debug_text_structure():
    """텍스트 구조 디버깅"""
    
    # 테스트 URL
    test_url = "http://goodrichplus.kr/gvKNg"
    
    print("🔍 텍스트 구조 디버깅")
    print("=" * 50)
    
    # PDF 텍스트 추출
    extractor = PDFTextExtractor()
    success, pages = extractor.extract_text_from_url(test_url)
    
    if not success:
        print("❌ PDF 텍스트 추출 실패")
        return
    
    # 9페이지 텍스트 분석
    page_9 = pages[8]  # 9페이지 (인덱스 8)
    text_9 = page_9.get('text', '')
    
    print(f"📊 9페이지 전체 텍스트:")
    print(text_9)
    print("\n" + "="*50)
    
    # 해약환급금 관련 라인 찾기
    lines = text_9.split('\n')
    print(f"📝 전체 라인 수: {len(lines)}")
    
    print(f"\n🔍 해약환급금 관련 라인들:")
    for i, line in enumerate(lines):
        line = line.strip()
        if any(keyword in line for keyword in ['해약환급금', '환급금', '경과기간', '납입보험료', '적립부분', '보장부분']):
            print(f"  라인 {i+1}: '{line}'")
    
    print(f"\n🎯 표 헤더 찾기:")
    for i, line in enumerate(lines):
        line = line.strip()
        if '경과기간' in line and '납입보험료' in line:
            print(f"  헤더 라인 {i+1}: '{line}'")
            print(f"  컬럼들: {line.split()}")
    
    print(f"\n📊 데이터 행 찾기:")
    for i, line in enumerate(lines):
        line = line.strip()
        if re.match(r'^\d+년', line) or re.match(r'^만기', line):
            print(f"  데이터 라인 {i+1}: '{line}'")
            print(f"  컬럼들: {line.split()}")

if __name__ == "__main__":
    import re
    debug_text_structure()
