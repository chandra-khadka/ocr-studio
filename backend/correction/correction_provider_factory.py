import logging

from backend.core.config import settings
from backend.correction.base import BaseCorrectionProvider
from backend.correction.gemini_corrector import GeminiCorrectionProvider
from backend.correction.mistral_corrector import MistralCorrectionProvider
from backend.correction.ollama_corrector import OllamaCorrectionProvider
from backend.correction.gemini_opensource_corrector import GeminiOpensourceCorrectionProvider
from backend.correction.vllm_corrector import VLLMCorrectionProvider
from backend.models.enums import CorrectionProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrectionProviderFactory:
    @staticmethod
    def create_provider(provider_type: CorrectionProvider, **kwargs) -> BaseCorrectionProvider:
        try:
            if provider_type == CorrectionProvider.GEMINI:
                if not settings.GEMINI_API_KEY:
                    logger.error("GEMINI_API_KEY is not set")
                    raise ValueError("Gemini API key is missing")
                model = kwargs.get('correction_model') or 'gemini-1.5-flash'
                provider = GeminiCorrectionProvider(api_key=settings.GEMINI_API_KEY, model=model)
                provider.configure()
                return provider
            elif provider_type == CorrectionProvider.MISTRAL:
                if not settings.MISTRAL_API_KEY:
                    logger.error("MISTRAL_API_KEY is not set")
                    raise ValueError("Mistral API key is missing")
                model = kwargs.get('correction_model') or 'mistral-small-latest'
                provider = MistralCorrectionProvider(api_key=settings.MISTRAL_API_KEY, model=model)
                provider.configure()
                return provider
            elif provider_type == CorrectionProvider.OLLAMA:
                endpoint = kwargs.get('endpoint', settings.OLLAMA_API)
                model = kwargs.get('correction_model') or 'gemma3:4b'
                logger.info(f"Creating OllamaCorrectionProvider with endpoint={endpoint}, model={model}")
                return OllamaCorrectionProvider(endpoint=endpoint, model=model)
            elif provider_type == CorrectionProvider.GEMINI_OPENSOURCE:
                if not settings.GEMINI_API_KEY:
                    logger.error("GEMINI_API_KEY is not set")
                    raise ValueError("Gemini API key is missing")
                model = kwargs.get('correction_model') or 'models/gemma-3-4b-it'
                logger.info(f"Creating GeminiOpensourceCorrectionProvider with model={model}")
                provider = GeminiOpensourceCorrectionProvider(api_key=settings.GEMINI_API_KEY, model=model)
                provider.configure()
                return provider
            elif provider_type == CorrectionProvider.VLLM:
                model = kwargs.get('correction_model') or 'google/gemma-3-12b-it'
                server_url = kwargs.get('server_url', settings.VLLM_SERVER_URL)
                logger.info(f"Creating VLLMCorrectionProvider with model={model}, server_url={server_url}")
                provider = VLLMCorrectionProvider(api_key="", model=model, server_url=server_url)
                provider.configure()
                return provider
            else:
                raise ValueError(f"Unsupported correction provider: {provider_type}")
        except Exception as e:
            logger.error(f"Failed to create provider {provider_type}: {e}")
            raise
