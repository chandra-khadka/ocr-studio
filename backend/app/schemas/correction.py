from pydantic import BaseModel

from backend.models.enums import DocumentType


class CorrectionRequest(BaseModel):
    text: str
    model: str  # "PROVIDER:MODEL"
    prompt: str | None = None
    document_type: DocumentType | None = None


class CorrectionResponse(BaseModel):
    corrected: str
