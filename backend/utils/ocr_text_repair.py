import logging
import re
from difflib import SequenceMatcher
from typing import Tuple, Dict, Any, Optional

from backend.config import logger


def detect_duplicate_text_issues(text: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect if OCR text has duplication issues often found in handwritten document OCR
    
    Args:
        text: OCR text to analyze
    
    Returns:
        Tuple of (has_duplication_issues, details_dict)
    """
    # Early exit for empty text
    if not text or len(text) < 100:
        return False, {"duplication_rate": 0.0, "details": "Text too short for analysis"}

    # Look for repeated line patterns
    lines = text.split('\n')
    line_count = len(lines)

    # Basic metrics
    repeated_lines = 0
    duplicate_sections = []
    line_repetition_indices = []

    # Check for exact line repetitions
    seen_lines = {}
    for i, line in enumerate(lines):
        # Skip very short lines or empty lines
        stripped = line.strip()
        if len(stripped) < 5:
            continue

        if stripped in seen_lines:
            repeated_lines += 1
            line_repetition_indices.append((seen_lines[stripped], i))
        else:
            seen_lines[stripped] = i

    # Calculate line repetition rate
    line_repetition_rate = repeated_lines / max(1, line_count)

    # Look for longer repeated sections using sequence matcher
    text_blocks = [text[i:i + 100] for i in range(0, len(text), 100) if i + 100 <= len(text)]
    block_count = len(text_blocks)

    repeated_blocks = 0
    for i in range(block_count):
        for j in range(i + 1, min(i + 10, block_count)):  # Only check nearby blocks for efficiency
            matcher = SequenceMatcher(None, text_blocks[i], text_blocks[j])
            similarity = matcher.ratio()
            if similarity > 0.8:  # High similarity threshold
                repeated_blocks += 1
                duplicate_sections.append((i, j, similarity))
                break

    # Calculate block repetition rate
    block_repetition_rate = repeated_blocks / max(1, block_count)

    # Combine metrics for overall duplication rate
    duplication_rate = max(line_repetition_rate, block_repetition_rate)

    # Detect patterns of repeated words in sequence (common OCR mistake)
    word_pattern = r'\b(\w+)\s+\1\b'
    repeated_words = len(re.findall(word_pattern, text))
    repeated_words_rate = repeated_words / max(1, len(text.split()))

    # Update duplication rate with word repetition
    duplication_rate = max(duplication_rate, repeated_words_rate)

    # Log detailed analysis
    logger.info(f"OCR duplication analysis: line_repetition={line_repetition_rate:.2f}, "
                f"block_repetition={block_repetition_rate:.2f}, "
                f"word_repetition={repeated_words_rate:.2f}, "
                f"final_rate={duplication_rate:.2f}")

    # Determine if this is a serious issue
    has_duplication = duplication_rate > 0.1

    # Return detailed results
    return has_duplication, {
        "duplication_rate": duplication_rate,
        "line_repetition_rate": line_repetition_rate,
        "block_repetition_rate": block_repetition_rate,
        "word_repetition_rate": repeated_words_rate,
        "repeated_lines": repeated_lines,
        "repeated_blocks": repeated_blocks,
        "repeated_words": repeated_words,
        "duplicate_sections": duplicate_sections[:10],  # Only include the first 10 for brevity
        "repetition_indices": line_repetition_indices[:10]
    }


def get_enhanced_preprocessing_options(current_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate enhanced preprocessing options for improved OCR on handwritten documents
    
    Args:
        current_options: Current preprocessing options (if available)
        
    Returns:
        Dict of enhanced options
    """
    # Start with current options or empty dict
    options = current_options.copy() if current_options else {}

    # Set document type to handwritten
    options["document_type"] = "handwritten"

    # Enhanced contrast - higher than normal for better handwriting extraction
    options["contrast"] = 1.4  # Higher than default

    # Apply grayscale
    options["grayscale"] = True

    # Apply adaptive thresholding optimized for handwriting
    options["adaptive_threshold"] = True
    options["threshold_block_size"] = 25  # Larger block size for handwriting
    options["threshold_c"] = 10  # Adjusted C value for better handwriting detection

    # Disable standard binarization which often loses handwriting detail
    options["binarize"] = False

    # Despeckle to reduce noise
    options["denoise"] = True

    # Enable handwriting-specific preprocessing
    options["handwriting_mode"] = True

    # Disable anything that might harm handwriting recognition
    if "sharpen" in options:
        options["sharpen"] = False

    logger.info(f"Enhanced handwriting preprocessing options generated: {options}")
    return options


def get_handwritten_specific_prompt(current_prompt: Optional[str] = None) -> str:
    """
    Generate a specialized prompt for handwritten document OCR
    
    Args:
        current_prompt: Current prompt (if available)
        
    Returns:
        str: Enhanced prompt for handwritten documents
    """
    # Base prompt for all handwritten documents
    base_prompt = ("This is a handwritten document that requires careful transcription. "
                   "Please transcribe all visible handwritten text, preserving the original "
                   "line breaks, paragraph structure, and any special formatting or indentation. "
                   "Pay special attention to:\n"
                   "1. Words that may be difficult to read due to handwriting style\n"
                   "2. Any crossed-out text (indicate with [crossed out: possible text])\n"
                   "3. Insertions or annotations between lines or in margins\n"
                   "4. Maintain the spatial layout of the text as much as possible\n"
                   "5. If there are multiple columns or non-linear text, preserve the reading order\n\n"
                   "If you cannot read a word with confidence, indicate with [?] or provide your best guess as [word?].")

    # If there's an existing prompt, combine them, otherwise just use the base
    if current_prompt:
        # Remove any redundant instructions about handwriting
        lower_prompt = current_prompt.lower()
        if "handwritten" in lower_prompt or "handwriting" in lower_prompt:
            # Extract any unique instructions from the current prompt
            # This logic is simplified and might need improvement
            current_sentences = [s.strip() for s in current_prompt.split('.') if s.strip()]
            handwriting_sentences = [s for s in current_sentences
                                     if "handwritten" not in s.lower()
                                     and "handwriting" not in s.lower()]

            # Add unique instructions to our base prompt
            if handwriting_sentences:
                combined_prompt = base_prompt + "\n\nAdditional instructions:\n"
                combined_prompt += ". ".join(handwriting_sentences) + "."
                return combined_prompt
        else:
            # If no handwriting instructions in the current prompt, just append it
            return f"{base_prompt}\n\nAdditional context from user:\n{current_prompt}"

    return base_prompt


def clean_duplicated_text(text: str) -> str:
    """
    Clean up duplicated text often found in OCR output for handwritten documents
    
    Args:
        text: OCR text to clean
        
    Returns:
        str: Cleaned text with duplications removed
    """
    if not text:
        return text

    # Split into lines for line-based deduplication
    lines = text.split('\n')

    # Remove consecutive duplicate lines
    deduped_lines = []
    prev_line = None

    for line in lines:
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            if not deduped_lines or deduped_lines[-1].strip():
                deduped_lines.append(line)  # Keep the first empty line
            continue

        # Skip if this line is a duplicate of the previous line
        if stripped == prev_line:
            continue

        deduped_lines.append(line)
        prev_line = stripped

    # Re-join the deduplicated lines
    deduped_text = '\n'.join(deduped_lines)

    # Remove repeated words
    word_pattern = r'\b(\w+)\s+\1\b'
    deduped_text = re.sub(word_pattern, r'\1', deduped_text)

    # Remove repeated phrases (3+ words)
    # This is a simplified approach and might need improvement
    words = deduped_text.split()
    cleaned_words = []
    i = 0

    while i < len(words):
        # Check for phrase repetition (phrases of 3 to 6 words)
        found_repeat = False

        for phrase_len in range(3, min(7, len(words) - i)):
            phrase = ' '.join(words[i:i + phrase_len])
            next_pos = i + phrase_len

            if next_pos + phrase_len <= len(words):
                next_phrase = ' '.join(words[next_pos:next_pos + phrase_len])

                if phrase.lower() == next_phrase.lower():
                    # Found a repeated phrase, skip the second occurrence
                    cleaned_words.extend(words[i:i + phrase_len])
                    i = next_pos + phrase_len
                    found_repeat = True
                    break

        if not found_repeat:
            cleaned_words.append(words[i])
            i += 1

    # Rejoin the cleaned words
    final_text = ' '.join(cleaned_words)

    # Log the cleaning results
    original_len = len(text)
    cleaned_len = len(final_text)
    reduction = 100 * (original_len - cleaned_len) / max(1, original_len)

    logger.info(f"Text cleaning: removed {original_len - cleaned_len} chars ({reduction:.1f}% reduction)")

    return final_text
