from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Mapping, Sequence

import httpx
from fastapi import APIRouter, Depends, HTTPException

from backend.app.deps import verify_api_key
from backend.app.schemas.ocr_premium import OCRPremiumResponse
from backend.config import logger
from backend.models.enums import OCRProvider
from backend.models.schemas import ImageProcessingRequest
from backend.service.ocr_service import OCRService
from backend.service.preprocess_image import dynamic_preprocess_image

router = APIRouter()


def _prune_none_deep(obj: Any) -> Any:
    """
    Recursively remove None values from dicts/lists.
    Keeps falsy-but-valid values (0, False, "", [], {}) as-is.
    """
    if isinstance(obj, Mapping):
        out = {}
        for k, v in obj.items():
            pv = _prune_none_deep(v)
            if pv is not None:  # only drop actual None
                out[k] = pv
        return out
    if isinstance(obj, list):
        return [_prune_none_deep(v) for v in obj if v is not None]
    return obj


# ----------------- MIME helpers -----------------

def _sniff_mime(file_bytes: bytes) -> Optional[str]:
    if not file_bytes or len(file_bytes) < 8:
        return None
    head = file_bytes[:16]
    if head.startswith(b"%PDF"): return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"): return "image/gif"
    if head.startswith(b"RIFF") and b"WEBP" in head[8:16]: return "image/webp"
    if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"): return "image/tiff"
    if head.startswith(b"BM"): return "image/bmp"
    return None


def _is_supported(mime: Optional[str]) -> bool:
    return bool(mime) and (mime == "application/pdf" or mime.startswith("image/"))


# ----------------- generic helpers -----------------

def _enum_val(e) -> Optional[str]:
    try:
        return e.value if hasattr(e, "value") else (e.name if hasattr(e, "name") else str(e))
    except Exception:
        return None


def _safe_decode_bytes(b: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return ""


def _maybe_json_loads(s: str) -> Any:
    s2 = s.strip()
    if not s2:
        return None
    if s2[0] in "{[" and s2[-1] in "]}":
        try:
            return json.loads(s2)
        except Exception:
            return None
    return None


def _flatten_dict(d: Mapping[str, Any], parent: str = "", sep: str = ".") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        key = f"{parent}{sep}{k}" if parent else str(k)
        if isinstance(v, Mapping):
            out.update(_flatten_dict(v, key, sep))
        elif isinstance(v, list):
            # index lists for determinism
            for i, item in enumerate(v):
                if isinstance(item, Mapping):
                    out.update(_flatten_dict(item, f"{key}[{i}]", sep))
                else:
                    out[f"{key}[{i}]"] = item
        else:
            out[key] = v
    return out


def _dict_to_kv_text(d: Dict[str, Any]) -> str:
    if not d:
        return ""
    # Prefer human-important keys first, then alphabetic
    preferred = [
        "full_name", "full_name_np", "full_name_en",
        "citizenship_no", "citizenship_number",
        "date_of_birth", "dob_text_np", "dob_structured",
        "place_of_birth", "birthplace_np",
        "gender",
        "father_name", "mother_name", "grandfather_name",
        "permanent_address", "current_address", "father_address", "mother_address",
        "citizenship_type", "certificate_type_np", "issuing_office_np",
    ]
    flat = _flatten_dict(d)
    lines: List[str] = []
    used = set()
    for k in preferred:
        if k in flat:
            lines.append(f"{k}: {flat[k]}")
            used.add(k)
    for k in sorted(k for k in flat.keys() if k not in used):
        lines.append(f"{k}: {flat[k]}")
    return "\n".join(lines)


def _summarize_list(lst: Sequence[Any]) -> str:
    if not lst:
        return ""
    # If list of dicts, show a compact table-like block
    if all(isinstance(x, Mapping) for x in lst):
        # gather keys (cap at some size to keep it readable)
        keys = list({k for item in lst for k in item.keys()})
        keys.sort()
        lines = []
        lines.append("items:")
        for i, item in enumerate(lst[:50]):  # avoid gigantic outputs
            row = ", ".join(f"{k}={item.get(k)!r}" for k in keys if k in item)
            lines.append(f"  - {row}")
        if len(lst) > 50:
            lines.append(f"  ... ({len(lst) - 50} more)")
        return "\n".join(lines)
    # Otherwise, simple bullet list
    items = [str(x) for x in lst[:200]]
    if len(lst) > 200:
        items.append(f"... ({len(lst) - 200} more)")
    return "\n".join(f"- {it}" for it in items)


def _extract_common_fields(d: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Pulls out common keys if present; leaves unknowns in structured_data.
    """
    out = {
        "raw_text": d.get("raw_text"),
        "corrected_text": d.get("corrected_text"),
        "text": d.get("text"),
        "pages": d.get("pages"),
        "images": d.get("images"),
        "language_detected": d.get("language_detected"),
        "confidence": d.get("confidence"),
        "document_type": d.get("document_type"),
        "structured_data": d.get("structured_data"),
    }
    # structured_json may be dict or JSON string
    sj = d.get("structured_json")
    if isinstance(sj, Mapping):
        sd = sj.get("structured_data")
        if isinstance(sd, Mapping):
            out["structured_data"] = sd
    elif isinstance(sj, str):
        parsed = _maybe_json_loads(sj)
        if isinstance(parsed, Mapping):
            sd = parsed.get("structured_data")
            if isinstance(sd, Mapping):
                out["structured_data"] = sd
    return out


def _looks_like_pure_structured(d: Mapping[str, Any]) -> bool:
    textish = {"raw_text", "corrected_text", "text", "pages", "images", "language_detected", "confidence"}
    return not any(k in d for k in textish)


def _normalize_any_result(result: Any) -> Dict[str, Any]:
    """
    Returns dict with keys: text(str), raw_text, corrected_text, pages, images, structured_data, meta_partial
    meta_partial: {language_detected, confidence, document_type}
    """
    text: str = ""
    raw_text = None
    corrected_text = None
    pages = None
    images = None
    structured_data: Optional[Dict[str, Any]] = None
    language_detected = None
    confidence = None
    document_type = None

    # 1) bytes -> decode → keep parsing flow on decoded str
    if isinstance(result, (bytes, bytearray)):
        s = _safe_decode_bytes(bytes(result))
        result = s if s else ""

    # 2) str → maybe JSON → else text
    if isinstance(result, str):
        parsed = _maybe_json_loads(result)
        if parsed is None:
            text = result  # plain text
            return {
                "text": text,
                "raw_text": raw_text,
                "corrected_text": corrected_text,
                "pages": pages,
                "images": images,
                "structured_data": structured_data,
                "meta_partial": {"language_detected": language_detected, "confidence": confidence,
                                 "document_type": document_type},
            }
        result = parsed  # fallthrough to dict/list branches

    # 3) list → summarize and also consider structured_data
    if isinstance(result, list):
        text = _summarize_list(result)
        # If list of dicts, keep as structured_data
        if all(isinstance(x, Mapping) for x in result):
            structured_data = {"items": result}
        return {
            "text": text,
            "raw_text": raw_text,
            "corrected_text": corrected_text,
            "pages": pages,
            "images": images,
            "structured_data": structured_data,
            "meta_partial": {"language_detected": language_detected, "confidence": confidence,
                             "document_type": document_type},
        }

    # 4) mapping / pydantic-like
    if isinstance(result, Mapping):
        # pydantic BaseModel compatibility (model_dump)
        if hasattr(result, "model_dump"):
            try:
                result = result.model_dump()
            except Exception:
                result = dict(result)

        common = _extract_common_fields(result)
        raw_text = common["raw_text"]
        corrected_text = common["corrected_text"]
        pages = common["pages"]
        images = common["images"]
        language_detected = common["language_detected"]
        confidence = common["confidence"]
        document_type = common["document_type"]
        structured_data = common["structured_data"]

        # If the entire dict is “pure structured”, treat it as structured_data
        if structured_data is None and _looks_like_pure_structured(result):
            structured_data = dict(result)

        # Decide text (priority: corrected > raw > text > pages join > structured serialization > fallback)
        if isinstance(corrected_text, str) and corrected_text.strip():
            text = corrected_text
        elif isinstance(raw_text, str) and raw_text.strip():
            text = raw_text
        elif isinstance(common["text"], str) and common["text"].strip():
            text = common["text"]
        else:
            # pages
            if isinstance(pages, list) and pages:
                page_texts: List[str] = []
                for p in pages:
                    if isinstance(p, Mapping):
                        for k in ("text", "raw_text", "content"):
                            val = p.get(k)
                            if isinstance(val, str) and val.strip():
                                page_texts.append(val)
                                break
                    elif isinstance(p, str) and p.strip():
                        page_texts.append(p)
                if page_texts:
                    text = "\n\n".join(page_texts)

            # structured fallback
            if not text and isinstance(structured_data, Mapping):
                text = _dict_to_kv_text(structured_data)

        # final fallback
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        return {
            "text": text,
            "raw_text": raw_text if isinstance(raw_text, str) else None,
            "corrected_text": corrected_text if isinstance(corrected_text, str) else None,
            "pages": pages if isinstance(pages, list) else None,
            "images": images if isinstance(images, list) else None,
            "structured_data": structured_data if isinstance(structured_data, Mapping) else None,
            "meta_partial": {"language_detected": language_detected, "confidence": confidence,
                             "document_type": document_type},
        }

    # 5) numbers / other scalars
    if isinstance(result, (int, float, bool)):
        text = str(result)
    else:
        # last resort repr
        text = str(result) if result is not None else ""

    return {
        "text": text,
        "raw_text": None,
        "corrected_text": None,
        "pages": None,
        "images": None,
        "structured_data": None,
        "meta_partial": {"language_detected": None, "confidence": None, "document_type": None},
    }


@router.post(
    "",
    response_model=OCRPremiumResponse,
    dependencies=[Depends(verify_api_key)],
)
async def ocr_premium(request: ImageProcessingRequest):
    """
    Endpoint to process an image **or PDF** from a URL or base64-encoded string for OCR and correction.
    Robust to any provider output shape (dict/list/JSON string/plain text/bytes).
    """
    try:
        if bool(request.image_url) == bool(request.base64_image):
            raise HTTPException(status_code=400,
                                detail="Provide either an image/PDF URL or base64 string, but not both.")

        if request.image_url:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(str(request.image_url))
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch file from URL.")
            file_bytes = r.content
            header_ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower() or None
            file_type = _sniff_mime(file_bytes) or header_ct
        else:
            b64 = request.base64_image
            data_uri_mime = None

            # Accept data URLs like: data:image/png;base64,AAAA...
            if isinstance(b64, str) and b64.startswith("data:"):
                # Extract MIME & payload safely
                try:
                    header, _, payload = b64.partition(",")
                    # header example: "data:image/png;base64"
                    mime_part = header[5:]  # drop 'data:'
                    # take up to the first ';' as the MIME (e.g., "image/png")
                    data_uri_mime = mime_part.split(";")[0].strip().lower() or None
                    b64 = payload
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid data URI format for base64 content.")

            # Normalize whitespace and padding
            b64 = (b64 or "").strip()
            # Some clients send base64 in form-encoded bodies where '+' becomes space.
            # If you EVER accept form-encoded, you'd need: b64 = b64.replace(" ", "+")
            # For JSON bodies, we keep it strict; still, remove common whitespace:
            b64 = "".join(b64.split())

            # Fix padding (base64 length must be multiple of 4)
            missing = (-len(b64)) % 4
            if missing:
                b64 += "=" * missing

            # Try standard first, then urlsafe alphabet
            decoded: bytes = b""
            try:
                decoded = base64.b64decode(b64, validate=False)
            except Exception:
                try:
                    decoded = base64.urlsafe_b64decode(b64)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid base64 string: {str(e)}")

            file_bytes = decoded

            # Prefer MIME from data-URI; else sniff
            file_type = data_uri_mime or _sniff_mime(file_bytes)

            # As a last resort, try to open via PIL to validate & infer type
            if not file_type:
                try:
                    from PIL import Image
                    import io
                    with Image.open(io.BytesIO(file_bytes)) as im:
                        fmt = (im.format or "").upper()
                        # Map PIL format -> MIME
                        pil2mime = {
                            "JPEG": "image/jpeg",
                            "PNG": "image/png",
                            "GIF": "image/gif",
                            "WEBP": "image/webp",
                            "TIFF": "image/tiff",
                            "BMP": "image/bmp",
                            "PDF": "application/pdf",
                            "HEIC": "image/heic",  # if pillow-heif installed
                            "HEIF": "image/heif",
                        }
                        file_type = pil2mime.get(fmt)
                except Exception:
                    pass

        if not _is_supported(file_type):
            raise HTTPException(status_code=400,
                                detail=f"Unsupported or unknown file type '{file_type}'. Only images or PDFs are "
                                       f"allowed.")

        preprocessing_report = None
        if request.ocr_provider != OCRProvider.MISTRAL:
            if file_type != "application/pdf" and file_type and file_type.startswith("image/"):
                try:
                    processed_bytes, preprocessing_report = dynamic_preprocess_image(
                        file_bytes,
                        preprocessing_options={"denoise": {"strength": 7, "template": 7, "search": 21}}
                    )

                    file_bytes = processed_bytes
                    file_type = "image/jpeg"
                    logger.info("Dynamic preprocessing applied to image input.")
                except Exception as e:
                    logger.warning(f"Dynamic preprocessing failed; proceeding with original image. Error: {e}")

        # ---- OCR pipeline ----
        result = await OCRService.process_image_url_or_base64(
            file_bytes=file_bytes,
            file_type=file_type,
            request=request,
        )

        # ---- Normalize ANY provider shape ----
        norm = _normalize_any_result(result)

        # Determine effective document type (request takes precedence, else provider)
        req_doc_type = _enum_val(getattr(request, "document_type", None)) or ""
        eff_doc_type = (req_doc_type or _enum_val(norm["meta_partial"]["document_type"]) or "").upper()

        if eff_doc_type == "GOVERNMENT_DOCUMENT":
            if isinstance(norm["structured_data"], (dict, list)):
                pruned = _prune_none_deep(norm["structured_data"])
                norm["structured_data"] = pruned
                if not (norm["corrected_text"] or norm["raw_text"] or norm["pages"]):
                    if isinstance(pruned, dict):
                        norm["text"] = _dict_to_kv_text(pruned)
                    elif isinstance(pruned, list):
                        pass

        meta = {
            "language_detected": norm["meta_partial"]["language_detected"],
            "confidence": norm["meta_partial"]["confidence"],
            "document_type": _enum_val(
                norm["meta_partial"]["document_type"] or getattr(request, "document_type", None)
            ),
            "ocr_provider": _enum_val(getattr(request, "ocr_provider", None)),
            "correction_provider": _enum_val(getattr(request, "correction_provider", None)),
            "preprocessing": {"enabled": bool(preprocessing_report), **(preprocessing_report or {})},
        }

        payload = OCRPremiumResponse(
            text=norm["text"],
            pages=norm["pages"],
            images=norm["images"],
            raw_text=norm["raw_text"],
            corrected_text=norm["corrected_text"],
            structured_data=norm["structured_data"],
            meta=meta,
        )
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image/PDF from URL/base64: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
