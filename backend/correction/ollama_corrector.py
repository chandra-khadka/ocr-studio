import logging
import requests

from backend.core.config import settings
from backend.correction.base import BaseCorrectionProvider
from backend.models.enums import DocumentType, DocumentFormat, Language

logger = logging.getLogger(__name__)


class OllamaCorrectionProvider(BaseCorrectionProvider):

    def __init__(self, endpoint: str = settings.OLLAMA_API, model: str = "gemma3:4b"):
        # Set attributes BEFORE calling parent class's __init__
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        super().__init__(api_key="")  # No API key needed
        self.client = None
        # Now configure the connection
        self.configure()

    def configure(self):
        self.client = self
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                available_models = [model["name"] for model in response.json().get("models", [])]
                logger.info(f"Correction: Available Ollama models for correction: {available_models}")

                if self.model not in available_models:
                    # Try fallback models
                    fallback_models = ["gemma2:latest", "llama3:8b", "mistral:7b"]
                    for fallback in fallback_models:
                        if fallback in available_models:
                            logger.warning(f"Model {self.model} not found, using {fallback}")
                            self.model = fallback
                            break
                    else:
                        raise ValueError(f"No suitable correction model found. Available: {available_models}")
            else:
                raise ConnectionError(f"Failed to connect to Ollama at {self.endpoint}")
        except requests.RequestException as e:
            raise ConnectionError(f"Cannot connect to Ollama at {self.endpoint}: {str(e)}")

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        try:
            prompt = self._create_correction_prompt(raw_text, document_type, document_format, language)
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1
                }
            }

            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                corrected_text = result.get("response", raw_text)
                return self._clean_response(corrected_text)
            else:
                logger.error(f"Ollama correction API error: {response.status_code}")
                return raw_text
        except Exception as e:
            logger.error(f"Ollama correction error: {e}")
            return raw_text

    def _create_correction_prompt(self, raw_text: str, document_type: DocumentType,
                                  document_format: DocumentFormat, language: Language) -> str:
        language_instruction = ""
        if language == Language.NEPALI:
            language_instruction = "The text contains Nepali language. Ensure proper Devanagari script accuracy."
        elif language == Language.ENGLISH:
            language_instruction = "The text is in English. Focus on English spelling and grammar."

        prompt = f"""You are an expert text correction AI. Your task is to correct OCR errors in text extracted from a {document_format.value} {document_type.value} document.

        {language_instruction}
        
        Instructions:
        1. Correct spelling mistakes and OCR errors
        2. Fix formatting issues while preserving original structure
        3. Preserve mathematical expressions in LaTeX format
        4. Replace phrases like "Dx heads towards 0" with proper limit notation
        5. Maintain all original information - do not add or remove content
        6. Output ONLY the corrected text in markdown, no explanations
        
        Original OCR Text:
        {raw_text}
        
        Corrected Text:"""
        return prompt

    @staticmethod
    def _clean_response(response: str) -> str:
        prefixes_to_remove = [
            "Corrected Text:",
            "Here is the corrected text:",
            "The corrected text is:",
            "Corrected version:",
        ]
        cleaned = response.strip()
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        return cleaned
