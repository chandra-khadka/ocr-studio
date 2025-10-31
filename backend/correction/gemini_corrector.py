import google.generativeai as genai

from backend.config import logger
from backend.correction.base import BaseCorrectionProvider
from backend.models.enums import DocumentType, Language, DocumentFormat


class GeminiCorrectionProvider(BaseCorrectionProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.model_name = model  # Set model_name before calling parent __init__
        super().__init__(api_key)  # Call parent __init__ which calls configure()
        self.model = None
        self.client = None

    def configure(self):
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name=self.model_name)
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        try:
            system_instructions = '''Role: You are an AI that corrects text extracted by OCR, ensuring it matches the original document.
            Input: Raw text output from OCR, which may contain errors such as misspellings, incorrect formatting, or missing characters.
            Task:
            - Correct all OCR errors to accurately reflect the original document.
            - For handwritten documents, focus on interpreting cursive or variable handwriting styles.
            - For printed documents, prioritize formatting and typographical accuracy.
            - Preserve mathematical expressions in LaTeX format (e.g., \\frac{dy}{dx}, \\lim_{\\Delta x \\to 0}).
            - Replace phrases like "Dx heads towards 0" with proper limit notation (e.g., \\lim_{\\Delta x \\to 0}).
            - Do not add, remove, or alter document_content beyond necessary corrections.
            Output: Only the corrected text in markdown with LaTeX for math, no explanations or additional comments.'''

            correction_prompt = f"""{system_instructions}

            Correct the following OCR text from a {document_format.value} {document_type.value} document.
            Expected language: {language.value}

            Raw OCR text:
            {raw_text}

            Output the corrected text in markdown, preserving mathematical expressions in LaTeX."""

            response = self.model.generate_content(correction_prompt)  # Use self.model instead of self.client
            return response.text if hasattr(response, "text") else raw_text
        except Exception as e:
            logger.error(f"Gemini correction error: {e}")
            return raw_text
