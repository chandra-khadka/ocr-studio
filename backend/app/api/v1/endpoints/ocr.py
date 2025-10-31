from fastapi import APIRouter, Depends

from backend.app.deps import verify_api_key
from backend.app.schemas.ocr import OCRResponse, OCRRequest
from backend.app.services.ocr_adapter import run_ocr

router = APIRouter()


@router.post("", response_model=OCRResponse, dependencies=[Depends(verify_api_key)])
async def ocr(req: OCRRequest):
    text = await run_ocr(
        file_base64=req.fileBase64,
        file_name=req.fileName,
        language=req.language,
        document_type=req.documentType,
        provider_str=req.provider,
        prompt=req.prompt,
    )
    return {"text": text, "pages": None, "images": None}
