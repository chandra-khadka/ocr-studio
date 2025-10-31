import logging
import re
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFContentFormatter:
    """Enhanced PDF document_content formatter for better display"""

    @staticmethod
    def format_text_blocks(text: str) -> str:
        """Format text blocks with proper spacing and structure"""
        if not text.strip():
            return text

        # Split into paragraphs and clean up
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []

        for para in paragraphs:
            # Clean up excessive whitespace
            para = re.sub(r'\s+', ' ', para.strip())
            if para:  # Only add non-empty paragraphs
                formatted_paragraphs.append(para)

        return '\n\n'.join(formatted_paragraphs)

    @staticmethod
    def extract_metadata_from_text(text: str) -> Dict[str, Any]:
        """Extract potential metadata from text"""
        metadata = {
            'word_count': len(text.split()),
            'character_count': len(text),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'line_count': len([line for line in text.split('\n') if line.strip()])
        }

        # Try to detect document structure
        if any(keyword in text.lower() for keyword in ['name:', 'date:', 'address:', 'phone:']):
            metadata['likely_form'] = True
        if any(keyword in text.lower() for keyword in ['total:', 'amount:', 'price:', '$', 'rs.']):
            metadata['likely_invoice'] = True
        if any(keyword in text.lower() for keyword in ['certificate', 'diploma', 'degree']):
            metadata['likely_certificate'] = True

        return metadata
