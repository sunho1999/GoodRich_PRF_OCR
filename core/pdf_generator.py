"""
PDF 보고서 생성 모듈
분석 결과를 UI/UX가 개선된 PDF 파일로 생성합니다.
ReportLab을 사용하여 한글을 지원하는 PDF를 생성합니다.
"""

from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Frame, PageTemplate, KeepTogether
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.doctemplate import BaseDocTemplate
from datetime import datetime
import os
import re
from typing import Dict, Any, Optional, List
from io import BytesIO


class PDFReportGenerator:
    """PDF 보고서 생성 클래스"""
    
    def __init__(self):
        """PDF 생성기 초기화"""
        self._setup_fonts()
        self._setup_styles()
        
    def _setup_fonts(self):
        """한글 폰트 설정"""
        # 시스템 기본 한글 폰트 사용
        font_paths = [
            # macOS 폰트들
            '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
            '/System/Library/Fonts/Supplemental/AppleMyungjo.ttf',
            '/System/Library/Fonts/AppleSDGothicNeo.ttc',
            # Linux 폰트들
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
            '/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf',
            # Windows 폰트들
            'C:\\Windows\\Fonts\\malgun.ttf',
            'C:\\Windows\\Fonts\\batang.ttf',
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # TTF 파일인 경우 직접 등록
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    self.korean_font = 'Korean'
                    print(f"✅ 폰트 로드 성공: {font_path}")
                    return
                except Exception as e:
                    print(f"⚠️ 폰트 로드 실패: {font_path} - {e}")
                    continue
        
        # 폰트를 찾지 못한 경우 경고
        print("⚠️ 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
        self.korean_font = 'Helvetica'
    
    def _setup_styles(self):
        """스타일 설정"""
        self.styles = getSampleStyleSheet()
        
        # 제목 스타일
        self.styles.add(ParagraphStyle(
            name='KoreanTitle',
            parent=self.styles['Heading1'],
            fontName=self.korean_font,
            fontSize=24,
            leading=30,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # 부제목 스타일
        self.styles.add(ParagraphStyle(
            name='KoreanSubtitle',
            parent=self.styles['Heading2'],
            fontName=self.korean_font,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#666666'),
            spaceAfter=24,
            alignment=TA_CENTER
        ))
        
        # 섹션 헤딩 스타일
        self.styles.add(ParagraphStyle(
            name='KoreanHeading1',
            parent=self.styles['Heading1'],
            fontName=self.korean_font,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#2d3748'),
            spaceBefore=12,
            spaceAfter=8,
            borderColor=colors.HexColor('#667eea'),
            borderWidth=0,
            borderPadding=0
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanHeading2',
            parent=self.styles['Heading2'],
            fontName=self.korean_font,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#667eea'),
            spaceBefore=10,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='KoreanHeading3',
            parent=self.styles['Heading3'],
            fontName=self.korean_font,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#764ba2'),
            spaceBefore=8,
            spaceAfter=4
        ))
        
        # 본문 스타일
        self.styles.add(ParagraphStyle(
            name='KoreanBody',
            parent=self.styles['BodyText'],
            fontName=self.korean_font,
            fontSize=10,
            leading=16,
            textColor=colors.HexColor('#333333'),
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # 정보 박스 스타일
        self.styles.add(ParagraphStyle(
            name='InfoBox',
            parent=self.styles['BodyText'],
            fontName=self.korean_font,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor('#2c3e50'),
            leftIndent=10,
            rightIndent=10,
            spaceAfter=12
        ))
        
        # 경고 박스 스타일
        self.styles.add(ParagraphStyle(
            name='WarningBox',
            parent=self.styles['BodyText'],
            fontName=self.korean_font,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor('#e74c3c'),
            leftIndent=10,
            rightIndent=10,
            spaceAfter=12
        ))
        
        # 배지 스타일
        self.styles.add(ParagraphStyle(
            name='Badge',
            parent=self.styles['Normal'],
            fontName=self.korean_font,
            fontSize=11,
            leading=14,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
    
    def generate_analysis_pdf(
        self, 
        product_name: str, 
        analysis_content: str,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        개별 상품 분석 PDF 생성
        
        Args:
            product_name: 상품명
            analysis_content: 분석 내용 (마크다운 형식)
            output_path: 저장 경로 (None이면 바이트로 반환)
            
        Returns:
            PDF 바이트 데이터
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # 문서 요소 리스트
        story = []
        
        # 헤더
        story.append(Paragraph("🛡️ 보험상품 분석 보고서", self.styles['KoreanTitle']))
        story.append(Spacer(1, 6*mm))
        
        # 날짜 정보
        current_date = datetime.now().strftime('%Y년 %m월 %d일')
        story.append(Paragraph(f"생성일: {current_date} | 분석 AI: GPT-4o-mini", self.styles['KoreanSubtitle']))
        story.append(Spacer(1, 10*mm))
        
        # 상품명 표지
        story.append(Paragraph(product_name, self.styles['KoreanTitle']))
        story.append(Paragraph("상품 상세 분석", self.styles['KoreanSubtitle']))
        story.append(Spacer(1, 15*mm))
        
        # 본문 내용 파싱
        story.extend(self._parse_markdown_to_elements(analysis_content))
        
        # 푸터
        story.append(Spacer(1, 10*mm))
        footer_text = """
        <para align="center">
        본 분석 보고서는 AI를 활용하여 자동 생성되었습니다.<br/>
        투자 및 보험 가입 시 반드시 전문가와 상담하시기 바랍니다.
        </para>
        """
        story.append(Paragraph(footer_text, self.styles['InfoBox']))
        
        # PDF 빌드
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_comparison_pdf(
        self,
        product1_name: str,
        product2_name: str,
        comparison_content: str,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        비교 분석 PDF 생성 (좌우 비교 레이아웃)
        
        Args:
            product1_name: 첫 번째 상품명
            product2_name: 두 번째 상품명
            comparison_content: 비교 분석 내용 (마크다운 형식)
            output_path: 저장 경로 (None이면 바이트로 반환)
            
        Returns:
            PDF 바이트 데이터
        """
        buffer = BytesIO()
        
        # 가로 모드 A4 사용
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        # 문서 요소 리스트
        story = []
        
        # 헤더
        story.append(Paragraph("📊 보험상품 비교 분석 보고서", self.styles['KoreanTitle']))
        story.append(Spacer(1, 3*mm))
        
        # 날짜 정보
        current_date = datetime.now().strftime('%Y년 %m월 %d일')
        story.append(Paragraph(f"생성일: {current_date} | 분석 AI: GPT-4o-mini", self.styles['KoreanSubtitle']))
        story.append(Spacer(1, 8*mm))
        
        # 비교 분석 내용을 파싱하여 구조화
        sections = self._parse_comparison_content(comparison_content)
        
        # 상품명 헤더 테이블
        header_data = [
            [
                Paragraph(f'<para align="center"><b><font color="white" size="12">상품 A</font></b><br/><font color="white" size="10">{product1_name}</font></para>', self.styles['KoreanBody']),
                Paragraph(f'<para align="center"><b><font color="white" size="12">상품 B</font></b><br/><font color="white" size="10">{product2_name}</font></para>', self.styles['KoreanBody'])
            ]
        ]
        
        header_table = Table(header_data, colWidths=[100*mm, 100*mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#667eea')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f093fb')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 5*mm))
        
        # 섹션별 좌우 비교 테이블 생성
        for section_title, product1_content, product2_content in sections:
            # 섹션 제목
            if section_title:
                story.append(Paragraph(section_title, self.styles['KoreanHeading2']))
                story.append(Spacer(1, 2*mm))
            
            # 좌우 비교 테이블
            comparison_data = [[
                self._create_product_cell(product1_content, colors.HexColor('#e8f4fd')),
                self._create_product_cell(product2_content, colors.HexColor('#fef5e7'))
            ]]
            
            comparison_table = Table(comparison_data, colWidths=[100*mm, 100*mm])
            comparison_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f7fafc')),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fffbf0')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#e2e8f0')),
            ]))
            
            # 테이블이 너무 크면 페이지 분할
            story.append(KeepTogether([comparison_table]))
            story.append(Spacer(1, 4*mm))
        
        # 푸터
        story.append(Spacer(1, 5*mm))
        footer_text = """
        <para align="center">
        <font size="8">본 분석 보고서는 AI를 활용하여 자동 생성되었습니다. 투자 및 보험 가입 시 반드시 전문가와 상담하시기 바랍니다.</font>
        </para>
        """
        story.append(Paragraph(footer_text, self.styles['InfoBox']))
        
        # PDF 빌드
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def _parse_comparison_content(self, content: str) -> List[tuple]:
        """
        비교 분석 내용을 파싱하여 섹션별로 나눔
        
        Returns:
            List of (section_title, product1_content, product2_content)
        """
        sections = []
        lines = content.split('\n')
        
        current_section = None
        product1_lines = []
        product2_lines = []
        in_product_section = False
        
        for line in lines:
            line = line.strip()
            
            # 주요 섹션 헤더 (##로 시작)
            if line.startswith('## '):
                # 이전 섹션 저장
                if current_section and (product1_lines or product2_lines):
                    sections.append((
                        current_section,
                        '\n'.join(product1_lines),
                        '\n'.join(product2_lines)
                    ))
                
                # 새 섹션 시작
                current_section = line[3:].strip()
                product1_lines = []
                product2_lines = []
                in_product_section = False
                
            # 상품별 서브섹션 (### 상품 A, ### 상품 B)
            elif line.startswith('### 상품 A'):
                in_product_section = 'A'
            elif line.startswith('### 상품 B'):
                in_product_section = 'B'
            elif line.startswith('###'):
                # 다른 서브섹션은 양쪽에 모두 추가
                product1_lines.append(line)
                product2_lines.append(line)
                in_product_section = False
            # 내용 추가
            elif line:
                if in_product_section == 'A':
                    product1_lines.append(line)
                elif in_product_section == 'B':
                    product2_lines.append(line)
                else:
                    # 상품 A/B 정보가 포함된 라인인지 확인
                    if '상품 A:' in line and '상품 B:' not in line:
                        product1_lines.append(line)
                    elif '상품 B:' in line and '상품 A:' not in line:
                        product2_lines.append(line)
                    elif '상품 A:' in line and '상품 B:' in line:
                        # 양쪽에 모두 있는 경우 분리
                        parts = line.split('상품 B:')
                        if len(parts) == 2:
                            product1_part = parts[0] + '상품 A:'
                            product2_part = '상품 B:' + parts[1]
                            product1_lines.append(product1_part)
                            product2_lines.append(product2_part)
                        else:
                            product1_lines.append(line)
                            product2_lines.append(line)
                    else:
                        # 일반 내용은 양쪽에 추가
                        product1_lines.append(line)
                        product2_lines.append(line)
        
        # 마지막 섹션 저장
        if current_section and (product1_lines or product2_lines):
            sections.append((
                current_section,
                '\n'.join(product1_lines),
                '\n'.join(product2_lines)
            ))
        
        return sections
    
    def _is_comparison_structure(self, lines: List[str], current_line: str) -> bool:
        """비교 구조인지 확인 (### 항목 + 상품 A/B 정보)"""
        current_idx = lines.index(current_line)
        
        # 다음 몇 줄을 확인
        for i in range(1, 6):
            if current_idx + i < len(lines):
                next_line = lines[current_idx + i].strip()
                if ('상품 A:' in next_line or '상품 B:' in next_line or '우위:' in next_line):
                    return True
        
        return False
    
    def _extract_comparison_data(self, lines: List[str], start_line: str) -> dict:
        """비교 데이터 추출"""
        start_idx = lines.index(start_line)
        product_a_info = []
        product_b_info = []
        
        # 다음 10줄 정도를 확인
        for i in range(1, 15):
            if start_idx + i < len(lines):
                line = lines[start_idx + i].strip()
                
                if line.startswith('### ') or line.startswith('## '):
                    # 다음 섹션 시작, 종료
                    break
                elif line.startswith('• 상품 A:'):
                    product_a_info.append(line[2:])  # • 제거
                elif line.startswith('• 상품 B:'):
                    product_b_info.append(line[2:])  # • 제거
                elif line.startswith('• 우위:'):
                    # 우위 정보는 양쪽에 추가
                    product_a_info.append(line[2:])
                    product_b_info.append(line[2:])
                elif line.startswith('**'):
                    # 일반 설명은 양쪽에 추가
                    product_a_info.append(line)
                    product_b_info.append(line)
        
        return {
            'product_a': '\n'.join(product_a_info) if product_a_info else '',
            'product_b': '\n'.join(product_b_info) if product_b_info else ''
        }
    
    def _create_product_cell(self, content: str, bg_color):
        """상품 셀 내용 생성 - 구조화된 비교 데이터를 테이블로 변환"""
        if not content.strip():
            return Paragraph("", self.styles['KoreanBody'])
        
        lines = content.split('\n')
        
        # 마크다운 테이블이 있는지 확인
        table_lines = []
        text_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 마크다운 테이블 라인
            if '|' in line and not line.startswith('|--'):
                table_lines.append(line)
            elif line.startswith('|--'):
                continue  # 구분선 무시
            else:
                text_lines.append(line)
        
        # 마크다운 테이블이 있으면 테이블 반환
        if table_lines:
            return self._create_mini_table(table_lines)
        
        # 비교 항목 구조 감지 (### 헤더 + 상품 A/B 항목)
        comparison_items = self._detect_comparison_structure(text_lines)
        if comparison_items:
            return self._create_comparison_table(comparison_items)
        
        # 일반 텍스트 포맷팅
        formatted_lines = []
        for line in text_lines:
            if line.startswith('### '):
                formatted_lines.append(f'<b>{self._format_text(line[4:])}</b>')
            elif line.startswith('- ') or line.startswith('• '):
                formatted_lines.append(f'• {self._format_text(line[2:])}')
            elif line.startswith('**'):
                formatted_lines.append(self._format_text(line))
            else:
                formatted_lines.append(self._format_text(line))
        
        html_content = '<br/>'.join(formatted_lines)
        return Paragraph(html_content, self.styles['KoreanBody'])
    
    def _detect_comparison_structure(self, lines: List[str]) -> List[dict]:
        """
        비교 항목 구조 감지 - 통합 테이블용
        예: ### 암 진단 보장
            • 상품 A: 4,000만원
            • 상품 B: 3,000만원
            • 우위: 상품 A
        """
        items = []
        current_item = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 섹션 헤더
            if line.startswith('### '):
                if current_item:
                    items.append(current_item)
                current_item = {
                    'title': line[4:].strip(),
                    'product_a': '',
                    'product_b': '',
                    'note': ''
                }
            # 상품 A 정보
            elif ('상품 A:' in line or '상품 A가' in line) and current_item:
                # "• 상품 A: 값" 형식에서 값 추출
                if '상품 A:' in line:
                    value = line.split('상품 A:', 1)[1].strip()
                    current_item['product_a'] = value.lstrip('• ').strip()
                else:
                    current_item['product_a'] = line.lstrip('• -').strip()
            # 상품 B 정보
            elif ('상품 B:' in line or '상품 B가' in line) and current_item:
                if '상품 B:' in line:
                    value = line.split('상품 B:', 1)[1].strip()
                    current_item['product_b'] = value.lstrip('• ').strip()
                else:
                    current_item['product_b'] = line.lstrip('• -').strip()
            # 우위/차이/비고 정보
            elif ('우위:' in line or '차이:' in line or '💡' in line or '⚠️' in line) and current_item:
                current_item['note'] = line.lstrip('• -').strip()
        
        # 마지막 아이템 추가
        if current_item:
            items.append(current_item)
        
        return items if len(items) > 0 else None
    
    def _create_comparison_table(self, items: List[dict]) -> Table:
        """통합 비교 테이블 생성 - 공통 항목 기준으로 상품 A/B 비교"""
        table_data = []
        
        # 헤더 (4열: 항목, 상품 A, 상품 B, 우위)
        table_data.append([
            Paragraph('<b>항목</b>', self.styles['KoreanBody']),
            Paragraph('<b>상품 A</b>', self.styles['KoreanBody']),
            Paragraph('<b>상품 B</b>', self.styles['KoreanBody']),
            Paragraph('<b>우위</b>', self.styles['KoreanBody'])
        ])
        
        for item in items:
            # 항목명
            title_text = f"<b>{self._format_text(item['title'])}</b>"
            
            # 상품 A 내용
            product_a_text = self._format_text(item['product_a']) if item['product_a'] else '-'
            
            # 상품 B 내용
            product_b_text = self._format_text(item['product_b']) if item['product_b'] else '-'
            
            # 우위 정보
            note_text = self._format_text(item['note']) if item['note'] else '-'
            
            table_data.append([
                Paragraph(title_text, self.styles['KoreanBody']),
                Paragraph(product_a_text, self.styles['KoreanBody']),
                Paragraph(product_b_text, self.styles['KoreanBody']),
                Paragraph(note_text, self.styles['KoreanBody'])
            ])
        
        # 테이블 생성 (4열로 조정)
        comparison_table = Table(table_data, colWidths=[25*mm, 30*mm, 30*mm, 20*mm])
        
        # 스타일 적용
        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 7),  # 폰트 크기 줄임
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#e8f4fd')),  # 상품 A 헤더
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#fef5e7')),  # 상품 B 헤더
            ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#f0f9ff')),  # 우위 헤더
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]
        
        comparison_table.setStyle(TableStyle(style_commands))
        return comparison_table
    
    def _create_mini_table(self, table_lines: List[str]) -> Table:
        """미니 테이블 생성 (셀 안에 들어가는 작은 테이블)"""
        table_data = []
        
        for line in table_lines:
            # 파이프로 구분하여 셀 추출
            cells = [cell.strip() for cell in line.split('|')]
            cells = [c for c in cells if c]  # 빈 셀 제거
            
            if cells:
                # 각 셀을 Paragraph로 변환
                formatted_cells = []
                for cell in cells:
                    # 첫 번째 행은 헤더로 처리
                    if not table_data:
                        formatted_cells.append(Paragraph(f'<b>{self._format_text(cell)}</b>', self.styles['KoreanBody']))
                    else:
                        formatted_cells.append(Paragraph(self._format_text(cell), self.styles['KoreanBody']))
                table_data.append(formatted_cells)
        
        if not table_data:
            return Paragraph("", self.styles['KoreanBody'])
        
        # 테이블 생성
        mini_table = Table(table_data)
        
        # 스타일 적용
        style_commands = [
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]
        
        mini_table.setStyle(TableStyle(style_commands))
        return mini_table
    
    def _parse_markdown_to_elements(self, markdown_text: str):
        """마크다운 텍스트를 PDF 요소로 변환"""
        elements = []
        lines = markdown_text.split('\n')
        
        in_table = False
        table_data = []
        in_list = False
        list_items = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if in_list:
                    # 리스트 종료
                    for item in list_items:
                        elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                    list_items = []
                    in_list = False
                    elements.append(Spacer(1, 3*mm))
                continue
            
            # 헤딩 처리
            if line.startswith('#### '):
                if in_list:
                    for item in list_items:
                        elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                    list_items = []
                    in_list = False
                elements.append(Spacer(1, 2*mm))
                elements.append(Paragraph(line[5:], self.styles['KoreanHeading3']))
            elif line.startswith('### '):
                if in_list:
                    for item in list_items:
                        elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                    list_items = []
                    in_list = False
                elements.append(Spacer(1, 3*mm))
                elements.append(Paragraph(line[4:], self.styles['KoreanHeading2']))
            elif line.startswith('## '):
                if in_list:
                    for item in list_items:
                        elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                    list_items = []
                    in_list = False
                elements.append(Spacer(1, 4*mm))
                elements.append(Paragraph(line[3:], self.styles['KoreanHeading1']))
            elif line.startswith('# '):
                if in_list:
                    for item in list_items:
                        elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                    list_items = []
                    in_list = False
                elements.append(Spacer(1, 5*mm))
                elements.append(Paragraph(line[2:], self.styles['KoreanHeading1']))
            # 테이블 처리
            elif '|' in line and not line.startswith('|--'):
                cells = [cell.strip() for cell in line.split('|')]
                cells = [c for c in cells if c]  # 빈 셀 제거
                
                if cells:
                    if not in_table:
                        in_table = True
                        table_data = []
                    table_data.append(cells)
            else:
                # 테이블 종료
                if in_table and table_data:
                    elements.append(self._create_table(table_data))
                    elements.append(Spacer(1, 3*mm))
                    table_data = []
                    in_table = False
                
                # 리스트 처리
                if line.startswith('- ') or line.startswith('* '):
                    in_list = True
                    list_items.append(self._format_text(line[2:]))
                elif re.match(r'^\d+\.\s', line):
                    in_list = True
                    content = re.sub(r'^\d+\.\s', '', line)
                    list_items.append(self._format_text(content))
                # 특수 박스 처리
                elif line.startswith('💡') or line.startswith('✅'):
                    if in_list:
                        for item in list_items:
                            elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                        list_items = []
                        in_list = False
                    elements.append(Paragraph(self._format_text(line), self.styles['InfoBox']))
                elif line.startswith('⚠️') or line.startswith('❌'):
                    if in_list:
                        for item in list_items:
                            elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                        list_items = []
                        in_list = False
                    elements.append(Paragraph(self._format_text(line), self.styles['WarningBox']))
                # 일반 텍스트
                else:
                    if in_list:
                        for item in list_items:
                            elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
                        list_items = []
                        in_list = False
                    elements.append(Paragraph(self._format_text(line), self.styles['KoreanBody']))
        
        # 남은 리스트 항목 처리
        if in_list and list_items:
            for item in list_items:
                elements.append(Paragraph(f"• {item}", self.styles['KoreanBody']))
        
        # 남은 테이블 처리
        if in_table and table_data:
            elements.append(self._create_table(table_data))
        
        return elements
    
    def _format_text(self, text: str) -> str:
        """텍스트 포맷팅 (볼드, 이탤릭 등)"""
        # ** 볼드 처리
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        return text
    
    def _create_table(self, data):
        """테이블 생성"""
        if not data:
            return Spacer(1, 0)
        
        # 테이블 스타일
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
        ])
        
        table = Table(data, repeatRows=1)
        table.setStyle(style)
        
        return table
