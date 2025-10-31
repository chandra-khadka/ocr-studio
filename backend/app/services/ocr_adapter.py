import base64
import logging
import mimetypes
import sys
from pathlib import Path as _P
from typing import Tuple

from backend.document_content.enhance_document_processor import FastAPIDocumentProcessor
from backend.models.enums import CorrectionProvider, OCRProvider, DocumentType, Language, DocumentFormat
from backend.service.preprocess_image import dynamic_preprocess_image

_engine = _P(__file__).resolve().parents[2] / "ocr-engine"
if _engine.exists():
    sys.path.append(str(_engine))

logger = logging.getLogger(__name__)


def _detect_mime_from_name(name: str) -> str:
    guess, _ = mimetypes.guess_type(name)
    return guess or "application/octet-stream"


def _split_provider(provider_str: str) -> Tuple[str, str | None]:
    # "PROVIDER:MODEL" -> ("PROVIDER", "MODEL")
    parts = provider_str.split(":", 1)
    if len(parts) == 2:
        return parts[0].strip().upper(), parts[1].strip()
    return provider_str.strip().upper(), None


async def run_ocr(
        *,
        file_base64: str,
        file_name: str,
        language: str,
        document_type: str,
        provider_str: str,
        prompt: str | None,
) -> str:
    file_bytes = base64.b64decode(file_base64)
    file_type = _detect_mime_from_name(file_name)

    ocr_provider_name, ocr_model = _split_provider(provider_str)
    correction_provider = CorrectionProvider.NONE

    # Map strings to enums
    ocr_provider = OCRProvider[ocr_provider_name]
    doc_type = DocumentType[document_type] if document_type in DocumentType.__members__ else DocumentType.GENERAL
    lang = Language[language] if language in Language.__members__ else Language.AUTO_DETECT

    provider_kwargs = {}
    if ocr_model:
        provider_kwargs["ocr_model"] = ocr_model

    if file_type != "application/pdf" and file_type and file_type.startswith("image/"):
        try:
            processed_bytes, preprocessing_report = dynamic_preprocess_image(
                file_bytes,
                preprocessing_options={"denoise": {"strength": 7, "template": 7, "search": 21}}
            )

            file_bytes = processed_bytes
            file_type = "image/jpeg"
            logger.info("Dynamic preprocessing applied to image input.")
        except Exception as e:
            logger.warning(f"Dynamic preprocessing failed; proceeding with original image. Error: {e}")

    result = await FastAPIDocumentProcessor.process_document_enhanced(
        file_bytes=file_bytes,
        file_type=file_type,
        ocr_provider=ocr_provider,
        correction_provider=correction_provider,
        document_type=doc_type,
        document_format=DocumentFormat.STANDARD,
        language=lang,
        enable_json_parsing=True,
        use_segmentation=False,
        max_pdf_pages=5,
        pdf_dpi=300,
        custom_prompt=prompt,
        **provider_kwargs,
    )
    # result contains keys raw_text, structured_json, pdf_content, status, ...
    return result.get("raw_text", "") or result.get("structured_json", {}).get("structured_data", "") or ""
