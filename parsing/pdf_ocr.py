v음과 같은 import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import io
from typing import List, Dict, Any, Tuple, Optional
import os
try:
    from core.gui_config import gui_settings as settings
except ImportError:
    try:
        from core.config import settings
    except ImportError:
        # 최소 설정으로 대체
        class MinimalSettings:
            ocr_languages = ["ko", "en"]
            enable_gpu = False
        settings = MinimalSettings()

try:
    from core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class PDFOCRProcessor:
    def __init__(self):
        self.ocr_languages = settings.ocr_languages
        self.enable_gpu = settings.enable_gpu
        
        # Initialize PaddleOCR
        try:
            from paddleocr import PaddleOCR
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='korean' if 'ko' in self.ocr_languages else 'en',
                use_gpu=self.enable_gpu
            )
            self.use_paddle = True
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.warning(f"PaddleOCR initialization failed: {e}")
            self.use_paddle = False
        
        # Initialize Tesseract as fallback
        try:
            import pytesseract
            self.tesseract = pytesseract
            self.use_tesseract = True
            logger.info("Tesseract initialized successfully")
        except Exception as e:
            logger.warning(f"Tesseract initialization failed: {e}")
            self.use_tesseract = False
    
    def process_pdf_with_ocr(self, file_path: str, pages: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Process PDF pages with OCR for pages that lack text"""
        try:
            processed_pages = []
            ocr_processed_count = 0
            
            for page_data in pages:
                if page_data.get('has_text', False) and page_data.get('text', '').strip():
                    # Page has text, no OCR needed
                    processed_pages.append(page_data)
                else:
                    # Page needs OCR
                    ocr_result = self._ocr_page(file_path, page_data['page_number'])
                    if ocr_result:
                        page_data.update(ocr_result)
                        page_data['is_ocr'] = True
                        ocr_processed_count += 1
                    else:
                        page_data['is_ocr'] = False
                        page_data['ocr_text'] = ""
                    
                    processed_pages.append(page_data)
            
            logger.info(f"OCR processed {ocr_processed_count} out of {len(pages)} pages")
            return True, processed_pages
            
        except Exception as e:
            logger.error(f"Error processing PDF with OCR {file_path}: {e}")
            return False, pages
    
    def _ocr_page(self, file_path: str, page_number: int) -> Optional[Dict[str, Any]]:
        """Extract text from a single page using OCR"""
        try:
            # Open PDF and get page
            doc = fitz.open(file_path)
            page = doc[page_number - 1]  # Convert to 0-based index
            
            # Convert page to image
            mat = fitz.Matrix(2.0, 2.0)  # Scale factor for better OCR
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Try PaddleOCR first
            if self.use_paddle:
                ocr_result = self._paddle_ocr_page(img_cv)
                if ocr_result:
                    doc.close()
                    return ocr_result
            
            # Fallback to Tesseract
            if self.use_tesseract:
                ocr_result = self._tesseract_ocr_page(img_cv)
                if ocr_result:
                    doc.close()
                    return ocr_result
            
            doc.close()
            return None
            
        except Exception as e:
            logger.error(f"Error in OCR for page {page_number}: {e}")
            return None
    
    def _paddle_ocr_page(self, img_cv: np.ndarray) -> Optional[Dict[str, Any]]:
        """Extract text using PaddleOCR"""
        try:
            result = self.paddle_ocr.ocr(img_cv, cls=True)
            
            if not result or not result[0]:
                return None
            
            # Extract text from results
            texts = []
            for line in result[0]:
                if len(line) >= 2:
                    text = line[1][0]  # Extract text from OCR result
                    confidence = line[1][1]  # Extract confidence
                    if confidence > 0.5:  # Filter low confidence results
                        texts.append(text)
            
            ocr_text = '\n'.join(texts)
            
            return {
                'ocr_text': ocr_text,
                'ocr_method': 'paddle',
                'ocr_confidence': 'high' if len(texts) > 0 else 'low'
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return None
    
    def _tesseract_ocr_page(self, img_cv: np.ndarray) -> Optional[Dict[str, Any]]:
        """Extract text using Tesseract"""
        try:
            # Preprocess image for better OCR
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Configure Tesseract
            config = '--oem 3 --psm 6'  # Page segmentation mode 6: uniform block of text
            
            # Add language support
            if 'ko' in self.ocr_languages:
                config += ' -l kor+eng'
            elif 'en' in self.ocr_languages:
                config += ' -l eng'
            
            # Extract text
            text = self.tesseract.image_to_string(binary, config=config)
            
            if text.strip():
                return {
                    'ocr_text': text.strip(),
                    'ocr_method': 'tesseract',
                    'ocr_confidence': 'medium'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Tesseract error: {e}")
            return None
    
    def get_ocr_statistics(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate OCR statistics"""
        total_pages = len(pages)
        ocr_pages = sum(1 for page in pages if page.get('is_ocr', False))
        text_pages = sum(1 for page in pages if page.get('has_text', False))
        
        return {
            "total_pages": total_pages,
            "ocr_processed_pages": ocr_pages,
            "text_extracted_pages": text_pages,
            "ocr_ratio": ocr_pages / total_pages if total_pages > 0 else 0,
            "text_coverage_ratio": text_pages / total_pages if total_pages > 0 else 0
        }
