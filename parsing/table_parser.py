#!/usr/bin/env python3
"""
표 구조 파싱을 위한 전용 모듈
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TableParser:
    """표 구조 파싱 전용 클래스"""
    
    def __init__(self):
        self.surrender_keywords = ['해약환급금', '환급금', '경과기간', '납입보험료', '적립부분', '보장부분']
    
    def parse_surrender_value_table(self, text: str) -> List[Dict[str, Any]]:
        """해약환급금 표 파싱"""
        try:
            # 해약환급금 표 섹션 추출
            surrender_section = self._extract_surrender_section(text)
            if not surrender_section:
                return []
            
            # 표 데이터 파싱
            table_data = self._parse_table_data(surrender_section)
            return table_data
            
        except Exception as e:
            logger.error(f"해약환급금 표 파싱 실패: {e}")
            return []
    
    def _extract_surrender_section(self, text: str) -> str:
        """해약환급금 관련 섹션 추출"""
        lines = text.split('\n')
        surrender_lines = []
        in_surrender_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 해약환급금 섹션 시작 감지
            if any(keyword in line for keyword in ['해약환급금 예시', '경과기간']):
                in_surrender_section = True
            
            # 해약환급금 섹션 종료 감지
            if in_surrender_section and line.startswith('해약환급금') and '①' in line:
                break
            
            if in_surrender_section:
                surrender_lines.append(line)
        
        return '\n'.join(surrender_lines)
    
    def _parse_table_data(self, section_text: str) -> List[Dict[str, Any]]:
        """표 데이터 파싱 (라인 기반)"""
        table_data = []
        lines = section_text.split('\n')
        
        # 헤더 라인들 찾기
        header_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if any(keyword in line for keyword in ['경과기간', '납입보험료', '적립부분환급금', '보장부분환급금', '환급금(합계)', '환급률']):
                header_lines.append((i, line))
        
        if not header_lines:
            return []
        
        # 헤더 정보 저장
        headers = [line for _, line in header_lines]
        table_data.append({
            "type": "header",
            "columns": headers,
            "row": 0
        })
        
        # 데이터 행 파싱 (라인 그룹으로)
        data_started = False
        current_row = []
        row_count = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 데이터 행 시작 감지
            if re.match(r'^\d+년', line) or re.match(r'^만기', line):
                if current_row:  # 이전 행이 있으면 저장
                    table_data.append({
                        "type": "data",
                        "columns": current_row,
                        "row": row_count,
                        "amounts": self._extract_amounts_from_columns(current_row)
                    })
                    row_count += 1
                
                current_row = [line]
                data_started = True
            elif data_started and (re.match(r'^\d+[,]', line) or re.match(r'^\d+\.\d+%', line) or line == '0'):
                # 숫자 데이터 라인
                current_row.append(line)
            elif data_started and not (re.match(r'^\d+[,]', line) or re.match(r'^\d+\.\d+%', line) or line == '0'):
                # 데이터 섹션 종료
                if current_row:
                    table_data.append({
                        "type": "data",
                        "columns": current_row,
                        "row": row_count,
                        "amounts": self._extract_amounts_from_columns(current_row)
                    })
                break
        
        return table_data
    
    def _parse_line_columns(self, line: str) -> List[str]:
        """라인을 컬럼으로 분리"""
        # 탭이나 공백으로 분리 시도
        columns = []
        
        # 먼저 탭으로 분리 시도
        if '\t' in line:
            columns = [col.strip() for col in line.split('\t') if col.strip()]
        else:
            # 공백으로 분리 (연속된 공백은 하나로 처리)
            columns = [col.strip() for col in re.split(r'\s{2,}', line) if col.strip()]
        
        return columns
    
    def _extract_amounts_from_columns(self, columns: List[str]) -> List[Dict[str, Any]]:
        """컬럼에서 금액 추출"""
        amounts = []
        
        for i, col in enumerate(columns):
            # 금액 패턴 매칭
            amount_patterns = [
                (r'([0-9,]+원)', 1),      # 85,804원
                (r'([0-9,]+)', 1),        # 1,029,648 (원 없음)
                (r'([0-9.]+%)', 1),       # 29.8%
            ]
            
            for pattern, multiplier in amount_patterns:
                match = re.search(pattern, col)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        if '%' in amount_str:
                            amount_value = float(amount_str.replace('%', ''))
                        else:
                            amount_value = float(amount_str)
                        
                        amounts.append({
                            "column": i,
                            "text": col,
                            "amount_raw": match.group(1),
                            "amount_norm": int(amount_value * multiplier),
                            "type": "percentage" if '%' in amount_str else "currency"
                        })
                        break
                    except:
                        continue
        
        return amounts

def test_table_parser():
    """표 파서 테스트"""
    parser = TableParser()
    
    # 테스트 텍스트
    test_text = """
경과기간    납입보험료    적립부분환급금    보장부분환급금    환급금(합계)    환급률
1년(37세)   1,029,648    0                0                0              0.0%
2년(38세)   2,059,296    0                0                0              0.0%
20년(56세)  20,592,960   0                6,149,393        6,149,393      29.8%
"""
    
    result = parser.parse_surrender_value_table(test_text)
    print("표 파싱 결과:")
    for item in result:
        print(f"  {item}")

if __name__ == "__main__":
    test_table_parser()
