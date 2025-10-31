import base64
import hashlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from backend.config import logger
from backend.utils.constants import CONTENT_THEMES, PERIOD_TAGS, DEFAULT_TAGS, GENERIC_TAGS


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
                # Default to octet-stream for unknown types
                mime_type = 'application/octet-stream'
        elif mime_type is None:
            # Default MIME type if we can't determine it
            mime_type = 'application/octet-stream'

        # Encode and create data URL
        encoded = base64.b64encode(file_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logger.error(f"Error encoding bytes to base64: {str(e)}")
        return ""


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

    try:
        # Use existing topics as starting point if available
        if 'topics' in result and result['topics']:
            subject_tags = list(result['topics'])

        # Add document type if detected
        if 'detected_document_type' in result:
            doc_type = result['detected_document_type'].capitalize()
            if doc_type not in subject_tags:
                subject_tags.append(doc_type)

        # Analyze document_content for common themes based on keywords
        if raw_text:
            raw_text_lower = raw_text.lower()

            # Track keyword matches for each theme and their frequency
            theme_matches = {}

            # First pass - find all matching keywords for each theme
            for theme, keywords in CONTENT_THEMES.items():
                matches = []
                for keyword in keywords:
                    # For multi-word keywords, we want exact phrase matching
                    if " " in keyword:
                        if keyword in raw_text_lower:
                            matches.append(keyword)
                    # For single-word keywords, we want word boundary matching to avoid partial matches
                    else:
                        import re
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, raw_text_lower):
                            matches.append(keyword)

                if matches:
                    # Store both the matches and their count
                    theme_matches[theme] = {
                        "matches": matches,
                        "count": len(matches)
                    }

            # Sort themes by match count in descending order
            sorted_themes = sorted(theme_matches.keys(),
                                   key=lambda t: theme_matches[t]["count"],
                                   reverse=True)

            # Add the most relevant themes (more matches = more relevant)
            # Limit to top 5 themes to avoid too many irrelevant tags
            top_themes = sorted_themes[:5] if len(sorted_themes) > 5 else sorted_themes

            # Add historical period tags first (they're often most important for historical research)
            period_themes = [t for t in top_themes if t in [
                "Prehistoric", "Ancient World", "Medieval", "Renaissance",
                "Early Modern", "18th Century", "19th Century", "20th Century", "Contemporary"
            ]]

            for theme in period_themes:
                if theme not in subject_tags:
                    subject_tags.append(theme)

            # Then add the remaining top themes
            for theme in top_themes:
                if theme not in period_themes and theme not in subject_tags:
                    subject_tags.append(theme)

            # Add debug information to log
            if theme_matches:
                logger.info(f"Extracted themes: {', '.join(top_themes)}")
                logger.info(f"Theme match details: {theme_matches}")

        # Add document period tag if date patterns are detected
        if raw_text:
            # Look for years in document_content
            import re
            year_matches = re.findall(r'\b1[0-9]{3}\b|\b20[0-1][0-9]\b', raw_text)
            if year_matches:
                # Convert to integers
                years = [int(y) for y in year_matches]
                # Get earliest year
                earliest = min(years)

                # Find the period tag for this year
                for year_range, period_tag in PERIOD_TAGS.items():
                    if year_range[0] <= earliest <= year_range[1]:
                        if period_tag not in subject_tags:
                            subject_tags.append(period_tag)
                        break

        # Add languages as topics if available
        if 'languages' in result and result['languages']:
            for lang in result['languages']:
                if lang and lang not in subject_tags:
                    lang_tag = f"{lang} Language"
                    subject_tags.append(lang_tag)

        # Add preprocessing information as tags if preprocessing was applied
        if preprocessing_options:
            preprocessing_methods = []
            if preprocessing_options.get("document_type", "standard") != "standard":
                doc_type = preprocessing_options["document_type"].capitalize()
                preprocessing_tag = f"Enhanced ({doc_type})"
                if preprocessing_tag not in subject_tags:
                    subject_tags.append(preprocessing_tag)

            if preprocessing_options.get("grayscale", False):
                preprocessing_methods.append("Grayscale")
            if preprocessing_options.get("denoise", False):
                preprocessing_methods.append("Denoised")
            if preprocessing_options.get("contrast", 0) != 0:
                contrast_val = preprocessing_options.get("contrast", 0)
                if contrast_val > 0:
                    preprocessing_methods.append("Contrast Enhanced")
                else:
                    preprocessing_methods.append("Contrast Reduced")
            if preprocessing_options.get("rotation", 0) != 0:
                preprocessing_methods.append("Rotated")

            # Add a combined preprocessing tag if methods were applied
            if preprocessing_methods:
                prep_tag = "Preprocessed"
                if prep_tag not in subject_tags:
                    subject_tags.append(prep_tag)

                # Add the specific method as a tag if only one was used
                if len(preprocessing_methods) == 1:
                    method_tag = preprocessing_methods[0]
                    if method_tag not in subject_tags:
                        subject_tags.append(method_tag)

    except Exception as e:
        logger.warning(f"Error generating subject tags: {str(e)}")
        # Fallback tags if extraction fails
        if not subject_tags:
            subject_tags = DEFAULT_TAGS.copy()

    # Ensure we have at least 3 tags
    while len(subject_tags) < 3:
        for tag in DEFAULT_TAGS:
            if tag not in subject_tags:
                subject_tags.append(tag)
                break
        else:
            # If all default tags are already used, add generic ones
            for tag in GENERIC_TAGS:
                if tag not in subject_tags:
                    subject_tags.append(tag)
                    break
            else:
                # If we still can't add any more tags, break the loop
                break

    return subject_tags
