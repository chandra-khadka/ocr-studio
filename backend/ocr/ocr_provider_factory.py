from backend.config import logger
from backend.core.config import settings
from backend.models.enums import OCRProvider
from backend.ocr.base import BaseOCRProvider
from backend.ocr.gemini_opensource_provider import GeminiOpensourceOCRProvider
from backend.ocr.gemini_provider import GeminiOCRProvider
from backend.ocr.mistral_provider import MistralOCRProvider
from backend.ocr.ollama_provider import OllamaOCRProvider
from backend.ocr.vllm_provider import VLLMProvider


class OCRProviderFactory:
    @staticmethod
    def create_provider(provider_type: OCRProvider, **kwargs) -> BaseOCRProvider:
        try:
            if provider_type == OCRProvider.GEMINI:
                if not settings.GEMINI_API_KEY:
                    logger.error("GEMINI_API_KEY is not set")
                    raise ValueError("Gemini API key is missing")
                model = kwargs.get('ocr_model') or 'gemini-2.0-flash-lite-001'
                return GeminiOCRProvider(api_key=settings.GEMINI_API_KEY, model=model)
            elif provider_type == OCRProvider.MISTRAL:
                if not settings.MISTRAL_API_KEY:
                    logger.error("MISTRAL_API_KEY is not set")
                    raise ValueError("Mistral API key is missing")
                model = kwargs.get('ocr_model') or 'mistral-ocr-latest'
                return MistralOCRProvider(api_key=settings.MISTRAL_API_KEY, model=model)
            elif provider_type == OCRProvider.OLLAMA:
                endpoint = kwargs.get('endpoint', settings.OLLAMA_API)
                model = kwargs.get('ocr_model') or 'gemma3:4b'
                logger.info(f"Creating OllamaOCRProvider with endpoint={endpoint}, model={model}")
                return OllamaOCRProvider(api_key="", endpoint=endpoint, model=model)
            elif provider_type == OCRProvider.GEMINI_OPENSOURCE:
                if not settings.GEMINI_API_KEY:
                    logger.error("GEMINI_API_KEY is not set")
                    raise ValueError("Gemini API key is missing")
                model = kwargs.get('ocr_model') or 'models/gemma-3-4b-it'
                logger.info(f"Creating GeminiOpensourceOCRProvider with model={model}")
                return GeminiOpensourceOCRProvider(api_key=settings.GEMINI_API_KEY, model=model)
            elif provider_type == OCRProvider.VLLM:
                model = kwargs.get('ocr_model') or 'google/gemma-3-12b-it'
                server_url = kwargs.get('server_url', settings.VLLM_SERVER_URL)
                logger.info(f"Creating VLLMProvider with model={model}, server_url={server_url}")
                return VLLMProvider(api_key="", model=model, server_url=server_url)
            else:
                raise ValueError(f"Unsupported OCR provider: {provider_type}")
        except Exception as e:
            logger.error(f"Failed to create OCR provider {provider_type}: {e}")
            raise
