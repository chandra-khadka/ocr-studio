"""
MistralOCRProvider for Mistral models
Supports OCR processing and (optional) prompt-driven post-processing for structured extraction
"""

import base64
import json
from typing import List, Dict, Any, Optional

from mistralai import Mistral, ImageURLChunk

from backend.config import logger
from backend.models.enums import DocumentType, DocumentFormat
from backend.models.mappings import DOCUMENT_FIELD_MAP
from backend.models.schemas import OCRResult
from backend.ocr.base import BaseOCRProvider


class MistralOCRProvider(BaseOCRProvider):
    """
    Mistral provider for OCR with optional prompt-driven post-processing (chat).
    - Passes the image to OCR endpoint to get faithful markdown text.
    - If a prompt is desired, runs a second-pass chat completion to transform/extract.
    """

    def __init__(
            self,
            api_key: str,
            model: str = "mistral-ocr-latest",
            postprocess_model: str = "mistral-large-latest",  # used for chat (prompt) pass
    ):
        self.model = model
        self.postprocess_model = postprocess_model
        self.available_models = [model]
        self.client: Optional[Mistral] = None
        super().__init__(api_key=api_key)
        self.configure()

    def configure(self):
        """Configure the Mistral client."""
        try:
            self.client = Mistral(api_key=self.api_key)
            logger.info(
                f"Configured Mistral client with OCR model '{self.model}' "
                f"and postprocess model '{self.postprocess_model}'"
            )
        except Exception as e:
            logger.error(f"Failed to configure Mistral API: {str(e)}")
            raise ConnectionError(f"Cannot connect to Mistral API: {str(e)}")

    def extract_text(
            self,
            image_data: bytes,
            document_type: DocumentType,
            document_format: DocumentFormat,
            custom_prompt: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from image using Mistral OCR.
        If a prompt is requested or a structured type is known, run a second chat pass to shape output.
        """
        try:
            logger.debug(f"Starting OCR extraction for doc type: {document_type}")

            # 1) OCR (high-fidelity transcription)
            encoded_image = base64.b64encode(image_data).decode("utf-8")
            base64_data_url = f"data:image/jpeg;base64,{encoded_image}"

            ocr_resp = self.client.ocr.process(
                document=ImageURLChunk(image_url=base64_data_url),
                model=self.model,
            )
            raw_text = ocr_resp.pages[0].markdown if getattr(ocr_resp, "pages", None) else ""

            # Default structured_data straight from raw OCR (if JSON blocks present)
            structured_data = None
            needs_prompting = bool(custom_prompt) or (document_type in DOCUMENT_FIELD_MAP)

            # 2) Optional prompt-driven post-processing
            if needs_prompting:
                try:
                    prompt = self._create_extraction_prompt(
                        document_type=document_type,
                        document_format=document_format,
                        custom_prompt=custom_prompt,
                    )
                    logger.debug("Running post-processing chat with custom prompt...")

                    chat = self.client.chat.complete(
                        model=self.postprocess_model,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a precise, conservative post-processor for OCR output. "
                                    "Do not invent content; only transform/structure what is provided."
                                ),
                            },
                            {"role": "user", "content": prompt},
                            {
                                "role": "user",
                                "content": (
                                        "Here is the OCR text (markdown) from the image. "
                                        "Apply the instructions strictly:\n\n" + raw_text
                                ),
                            },
                        ],
                        temperature=0.1,
                        top_p=0.9,
                        max_tokens=4096,
                    )

                    # Mistral SDK response shape: choices[0].message.content (string or list of content parts)
                    post_text = ""
                    try:
                        choice = chat.choices[0]
                        content = getattr(choice.message, "content", "")
                        if isinstance(content, list):
                            # some SDK versions return content as a list of parts
                            post_text = "".join(
                                part.get("text", "") if isinstance(part, dict) else str(part)
                                for part in content
                            )
                        else:
                            post_text = str(content)
                    except Exception:
                        post_text = ""

                    # If post-processing produced any text, try to parse structured JSON from it;
                    # else fall back to parsing from raw_text
                    if post_text.strip():
                        structured_data = self._parse_structured_response(post_text, document_type)
                        # If no JSON found in post_text, try raw_text as a last resort
                        if structured_data is None and document_type in DOCUMENT_FIELD_MAP:
                            structured_data = self._parse_structured_response(raw_text, document_type)
                    else:
                        if document_type in DOCUMENT_FIELD_MAP:
                            structured_data = self._parse_structured_response(raw_text, document_type)

                except Exception as pe:
                    logger.warning(f"Post-processing (chat) failed; returning raw OCR only. Error: {pe}")
                    if document_type in DOCUMENT_FIELD_MAP:
                        structured_data = self._parse_structured_response(raw_text, document_type)

            else:
                # No prompting requested — try direct JSON pickup (if user embedded any)
                if document_type in DOCUMENT_FIELD_MAP:
                    structured_data = self._parse_structured_response(raw_text, document_type)

            return OCRResult(
                raw_text=raw_text,  # faithful OCR markdown
                structured_data=structured_data,
                provider_used=f"mistral:{self.model}",
                language_detected="auto_detected",
            )

        except Exception as e:
            logger.error(f"Mistral OCR error: {e}")
            raise

    @staticmethod
    def _parse_structured_response(
            response_text: str,
            document_type: DocumentType,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts to extract a JSON object from the (possibly prompted) text,
        then validates and returns only the expected fields for the document type.
        """
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed_data = json.loads(json_text)
                expected_fields = DOCUMENT_FIELD_MAP.get(document_type, [])
                return {field: parsed_data.get(field, None) for field in
                        expected_fields} if expected_fields else parsed_data
            else:
                logger.warning(f"No JSON detected in result for {document_type}")
                return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for {document_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during structured extraction: {e}")
            return None

    def list_available_models(self) -> List[str]:
        """Returns available Mistral models (static in this case)."""
        return self.available_models
