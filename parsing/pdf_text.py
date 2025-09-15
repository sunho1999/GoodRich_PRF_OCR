import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
from typing import List, Dict, Any, Tuple
import re
try:
    from core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class PDFTextExtractor:
    def __init__(self):
        self.lap_params = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
            detect_vertical=True
        )
    
    def extract_text_from_pdf(self, file_path: str, use_ocr: bool = True) -> Tuple[bool, List[Dict[str, Any]]]:
        """Extract text from PDF using multiple methods with OCR support"""
        try:
            pages = []
            extraction_success = False
            
            # Step 1: Try PyMuPDF first (fast and accurate for text-based PDFs)
            try:
                pages = self._extract_with_pymupdf(file_path)
                if pages and any(page.get('text', '').strip() for page in pages):
                    logger.info(f"Successfully extracted text using PyMuPDF from {file_path}")
                    extraction_success = True
                else:
                    logger.warning(f"PyMuPDF extracted no meaningful text from {file_path}")
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed for {file_path}: {e}")
            
            # Step 2: Fallback to pdfminer if PyMuPDF failed
            if not extraction_success:
                try:
                    pages = self._extract_with_pdfminer(file_path)
                    if pages and any(page.get('text', '').strip() for page in pages):
                        logger.info(f"Successfully extracted text using pdfminer from {file_path}")
                        extraction_success = True
                    else:
                        logger.warning(f"pdfminer extracted no meaningful text from {file_path}")
                except Exception as e:
                    logger.warning(f"pdfminer extraction failed for {file_path}: {e}")
            
            # Step 3: Apply OCR to enhance extraction or handle image-based PDFs
            if use_ocr:
                try:
                    enhanced_pages = self._apply_ocr_enhancement(file_path, pages)
                    if enhanced_pages:
                        pages = enhanced_pages
                        extraction_success = True
                        logger.info(f"Successfully enhanced text extraction with OCR for {file_path}")
                except Exception as e:
                    logger.warning(f"OCR enhancement failed for {file_path}: {e}")
            
            # If everything failed, create empty pages structure
            if not pages:
                pages = self._create_empty_pages(file_path)
            
            return extraction_success, pages
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return False, []
    
    def _extract_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text using PyMuPDF for better layout preservation"""
        pages = []
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text with layout preservation
            text = page.get_text("text")
            
            # Extract text blocks for better structure
            blocks = page.get_text("dict")["blocks"]
            structured_text = self._extract_structured_text(blocks)
            
            page_data = {
                "page_number": page_num + 1,
                "text": text,
                "structured_text": structured_text,
                "text_length": len(text),
                "extraction_method": "pymupdf",
                "has_text": bool(text.strip())
            }
            
            pages.append(page_data)
        
        doc.close()
        return pages
    
    def _extract_with_pdfminer(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text using pdfminer for fallback"""
        pages = []
        
        # Extract full text first
        full_text = extract_text(file_path, laparams=self.lap_params)
        
        # Split into pages (approximate)
        text_parts = self._split_text_into_pages(full_text)
        
        for i, text_part in enumerate(text_parts):
            page_data = {
                "page_number": i + 1,
                "text": text_part,
                "structured_text": [],
                "text_length": len(text_part),
                "extraction_method": "pdfminer",
                "has_text": bool(text_part.strip())
            }
            pages.append(page_data)
        
        return pages
    
    def _extract_structured_text(self, blocks: List[Dict]) -> List[Dict[str, Any]]:
        """Extract structured text from PyMuPDF blocks"""
        structured = []
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            structured.append({
                                "text": span["text"],
                                "bbox": span["bbox"],
                                "font": span["font"],
                                "size": span["size"],
                                "flags": span["flags"]
                            })
        
        return structured
    
    def _split_text_into_pages(self, text: str) -> List[str]:
        """Split text into approximate pages"""
        # Simple page splitting - can be improved with more sophisticated logic
        lines = text.split('\n')
        lines_per_page = max(1, len(lines) // 10)  # Assume 10 pages
        
        pages = []
        current_page = []
        
        for i, line in enumerate(lines):
            current_page.append(line)
            
            if (i + 1) % lines_per_page == 0:
                pages.append('\n'.join(current_page))
                current_page = []
        
        # Add remaining lines to last page
        if current_page:
            pages.append('\n'.join(current_page))
        
        return pages
    
    def _create_empty_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """Create empty page structure when text extraction fails"""
        # Try to get page count using PyMuPDF
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
        except:
            page_count = 1
        
        pages = []
        for i in range(page_count):
            page_data = {
                "page_number": i + 1,
                "text": "",
                "structured_text": [],
                "text_length": 0,
                "extraction_method": "failed",
                "has_text": False
            }
            pages.append(page_data)
        
        return pages
    
    def _apply_ocr_enhancement(self, file_path: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply OCR to enhance text extraction, especially for image-based content"""
        try:
            # Import OCR processor (lazy import to avoid dependency issues)
            try:
                from parsing.pdf_ocr import PDFOCRProcessor
                ocr_processor = PDFOCRProcessor()
            except ImportError as e:
                logger.warning(f"OCR processor not available: {e}")
                return pages
            
            enhanced_pages = []
            ocr_threshold = 50  # Minimum text length to consider OCR
            
            for page in pages:
                page_text = page.get('text', '').strip()
                page_num = page.get('page_number', 1)
                
                # Decision logic for when to apply OCR
                should_use_ocr = (
                    len(page_text) < ocr_threshold or  # Very little text extracted
                    self._is_likely_scanned_page(page_text) or  # Likely scanned document
                    self._has_poor_text_quality(page_text)  # Poor text quality
                )
                
                if should_use_ocr:
                    logger.info(f"Applying OCR to page {page_num} (text length: {len(page_text)})")
                    
                    # Get OCR result for this page
                    ocr_result = ocr_processor._ocr_page(file_path, page_num)
                    
                    if ocr_result and ocr_result.get('ocr_text'):
                        ocr_text = ocr_result.get('ocr_text', '')
                        
                        # Choose the better text (OCR vs original)
                        if len(ocr_text.strip()) > len(page_text):
                            logger.info(f"OCR provided better text for page {page_num}: {len(ocr_text)} vs {len(page_text)} chars")
                            page['text'] = ocr_text
                            page['extraction_method'] = 'ocr_enhanced'
                            page['original_text'] = page_text
                        else:
                            # Combine both texts for maximum coverage
                            combined_text = f"{page_text}\n\n[OCR추가내용]\n{ocr_text}" if page_text else ocr_text
                            page['text'] = combined_text
                            page['extraction_method'] = 'hybrid'
                            
                        page['ocr_confidence'] = ocr_result.get('confidence', 0.0)
                        page['has_ocr'] = True
                    else:
                        page['has_ocr'] = False
                        page['extraction_method'] = page.get('extraction_method', 'pymupdf')
                else:
                    page['has_ocr'] = False
                    page['extraction_method'] = page.get('extraction_method', 'pymupdf')
                
                # Update text statistics
                page['text_length'] = len(page.get('text', ''))
                page['has_text'] = page['text_length'] > 0
                
                enhanced_pages.append(page)
            
            # Log enhancement statistics
            ocr_enhanced_count = sum(1 for p in enhanced_pages if p.get('has_ocr', False))
            logger.info(f"OCR enhancement completed: {ocr_enhanced_count}/{len(enhanced_pages)} pages enhanced")
            
            return enhanced_pages
            
        except Exception as e:
            logger.error(f"Error in OCR enhancement: {e}")
            return pages
    
    def _is_likely_scanned_page(self, text: str) -> bool:
        """Detect if a page is likely from a scanned document"""
        if not text or len(text) < 10:
            return True
            
        # Check for OCR artifacts
        ocr_artifacts = ['l', '|', 'I', '1']  # Common OCR misreads
        artifact_ratio = sum(1 for char in text if char in ocr_artifacts) / len(text)
        
        # Check for unusual character patterns
        weird_spacing = text.count('  ') / max(len(text.split()), 1)
        
        return artifact_ratio > 0.3 or weird_spacing > 0.5
    
    def _has_poor_text_quality(self, text: str) -> bool:
        """Detect poor text quality that might benefit from OCR"""
        if not text:
            return True
            
        # Check for encoding issues
        encoding_issues = ['�', '???', 'ï¿½']
        has_encoding_issues = any(issue in text for issue in encoding_issues)
        
        # Check for broken words (excessive single characters)
        words = text.split()
        if words:
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            return has_encoding_issues or single_char_ratio > 0.4
        
        return has_encoding_issues
    
    def get_text_coverage(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate text coverage statistics"""
        total_pages = len(pages)
        pages_with_text = sum(1 for page in pages if page.get('has_text', False))
        total_text_length = sum(page.get('text_length', 0) for page in pages)
        
        return {
            "total_pages": total_pages,
            "pages_with_text": pages_with_text,
            "text_coverage_ratio": pages_with_text / total_pages if total_pages > 0 else 0,
            "total_text_length": total_text_length,
            "average_text_per_page": total_text_length / total_pages if total_pages > 0 else 0
        }
    
    def extract_text_from_url(self, url: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """URL에서 PDF를 다운로드하고 텍스트 추출"""
        import requests
        import tempfile
        import os
        
        try:
            logger.info(f"PDF URL에서 다운로드 시작: {url}")
            
            # PDF 다운로드
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"URL이 PDF 파일이 아닐 수 있습니다. Content-Type: {content_type}")
            
            # 임시 파일에 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            logger.info(f"PDF 다운로드 완료: {len(response.content)} bytes")
            
            # 텍스트 추출 (OCR 포함)
            success, pages = self.extract_text_from_pdf(temp_file_path, use_ocr=True)
            
            # 임시 파일 삭제
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"임시 파일 삭제 실패: {e}")
            
            if success:
                logger.info(f"URL PDF 텍스트 추출 성공: {len(pages)} 페이지")
            else:
                logger.error(f"URL PDF 텍스트 추출 실패")
            
            return success, pages
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PDF 다운로드 실패: {e}")
            return False, []
        except Exception as e:
            logger.error(f"URL PDF 처리 오류: {e}")
            return False, []
