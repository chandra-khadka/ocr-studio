"""
File utility functions for historical OCR processing.
"""
import base64
import io
import os
from pathlib import Path

import requests
from PIL import Image

from backend.config import logger


def get_base64_from_image(image_path):
    """
    Get base64 data URL from image file with proper MIME type.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 data URL with appropriate MIME type prefix
    """
    try:
        # Convert to Path object for better handling
        path_obj = Path(image_path)

        # Determine mime type based on file extension
        mime_type = 'image/jpeg'  # Default mime type
        suffix = path_obj.suffix.lower()
        if suffix == '.png':
            mime_type = 'image/png'
        elif suffix == '.gif':
            mime_type = 'image/gif'
        elif suffix in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif suffix == '.pdf':
            mime_type = 'application/pdf'

        # Read and encode file
        with open(path_obj, "rb") as file:
            encoded = base64.b64encode(file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logger.error(f"Error encoding file to base64: {str(e)}")
        return ""


def get_base64_from_bytes(file_bytes, mime_type=None, file_name=None):
    """
    Get base64 data URL from file bytes with proper MIME type.

    Args:
        file_bytes: Binary file data
        mime_type: MIME type of the file (optional)
        file_name: Original file name for MIME type detection (optional)

    Returns:
        Base64 data URL with appropriate MIME type prefix
    """
    try:
        # Determine mime type if not provided
        if mime_type is None and file_name is not None:
            # Get file extension
            suffix = Path(file_name).suffix.lower()
            if suffix == '.png':
                mime_type = 'image/png'
            elif suffix == '.gif':
                mime_type = 'image/gif'
            elif suffix in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif suffix == '.pdf':
                mime_type = 'application/pdf'
            else:
                # Default to image/jpeg for unknown types when processing images
                mime_type = 'image/jpeg'
        elif mime_type is None:
            # Default MIME type if we can't determine it
            mime_type = 'image/jpeg'

        # Encode and create data URL
        encoded = base64.b64encode(file_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logger.error(f"Error encoding bytes to base64: {str(e)}")
        return ""


def handle_temp_files(temp_file_paths):
    """
    Clean up temporary files

    Args:
        temp_file_paths: List of temporary file paths to clean up
    """
    for temp_path in temp_file_paths:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.info(f"Removed temporary file: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {temp_path}: {str(e)}")


def validate_image_url(url: str) -> tuple[bool, str, bytes]:
    """
    Validate and fetch image data from a URL.

    Args:
        url: URL of the image to validate and fetch

    Returns:
        Tuple of (is_valid, content_type, image_bytes)
        - is_valid: True if the URL points to a valid image, False otherwise
        - content_type: Detected MIME type of the content
        - image_bytes: Raw bytes of the image if valid, empty bytes otherwise
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Get content type from headers
        content_type = response.headers.get('content-type', '').lower()
        logger.info(f"URL {url} content-type: {content_type}")

        # Check if content type is an image
        if not content_type.startswith('image/'):
            logger.warning(f"URL {url} does not point to an image (content-type: {content_type})")
            return False, content_type, b""

        # Validate it's a valid image
        try:
            Image.open(io.BytesIO(response.content))
            logger.info(f"URL {url} validated as a valid image")
            return True, content_type, response.content
        except Exception as e:
            logger.error(f"Image validation failed for URL {url}: {str(e)}")
            return False, content_type, b""

    except requests.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {str(e)}")
        return False, "", b""


def generate_unique_key(base_key: str, session_state=None) -> str:
    """
    Generate a unique key for Streamlit components to avoid duplicate key errors.

    Args:
        base_key: Base string for the key (e.g., 'page_content', 'chat_input')
        session_state: Streamlit session_state dictionary (optional)

    Returns:
        Unique key string
    """
    try:
        import uuid
        # Use session_state render_count if available, otherwise use UUID
        if session_state is not None and 'render_count' in session_state:
            unique_suffix = str(session_state['render_count'])
        else:
            unique_suffix = str(uuid.uuid4())[:8]  # Short UUID for uniqueness
        return f"{base_key}_{unique_suffix}"
    except Exception as e:
        logger.error(f"Error generating unique key for {base_key}: {str(e)}")
        return base_key  # Fallback to base_key if generation fails
