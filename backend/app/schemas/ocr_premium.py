from __future__ import annotations

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, HttpUrl

from backend.models.enums import (
    OCRProvider,
    CorrectionProvider,
    DocumentType,
    DocumentFormat,
    Language,
)


class ProviderConfig(BaseModel):
    ocr_model: Optional[str] = None
    correction_model: Optional[str] = None


class OCRPremiumRequest(BaseModel):
    # One of these must be provided (exactly one)
    image_url: Optional[HttpUrl] = Field(None, description="Publicly accessible image/PDF URL")
    base64_image: Optional[str] = Field(None, description="Base64-encoded image/PDF (no data URI needed)")

    # Processing configuration
    ocr_provider: OCRProvider = OCRProvider.VLLM
    correction_provider: CorrectionProvider = CorrectionProvider.NONE
    document_type: DocumentType = DocumentType.GENERAL
    document_format: DocumentFormat = DocumentFormat.STANDARD
    language: Language = Language.AUTO_DETECT

    enable_json_parsing: bool = True
    use_segmentation: bool = False
    max_pdf_pages: int = 5
    pdf_dpi: int = 300

    custom_prompt: Optional[str] = Field(
        None, description="Custom extraction instruction (e.g., 'Return Markdown with tables')."
    )
    provider_config: ProviderConfig = ProviderConfig()


class OCRPremiumResponse(BaseModel):
    # Keep it compatible with your UI
    text: str
    pages: Optional[int] = None
    images: Optional[List[str]] = None

    # Extra (metadata/advanced)
    raw_text: Optional[str] = None
    corrected_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
