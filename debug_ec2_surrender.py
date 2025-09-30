#!/usr/bin/env python3
"""
EC2에서 해약환급금 표 인식 디버깅 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_ec2_surrender():
    """EC2에서 해약환급금 표 인식 디버깅"""
    
    print("🔍 EC2 해약환급금 표 인식 디버깅 시작")
    print("=" * 50)
    
    # 1. 모듈 import 테스트
    print("1. 모듈 import 테스트:")
    try:
        from parsing.pdf_text import PDFTextExtractor
        print("✅ PDFTextExtractor import 성공")
    except Exception as e:
        print(f"❌ PDFTextExtractor import 실패: {e}")
        return
    
    try:
        from parsing.table_parser import TableParser
        print("✅ TableParser import 성공")
    except Exception as e:
        print(f"❌ TableParser import 실패: {e}")
        return
    
    try:
        from llm.gpt_summarizer import GPTSummarizer
        print("✅ GPTSummarizer import 성공")
    except Exception as e:
        print(f"❌ GPTSummarizer import 실패: {e}")
        return
    
    # 2. 테스트 URL
    test_url = "http://goodrichplus.kr/gvKNg"
    print(f"\n2. PDF 텍스트 추출 테스트: {test_url}")
    
    try:
        extractor = PDFTextExtractor()
        success, pages = extractor.extract_text_from_url(test_url)
        
        if not success:
            print("❌ PDF 텍스트 추출 실패")
            return
        
        print(f"✅ PDF 텍스트 추출 성공: {len(pages)} 페이지")
        
        # 3. 9페이지 해약환급금 표 테스트
        page_9 = pages[8]  # 9페이지 (인덱스 8)
        text_9 = page_9.get('text', '')
        
        print(f"\n3. 9페이지 해약환급금 표 테스트:")
        print(f"텍스트 길이: {len(text_9)}")
        
        # 해약환급금 키워드 확인
        surrender_keywords = ['해약환급금', '환급금', '경과기간', '납입보험료']
        found_keywords = [kw for kw in surrender_keywords if kw in text_9]
        print(f"발견된 키워드: {found_keywords}")
        
        if '해약환급금' in text_9:
            print("✅ 해약환급금 키워드 발견")
        else:
            print("❌ 해약환급금 키워드 없음")
            return
        
        # 4. 표 파서 테스트
        print(f"\n4. 표 파서 테스트:")
        try:
            parser = TableParser()
            table_data = parser.parse_surrender_value_table(text_9)
            
            if table_data:
                print(f"✅ 표 파싱 성공: {len(table_data)}개 항목")
                
                # 데이터 행만 필터링
                data_rows = [item for item in table_data if item.get('type') == 'data']
                print(f"데이터 행: {len(data_rows)}개")
                
                for i, item in enumerate(data_rows[:3]):  # 처음 3개만
                    columns = item.get('columns', [])
                    if len(columns) >= 6:
                        print(f"  {i+1}. {columns[0]}: {columns[4]}원 ({columns[5]})")
            else:
                print("❌ 표 파싱 실패: 데이터 없음")
                
        except Exception as e:
            print(f"❌ 표 파서 테스트 실패: {e}")
            return
        
        # 5. GPT Summarizer 테스트
        print(f"\n5. GPT Summarizer 테스트:")
        try:
            # API 키 없이도 표 데이터 추출은 가능
            summarizer = GPTSummarizer.__new__(GPTSummarizer)
            table_data_str = summarizer._extract_table_data_from_pages(pages)
            
            if "표 데이터 없음" in table_data_str:
                print("❌ GPT Summarizer에서 표 데이터 추출 실패")
            else:
                print("✅ GPT Summarizer에서 표 데이터 추출 성공")
                print(f"표 데이터 길이: {len(table_data_str)}")
                
        except Exception as e:
            print(f"❌ GPT Summarizer 테스트 실패: {e}")
    
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ec2_surrender()
