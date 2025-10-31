import logging
from typing import Any

from backend.models.enums import DocumentType, DocumentFormat, Language

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseCorrectionProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client: Any = None
        self.configure()

    def configure(self):
        raise NotImplementedError

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        raise NotImplementedError
