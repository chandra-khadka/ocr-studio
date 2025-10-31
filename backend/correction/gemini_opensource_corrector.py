"""
GeminiOpensource Correction Provider for Google Gemini models
Supports models that implement 'generateContent'
"""

import google.generativeai as genai

from backend.config import logger
from backend.correction.base import BaseCorrectionProvider
from backend.models.enums import DocumentType, DocumentFormat, Language


class GeminiOpensourceCorrectionProvider(BaseCorrectionProvider):
    """Gemini provider for text correction using generative models"""

    def __init__(self, api_key: str, model: str = "models/gemma-3-4b-it"):
        # Store model in a unique attribute to avoid parent class conflicts
        self.__gemini_model = model
        self.available_models = []
        self.client = None
        # Call parent initializer
        super().__init__(api_key=api_key)
        logger.debug(f"Initialized GeminiOpensourceCorrectionProvider with model: {self.__gemini_model}")
        # Configure after parent initialization
        self.configure()

    def configure(self):
        """Configure the Gemini connection and select an appropriate model"""
        try:
            logger.debug(f"Configuring with model: {self.__gemini_model}")
            genai.configure(api_key=self.api_key)
            # Fetch available models
            models = genai.list_models()
            self.available_models = [model.name for model in models if
                                     'generateContent' in model.supported_generation_methods]
            logger.info(f"Available Gemini models for correction: {self.available_models}")

            # Check if selected model is available
            current_model = self.__gemini_model
            if current_model not in self.available_models:
                # Try fallback models
                fallback_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
                for fallback in fallback_models:
                    if fallback in self.available_models:
                        logger.warning(f"Model {current_model} not found, using {fallback}")
                        self.__gemini_model = fallback
                        break
                else:
                    raise ValueError(f"No suitable correction model found. Available: {self.available_models}")

            # Initialize the model
            self.client = genai.GenerativeModel(self.__gemini_model)
            logger.debug(f"Model initialized: {self.__gemini_model}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {str(e)}")
            raise ConnectionError(f"Cannot connect to Gemini API: {str(e)}")

    @property
    def model(self) -> str:
        """Getter for model attribute to maintain compatibility"""
        return self.__gemini_model

    def correct_text(self, raw_text: str, document_type: DocumentType,
                     document_format: DocumentFormat, language: Language) -> str:
        """Correct text using Gemini model"""
        try:
            logger.debug(f"Correcting text with model: {self.__gemini_model}")
            prompt = self._create_correction_prompt(raw_text, document_type, document_format, language)
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )
            corrected_text = response.text
            return self._clean_response(corrected_text)
        except Exception as e:
            logger.error(f"Gemini correction error: {e}")
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
