from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel


class DocumentType(str, Enum):
    GENERAL = "GENERAL"
    GOVERNMENT_DOCUMENT = "GOVERNMENT_DOCUMENT"
    CTZN_FRONT = "CTZN_FRONT"
    CTZN_BACK = "CTZN_BACK"
    LICENSE = "LICENSE"
    VOTER_ID = "VOTER_ID"
    PASSPORT_FRONT = "PASSPORT_FRONT"
    PASSPORT_BACK = "PASSPORT_BACK"
    NATIONAL_ID_FRONT = "NATIONAL_ID_FRONT"
    NATIONAL_ID_BACK = "NATIONAL_ID_BACK"
    NEWSPAPER = "NEWSPAPER"
    LETTER = "LETTER"
    FORM = "FORM"
    BOOK = "BOOK"
    RECIPE = "RECIPE"
    HANDWRITTEN = "HANDWRITTEN"
    MAP = "MAP"
    TABLE = "TABLE"
    OTHER = "OTHER"


class DocumentFormat(str, Enum):
    HANDWRITTEN = "HANDWRITTEN"
    PRINTED = "PRINTED"
    STANDARD = "STANDARD"
    PLASTIC_COVER = "PLASTIC_COVER"


class Language(str, Enum):
    NEPALI = "NEPALI"
    ENGLISH = "ENGLISH"
    AUTO_DETECT = "AUTO_DETECT"


class OCRProvider(str, Enum):
    GEMINI = "GEMINI"
    MISTRAL = "MISTRAL"
    OLLAMA = "OLLAMA"
    VLLM = "VLLM"
    GEMINI_OPENSOURCE = "GEMINI_OPENSOURCE"
    NONE = "NONE"


class CorrectionProvider(str, Enum):
    GEMINI = "GEMINI"
    MISTRAL = "MISTRAL"
    OLLAMA = "OLLAMA"
    VLLM = "VLLM"
    GEMINI_OPENSOURCE = "GEMINI_OPENSOURCE"
    NONE = "NONE"


class StructuredOCRResult(BaseModel):
    raw_text: str
    corrected_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    language_detected: Optional[str] = None
