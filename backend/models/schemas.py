from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, HttpUrl
from pydantic.v1 import root_validator

from backend.models.enums import OCRProvider, CorrectionProvider, DocumentType, DocumentFormat, Language


class OCRResult(BaseModel):
    """Result from OCR processing"""
    raw_text: str = Field(description="Raw text extracted from OCR")
    structured_data: Optional[Dict[str, Any]] = None
    corrected_text: Optional[str] = Field(None, description="AI-corrected text")
    confidence: Optional[float] = Field(None, description="Confidence score of OCR result")
    language_detected: Optional[str] = Field(None, description="Detected language")
    processing_time: Optional[float] = Field(None, description="Time taken to process in seconds")
    provider_used: Optional[str] = Field(None, description="OCR provider used")
    timestamp: datetime = Field(default_factory=datetime.now)


class DocumentInfo(BaseModel):
    """Information about the processed document"""
    filename: str
    file_type: str
    file_size: int
    document_type: str
    document_format: str
    language: str


class ChatMessage(BaseModel):
    """Chat message structure"""
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message document_content")
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Chat session with document context"""
    session_id: str
    document_context: Optional[OCRResult] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class ProcessingRequest(BaseModel):
    """Request for document processing"""
    document_type: str
    document_format: str
    language: str
    ocr_provider: str
    correction_provider: str
    enable_chat: bool = True


class StructuredDocumentData(BaseModel):
    """Structured data for specific document types"""
    # Common fields
    document_number: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None

    # License specific
    license_class: Optional[str] = None
    restrictions: Optional[List[str]] = None

    # Citizenship specific
    citizenship_number: Optional[str] = None
    place_of_birth: Optional[str] = None
    parents_name: Optional[str] = None

    # Passport specific
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    place_of_issue: Optional[str] = None

    # Voter ID specific
    voter_id_number: Optional[str] = None
    constituency: Optional[str] = None
    polling_station: Optional[str] = None

    # Additional extracted data
    other_fields: Dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    ocr_model: Optional[str] = None
    correction_model: Optional[str] = None


class DocumentProcessingRequest(BaseModel):
    # Common document controls
    ocr_provider: OCRProvider = OCRProvider.VLLM
    correction_provider: CorrectionProvider = CorrectionProvider.VLLM
    document_type: DocumentType = DocumentType.GENERAL
    document_format: DocumentFormat = DocumentFormat.STANDARD
    language: Language = Language.AUTO_DETECT
    enable_json_parsing: bool = True
    use_segmentation: bool = False
    max_pdf_pages: int = 5
    pdf_dpi: int = 300
    custom_prompt: Optional[str] = None
    provider_config: ProviderConfig = ProviderConfig()

    # File metadata (optional)
    file_name: Optional[str] = Field(None, alias="fileName")

    class Config:
        allow_population_by_field_name = True


class ImageProcessingRequest(DocumentProcessingRequest):
    # New (preferred) fields
    image_url: Optional[HttpUrl] = None
    base64_image: Optional[str] = None
    apply_correction: bool = False

    class Config:
        allow_population_by_field_name = True

    @root_validator(pre=True)
    def _compat_and_normalize(cls, v: Dict[str, Any]):
        """Map old keys (camelCase) to new ones (snake_case) to accept both."""
        data = dict(v or {})

        # Back-compat field mappings
        # content
        if "fileBase64" in data and "base64_image" not in data:
            data["base64_image"] = data.pop("fileBase64")
        if "imageUrl" in data and "image_url" not in data:
            data["image_url"] = data.pop("imageUrl")

        # enums / options
        if "provider" in data and "ocr_provider" not in data:
            data["ocr_provider"] = data.pop("provider")
        if "documentType" in data and "document_type" not in data:
            data["document_type"] = data.pop("documentType")
        if "documentFormat" in data and "document_format" not in data:
            data["document_format"] = data.pop("documentFormat")
        if "languageCode" in data and "language" not in data:
            data["language"] = data.pop("languageCode")

        # file name
        if "fileName" in data and "file_name" not in data:
            data["file_name"] = data.pop("fileName")

        # Strip data URI prefix if present (safe to do here)
        b64 = data.get("base64_image")
        if isinstance(b64, str) and b64.startswith("data:"):
            data["base64_image"] = b64.split(",", 1)[1]

        return data

    @root_validator
    def _one_of_url_or_base64(cls, values):
        has_url = bool(values.get("image_url"))
        has_b64 = bool(values.get("base64_image"))
        if has_url == has_b64:
            # both True or both False → invalid
            raise ValueError("Provide exactly one of image_url or base64_image.")
        return values
