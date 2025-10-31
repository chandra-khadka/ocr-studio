def classify_document_content(result):
    """Classify document document_content based on structure and document_content"""
    classification = {
        'has_title': False,
        'has_content': False,
        'has_sections': False,
        'is_structured': False
    }

    if 'ocr_contents' not in result or not isinstance(result['ocr_contents'], dict):
        return classification

    # Check for title
    if 'title' in result['ocr_contents'] and result['ocr_contents']['title']:
        classification['has_title'] = True

    # Check for document_content
    content_fields = ['document_content', 'transcript', 'text']
    for field in content_fields:
        if field in result['ocr_contents'] and result['ocr_contents'][field]:
            classification['has_content'] = True
            break

    # Check for sections
    section_count = 0
    for key in result['ocr_contents'].keys():
        if key not in ['raw_text', 'error'] and result['ocr_contents'][key]:
            section_count += 1

    classification['has_sections'] = section_count > 2

    # Check if structured
    classification['is_structured'] = (
            classification['has_title'] and
            classification['has_content'] and
            classification['has_sections']
    )

    return classification


def extract_document_text(result):
    """Extract main document text document_content"""
    if 'ocr_contents' not in result or not isinstance(result['ocr_contents'], dict):
        return ""

    # Try to get the text from document_content fields in preferred order - prioritize main_text
    for field in ['main_text', 'document_content', 'transcript', 'text', 'raw_text']:
        if field in result['ocr_contents'] and result['ocr_contents'][field]:
            content = result['ocr_contents'][field]
            if isinstance(content, str):
                return content

    return ""


def extract_image_description(image_data):
    """Extract image description from data"""
    if not image_data or not isinstance(image_data, dict):
        return ""

    # Try different fields that might contain descriptions
    for field in ['alt_text', 'caption', 'description']:
        if field in image_data and image_data[field]:
            return image_data[field]

    return ""
