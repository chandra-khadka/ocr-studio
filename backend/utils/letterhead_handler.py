from pathlib import Path

from backend.config import logger


def is_likely_letterhead(file_path, features=None):
    """
    Determine if a document is likely to contain letterhead or marginalia
    
    Args:
        file_path: Path to the document image
        features: Optional dictionary of pre-extracted features like text density
        
    Returns:
        bool: True if the document likely contains letterhead, False otherwise
    """
    # Simple logic based on filename for initial version
    file_name = Path(file_path).name.lower()
    letterhead_indicators = ['letter', 'letterhead', 'correspondence', 'memo']

    # Check filename for indicators
    for indicator in letterhead_indicators:
        if indicator in file_name:
            logger.info(f"Letterhead detected based on filename: {file_name}")
            return True

    # Check features if provided
    if features:
        # High text density at the top of the document may indicate letterhead
        if 'top_density' in features and features['top_density'] > 0.5:
            logger.info(f"Letterhead detected based on top text density: {features['top_density']}")
            return True

        # Uneven text distribution may indicate marginalia
        if 'density_variance' in features and features['density_variance'] > 0.3:
            logger.info(f"Possible marginalia detected based on text density variance")
            return True

    # Default to standard document
    return False


def get_letterhead_prompt(features=None):
    """
    Generate a specialized prompt for letterhead document OCR
    
    Args:
        features: Optional dictionary of pre-extracted features
        
    Returns:
        str: Specialized prompt for letterhead document OCR
    """
    # Base prompt for all letterhead documents
    base_prompt = ("This document appears to be a letter or includes letterhead elements. "
                   "Please extract the following components separately if present:\n"
                   "1. Letterhead (header with logo, organization name, address, etc.)\n"
                   "2. Date\n"
                   "3. Recipient information (address, name, title)\n"
                   "4. Salutation (e.g., 'Dear Sir/Madam')\n"
                   "5. Main body text\n"
                   "6. Closing (e.g., 'Sincerely')\n"
                   "7. Signature\n"
                   "8. Any footnotes, marginalia, or annotations\n\n"
                   "Preserve the original formatting and structure as much as possible.")

    # Enhanced prompts based on features
    if features:
        # Extract additional context from features if available
        if 'is_historical' in features and features['is_historical']:
            base_prompt += ("\n\nThis appears to be a historical document. Pay special attention to older "
                            "letterhead styles, formal language patterns, and period-specific formatting.")

        if 'has_marginalia' in features and features['has_marginalia']:
            base_prompt += ("\n\nThe document contains marginalia or handwritten notes in the margins. "
                            "Please extract these separately from the main text and indicate their position.")

    return base_prompt
