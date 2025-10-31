from backend.models.enums import DocumentType
from backend.utils.post_ocr_util import normalize_passport_dates


class PostOCRService:
    @staticmethod
    async def process(results, document_type):
        results["document_type"] = document_type
        if document_type == DocumentType.PASSPORT_FRONT:
            return normalize_passport_dates(results)

        return results
