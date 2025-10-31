import logging

from backend.utils.constants import MAX_FILE_SIZE_MB

logger = logging.getLogger("error_handler")
logger.setLevel(logging.INFO)


def handle_ocr_error(exception, progress_reporter=None):
    """
    Handle OCR processing errors and provide user-friendly messages
    
    Args:
        exception: The exception that occurred
        progress_reporter: ProgressReporter instance for UI updates
        
    Returns:
        str: User-friendly error message
    """
    error_message = str(exception)

    # Complete progress reporting if provided
    if progress_reporter:
        progress_reporter.complete(success=False)

    # Check for specific error types and provide helpful user-facing messages
    if "rate limit" in error_message.lower() or "429" in error_message or "requests rate limit exceeded" in error_message.lower():
        friendly_message = "The AI service is currently experiencing high demand. Please try again in a few minutes."
        logger.error(f"Rate limit error: {error_message}")
        return friendly_message
    elif "quota" in error_message.lower() or "credit" in error_message.lower() or "subscription" in error_message.lower():
        friendly_message = "The API usage quota has been reached. Please check your API key and subscription limits."
        logger.error(f"API quota error: {error_message}")
        return friendly_message
    elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
        friendly_message = ("The request timed out. This may be due to a large document or high server load. Please "
                            "try again or use a smaller document.")
        logger.error(f"Timeout error: {error_message}")
        return friendly_message
    elif "file size" in error_message.lower() or "too large" in error_message.lower():
        friendly_message = f"The file is too large. Maximum file size is {MAX_FILE_SIZE_MB}MB."
        logger.error(f"File size error: {error_message}")
        return friendly_message
    else:
        # Generic error message for other errors
        logger.error(f"OCR processing error: {error_message}", exc_info=True)
        return f"An error occurred during processing: {error_message}"


def check_file_size(file_bytes):
    """
    Check if file size is within limits
    
    Args:
        file_bytes: File document_content as bytes
        
    Returns:
        tuple: (is_valid, file_size_mb, error_message)
    """
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        error_message = f"File size {file_size_mb:.2f} MB exceeds limit of {MAX_FILE_SIZE_MB} MB"
        return False, file_size_mb, error_message

    return True, file_size_mb, None
