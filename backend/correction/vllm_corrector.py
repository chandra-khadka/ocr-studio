"""
VLLM Correction Provider for VLLM-based models
Supports models that implement OpenAI-compatible chat completions endpoint
"""
import logging
import requests
from typing import List

from backend.config import logger
from backend.correction.base import BaseCorrectionProvider
from backend.models.enums import DocumentType, DocumentFormat, Language


class VLLMCorrectionProvider(BaseCorrectionProvider):
    """VLLM provider for text correction using models served via OpenAI-compatible API"""

    def __init__(self, api_key: str, model: str = "google/gemma-3-12b-it",
                 server_url: str = "http://localhost:8000/v1"):
        self.__vllm_model = model
        self.server_url = server_url
        self.available_models = []
        self.client = None
        super().__init__(api_key=api_key)
        logger.debug(f"Initialized VLLMCorrectionProvider with model: {self.__vllm_model}, server: {self.server_url}")
        self.configure()

    def configure(self):
        """Configure the VLLM connection and fetch available models"""
        try:
            logger.debug(f"Configuring with model: {self.__vllm_model}")
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.server_url}/models", headers=headers, timeout=10)
            response.raise_for_status()
            self.available_models = [model["id"] for model in response.json().get("data", [])]
            logger.info(f"Available VLLM models for correction: {self.available_models}")

            if self.__vllm_model not in self.available_models:
                fallback_models = ["google/gemma-3-12b-it"]
                for fallback in fallback_models:
                    if fallback in self.available_models:
                        logger.warning(f"Model {self.__vllm_model} not found, using {fallback}")
                        self.__vllm_model = fallback
                        break
                else:
                    raise ValueError(f"No suitable correction model found. Available: {self.available_models}")

            self.client = requests.Session()
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
            logger.debug(f"Model initialized: {self.__vllm_model}")

        except Exception as e:
            logger.error(f"Failed to configure VLLM API: {str(e)}")
            raise ConnectionError(f"Cannot connect to VLLM API: {str(e)}")

    @property
    def model(self) -> str:
        """Getter for model attribute"""
        return self.__vllm_model

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        """Correct text using VLLM model"""
        try:
            logger.debug(f"Correcting text with model: {self.__vllm_model}")
            prompt = self._create_correction_prompt(raw_text, document_type, document_format, language)

            payload = {
                "model": self.__vllm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "top_p": 0.9,
                "max_tokens": 1024
            }

            response = self.client.post(f"{self.server_url}/chat/completions", json=payload, timeout=30)
            response.raise_for_status()
            corrected_text = response.json()["choices"][0]["message"]["content"]
            return self._clean_response(corrected_text)

        except Exception as e:
            logger.error(f"VLLM correction error: {e}")
            return raw_text

    def _create_correction_prompt(self, raw_text: str, document_type: DocumentType,
                                  document_format: DocumentFormat, language: Language) -> str:
        """Create correction prompt based on document type, format, and language"""
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
        """Clean the response by removing common prefixes"""
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

    def list_available_models(self) -> List[str]:
        """List all available models in VLLM API"""
        return self.available_models
