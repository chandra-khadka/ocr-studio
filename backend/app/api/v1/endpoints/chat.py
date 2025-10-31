from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.app.deps import verify_api_key
from backend.config import logger
from backend.core.config import settings

try:
    import google.generativeai as genai
except Exception:
    genai = None  # we’ll check at runtime

router = APIRouter()


class ChatAttachment(BaseModel):
    filename: Optional[str] = None
    mime_type: str = Field(..., description="e.g., image/jpeg, image/png, application/pdf")
    base64_data: str = Field(..., description="Base64 (with or without data: prefix)")


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    # auto = document chat when attachments present else general
    mode: Optional[Literal["auto", "document", "general"]] = "auto"
    attachments: List[ChatAttachment] = Field(default_factory=list)
    temperature: Optional[float] = 0.3


class ChatResponse(BaseModel):
    reply: str
    meta: Optional[Dict[str, Any]] = None


class GeminiChatService:
    """
    Minimal chat wrapper around google.generativeai for text-only and doc-chat (images/PDFs).
    """

    def __init__(self, api_key: Optional[str], model: str = "gemini-2.0-flash-001") -> None:
        if not genai:
            raise RuntimeError("google-generativeai is not installed")

        api_key = api_key or settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        self._requested_model = model
        self._model_id = None  # full model id (e.g., models/gemini-2.0-flash-001)
        self._client = None
        self._configure(api_key)

    def _configure(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

        # Normalize & find a supported model
        available_map: Dict[str, str] = {}
        try:
            for m in genai.list_models():
                # keep only text/image generation capable models
                if "generateContent" in getattr(m, "supported_generation_methods", []):
                    short = m.name.replace("models/", "")
                    available_map[short] = m.name
        except Exception as e:
            logger.error(f"Gemini list_models failed: {e}")

        # preferred → fallbacks
        candidates = [
            self._requested_model,
            "gemini-2.0-flash-001",
            "gemini-2.0-flash-lite-001",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        chosen_short = None
        for c in candidates:
            if c in available_map:
                chosen_short = c
                break
        if not chosen_short:
            raise RuntimeError(f"No suitable Gemini model found. Available: {sorted(available_map.keys())}")

        self._model_id = available_map[chosen_short]
        self._client = genai.GenerativeModel(self._model_id)
        logger.info(f"Gemini chat configured with: {chosen_short} ({self._model_id})")

    @staticmethod
    def _strip_data_url(b64: str) -> str:
        if not b64:
            return b64
        if "," in b64 and b64.strip().startswith("data:"):
            return b64.split(",", 1)[1]
        return b64

    def _build_content(
            self,
            message: str,
            context: Optional[str],
            attachments: List[ChatAttachment],
            mode: str,
    ) -> List[Any]:
        """
        Build Gemini content array. For PDFs we upload a temp file with genai.upload_file and
        pass file references; for images we use inline_data.
        """
        # 1) System / behavior prompt
        sys_doc = (
            "You are a helpful assistant. "
            "When documents are provided, behave as a document chat assistant: "
            "answer with references to the attached content, be concise, and preserve important fields."
        )

        # 2) Optional context
        ctx = (context or "").strip()
        ctx_block = f"Context:\n{ctx}" if ctx else None

        content: List[Any] = [sys_doc]
        if ctx_block:
            content.append(ctx_block)

        # 3) Attachments
        has_attachments = bool(attachments)
        file_refs: List[Any] = []

        if has_attachments:
            for att in attachments:
                mt = (att.mime_type or "").lower()
                raw = base64.b64decode(self._strip_data_url(att.base64_data))

                if mt.startswith("image/"):
                    # Send inline for images
                    content.append(
                        {
                            "inline_data": {
                                "data": base64.b64encode(raw).decode("utf-8"),
                                "mime_type": mt,
                            }
                        }
                    )
                elif mt == "application/pdf":
                    # Upload temp file then reference it
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(raw)
                        tmp.flush()
                        path = tmp.name
                    try:
                        f = genai.upload_file(path=path, mime_type="application/pdf")
                        file_refs.append(f)
                    finally:
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                else:
                    # Unsupported mimetype → best effort as inline binary
                    content.append(
                        {
                            "inline_data": {
                                "data": base64.b64encode(raw).decode("utf-8"),
                                "mime_type": mt or "application/octet-stream",
                            }
                        }
                    )

            # PDFs must be added as file references after upload
            for f in file_refs:
                content.append(f)

        # 4) The user message
        if mode == "document" or (mode == "auto" and has_attachments):
            user_block = (
                "User request (document chat mode):\n"
                f"{message}\n"
                "When answering, cite the exact field names if relevant and keep structure readable."
            )
        else:
            user_block = f"User request (general chat):\n{message}"

        content.append(user_block)
        return content

    def generate(
            self,
            message: str,
            context: Optional[str],
            attachments: List[ChatAttachment],
            mode: str = "auto",
            temperature: float = 0.3,
    ) -> str:
        content = self._build_content(message, context, attachments, mode)
        resp = self._client.generate_content(
            content,
            generation_config={
                "temperature": max(0.0, min(1.0, float(temperature))),
                "top_p": 0.95,
                "top_k": 40,
            },
        )
        return getattr(resp, "text", "") or ""


@router.post("", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest):
    """
    Gemini-powered chat endpoint.
    - If `attachments` are provided (or `mode="document"`), runs document chat.
    - Otherwise, general chat.
    Uses model 'gemini-2.0-flash-001' with graceful fallback.
    """
    if not genai:
        raise HTTPException(status_code=500, detail="google-generativeai not installed on server")

    # Read API key from env to avoid hard-coding in repo
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    try:
        svc = GeminiChatService(api_key=api_key, model="gemini-2.0-flash-001")
        # run blocking gen call in a thread so we don't block the event loop
        reply = await run_in_threadpool(
            svc.generate,
            req.message,
            req.context,
            req.attachments,
            req.mode or "auto",
            req.temperature or 0.3,
        )
        return ChatResponse(reply=reply, meta={"model": "gemini", "requested": "gemini-2.0-flash-001"})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Gemini chat error")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
