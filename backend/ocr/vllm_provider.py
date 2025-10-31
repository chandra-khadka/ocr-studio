import base64
import json
import re
from typing import List, Dict, Any, Optional

import httpx

from backend.config import logger
from backend.models.enums import DocumentType, DocumentFormat
from backend.models.mappings import DOCUMENT_FIELD_MAP
from backend.models.schemas import OCRResult
from backend.ocr.base import BaseOCRProvider


class VLLMProvider(BaseOCRProvider):
    """VLLM provider for OCR using models served via OpenAI-compatible API"""

    def __init__(self, api_key: str, model: str = "google/gemma-3-12b-it",
                 server_url: str = "https://vllm.server.com.np"):  # Removed /v1 from default
        self.__vllm_model = model
        self.server_url = server_url.rstrip('/')  # Remove trailing slash if present
        self.available_models = []
        self.client: Optional[httpx.Client] = None
        super().__init__(api_key=api_key)
        logger.debug(f"Initialized VLLMProvider with model: {self.__vllm_model}, server: {self.server_url}")
        self.configure()

    def configure(self):
        """Configure the VLLM connection and create HTTPX client"""
        logger.debug(f"Configuring VLLMProvider with model: {self.__vllm_model}")
        try:
            self.client = httpx.Client(timeout=30.0)
            logger.info(f"HTTPX client configured for VLLM model '{self.model}'")
        except Exception as e:
            logger.error(f"Failed to configure HTTPX client: {str(e)}")
            raise ConnectionError(f"Cannot configure HTTPX client: {str(e)}")

    @property
    def model(self) -> str:
        return self.__vllm_model

    def extract_text(self, image_data: bytes, document_type: DocumentType,
                     document_format: DocumentFormat, custom_prompt: Optional[str] = None) -> OCRResult:
        """Extract text from image using VLLM model with structured JSON output"""
        if self.client is None:
            raise RuntimeError("HTTPX client is not configured. Call configure() before using extract_text.")

        try:
            logger.debug(f"Starting OCR extraction using model: {self.__vllm_model}")

            encoded_image = base64.b64encode(image_data).decode('utf-8')
            prompt = self._create_extraction_prompt(document_type, document_format, custom_prompt)

            payload = {
                "model": self.__vllm_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "top_p": 0.9
            }

            # Fixed URL construction
            url = f"{self.server_url}/v1/chat/completions"
            logger.debug(f"Sending request to VLLM at {url}")

            # Add headers to match curl request
            headers = {
                "Content-Type": "application/json"
            }

            # Log request details for debugging
            logger.debug(f"Request payload keys: {list(payload.keys())}")
            logger.debug(f"Model in payload: {payload.get('model')}")
            logger.debug(f"Request headers: {headers}")

            response = self.client.post(url, json=payload, headers=headers)

            # Log response details before raising for status
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            if response.status_code != 200:
                logger.error(f"Response content: {response.text}")

            response.raise_for_status()

            raw_text = response.json()["choices"][0]["message"]["content"]

            structured_data = {}
            if document_type in DOCUMENT_FIELD_MAP:
                parsed_data = self._parse_structured_response(raw_text, document_type)
                structured_data = parsed_data if parsed_data else {}

            return OCRResult(
                raw_text=raw_text,
                structured_data=structured_data,
                provider_used=f"vllm:{self.__vllm_model}",
                language_detected="auto_detected"
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during VLLM OCR request: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during VLLM OCR extraction: {e}")
            raise

    @staticmethod
    def _parse_structured_response(response_text: str, document_type: DocumentType) -> Optional[Dict[str, Any]]:
        """Parse and validate structured JSON response"""
        try:
            cleaned_text = re.sub(r'```json\n|\n```', '', response_text).strip()
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1

            if json_start == -1 or json_end <= json_start:
                logger.warning(f"No valid JSON found in response for {document_type}")
                return None

            json_text = cleaned_text[json_start:json_end]
            parsed_data = json.loads(json_text)

            expected_fields = DOCUMENT_FIELD_MAP.get(document_type, [])
            if not expected_fields:
                logger.warning(f"No expected fields defined for {document_type}")
                return parsed_data

            validated_data = {field: parsed_data.get(field, None) for field in expected_fields}
            return validated_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response for {document_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing structured response for {document_type}: {e}")
            return None

    def list_available_models(self) -> List[str]:
        """List all available models in VLLM API"""
        return self.available_models

    def __del__(self):
        """Ensure HTTPX client is properly closed"""
        if self.client:
            self.client.close()
