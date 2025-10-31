import logging
import sys
from pathlib import Path as _P
from typing import Tuple

from backend.correction.correction_provider_factory import CorrectionProviderFactory
from backend.models.enums import CorrectionProvider, DocumentType, DocumentFormat, Language

_engine = _P(__file__).resolve().parents[2] / "ocr-engine"
if _engine.exists():
    sys.path.append(str(_engine))

logger = logging.getLogger(__name__)


def _split_provider(provider_str: str) -> Tuple[str, str | None]:
    parts = provider_str.split(":", 1)
    if len(parts) == 2:
        return parts[0].strip().upper(), parts[1].strip()
    return provider_str.strip().upper(), None


GOVERNMENT_PROMPT = (
    "You are correcting OCR for Nepali government documents (citizenship, licenses, "
    "voter id, passport, national id etc). Fix OCR artifacts, preserve all original content and language. "
    "Return clean Markdown. If tables or boxes appear, render as Markdown tables. "
    "Normalize dates to YYYY-MM-DD when unambiguous; otherwise keep original. "
    "Do not hallucinate or add fields. Keep headings and stamps as text."
)

GENERAL_PROMPT = (
    "Correct OCR artifacts while preserving the original meaning and structure. "
    "Return clean Markdown. Render tables as Markdown tables. "
    "Do not rewrite, summarize, or add content. Keep lists and headings."
)


async def run_correction(
        *,
        text: str,
        model_str: str,
        prompt: str | None,
        document_type: DocumentType,
) -> str:
    provider_name, correction_model = _split_provider(model_str)
    provider_enum = CorrectionProvider[provider_name]

    # Choose a prompt: user-provided > hardcoded-by-doc-type
    final_prompt = (prompt or "").strip()
    if not final_prompt:
        final_prompt = GOVERNMENT_PROMPT if document_type == DocumentType.GOVERNMENT_DOCUMENT else GENERAL_PROMPT

    provider = CorrectionProviderFactory.create_provider(
        provider_enum,
        correction_model=correction_model,
        instruction_prompt=final_prompt,
    )

    corrected = provider.correct_text(
        raw_text=text,
        document_type=document_type,
        document_format=DocumentFormat.STANDARD,
        language=Language.AUTO_DETECT,
    )
    return corrected
