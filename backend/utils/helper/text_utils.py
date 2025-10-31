"""
Utility functions for text processing.
Contains helper functions for working with text data from OCR.
"""
import difflib
import re
from typing import List, Dict, Any


def format_ocr_text(text: str, for_display: bool = False) -> str:
    """
    Format OCR text for display or processing.
    This function maintains clean separation between data and presentation.

    Args:
        text: OCR text to format
        for_display: Whether to format for display (HTML) or plain text

    Returns:
        Formatted text
    """
    if not text:
        return ""

    # Clean the text first
    text = clean_raw_text(text)

    # Basic text formatting (line breaks, etc.)
    formatted_text = text.replace("\n", "<br>" if for_display else "\n")

    if for_display:
        # For display, wrap in paragraph tags but avoid unnecessary divs
        # to maintain document_content purity
        return f"<p>{formatted_text}</p>"
    else:
        # For processing, return clean text only - no markup
        return formatted_text


def format_markdown_text(text: str, preserve_format: bool = True) -> str:
    """
    Format text as Markdown, preserving or enhancing its structure.
    Ensures that text has clean markdown formatting without introducing
    unnecessary presentation elements.

    Args:
        text: Raw text to format as Markdown
        preserve_format: Whether to preserve original formatting

    Returns:
        Markdown-formatted text
    """
    if not text:
        return ""

    # Clean the text first
    text = clean_raw_text(text)

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Preserve paragraphs if requested
    if preserve_format:
        # Ensure paragraphs are separated by double line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
    else:
        # Convert single line breaks within paragraphs to spaces
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        # Ensure paragraphs are separated by double line breaks
        text = re.sub(r'\n{2,}', '\n\n', text)

    # Remove excess whitespace
    text = re.sub(r' {2,}', ' ', text)

    # Enhance markdown features if they exist

    # Make sure headers have space after # marks
    text = re.sub(r'(^|\n)(#{1,6})([^#\s])', r'\1\2 \3', text)

    # Make sure list items have space after markers
    text = re.sub(r'(^|\n)([*+-])([^\s])', r'\1\2 \3', text)
    text = re.sub(r'(^|\n)(\d+\.)([^\s])', r'\1\2 \3', text)

    return text.strip()


def clean_raw_text(text: str) -> str:
    """
    Clean raw text by removing unnecessary whitespace and artifacts.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove image references like ![image](data:image/...)
    text = re.sub(r'!\[.*?\]\(data:image/[^)]+\)', '', text)

    # Remove basic markdown image references like ![alt](img-1.jpg)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)

    # Remove base64 encoded image data
    text = re.sub(r'data:image/[^;]+;base64,[a-zA-Z0-9+/=]+', '', text)

    # Clean up any JSON-like image object references
    text = re.sub(r'{"image(_data)?":("[^"]*"|null|true|false|\{[^}]*\}|\[[^\]]*\])}', '', text)

    # Clean up excessive whitespace and line breaks created by removals
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'\s{3,}', ' ', text)

    return text.strip()


def detect_content_regions(image_np):
    """
    Detect document_content regions based on text density analysis.
    Returns regions with adaptive overlapping.

    Args:
        image_np: Numpy array image

    Returns:
        list: List of region tuples (x, y, width, height)
    """
    # Import necessary modules
    import numpy as np
    import cv2

    # Convert to grayscale for text detection
    if len(image_np.shape) > 2 and image_np.shape[2] == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np

    # Create text density profile
    # Sum pixel values horizontally to get vertical text density
    v_profile = np.sum(255 - gray, axis=1)

    # Normalize the profile
    v_profile = v_profile / np.max(v_profile) if np.max(v_profile) > 0 else v_profile

    # Find significant density changes
    changes = []
    threshold = 0.2
    for i in range(1, len(v_profile)):
        if abs(v_profile[i] - v_profile[i - 1]) > threshold:
            changes.append(i)

    # Create adaptive regions based on density changes
    img_height, img_width = gray.shape

    # Default to at least 3 regions with overlap
    if len(changes) < 2:
        # If no significant changes, use default division with overlapping regions
        header_height = int(img_height * 0.3)
        middle_start = int(img_height * 0.2)
        middle_height = int(img_height * 0.4)
        body_start = int(img_height * 0.5)
        body_height = img_height - body_start
    else:
        # Use detected density changes for more precise regions
        changes = sorted(changes)
        header_height = changes[0] + int(img_height * 0.05)  # Add overlap
        middle_start = max(0, changes[0] - int(img_height * 0.05))

        if len(changes) > 1:
            middle_height = (changes[1] - middle_start) + int(img_height * 0.05)
            body_start = max(0, changes[1] - int(img_height * 0.05))
        else:
            middle_height = int(img_height * 0.4)
            body_start = int(img_height * 0.5)

        body_height = img_height - body_start

    # Define regions with adaptive overlap
    regions = [
        (0, 0, img_width, header_height),  # Header region
        (0, middle_start, img_width, middle_height),  # Middle region with overlap
        (0, body_start, img_width, body_height)  # Body region with overlap
    ]

    return regions


def merge_region_texts(regions: List[Dict[str, Any]], min_similarity_threshold: float = 0.7) -> str:
    """
    Intelligently merge text from multiple document regions, handling overlapping document_content.
    Uses text similarity detection to avoid duplicating document_content from overlapping regions.

    Args:
        regions: List of region dictionaries, each containing 'text' and 'order' keys
        min_similarity_threshold: Minimum similarity ratio to consider text as duplicate

    Returns:
        Merged text with duplications removed
    """
    # If no regions, return empty string
    if not regions:
        return ""

    # If only one region, return its text directly
    if len(regions) == 1:
        return regions[0]['text']

    # Sort regions by their defined order
    sorted_regions = sorted(regions, key=lambda x: x.get('order', 0))

    # Extract text segments from each region
    texts = [region.get('text', '').strip() for region in sorted_regions]

    # Remove empty texts
    texts = [t for t in texts if t]

    if not texts:
        return ""

    # Start with the first region's text
    merged_text = texts[0]

    # Process each subsequent region
    for i in range(1, len(texts)):
        current_text = texts[i]

        # Skip if current text is empty
        if not current_text:
            continue

        # Find potential overlap with existing merged text
        # Split both texts into lines for line-by-line comparison
        merged_lines = merged_text.splitlines()
        current_lines = current_text.splitlines()

        # Initialize variables to track where to start appending
        append_from_line = 0  # Default: append all lines from current text
        max_similarity = 0.0
        max_similarity_pos = -1

        # Check for potential line duplications
        # Look at the last N lines of merged text (N = min(20, len(merged_lines)))
        # to see if they match the first N lines of current text
        check_lines = min(20, len(merged_lines))
        for j in range(1, check_lines + 1):
            # Get the last j lines from merged text
            merged_end = "\n".join(merged_lines[-j:])

            # Get the first j lines from current text
            current_start = "\n".join(current_lines[:j])

            # Skip comparison if either section is too short
            if len(merged_end) < 10 or len(current_start) < 10:
                continue

            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, merged_end, current_start).ratio()

            # If we found a better match, update
            if similarity > max_similarity and similarity >= min_similarity_threshold:
                max_similarity = similarity
                max_similarity_pos = j

        # If we found a good match, skip those lines from current text
        if max_similarity_pos > 0:
            logger.info(
                f"Found overlapping text with similarity {max_similarity:.2f}, skipping {max_similarity_pos} lines")
            append_from_line = max_similarity_pos

        # Append non-duplicated document_content with a separator
        if append_from_line < len(current_lines):
            remaining_text = "\n".join(current_lines[append_from_line:])
            if remaining_text.strip():
                merged_text += "\n\n" + remaining_text

    return merged_text
