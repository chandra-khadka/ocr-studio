"""
General utility functions for historical OCR processing.
"""
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

from backend.config import logger


def generate_cache_key(file_bytes, file_type, use_vision, preprocessing_options=None, pdf_rotation=0,
                       custom_prompt=None):
    """
    Generate a cache key for OCR processing
    
    Args:
        file_bytes: File document_content as bytes
        file_type: Type of file (pdf or image)
        use_vision: Whether to use vision model
        preprocessing_options: Dictionary of preprocessing options
        pdf_rotation: PDF rotation value
        custom_prompt: Custom prompt for OCR
        
    Returns:
        str: Cache key
    """
    # Generate file hash
    file_hash = hashlib.md5(file_bytes).hexdigest()

    # Include preprocessing options in cache key
    preprocessing_options_hash = ""
    if preprocessing_options:
        # Add pdf_rotation to preprocessing options to ensure it's part of the cache key
        if pdf_rotation != 0:
            preprocessing_options_with_rotation = preprocessing_options.copy()
            preprocessing_options_with_rotation['pdf_rotation'] = pdf_rotation
            preprocessing_str = str(sorted(preprocessing_options_with_rotation.items()))
        else:
            preprocessing_str = str(sorted(preprocessing_options.items()))
        preprocessing_options_hash = hashlib.md5(preprocessing_str.encode()).hexdigest()
    elif pdf_rotation != 0:
        # If no preprocessing options but we have rotation, include that in the hash
        preprocessing_options_hash = hashlib.md5(f"pdf_rotation_{pdf_rotation}".encode()).hexdigest()

    # Create base cache key
    cache_key = f"{file_hash}_{file_type}_{use_vision}_{preprocessing_options_hash}"

    # Include custom prompt in cache key if provided
    if custom_prompt:
        custom_prompt_hash = hashlib.md5(str(custom_prompt).encode()).hexdigest()
        cache_key = f"{cache_key}_{custom_prompt_hash}"

    return cache_key


def timing(description):
    """Context manager for timing code execution"""

    class TimingContext:
        def __init__(self, description):
            self.description = description

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            end_time = time.time()
            execution_time = end_time - self.start_time
            logger.info(f"{self.description} took {execution_time:.2f} seconds")
            return False

    return TimingContext(description)


def format_timestamp(timestamp=None, for_filename=False):
    """
    Format timestamp for display or filenames
    
    Args:
        timestamp: Datetime object or string to format (defaults to current time)
        for_filename: Whether to format for use in a filename (defaults to False)
        
    Returns:
        str: Formatted timestamp
    """
    if timestamp is None:
        timestamp = datetime.now()
    elif isinstance(timestamp, str):
        try:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()

    if for_filename:
        # Format suitable for filenames: "Apr 30, 2025"
        return timestamp.strftime("%b %d, %Y")
    else:
        # Standard format for display
        return timestamp.strftime("%Y-%m-%d %H:%M")


def create_descriptive_filename(original_filename, result, file_ext, preprocessing_options=None):
    """
    Create a user-friendly descriptive filename for the result
    
    Args:
        original_filename: Original filename
        result: OCR result dictionary
        file_ext: File extension
        preprocessing_options: Dictionary of preprocessing options
        
    Returns:
        str: Human-readable descriptive filename
    """
    # Get base name without extension and capitalize words
    original_name = Path(original_filename).stem

    # Make the original name more readable by replacing dashes and underscores with spaces
    # Then capitalize each word
    readable_name = original_name.replace('-', ' ').replace('_', ' ')
    # Split by spaces and capitalize each word, then rejoin
    name_parts = readable_name.split()
    readable_name = ' '.join(word.capitalize() for word in name_parts)

    # Determine document type
    doc_type = None
    if 'detected_document_type' in result and result['detected_document_type']:
        doc_type = result['detected_document_type'].capitalize()
    elif 'topics' in result and result['topics']:
        # Use first topic as document type if not explicitly detected
        doc_type = result['topics'][0]

    # Find period/era information
    period_info = None
    if 'topics' in result and result['topics']:
        for tag in result['topics']:
            if "century" in tag.lower() or "pre-" in tag.lower() or "era" in tag.lower():
                period_info = tag
                break

    # Format metadata within parentheses if available
    metadata = []
    if doc_type:
        metadata.append(doc_type)
    if period_info:
        metadata.append(period_info)

    metadata_str = ""
    if metadata:
        metadata_str = f" ({', '.join(metadata)})"

    # Add current date for uniqueness and sorting
    current_date = format_timestamp(for_filename=True)
    date_str = f" - {current_date}"

    # Generate final user-friendly filename
    descriptive_name = f"{readable_name}{metadata_str}{date_str}{file_ext}"
    return descriptive_name


def extract_subject_tags(result, raw_text, preprocessing_options=None):
    """
    Extract subject tags from OCR result
    
    Args:
        result: OCR result dictionary
        raw_text: Raw text from OCR
        preprocessing_options: Dictionary of preprocessing options
        
    Returns:
        list: Subject tags
    """
    subject_tags = []

    # Use existing topics as starting point if available
    if 'topics' in result and result['topics']:
        subject_tags = list(result['topics'])

    # Add document type if detected
    if 'detected_document_type' in result:
        doc_type = result['detected_document_type'].capitalize()
        if doc_type not in subject_tags:
            subject_tags.append(doc_type)

    # If no tags were found, add some defaults
    if not subject_tags:
        subject_tags = ["Document", "Historical Document"]

        # Try to infer document_content type
        if "letter" in raw_text.lower()[:1000] or "dear" in raw_text.lower()[:200]:
            subject_tags.append("Letter")

        # Check if it might be a newspaper
        if "newspaper" in raw_text.lower()[:1000] or "editor" in raw_text.lower()[:500]:
            subject_tags.append("Newspaper")

    return subject_tags
