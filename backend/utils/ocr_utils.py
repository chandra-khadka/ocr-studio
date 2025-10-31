"""
OCR utility functions for image processing and OCR operations.
This module provides helper functions used across the Historical OCR application.
"""

import base64
from pathlib import Path
from typing import Union, Optional

from backend.config import logger

# Try to import optional dependencies
try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    logger.warning("pytesseract not available - local OCR fallback will not work")
    TESSERACT_AVAILABLE = False

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    logger.warning("PIL not available - image preprocessing will be limited")
    PILLOW_AVAILABLE = False


def encode_image_for_api(image_path: Union[str, Path]) -> str:
    """
    Encode an image as base64 data URL for API submission with proper MIME type.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 data URL for the image
    """
    # Convert to Path object if string
    image_file = Path(image_path) if isinstance(image_path, str) else image_path

    # Verify image exists
    if not image_file.is_file():
        raise FileNotFoundError(f"Image file not found: {image_file}")

    # Determine mime type based on file extension
    mime_type = 'image/jpeg'  # Default mime type
    suffix = image_file.suffix.lower()
    if suffix == '.png':
        mime_type = 'image/png'
    elif suffix == '.gif':
        mime_type = 'image/gif'
    elif suffix in ['.jpg', '.jpeg']:
        mime_type = 'image/jpeg'
    elif suffix == '.pdf':
        mime_type = 'application/pdf'

    # Encode image as base64
    encoded = base64.b64encode(image_file.read_bytes()).decode()
    return f"data:{mime_type};base64,{encoded}"


def try_local_ocr_fallback(file_path: Union[str, Path], base64_data_url: Optional[str] = None) -> Optional[str]:
    """
    Try to perform OCR using local Tesseract as a fallback when the API is unavailable.
    
    Args:
        file_path: Path to the image file
        base64_data_url: Optional base64 data URL if already available
        
    Returns:
        Extracted text or None if extraction failed
    """
    if not TESSERACT_AVAILABLE or not PILLOW_AVAILABLE:
        logger.warning("Local OCR fallback is not available (missing dependencies)")
        return None

    try:
        logger.info("Using local Tesseract OCR as fallback")

        # Use PIL to open the image
        img = Image.open(file_path)

        # Use Tesseract to extract text
        text = pytesseract.image_to_string(img)

        if text:
            logger.info("Successfully extracted text using local Tesseract OCR")
            return text
        else:
            logger.warning("Tesseract extracted no text")
            return None
    except Exception as e:
        logger.error(f"Error using local OCR fallback: {str(e)}")
        return None
