import base64
import io
from pathlib import Path
from typing import Dict, Any, List

import fitz
from PyPDF2 import PdfReader
from fastapi import HTTPException
from pdf2image import convert_from_bytes

from backend.config import logger
from backend.document_content.document_processor import DocumentProcessor
from backend.document_content.pdf_content_formatter import PDFContentFormatter
from backend.models.enums import OCRProvider, CorrectionProvider, DocumentType, DocumentFormat, Language
from backend.models.schemas import OCRResult
from backend.ocr.ocr_provider_factory import OCRProviderFactory
from backend.utils.helper.image_segmentation import segment_image_for_ocr
from backend.utils.ui_helpers import parse_corrected_markdown


class FastAPIDocumentProcessor(DocumentProcessor):
    """FastAPI-specific document processor with enhanced PDF handling for API usage"""

    @staticmethod
    async def extract_pdf_content_advanced(file_bytes: bytes, max_pages: int = 5) -> Dict[str, Any]:
        """Advanced PDF content extraction with multiple methods"""
        pdf_content = {
            'pages': [],
            'total_pages': 0,
            'extraction_method': 'hybrid',
            'metadata': {}
        }

        try:
            # Try PyMuPDF first (better formatting)
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            pdf_content['total_pages'] = len(pdf_doc)
            pdf_content['metadata'] = pdf_doc.metadata

            for page_num in range(min(len(pdf_doc), max_pages)):
                page = pdf_doc[page_num]

                # Extract text with formatting
                text_dict = page.get_text("dict")
                formatted_text = FastAPIDocumentProcessor._format_pymupdf_text(text_dict)

                # Get page image for OCR if text is insufficient
                page_image = None
                if len(formatted_text.strip()) < 50:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    page_image = pix.tobytes("jpeg")

                page_info = {
                    'page_number': page_num + 1,
                    'text': formatted_text,
                    'text_length': len(formatted_text),
                    'has_images': len(page.get_images()) > 0,
                    'image_data': base64.b64encode(page_image).decode() if page_image else None,
                    'needs_ocr': len(formatted_text.strip()) < 50
                }

                pdf_content['pages'].append(page_info)

            pdf_doc.close()

        except Exception as e:
            logger.warning(f"PyMuPDF failed, falling back to PyPDF2: {e}")
            return FastAPIDocumentProcessor._extract_with_pypdf2(file_bytes, max_pages)

        return pdf_content

    @staticmethod
    def _format_pymupdf_text(text_dict: Dict) -> str:
        """Format PyMuPDF text dictionary into readable text"""
        formatted_lines = []

        for block in text_dict.get('blocks', []):
            if 'lines' in block:
                block_lines = []
                for line in block['lines']:
                    line_text = "".join(span['text'] for span in line['spans'])
                    if line_text.strip():
                        block_lines.append(line_text.strip())

                if block_lines:
                    formatted_lines.append(' '.join(block_lines))

        return '\n\n'.join(formatted_lines)

    @staticmethod
    def _extract_with_pypdf2(file_bytes: bytes, max_pages: int) -> Dict[str, Any]:
        """Fallback PDF extraction with PyPDF2"""
        pdf_content = {
            'pages': [],
            'total_pages': 0,
            'extraction_method': 'pypdf2',
            'metadata': {}
        }

        try:
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            pdf_content['total_pages'] = len(pdf_reader.pages)

            if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                pdf_content['metadata'] = dict(pdf_reader.metadata)

            for page_num in range(min(len(pdf_reader.pages), max_pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                page_info = {
                    'page_number': page_num + 1,
                    'text': PDFContentFormatter.format_text_blocks(text),
                    'text_length': len(text),
                    'needs_ocr': len(text.strip()) < 50
                }

                pdf_content['pages'].append(page_info)

        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")
        return pdf_content

    @staticmethod
    async def process_document_enhanced(
            file_bytes: bytes,
            file_type: str,
            ocr_provider: OCRProvider,
            correction_provider: CorrectionProvider,
            document_type: DocumentType,
            document_format: DocumentFormat,
            language: Language,
            enable_json_parsing: bool = True,
            use_segmentation: bool = False,
            max_pdf_pages: int = 5,
            pdf_dpi: int = 300,
            custom_prompt=None,
            **provider_kwargs,
    ) -> Dict[str, Any]:
        """Process document and return results for FastAPI"""
        try:
            logger.info(f"Creating {ocr_provider} OCR provider")
            ocr = OCRProviderFactory.create_provider(ocr_provider, **provider_kwargs)

            ocr_results = []
            pdf_content = None
            if file_type.startswith("image/"):
                logger.info("Processing image...")
                if use_segmentation:
                    temp_image_path = Path("temp_image.jpg")
                    with open(temp_image_path, "wb") as f:
                        f.write(file_bytes)
                    seg_result = segment_image_for_ocr(temp_image_path, vision_enabled=True)
                    temp_image_path.unlink()

                    for region in seg_result.get('region_images', []):
                        img_bytes = io.BytesIO()
                        region['pil_image'].save(img_bytes, format="JPEG")
                        ocr_result = ocr.extract_text(img_bytes.getvalue(), DocumentType.GENERAL, document_format,
                                                      custom_prompt)
                        ocr_result = DocumentProcessor._normalize_ocr_result(ocr_result)
                        ocr_results.append(ocr_result)
                else:
                    ocr_result = ocr.extract_text(file_bytes, document_type, document_format)
                    ocr_result = DocumentProcessor._normalize_ocr_result(ocr_result)
                    ocr_results.append(ocr_result)

            elif file_type == "application/pdf":
                logger.info("Processing PDF with enhanced extraction...")
                pdf_content = await FastAPIDocumentProcessor.extract_pdf_content_advanced(file_bytes, max_pdf_pages)
                combined_text = ""
                pages_needing_ocr = []

                for page_info in pdf_content['pages']:
                    if page_info['text'] and len(page_info['text'].strip()) > 50:
                        combined_text += f"\n--- Page {page_info['page_number']} ---\n{page_info['text']}\n"
                    else:
                        pages_needing_ocr.append(page_info)

                # Create OCR result from extracted text
                if combined_text.strip():
                    text_ocr_result = OCRResult(
                        raw_text=combined_text.strip(),
                        provider_used=f"text_extraction_{pdf_content['extraction_method']}",
                        language_detected="auto_detected",
                        structured_data={}
                    )
                    ocr_results.append(text_ocr_result)

                # Process pages that need OCR
                if pages_needing_ocr:
                    logger.info(f"Running OCR on {len(pages_needing_ocr)} pages...")
                    images = convert_from_bytes(file_bytes, dpi=pdf_dpi)

                    for page_info in pages_needing_ocr:
                        page_idx = page_info['page_number'] - 1
                        if page_idx < len(images):
                            img_byte_arr = io.BytesIO()
                            images[page_idx].save(img_byte_arr, format="JPEG")
                            img_bytes = img_byte_arr.getvalue()

                            page_ocr_result = ocr.extract_text(img_bytes, document_type, document_format)
                            page_ocr_result = DocumentProcessor._normalize_ocr_result(page_ocr_result)

                            # Add page information to the result
                            if hasattr(page_ocr_result, 'raw_text'):
                                page_ocr_result.raw_text = f"--- Page {page_info['page_number']} (OCR) ---\n{page_ocr_result.raw_text}"
                                page_ocr_result.structured_data = {}
                            ocr_results.append(page_ocr_result)

            logger.info("Combining results...")
            combined_raw_text = "\n\n".join(result.raw_text for result in ocr_results if result.raw_text)
            if not combined_raw_text.strip():
                return {"status": "error", "raw_text": "", "structured_json": {"structured_data": {}},
                        "message": "No text extracted"}

            combined_structured_data = {}
            for result in ocr_results:
                if hasattr(result, 'structured_data') and result.structured_data:
                    combined_structured_data.update(result.structured_data)

            result = {
                "raw_text": combined_raw_text,
                "pdf_content": pdf_content,
                "status": "success",
                "structured_json": {
                    "structured_data": (
                        combined_structured_data if combined_structured_data
                        else {"raw_text": combined_raw_text}
                    )
                }
            }

            corrected_text = None
            from backend.correction.correction_provider_factory import CorrectionProviderFactory

            if correction_provider != CorrectionProvider.NONE:
                logger.info("Applying AI correction...")
                logger.info(f"Creating {correction_provider} correction provider")
                corrector = CorrectionProviderFactory.create_provider(correction_provider, **provider_kwargs)
                if corrector is None:
                    raise HTTPException(status_code=500, detail="Failed to initialize correction provider.")
                try:
                    corrected_text = corrector.correct_text(combined_raw_text, document_type, document_format, language)
                    result["corrected_text"] = corrected_text  # Optional
                    result["improvements"] = FastAPIDocumentProcessor._identify_improvements(combined_raw_text,
                                                                                             corrected_text)  # Optional
                    result["improvement_score"] = FastAPIDocumentProcessor._calculate_improvement_score(
                        combined_raw_text, corrected_text)  # Optional
                except Exception as e:
                    logger.error(f"Correction error: {e}")
                    result["warning"] = f"Correction failed: {str(e)}"

                if corrected_text and enable_json_parsing:
                    logger.info("Parsing to structured JSON...")
                    base64_data_url = ""
                    if file_type.startswith("image/"):
                        encoded_image = base64.b64encode(file_bytes).decode()
                        base64_data_url = f"data:image/jpeg;base64,{encoded_image}"
                    try:
                        structured_json = parse_corrected_markdown(correction_provider, base64_data_url, corrected_text)
                        if structured_json:
                            result["structured_json"] = {
                                "structured_data": structured_json if isinstance(structured_json,
                                                                                 dict) else structured_json.__dict__
                            }  # Optional
                            result["json_summary"] = FastAPIDocumentProcessor._summarize_json_fields(
                                structured_json if isinstance(structured_json, dict) else structured_json.__dict__
                            )  # Optional
                        else:
                            result["structured_json"] = {"structured_data": combined_structured_data}
                            result["warning"] = result.get("warning",
                                                           "") + " Failed to parse structured JSON, using combined structured data."
                    except Exception as e:
                        logger.error(f"JSON parsing error: {e}")
                        result["structured_json"] = {"structured_data": combined_structured_data}
                        result["warning"] = result.get("warning", "") + f" JSON parsing failed: {str(e)}"

            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    @staticmethod
    def _calculate_improvement_score(raw_text: str, corrected_text: str) -> int:
        """Calculate a simple improvement score based on text quality indicators"""
        score = 50  # Base score

        # Check for improvements
        raw_sentences = len([s for s in raw_text.split('.') if s.strip()])
        corrected_sentences = len([s for s in corrected_text.split('.') if s.strip()])

        # Better sentence structure
        if corrected_sentences > raw_sentences:
            score += 10

        # Check for common OCR error corrections
        ocr_errors = ['rn' in raw_text, 'l1' in raw_text, '0O' in raw_text]
        if any(ocr_errors) and not any(error in corrected_text for error in ['rn', 'l1', '0O']):
            score += 15

        # Check for proper capitalization
        if corrected_text.count('. ') > raw_text.count('. '):
            score += 10

        # Length improvement (within reason)
        length_ratio = len(corrected_text) / len(raw_text) if raw_text else 1
        if 1.0 <= length_ratio <= 1.3:  # 0-30% increase is good
            score += 15

        return min(score, 95)  # Cap at 95%

    @staticmethod
    def _identify_improvements(raw_text: str, corrected_text: str) -> List[str]:
        """Identify specific improvements made during correction"""
        improvements = []

        # Check for common improvements
        if len(corrected_text.split('.')) > len(raw_text.split('.')):
            improvements.append("Improved sentence structure and punctuation")

        if corrected_text.count('\n\n') > raw_text.count('\n\n'):
            improvements.append("Better paragraph organization")

        if corrected_text.istitle() != raw_text.istitle() and any(c.isupper() for c in corrected_text):
            improvements.append("Fixed capitalization and proper nouns")

        # Check for number formatting
        import re
        raw_numbers = len(re.findall(r'\d+', raw_text))
        corrected_numbers = len(re.findall(r'\d+', corrected_text))
        if corrected_numbers >= raw_numbers:
            improvements.append("Preserved/corrected numerical data")

        # Check for special characters
        if '"' in corrected_text and '"' not in raw_text:
            improvements.append("Added proper quotation marks")

        if not improvements:
            improvements.append("General text cleanup and formatting")

        return improvements

    @staticmethod
    def _get_json_depth(obj, depth=0):
        """Get the maximum depth of a JSON object"""
        if depth > 10:  # Prevent infinite recursion
            return depth

        if isinstance(obj, dict):
            return max([FastAPIDocumentProcessor._get_json_depth(v, depth + 1) for v in obj.values()] + [depth])
        elif isinstance(obj, list):
            return max([FastAPIDocumentProcessor._get_json_depth(item, depth + 1) for item in obj] + [depth])
        else:
            return depth

    @staticmethod
    def _summarize_json_fields(json_obj: dict, prefix="") -> Dict[str, List[str]]:
        """Summarize the fields in a JSON object by type"""
        summary = {
            "Text Fields": [],
            "Number Fields": [],
            "Date Fields": [],
            "List Fields": [],
            "Object Fields": []
        }

        for key, value in json_obj.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, str):
                # Check if it's a date
                import re
                if re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', value) or re.search(r'\d{4}-\d{2}-\d{2}', value):
                    summary["Date Fields"].append(full_key)
                else:
                    summary["Text Fields"].append(full_key)
            elif isinstance(value, (int, float)):
                summary["Number Fields"].append(full_key)
            elif isinstance(value, list):
                summary["List Fields"].append(f"{full_key} ({len(value)} items)")
            elif isinstance(value, dict):
                summary["Object Fields"].append(full_key)
                # Recursively process nested objects (limit depth)
                if len(prefix.split('.')) < 2:
                    nested_summary = FastAPIDocumentProcessor._summarize_json_fields(value, full_key)
                    for field_type, fields in nested_summary.items():
                        summary[field_type].extend(fields)

        return summary
