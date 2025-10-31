from __future__ import annotations

from typing import Dict, Any, Optional, List

from fastapi import HTTPException

from backend.app.schemas.ocr_premium import OCRPremiumRequest, OCRPremiumResponse
from backend.document_content.enhance_document_processor import FastAPIDocumentProcessor


def _detect_mime_from_sniff(file_bytes: bytes, fallback: str) -> str:
    # If this is clearly a PDF, override content-type
    if file_bytes[:5] == b"%PDF-":
        return "application/pdf"
    return fallback


def _mk_provider_kwargs(req: OCRPremiumRequest) -> Dict[str, Any]:
    kw: Dict[str, Any] = {}
    if req.provider_config and req.provider_config.ocr_model:
        kw["ocr_model"] = req.provider_config.ocr_model
    if req.provider_config and req.provider_config.correction_model:
        kw["correction_model"] = req.provider_config.correction_model
    return kw


def _to_markdown_from_struct(structured: Any) -> Optional[str]:
    """
    Turn a dict/list structured data into a readable Markdown.
    """
    if not structured:
        return None

    def kv_md(d: Dict[str, Any]) -> str:
        lines = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"### {k}\n")
                lines.append(kv_md(v))
            elif isinstance(v, list):
                lines.append(f"- **{k}**:")
                for item in v:
                    if isinstance(item, (dict, list)):
                        lines.append(f"  - {item!r}")
                    else:
                        lines.append(f"  - {item}")
            else:
                lines.append(f"- **{k}**: {v}")
        return "\n".join(lines)

    if isinstance(structured, dict):
        return kv_md(structured)
    if isinstance(structured, list):
        # List of rows -> table if rows are dicts with same keys
        if structured and all(isinstance(r, dict) for r in structured):
            keys = list({k for row in structured for k in row.keys()})
            header = "| " + " | ".join(keys) + " |\n| " + " | ".join(["---"] * len(keys)) + " |"
            rows = []
            for row in structured:
                rows.append("| " + " | ".join(str(row.get(k, "")) for k in keys) + " |")
            return "\n".join([header] + rows)
        # Fallback bullet list
        return "\n".join(f"- {item!r}" for item in structured)
    # Fallback
    return None
