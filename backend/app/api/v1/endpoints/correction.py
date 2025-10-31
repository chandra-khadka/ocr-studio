from fastapi import APIRouter, Depends

from backend.app.deps import verify_api_key
from backend.app.schemas.correction import CorrectionResponse, CorrectionRequest
from backend.app.services.correction_adapter import run_correction
from backend.models.enums import DocumentType

router = APIRouter()


@router.post("", response_model=CorrectionResponse, dependencies=[Depends(verify_api_key)])
async def correct(req: CorrectionRequest):
    corrected = await run_correction(
        text=req.text,
        model_str=req.model,
        prompt=req.prompt,
        document_type=req.document_type or DocumentType.GENERAL,
    )
    return {"corrected": corrected}
