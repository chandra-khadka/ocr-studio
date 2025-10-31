from fastapi import HTTPException

from backend.config import logger
from backend.core.config import settings
from backend.document_content.enhance_document_processor import FastAPIDocumentProcessor
from backend.models.enums import OCRProvider, CorrectionProvider
from backend.models.schemas import ProviderConfig, DocumentProcessingRequest, ImageProcessingRequest
from backend.service.post_ocr_service import PostOCRService


class OCRService:

    @staticmethod
    def prepare_provider_config(ocr_provider: OCRProvider,
                                correction_provider: CorrectionProvider,
                                provider_config: ProviderConfig
                                ):
        config = {'ocr_model': provider_config.ocr_model,
                  'ocr_correction_model': provider_config.correction_model}
        if ocr_provider == OCRProvider.OLLAMA or correction_provider == CorrectionProvider.OLLAMA:
            config['endpoint'] = provider_config.ollama_endpoint or settings.OLLAMA_API
        return config

    @classmethod
    async def upload_document(
            cls,
            file,
            request_model: DocumentProcessingRequest
    ):
        """
        Endpoint to upload and process an image or PDF file for OCR and correction.
        """
        try:
            # Prepare provider configuration
            provider_config = cls.prepare_provider_config(
                request_model.ocr_provider,
                request_model.correction_provider,
                request_model.provider_config
            )

            # Read file bytes
            document_bytes = await file.read()
            document_type = file.content_type

            # Process document using EnhancedDocumentProcessor
            return await FastAPIDocumentProcessor.process_document_enhanced(
                file_bytes=document_bytes,
                file_type=document_type,
                ocr_provider=request_model.ocr_provider,
                correction_provider=request_model.correction_provider,
                document_type=request_model.document_type,
                document_format=request_model.document_format,
                language=request_model.language,
                enable_json_parsing=request_model.enable_json_parsing,
                use_segmentation=request_model.use_segmentation,
                max_pdf_pages=request_model.max_pdf_pages,
                pdf_dpi=request_model.pdf_dpi,
                custom_prompt=request_model.custom_prompt,
                **provider_config
            )

        except Exception as e:
            logger.error(f"Error processing uploaded document: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    @classmethod
    async def process_image_url_or_base64(cls, file_bytes, file_type, request: ImageProcessingRequest):
        try:
            # Decide correction provider once
            correction_provider = (
                request.correction_provider if request.apply_correction
                else CorrectionProvider.NONE
            )

            # Build provider kwargs from prepare_provider_config
            provider_config = cls.prepare_provider_config(
                request.ocr_provider,
                correction_provider,
                request.provider_config,
            )

            response = await FastAPIDocumentProcessor.process_document_enhanced(
                file_bytes=file_bytes,
                file_type=file_type,
                ocr_provider=request.ocr_provider,
                correction_provider=correction_provider,
                document_type=request.document_type,
                document_format=request.document_format,
                language=request.language,
                enable_json_parsing=request.enable_json_parsing,
                use_segmentation=request.use_segmentation,
                max_pdf_pages=request.max_pdf_pages,
                pdf_dpi=request.pdf_dpi,
                custom_prompt=request.custom_prompt,
                **provider_config
            )
            response = response['structured_json']['structured_data']
            return await PostOCRService.process(response, request.document_type)

        except Exception as e:
            logger.error(f"Error processing image from URL/base64: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
