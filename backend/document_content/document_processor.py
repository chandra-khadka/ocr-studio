from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes

from backend.config import logger
from backend.models.enums import (
    OCRProvider,
    CorrectionProvider,
    DocumentType,
    DocumentFormat,
    Language,
)
from backend.models.schemas import OCRResult
from backend.ocr.ocr_provider_factory import OCRProviderFactory
from backend.utils.helper.image_segmentation import segment_image_for_ocr
from backend.utils.ui_helpers import parse_corrected_markdown


def _emit_progress(cb: Optional[Callable[[int, str], None]], pct: int, msg: str) -> None:
    if cb:
        try:
            cb(pct, msg)
            return
        except Exception:  # don’t break processing if the reporter fails
            logger.debug("progress_callback failed", exc_info=True)
    # fallback to log
    logger.info("[progress %d%%] %s", pct, msg)


def _normalize_ocr_result(ocr_result: Any) -> OCRResult:
    """
    Accept either OCRResult (preferred) or a structured enum-like holder
    and return an OCRResult instance.
    """
    from backend.models.schemas import OCRResult as OCRResultSchema
    from backend.models.enums import StructuredOCRResult as StructuredOCRResultEnum

    if isinstance(ocr_result, OCRResultSchema):
        return ocr_result
    elif isinstance(ocr_result, StructuredOCRResultEnum):
        return OCRResultSchema(
            raw_text=getattr(ocr_result, "raw_text", None),
            corrected_text=getattr(ocr_result, "corrected_text", None),
            structured_data=getattr(ocr_result, "structured_data", None),
            confidence=getattr(ocr_result, "confidence", None),
            language_detected=getattr(ocr_result, "language_detected", None),
            provider_used=getattr(ocr_result, "provider_used", None),
        )
    else:
        raise TypeError(f"Unexpected OCR result type: {type(ocr_result)}")


def _to_dict(obj: Any) -> Any:
    """
    Best-effort conversion to JSON-serializable dict.
    Supports Pydantic v1/v2, dataclasses, and plain objects.
    """
    if obj is None:
        return None
    for attr in ("model_dump", "dict"):
        if hasattr(obj, attr):
            try:
                return getattr(obj, attr)()
            except Exception:
                pass
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return obj


class DocumentProcessor:
    """
    Pure backend document processor for OCR -> (optional) correction -> (optional) JSON parsing.
    No Streamlit/UI side effects. Returns an API-friendly payload (dict).
    """

    @staticmethod
    def process_document(
            *,
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
            progress_callback: Optional[Callable[[int, str], None]] = None,
            **provider_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Returns:
            {
              "combined_ocr": <OCRResult as dict>,
              "structured_json": <dict | None>,
              "meta": {
                 "provider_used": str,
                 "language_detected": str,
                 "file_type": str,
                 "pages_processed": int,
                 "used_segmentation": bool
              }
            }
        Raises:
            Exception on unrecoverable errors (let your FastAPI route map to 4xx/5xx).
        """
        _emit_progress(progress_callback, 10, "Initializing document processing")

        # Create OCR provider instance
        logger.info("Creating OCR provider: %s", ocr_provider)
        ocr = OCRProviderFactory.create_provider(ocr_provider, **provider_kwargs)
        if ocr is None:
            raise RuntimeError(f"Failed to initialize OCR provider: {ocr_provider}")

        ocr_results: List[OCRResult] = []
        pages_processed = 0

        if file_type.startswith("image/"):
            _emit_progress(progress_callback, 20, "Processing image")
            if use_segmentation:
                with tempfile.TemporaryDirectory() as td:
                    temp_image_path = Path(td) / "image_for_seg.jpg"
                    temp_image_path.write_bytes(file_bytes)

                    seg_result = segment_image_for_ocr(temp_image_path, vision_enabled=True)

                    # Iterate over detected regions and OCR each region
                    for region in seg_result.get("region_images", []):
                        img_bytes = io.BytesIO()
                        region["pil_image"].save(img_bytes, format="JPEG")
                        r = ocr.extract_text(img_bytes.getvalue(), document_type, document_format)
                        ocr_results.append(_normalize_ocr_result(r))

                    pages_processed = 1
            else:
                r = ocr.extract_text(file_bytes, document_type, document_format)
                ocr_results.append(_normalize_ocr_result(r))
                pages_processed = 1

        elif file_type == "application/pdf":
            _emit_progress(progress_callback, 20, "Processing PDF")
            try:
                pdf_reader = PdfReader(io.BytesIO(file_bytes))
                total_pages = len(pdf_reader.pages)
                pages_to_process = min(total_pages, max_pdf_pages)

                # Try fast text extraction first
                raw_text_chunks: List[str] = []
                for idx, page in enumerate(pdf_reader.pages[:pages_to_process], 1):
                    page_text = page.extract_text()
                    if page_text:
                        raw_text_chunks.append(page_text)
                if raw_text_chunks:
                    ocr_results.append(
                        OCRResult(
                            raw_text="\n".join(raw_text_chunks).strip(),
                            provider_used="pypdf2",
                            language_detected="auto_detected",
                        )
                    )
                    pages_processed = pages_to_process
                else:
                    # Fallback: render pages to images and OCR each
                    images = convert_from_bytes(file_bytes, dpi=pdf_dpi, size=(None, None))
                    for i, image in enumerate(images[:pages_to_process]):
                        _emit_progress(
                            progress_callback,
                            20 + (i + 1) * 30 // pages_to_process,
                            f"OCR on PDF page {i + 1}/{pages_to_process}",
                        )
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format="JPEG")
                        img_bytes = img_byte_arr.getvalue()

                        if use_segmentation:
                            with tempfile.TemporaryDirectory() as td:
                                temp_image_path = Path(td) / f"page_{i + 1}.jpg"
                                temp_image_path.write_bytes(img_bytes)
                                seg_result = segment_image_for_ocr(temp_image_path, vision_enabled=True)
                                for region in seg_result.get("region_images", []):
                                    region_img_bytes = io.BytesIO()
                                    region["pil_image"].save(region_img_bytes, format="JPEG")
                                    r = ocr.extract_text(
                                        region_img_bytes.getvalue(), document_type, document_format
                                    )
                                    ocr_results.append(_normalize_ocr_result(r))
                        else:
                            r = ocr.extract_text(img_bytes, document_type, document_format)
                            ocr_results.append(_normalize_ocr_result(r))
                    pages_processed = pages_to_process
            except Exception as e:
                logger.error("PDF processing error: %s", e)
                raise

        else:
            raise ValueError(f"Unsupported file type: {file_type}. Please upload an image or PDF.")

        _emit_progress(progress_callback, 50, "Combining OCR results")

        combined_raw_text = "\n".join([r.raw_text for r in ocr_results if getattr(r, "raw_text", None)])
        provider_used = ocr_results[0].provider_used if ocr_results else "unknown"

        combined_ocr_result = OCRResult(
            raw_text=(combined_raw_text or "").strip(),
            provider_used=provider_used,
            language_detected="auto_detected",
        )

        # Optional correction
        corrected_text: Optional[str] = None
        if correction_provider != CorrectionProvider.NONE:
            _emit_progress(progress_callback, 70, "Applying AI correction")
            logger.info("Creating correction provider: %s", correction_provider)
            from backend.correction.correction_provider_factory import CorrectionProviderFactory

            corrector = CorrectionProviderFactory.create_provider(correction_provider, **provider_kwargs)
            if corrector is None:
                logger.warning("Failed to initialize correction provider (%s). Skipping correction.",
                               correction_provider)
            else:
                corrected_text = corrector.correct_text(
                    combined_ocr_result.raw_text or "",
                    document_type,
                    document_format,
                    language,
                )
                combined_ocr_result.corrected_text = corrected_text

        # Optional JSON parsing
        structured_json: Optional[Dict[str, Any]] = None
        if corrected_text and enable_json_parsing:
            _emit_progress(progress_callback, 90, "Parsing corrected text to structured JSON")
            base64_data_url = ""
            if file_type.startswith("image/"):
                encoded_image = base64.b64encode(file_bytes).decode("utf-8")
                base64_data_url = f"data:image/jpeg;base64,{encoded_image}"

            parsed = parse_corrected_markdown(correction_provider, base64_data_url, corrected_text)
            # parsed might be a Pydantic model, dataclass, or dict
            structured_json = _to_dict(parsed)

        _emit_progress(progress_callback, 100, "Completed")

        payload: Dict[str, Any] = {
            "combined_ocr": _to_dict(combined_ocr_result),
            "structured_json": structured_json,
            "meta": {
                "provider_used": provider_used,
                "language_detected": "auto_detected",
                "file_type": file_type,
                "pages_processed": pages_processed,
                "used_segmentation": bool(use_segmentation),
                "json_parsing_enabled": bool(enable_json_parsing),
                "correction_provider": str(correction_provider),
                "ocr_provider": str(ocr_provider),
            },
        }
        return payload

    @staticmethod
    def _normalize_ocr_result(ocr_result):
        from backend.models.schemas import OCRResult as OCRResultSchema
        from backend.models.enums import StructuredOCRResult as StructuredOCRResultEnum

        if isinstance(ocr_result, OCRResultSchema):
            return ocr_result
        elif isinstance(ocr_result, StructuredOCRResultEnum):
            return OCRResultSchema(
                raw_text=ocr_result.raw_text,
                corrected_text=ocr_result.corrected_text,
                structured_data=ocr_result.structured_data,
                confidence=ocr_result.confidence,
                language_detected=ocr_result.language_detected,
                provider_used=getattr(ocr_result, "provider_used", None),
            )
        else:
            logger.error(f"Unexpected OCR result type: {type(ocr_result)}")
            raise TypeError(f"Unexpected OCR result type: {type(ocr_result)}")
