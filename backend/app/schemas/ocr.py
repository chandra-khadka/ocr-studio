from pydantic import BaseModel, Field

from backend.models.enums import DocumentType


class OCRRequest(BaseModel):
    fileName: str
    fileBase64: str = Field(..., description="Base64-encoded file (no data URI)")
    language: str
    documentType: str = DocumentType.GENERAL.value
    provider: str  # "PROVIDER:MODEL"
    prompt: str | None = None


class OCRResponse(BaseModel):
    text: str
    pages: int | None = None
    images: list[str] | None = None
