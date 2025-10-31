"""
Ollama OCR Provider for local model inference
Supports Gemma3 models: 4b, 8b, 12b, 27b
Updated to support structured JSON extraction for specific document types
"""
import base64
import json
from typing import List, Dict, Any, Optional

import requests

from backend.config import logger
from backend.core.config import settings
from backend.models.enums import DocumentType, DocumentFormat
from backend.models.mappings import DOCUMENT_FIELD_MAP
from backend.models.schemas import OCRResult
from backend.ocr.base import BaseOCRProvider


class OllamaOCRProvider(BaseOCRProvider):
    """Ollama provider for OCR using Gemma3 models with structured JSON extraction"""

    def __init__(self, api_key: str, endpoint: str = settings.OLLAMA_API, model: str = "gemma3:4b"):
        # Store endpoint and model in unique attributes to avoid parent class conflicts
        self.__endpoint = endpoint.rstrip('/')
        self.__ollama_model = model
        self.available_models = []
        # Call parent initializer
        super().__init__(api_key=api_key)
        logger.debug(f"Initialized OllamaOCRProvider with model: {self.__ollama_model} at endpoint: {self.__endpoint}")
        # Configure after parent initialization to ensure attributes are preserved
        self.configure()

    def configure(self):
        """Configure the Ollama connection and select an appropriate model"""
        try:
            logger.debug(f"Configuring with model: {self.__ollama_model}")
            # Test connection to Ollama
            response = requests.get(f"{self.__endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                self.available_models = [model["name"] for model in response.json().get("models", [])]
                logger.info(f"Available Ollama models: {self.available_models}")

                # Check if selected model is available
                current_model = self.__ollama_model
                if current_model not in self.available_models:
                    # Try fallback models
                    fallback_models = ["gemma2:4b", "llava:7b", "gemma2:8b"]
                    for fallback in fallback_models:
                        if fallback in self.available_models:
                            logger.warning(f"Model {current_model} not found, using {fallback}")
                            self.__ollama_model = fallback
                            break
                    else:
                        raise ValueError(f"No suitable model found. Available: {self.available_models}")
            else:
                raise ConnectionError(f"Failed to connect to Ollama at {self.__endpoint}")

        except requests.RequestException as e:
            logger.error(f"Failed to configure Ollama API: {str(e)}")
            raise ConnectionError(f"Cannot connect to Ollama at {self.__endpoint}: {str(e)}")

    @property
    def model(self) -> str:
        """Getter for model attribute to maintain compatibility"""
        return self.__ollama_model

    def extract_text(self, image_data: bytes, document_type: DocumentType,
                     document_format: DocumentFormat, custom_prompt: Optional[str] = None) -> OCRResult:
        """Extract text from image using Ollama vision model with structured JSON output for supported documents"""
        try:
            logger.debug(f"Extracting text with model: {self.__ollama_model}")

            # Convert image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')

            # Create prompt based on document type and format
            prompt = self._create_extraction_prompt(document_type, document_format)

            # Prepare request for Ollama API
            payload = {
                "model": self.__ollama_model,
                "prompt": prompt,
                "images": [encoded_image],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }

            # Make request to Ollama
            response = requests.post(
                f"{self.__endpoint}/api/generate",
                json=payload,
                timeout=120  # OCR can take time
            )

            if response.status_code == 200:
                result = response.json()
                raw_text = result.get("response", "")

                # For structured document types, attempt to parse and validate JSON
                structured_data = None
                if document_type in DOCUMENT_FIELD_MAP:
                    structured_data = self._parse_structured_response(raw_text, document_type)

                return OCRResult(
                    raw_text=raw_text,
                    structured_data=structured_data,
                    provider_used=f"ollama:{self.__ollama_model}",
                    language_detected="auto_detected"
                )
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Ollama OCR error: {e}")
            raise

    @staticmethod
    def _parse_structured_response(response_text: str, document_type: DocumentType) -> Optional[Dict[str, Any]]:
        """Parse and validate structured JSON response"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_data = json.loads(json_text)

                # Validate that expected fields are present
                expected_fields = DOCUMENT_FIELD_MAP.get(document_type, [])
                validated_data = {}

                for field in expected_fields:
                    validated_data[field] = parsed_data.get(field, None)

                return validated_data
            else:
                logger.warning(f"No valid JSON found in response for {document_type}")
                return None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response for {document_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing structured response: {e}")
            return None

    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model to Ollama"""
        try:
            payload = {"name": model_name}
            response = requests.post(
                f"{self.__endpoint}/api/pull",
                json=payload,
                timeout=600  # Model download can take time
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    def list_available_models(self) -> List[str]:
        """List all available models in Ollama"""
        try:
            response = requests.get(f"{self.__endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                return [model["name"] for model in response.json().get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
