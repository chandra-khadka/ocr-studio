import logging
from mistralai import Mistral

from backend.config import logger
from backend.correction.base import BaseCorrectionProvider
from backend.models.enums import DocumentType, Language, DocumentFormat


class MistralCorrectionProvider(BaseCorrectionProvider):
    def __init__(self, api_key: str, model: str = "mistral-small-latest"):
        super().__init__(api_key)
        self.model = model
        self.client = None
        self.configure()

    def configure(self):
        try:
            self.client = Mistral(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to configure Mistral client: {e}")
            raise

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""You are an AI that corrects OCR text from {document_format.value} {document_type.value} documents.
                    Instructions:
                    - Correct spelling and formatting errors while preserving original document_content and structure.
                    - Preserve mathematical expressions in LaTeX format 
                    - Replace phrases like "Dx heads towards 0" with proper limit notation
                    - Output only the corrected text in markdown, no explanations."""
                },
                {
                    "role": "user",
                    "content": f"Correct this OCR text (language: {language.value}):\n\n{raw_text}"
                }
            ]

            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                temperature=0.1
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Mistral correction error: {e}")
            return raw_text
