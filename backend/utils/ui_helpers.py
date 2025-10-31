import json
import logging
from typing import Tuple

from mistralai import Mistral, ImageURLChunk, TextChunk

from backend.core.config import settings
from backend.models.enums import OCRProvider, CorrectionProvider, Language, StructuredOCRResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_default_providers_by_language(language: Language) -> Tuple[OCRProvider, CorrectionProvider]:
    if language == Language.NEPALI:
        return OCRProvider.GEMINI, CorrectionProvider.GEMINI
    else:
        return OCRProvider.MISTRAL, CorrectionProvider.MISTRAL  # Use Mistral for English/math


def parse_corrected_markdown_to_json_mistral(base64_data_url: str, corrected_markdown: str):
    try:
        api_key = settings.MISTRAL_API_KEY
        if not api_key:
            logger.error("MISTRAL_API_KEY environment variable not set")
            return None
        client = Mistral(api_key=api_key)

        chat_response = client.chat.parse(
            model="pixtral-12b-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        ImageURLChunk(image_url=base64_data_url),
                        TextChunk(
                            text=(
                                "This is the image's corrected OCR in markdown:\n"
                                f"<BEGIN_IMAGE_OCR>\n{corrected_markdown}\n<END_IMAGE_OCR>\n"
                                "Please convert this into a clean, structured JSON object with keys and human-readable text, "
                                "preserving math formulas in LaTeX (e.g., \\frac{{dy}}{{dx}}, \\lim_{{\\Delta x \\to 0}})."
                            )
                        ),
                    ],
                },
            ],
            response_format=StructuredOCRResult,
            temperature=0,
        )

        parsed_json_str = chat_response.choices[0].message.parsed.model_dump_json()
        parsed_json = json.loads(parsed_json_str)
        return parsed_json
    except Exception as e:
        logger.error(f"Error parsing corrected markdown: {e}")
        return None


def parse_corrected_markdown_to_json_gemini(base64_data_url: str, corrected_markdown: str):
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.5-pro")

        prompt = (
            "You are a data extractor. Convert the following markdown into a structured JSON object:\n\n"
            f"<BEGIN_IMAGE_OCR>\n{corrected_markdown}\n<END_IMAGE_OCR>\n\n"
            "Make sure the JSON has proper keys and values, and preserve mathematical LaTeX formulas if any.\n"
            "Output only valid JSON without any explanation or markdown."
        )

        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        logger.error(f"Gemini JSON parse error: {e}")
        return None


def parse_corrected_markdown_to_json_geminiopensource(base64_data_url: str, corrected_markdown: str):
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = (
            "Please convert the corrected OCR markdown between the tags below into a clean JSON format:\n\n"
            f"<BEGIN_IMAGE_OCR>\n{corrected_markdown}\n<END_IMAGE_OCR>\n\n"
            "Output only a valid JSON. No other commentary or text should be added."
        )

        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        logger.error(f"GeminiOpenSource JSON parse error: {e}")
        return None


def parse_corrected_markdown_to_json_ollama(base64_data_url: str, corrected_markdown: str):
    try:
        import requests
        prompt = (
            "Convert the following OCR-corrected markdown text between the tags into structured JSON format only.\n\n"
            f"<BEGIN_IMAGE_OCR>\n{corrected_markdown}\n<END_IMAGE_OCR>\n\n"
            "Preserve math formulas in LaTeX, and do not add explanations or markdown."
        )

        payload = {
            "model": "gemma3:4b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(
            f"{settings.OLLAMA_API}/api/generate",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            return json.loads(text)
        else:
            logger.error(f"Ollama JSON parse API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Ollama JSON parse error: {e}")
        return None


def parse_corrected_markdown(provider: CorrectionProvider, base64_data_url: str, corrected_markdown: str):
    return parse_corrected_markdown_to_json_mistral(base64_data_url, corrected_markdown)
    # if provider == CorrectionProvider.MISTRAL or CorrectionProvider.GEMINI:
    #     return parse_corrected_markdown_to_json_mistral(base64_data_url, corrected_markdown)
    # elif provider == CorrectionProvider.GEMINI:
    #     return parse_corrected_markdown_to_json_gemini(base64_data_url, corrected_markdown)
    # elif provider == CorrectionProvider.GEMINI_OPENSOURCE:
    #     return parse_corrected_markdown_to_json_geminiopensource(base64_data_url, corrected_markdown)
    # elif provider == CorrectionProvider.OLLAMA:
    #     return parse_corrected_markdown_to_json_ollama(base64_data_url, corrected_markdown)
    # else:
    #     logger.warning(f"Unsupported correction provider for JSON parsing: {provider}")
    #     return None
