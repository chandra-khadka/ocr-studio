"""
GeminiOpensource OCR Provider for Google Gemini models
Supports models that implement 'generateContent'
Updated to support structured JSON extraction for specific document types
"""
import base64
import json
import re
from typing import List, Dict, Any, Optional

import google.generativeai as genai

from backend.config import logger
from backend.models.enums import DocumentType, DocumentFormat
from backend.models.mappings import DOCUMENT_FIELD_MAP
from backend.models.schemas import OCRResult
from backend.ocr.base import BaseOCRProvider


class GeminiOpensourceOCRProvider(BaseOCRProvider):
    """Gemini provider for OCR using generative models with structured JSON extraction"""

    def __init__(self, api_key: str, model: str = "models/gemma-3-12b-it"):
        # Store model in a unique attribute to avoid parent class conflicts
        self.__gemini_model = model
        self.available_models = []
        self.client = None
        # Call parent initializer
        super().__init__(api_key=api_key)
        logger.debug(f"Initialized GeminiOpensourceOCRProvider with model: {self.__gemini_model}")
        # Configure after parent initialization to ensure attributes are preserved
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
            logger.info(f"Available Gemini models: {self.available_models}")

            # Check if selected model is available
            current_model = self.model
            if current_model not in self.available_models:
                # Try fallback models
                fallback_models = ["models/gemma-3-4b-it", "models/gemma-3-12b-it"]
                for fallback in fallback_models:
                    if fallback in self.available_models:
                        logger.warning(f"Model {current_model} not found, using {fallback}")
                        self.__gemini_model = fallback
                        break
                else:
                    raise ValueError(f"No suitable model found. Available: {self.available_models}")

            # Initialize the model
            self.client = genai.GenerativeModel(self.__gemini_model)
            logger.info(f"Model initialized: {self.__gemini_model}")

        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {str(e)}")
            raise ConnectionError(f"Cannot connect to Gemini API: {str(e)}")

    @property
    def model(self) -> str:
        """Getter for model attribute to maintain compatibility"""
        return self.__gemini_model

    def extract_text(self, image_data: bytes, document_type: DocumentType,
                     document_format: DocumentFormat, custom_prompt: Optional[str] = None) -> OCRResult:
        """Extract text from image using Gemini model with structured JSON output for supported documents"""
        try:
            logger.debug(f"Extracting text with model: {self.__gemini_model}")

            # Convert image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')

            # Create prompt based on document type and format
            prompt = self._create_extraction_prompt(document_type, document_format, custom_prompt)

            # Prepare document_content for Gemini API
            content = [
                prompt,
                {
                    "inline_data": {
                        "data": encoded_image,
                        "mime_type": "image/jpeg"
                    }
                }
            ]

            # Make request to Gemini API
            response = self.client.generate_content(
                content,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40
                }
            )

            raw_text = response.text

            # For structured document types, attempt to parse and validate JSON
            structured_data = {}
            if document_type in DOCUMENT_FIELD_MAP:
                parsed_data = self._parse_structured_response(raw_text, document_type)
                structured_data = parsed_data if parsed_data is not None else {}

            return OCRResult(
                raw_text=raw_text,
                structured_data=structured_data,
                provider_used=f"gemini:{self.__gemini_model}",
                language_detected="auto_detected"
            )

        except Exception as e:
            logger.error(f"Gemini OCR error: {e}")
            raise

    @staticmethod
    def _parse_structured_response(response_text: str, document_type: DocumentType) -> Optional[Dict[str, Any]]:
        """Parse and validate structured JSON response"""
        try:
            # Remove triple backticks and 'json' marker if present
            cleaned_text = re.sub(r'```json\n|\n```', '', response_text).strip()

            # Extract JSON by finding the first { and last }
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1

            if json_start == -1 or json_end <= json_start:
                logger.warning(f"No valid JSON found in response for {document_type}")
                return None

            json_text = cleaned_text[json_start:json_end]
            parsed_data = json.loads(json_text)

            # Validate that expected fields are present
            expected_fields = DOCUMENT_FIELD_MAP.get(document_type, [])
            if not expected_fields:
                logger.warning(f"No expected fields defined for {document_type}")
                return parsed_data  # Return full parsed data if no specific fields defined

            validated_data = {
                field: parsed_data.get(field, None)
                for field in expected_fields
            }

            return validated_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response for {document_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing structured response for {document_type}: {e}")
            return None

    def list_available_models(self) -> List[str]:
        """List all available models in Gemini API"""
        return self.available_models
