"""
Utility functions for OCR image processing with Mistral AI.
Contains helper functions for working with OCR responses and image handling.
"""

import base64
import io
import json
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Union

# Third-party imports
import numpy as np

# Mistral AI imports
from mistralai.models import OCRImageObject

from backend.config import logger
from backend.utils.content_utils import classify_document_content, extract_image_description, extract_document_text

# Check for image processing libraries
try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    PILLOW_AVAILABLE = True
except ImportError:
    logger.warning("PIL not available - image preprocessing will be limited")
    PILLOW_AVAILABLE = False

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV (cv2) not available - advanced image processing will be limited")
    CV2_AVAILABLE = False

# Import configuration
try:
    from config import IMAGE_PREPROCESSING
except ImportError:
    # Fallback defaults if config not available
    IMAGE_PREPROCESSING = {
        "enhance_contrast": 1.5,
        "sharpen": True,
        "denoise": True,
        "max_size_mb": 8.0,
        "target_dpi": 300,
        "compression_quality": 92
    }


def detect_skew(image: Union[Image.Image, np.ndarray]) -> float:
    """
    Quick skew detection that returns angle in degrees.
    Uses a computationally efficient approach by analyzing at 1% resolution.

    Args:
        image: PIL Image or numpy array

    Returns:
        Estimated skew angle in degrees (positive or negative)
    """
    # Convert PIL Image to numpy array if needed
    if isinstance(image, Image.Image):
        # Convert to grayscale for processing
        if image.mode != 'L':
            img_np = np.array(image.convert('L'))
        else:
            img_np = np.array(image)
    else:
        # If already numpy array, ensure it's grayscale
        if len(image.shape) == 3:
            if CV2_AVAILABLE:
                img_np = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                # Fallback grayscale conversion
                img_np = np.mean(image, axis=2).astype(np.uint8)
        else:
            img_np = image

    # Downsample to 1% resolution for faster processing
    height, width = img_np.shape
    target_size = int(min(width, height) * 0.01)

    # Use a sane minimum size and ensure we have enough pixels to detect lines
    target_size = max(target_size, 100)

    if CV2_AVAILABLE:
        # OpenCV-based implementation (faster)
        # Resize the image to the target size
        scale_factor = target_size / max(width, height)
        small_img = cv2.resize(img_np, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

        # Apply binary thresholding to get cleaner edges
        _, binary = cv2.threshold(small_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Use Hough Line Transform to detect lines
        lines = cv2.HoughLinesP(binary, 1, np.pi / 180, threshold=target_size // 10,
                                minLineLength=target_size // 5, maxLineGap=target_size // 10)

        if lines is None or len(lines) < 3:
            # Not enough lines detected, assume no significant skew
            return 0.0

        # Calculate angles of lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 == 0:  # Avoid division by zero
                continue
            angle = math.atan2(y2 - y1, x2 - x1) * 180.0 / np.pi

            # Normalize angle to -45 to 45 range
            angle = angle % 180
            if angle > 90:
                angle -= 180
            if angle > 45:
                angle -= 90
            if angle < -45:
                angle += 90

            angles.append(angle)

        if not angles:
            return 0.0

        # Use median to reduce impact of outliers
        angles.sort()
        median_angle = angles[len(angles) // 2]

        return median_angle
    else:
        # PIL-only fallback implementation
        # Resize using PIL
        small_img = Image.fromarray(img_np).resize(
            (int(width * target_size / max(width, height)),
             int(height * target_size / max(width, height))),
            Image.NEAREST
        )

        # Find edges
        edges = small_img.filter(ImageFilter.FIND_EDGES)
        edges_data = np.array(edges)

        # Simple edge orientation analysis (less precise than OpenCV)
        # Count horizontal vs vertical edges
        h_edges = np.sum(np.abs(np.diff(edges_data, axis=1)))
        v_edges = np.sum(np.abs(np.diff(edges_data, axis=0)))

        # If horizontal edges dominate, no significant skew
        if h_edges > v_edges * 1.2:
            return 0.0

        # Simple angle estimation based on edge distribution
        # This is a simplified approach that works for slight skews
        rows, cols = edges_data.shape
        xs, ys = [], []

        # Sample strong edge points
        for r in range(0, rows, 2):
            for c in range(0, cols, 2):
                if edges_data[r, c] > 128:
                    xs.append(c)
                    ys.append(r)

        if len(xs) < 10:  # Not enough edge points
            return 0.0

        # Use simple linear regression to estimate the slope
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        # Calculate slope
        numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
        denominator = sum((xs[i] - mean_x) ** 2 for i in range(n))

        if abs(denominator) < 1e-6:  # Avoid division by zero
            return 0.0

        slope = numerator / denominator
        angle = math.atan(slope) * 180.0 / math.pi

        # Normalize to -45 to 45 degrees
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90

        return angle


def replace_images_in_markdown(md: str, images: dict[str, str]) -> str:
    """
    Replace image placeholders in markdown with base64-encoded images.
    Uses regex-based matching to handle variations in image IDs and formats.

    Args:
        md: Markdown text containing image placeholders
        images: Dictionary mapping image IDs to base64 strings

    Returns:
        Markdown text with images replaced by base64 data
    """
    # Process each image ID in the dictionary
    for img_id, base64_str in images.items():
        # Extract the base ID without extension for more flexible matching
        base_id = img_id.split('.')[0]

        # Match markdown image pattern where URL contains the base ID
        # Using a single regex with groups to capture the full pattern
        pattern = re.compile(rf'!\[([^\]]*)\]\(([^\)]*{base_id}[^\)]*)\)')

        # Process all matches
        matches = list(pattern.finditer(md))
        for match in reversed(matches):  # Process in reverse to avoid offset issues
            # Replace the entire match with a properly formatted base64 image
            md = md[:match.start()] + f"![{img_id}](data:image/jpeg;base64,{base64_str})" + md[match.end():]

    return md


def get_combined_markdown(ocr_response) -> str:
    """
    Combine OCR text and images into a single markdown document.
    
    Args:
        ocr_response: OCR response object from Mistral AI
        
    Returns:
        Combined markdown string with embedded images
    """
    markdowns = []

    # Process each page of the OCR response
    for page in ocr_response.pages:
        # Extract image data if available
        image_data = {}
        if hasattr(page, "images"):
            for img in page.images:
                if hasattr(img, "id") and hasattr(img, "image_base64"):
                    image_data[img.id] = img.image_base64

        # Replace image placeholders with base64 data
        page_markdown = page.markdown if hasattr(page, "markdown") else ""
        processed_markdown = replace_images_in_markdown(page_markdown, image_data)
        markdowns.append(processed_markdown)

    # Join all pages' markdown with double newlines
    return "\n\n".join(markdowns)


def encode_image_for_api(image_path: Union[str, Path]) -> str:
    """
    Encode an image as base64 data URL for API submission.
    
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


def encode_bytes_for_api(file_bytes: bytes, mime_type: str) -> str:
    """
    Encode binary data as base64 data URL for API submission.
    
    Args:
        file_bytes: Binary file data
        mime_type: MIME type of the file (e.g., 'image/jpeg', 'application/pdf')
        
    Returns:
        Base64 data URL for the data
    """
    # Encode data as base64
    encoded = base64.b64encode(file_bytes).decode()
    return f"data:{mime_type};base64,{encoded}"


def calculate_image_entropy(pil_img: Image.Image) -> float:
    """
    Calculate the entropy of a PIL image.
    Entropy is a measure of randomness; low entropy indicates a blank or simple image,
    high entropy indicates more complex document_content (e.g., text or detailed images).
    
    Args:
        pil_img: PIL Image object
    
    Returns:
        float: Entropy value
    """
    # Convert to grayscale for entropy calculation
    gray_img = pil_img.convert("L")
    arr = np.array(gray_img)
    # Compute histogram
    hist, _ = np.histogram(arr, bins=256, range=(0, 255), density=True)
    # Remove zero entries to avoid log(0)
    hist = hist[hist > 0]
    # Calculate entropy
    entropy = -np.sum(hist * np.log2(hist))
    return float(entropy)


def estimate_text_density(image_np):
    """
    Estimate text density patterns in an image.
    Returns metrics on text distribution and special cases.
    
    Args:
        image_np: Numpy array of the image
        
    Returns:
        dict: Text density metrics
    """
    # Convert to grayscale
    if len(image_np.shape) > 2 and image_np.shape[2] == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np

    # Binarize image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Analyze vertical text density profile (important for headers/footers)
    height, width = gray.shape
    vertical_profile = np.sum(binary, axis=1) / width

    # Analyze horizontal text density profile
    horizontal_profile = np.sum(binary, axis=0) / height

    # Calculate statistics
    v_mean = np.mean(vertical_profile)
    v_std = np.std(vertical_profile)
    v_max = np.max(vertical_profile)

    # Detect uppercase text regions (common in headers of Baldwin document)
    # Uppercase text tends to have more consistent height and uniform vertical density
    section_height = height // 10  # Divide into 10 vertical sections
    uppercase_sections = 0

    for i in range(0, height, section_height):
        section = binary[i:min(i + section_height, height), :]
        section_profile = np.sum(section, axis=1) / width

        # Uppercase characteristics: high density with low variation
        if np.mean(section_profile) > v_mean * 1.5 and np.std(section_profile) < v_std * 0.7:
            uppercase_sections += 1

    # Determine overall pattern
    if v_std / v_mean > 0.8:
        pattern = 'varied'  # High variance indicates sections with different text densities
    else:
        pattern = 'uniform'  # Low variance indicates uniform text distribution

    return {
        'mean_density': float(v_mean),
        'density_variation': float(v_std),
        'pattern': pattern,
        'uppercase_sections': uppercase_sections,
        'max_density': float(v_max)
    }


def serialize_ocr_object(obj):
    """
    Serialize OCR response objects to JSON serializable format.
    Handles OCRImageObject specifically to prevent serialization errors.
    
    Args:
        obj: The object to serialize
        
    Returns:
        JSON serializable representation of the object
    """
    # Fast path: Handle primitive types directly
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle collections
    if isinstance(obj, list):
        return [serialize_ocr_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_ocr_object(v) for k, v in obj.items()}
    elif isinstance(obj, OCRImageObject):
        # Special handling for OCRImageObject
        return {
            'id': obj.id if hasattr(obj, 'id') else None,
            'image_base64': obj.image_base64 if hasattr(obj, 'image_base64') else None
        }
    elif hasattr(obj, '__dict__'):
        # For objects with __dict__ attribute
        return {k: serialize_ocr_object(v) for k, v in obj.__dict__.items()
                if not k.startswith('_')}  # Skip private attributes
    else:
        # Try to convert to string as last resort
        try:
            return str(obj)
        except:
            return None


# Clean OCR result with focus on Mistral compatibility
def clean_ocr_result(result, use_segmentation=False, vision_enabled=True, preprocessing_options=None):
    """
    Clean text document_content in OCR results, preserving original structure from Mistral API.
    Only removes markdown/HTML conflicts without duplicating document_content across fields.
    
    Args:
        result: OCR result object or dictionary
        use_segmentation: Whether image segmentation was used
        vision_enabled: Whether vision model was used
        preprocessing_options: Dictionary of preprocessing options
        
    Returns:
        Cleaned result object
    """
    if not result:
        return result

    # Import text utilities for cleaning
    try:
        from utils.text_utils import clean_raw_text
        text_cleaner_available = True
    except ImportError:
        text_cleaner_available = False

    def clean_text(text):
        """Clean text document_content, removing markdown image references and base64 data"""
        if not text or not isinstance(text, str):
            return ""

        if text_cleaner_available:
            text = clean_raw_text(text)
        else:
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

    # Process dictionary
    if isinstance(result, dict):
        # For PDF documents, preserve original structure from Mistral API
        is_pdf = result.get('file_type', '') == 'pdf' or (
            result.get('file_name', '').lower().endswith('.pdf')
        )

        # Ensure ocr_contents exists
        if 'ocr_contents' not in result:
            result['ocr_contents'] = {}

        # Clean raw_text if it exists but don't duplicate it
        if 'raw_text' in result:
            result['raw_text'] = clean_text(result['raw_text'])

        # Handle ocr_contents fields - clean them but don't duplicate
        if 'ocr_contents' in result:
            for key, value in list(result['ocr_contents'].items()):
                # Skip binary fields and image data
                if key in ['image_base64', 'images', 'binary_data'] and value:
                    continue

                # Clean string values to remove markdown/HTML conflicts
                if isinstance(value, str):
                    result['ocr_contents'][key] = clean_text(value)

        # Handle segmentation data
        if use_segmentation and preprocessing_options and 'segmentation_data' in preprocessing_options:
            # Store segmentation metadata
            result['segmentation_applied'] = True

            # Extract combined text if available
            if 'combined_text' in preprocessing_options['segmentation_data']:
                segmentation_text = clean_text(preprocessing_options['segmentation_data']['combined_text'])
                # Add as dedicated field
                result['ocr_contents']['segmentation_text'] = segmentation_text

                # IMPORTANT: For documents with overlapping regions like baldwin-15th-north,
                # the intelligently merged segmentation text is more accurate than the raw OCR 
                # Always use segmentation text as the primary source when available
                # This ensures clean, non-duplicated document_content from overlapping regions
                result['ocr_contents']['raw_text'] = segmentation_text

                # Also update the 'text' field which is used in some contexts
                if 'text' in result['ocr_contents']:
                    result['ocr_contents']['text'] = segmentation_text

        # Clean pages_data if available (Mistral OCR format)
        if 'pages_data' in result:
            for page in result['pages_data']:
                if isinstance(page, dict):
                    # Clean text field
                    if 'text' in page:
                        page['text'] = clean_text(page['text'])

                    # Clean markdown field
                    if 'markdown' in page:
                        page['markdown'] = clean_text(page['markdown'])

    # Handle list document_content recursively
    elif isinstance(result, list):
        return [clean_ocr_result(item, use_segmentation, vision_enabled, preprocessing_options)
                for item in result]

    return result


def create_results_zip(results, output_dir=None, zip_name=None):
    """
    Create a zip file containing OCR results.
    
    Args:
        results: Dictionary or list of OCR results
        output_dir: Optional output directory
        zip_name: Optional zip file name
        
    Returns:
        Path to the created zip file
    """
    # Create temporary output directory if not provided
    if output_dir is None:
        output_dir = Path.cwd() / "output"
        output_dir.mkdir(exist_ok=True)
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

    # Generate zip name if not provided
    if zip_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if isinstance(results, list):
            # For a list of results, create a descriptive name
            file_count = len(results)
            zip_name = f"ocr_results_{file_count}_{timestamp}.zip"
        else:
            # For single result, create descriptive filename
            base_name = results.get('file_name', 'document').split('.')[0]
            zip_name = f"{base_name}_{timestamp}.zip"

    try:
        # Get zip data in memory first
        zip_data = create_results_zip_in_memory(results)

        # Save to file
        zip_path = output_dir / zip_name
        with open(zip_path, 'wb') as f:
            f.write(zip_data)

        return zip_path
    except Exception as e:
        # Create an empty zip file as fallback
        logger.error(f"Error creating zip file: {str(e)}")
        zip_path = output_dir / zip_name
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr("info.txt", "Could not create complete archive")

        return zip_path


def create_results_zip_in_memory(results):
    """
    Create a zip file containing OCR results in memory.
    Packages markdown with embedded image tags, raw text, and JSON file
    in a contextually relevant structure.
    
    Args:
        results: Dictionary or list of OCR results
        
    Returns:
        Binary zip file data
    """
    # Create a BytesIO object
    zip_buffer = io.BytesIO()

    # Create a ZipFile instance
    with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        # Check if results is a list or a dictionary
        is_list = isinstance(results, list)

        if is_list:
            # Handle multiple results by creating subdirectories
            for idx, result in enumerate(results):
                if result and isinstance(result, dict):
                    # Create a folder name based on the file name or index
                    folder_name = result.get('file_name', f'document_{idx + 1}')
                    folder_name = Path(folder_name).stem  # Remove file extension

                    # Add files to this folder
                    add_result_files_to_zip(zipf, result, f"{folder_name}/")
        else:
            # Single result - add files directly to root of zip
            add_result_files_to_zip(zipf, results)

    # Seek to the beginning of the BytesIO object
    zip_buffer.seek(0)

    # Return the zip file bytes
    return zip_buffer.getvalue()


def truncate_base64_in_result(result, prefix_length=32, suffix_length=32):
    """
    Create a copy of the result dictionary with base64 image data truncated.
    This keeps the structure intact while making the JSON more readable.
    
    Args:
        result: OCR result dictionary
        prefix_length: Number of characters to keep at the beginning
        suffix_length: Number of characters to keep at the end
        
    Returns:
        Dictionary with truncated base64 data
    """
    if not result or not isinstance(result, dict):
        return {}

    # Create a deep copy to avoid modifying the original
    import copy
    truncated_result = copy.deepcopy(result)

    # Helper function to truncate base64 strings
    def truncate_base64(data):
        if not isinstance(data, str) or len(data) <= prefix_length + suffix_length + 10:
            return data

        # Extract prefix and suffix based on whether this is a data URI or raw base64
        if data.startswith('data:'):
            # Handle data URIs like 'data:image/jpeg;base64,/9j/4AAQ...'
            parts = data.split(',', 1)
            if len(parts) != 2:
                return data  # Unexpected format, return as is

            header = parts[0] + ','
            base64_content = parts[1]

            if len(base64_content) <= prefix_length + suffix_length + 10:
                return data  # Not long enough to truncate

            truncated = (f"{header}{base64_content[:prefix_length]}..."
                         f"[truncated {len(base64_content) - prefix_length - suffix_length} chars]..."
                         f"{base64_content[-suffix_length:]}")
        else:
            # Handle raw base64 strings
            truncated = (f"{data[:prefix_length]}..."
                         f"[truncated {len(data) - prefix_length - suffix_length} chars]..."
                         f"{data[-suffix_length:]}")

        return truncated

    # Helper function to recursively truncate base64 in nested structures
    def truncate_base64_recursive(obj):
        if isinstance(obj, dict):
            # Check for keys that typically contain base64 data
            for key in list(obj.keys()):
                if key in ['image_base64', 'base64'] and isinstance(obj[key], str):
                    obj[key] = truncate_base64(obj[key])
                elif isinstance(obj[key], (dict, list)):
                    truncate_base64_recursive(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    truncate_base64_recursive(item)

    # Truncate base64 data throughout the result
    truncate_base64_recursive(truncated_result)

    # Specifically handle the pages_data structure
    if 'pages_data' in truncated_result:
        for page in truncated_result['pages_data']:
            if isinstance(page, dict) and 'images' in page:
                for img in page['images']:
                    if isinstance(img, dict) and 'image_base64' in img and isinstance(img['image_base64'], str):
                        img['image_base64'] = truncate_base64(img['image_base64'])

    # Handle raw_response_data if present
    if 'raw_response_data' in truncated_result and isinstance(truncated_result['raw_response_data'], dict):
        if 'pages' in truncated_result['raw_response_data']:
            for page in truncated_result['raw_response_data']['pages']:
                if isinstance(page, dict) and 'images' in page:
                    for img in page['images']:
                        if isinstance(img, dict) and 'base64' in img and isinstance(img['base64'], str):
                            img['base64'] = truncate_base64(img['base64'])

    return truncated_result


def clean_base64_from_result(result):
    """
    Create a clean copy of the result dictionary with base64 image data removed.
    This ensures JSON files don't contain large base64 strings.
    
    Args:
        result: OCR result dictionary
        
    Returns:
        Cleaned dictionary without base64 data
    """
    if not result or not isinstance(result, dict):
        return {}

    # Create a deep copy to avoid modifying the original
    import copy
    clean_result = copy.deepcopy(result)

    # Helper function to recursively clean base64 from nested structures
    def clean_base64_recursive(obj):
        if isinstance(obj, dict):
            # Check for keys that typically contain base64 data
            for key in list(obj.keys()):
                if key in ['image_base64', 'base64']:
                    obj[key] = "[BASE64_DATA_REMOVED]"
                elif isinstance(obj[key], (dict, list)):
                    clean_base64_recursive(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    clean_base64_recursive(item)

    # Clean the entire result
    clean_base64_recursive(clean_result)

    # Specifically handle the pages_data structure
    if 'pages_data' in clean_result:
        for page in clean_result['pages_data']:
            if isinstance(page, dict) and 'images' in page:
                for img in page['images']:
                    if isinstance(img, dict) and 'image_base64' in img:
                        img['image_base64'] = "[BASE64_DATA_REMOVED]"

    # Handle raw_response_data if present
    if 'raw_response_data' in clean_result and isinstance(clean_result['raw_response_data'], dict):
        if 'pages' in clean_result['raw_response_data']:
            for page in clean_result['raw_response_data']['pages']:
                if isinstance(page, dict) and 'images' in page:
                    for img in page['images']:
                        if isinstance(img, dict) and 'base64' in img:
                            img['base64'] = "[BASE64_DATA_REMOVED]"

    return clean_result


def create_markdown_with_file_references(result, image_path_prefix="images/"):
    """
    Create a markdown document with file references to images instead of base64 embedding.
    Ideal for use in zip archives where images are stored as separate files.
    
    Args:
        result: OCR result dictionary
        image_path_prefix: Path prefix for image references (e.g., "images/")
        
    Returns:
        Markdown document_content as string with file references
    """
    # Similar to create_markdown_with_images but uses file references
    # Import document_content utils to use classification functions
    try:
        from utils import classify_document_content, extract_document_text, \
            extract_image_description
        content_utils_available = True
    except ImportError:
        content_utils_available = False

    # Get document_content classification
    has_text = True
    has_images = False

    if content_utils_available:
        classification = classify_document_content(result)
        has_text = classification['has_content']
        has_images = result.get('has_images', False)
    else:
        # Minimal fallback detection
        if 'has_images' in result:
            has_images = result['has_images']

        # Check for image data more thoroughly
        if 'pages_data' in result and isinstance(result['pages_data'], list):
            for page in result['pages_data']:
                if isinstance(page, dict) and 'images' in page and page['images']:
                    has_images = True
                    break

    # Start building the markdown document
    md = []

    # Add document title/header
    md.append(f"# {result.get('file_name', 'Document')}\n")

    # Add metadata section
    md.append("## Document Metadata\n")

    # Add timestamp
    if 'timestamp' in result:
        md.append(f"**Processed:** {result['timestamp']}\n")

    # Add languages if available
    if 'languages' in result and result['languages']:
        languages = [lang for lang in result['languages'] if lang]
        if languages:
            md.append(f"**Languages:** {', '.join(languages)}\n")

    # Add document type and topics
    if 'detected_document_type' in result:
        md.append(f"**Document Type:** {result['detected_document_type']}\n")

    if 'topics' in result and result['topics']:
        md.append(f"**Topics:** {', '.join(result['topics'])}\n")

    md.append("\n---\n")

    # Document title - extract from result if available
    if 'ocr_contents' in result and 'title' in result['ocr_contents'] and result['ocr_contents']['title']:
        title_content = result['ocr_contents']['title']
        md.append(f"## {title_content}\n")

    # Add images if present
    if has_images and 'pages_data' in result:
        md.append("## Images\n")

        # Extract and display all images with file references
        for page_idx, page in enumerate(result['pages_data']):
            if 'images' in page and isinstance(page['images'], list):
                for img_idx, img in enumerate(page['images']):
                    if 'image_base64' in img:
                        # Create image reference to file in the zip
                        image_filename = f"image_{page_idx + 1}_{img_idx + 1}.jpg"
                        image_path = f"{image_path_prefix}{image_filename}"
                        image_caption = f"Image {page_idx + 1}-{img_idx + 1}"
                        md.append(f"![{image_caption}]({image_path})\n")

                        # Add image description if available through utils
                        if content_utils_available:
                            description = extract_image_description(result)
                            if description:
                                md.append(f"*{description}*\n")

        md.append("\n---\n")

    # Add document text section
    md.append("## Text Content\n")

    # Extract text document_content systematically
    text_content = ""
    structured_sections = {}

    # Helper function to extract clean text from dictionary objects
    def extract_clean_text(content):
        if isinstance(content, str):
            # Check if document_content is a stringified JSON
            if content.strip().startswith("{") and content.strip().endswith("}"):
                try:
                    # Try to parse as JSON
                    content_dict = json.loads(content.replace("'", '"'))
                    if 'text' in content_dict:
                        return content_dict['text']
                    return content
                except:
                    return content
            return content
        elif isinstance(content, dict):
            # If it's a dictionary with a 'text' key, return just that value
            if 'text' in content and isinstance(content['text'], str):
                return content['text']
            return content
        return content

    if content_utils_available:
        # Use the systematic utility function for main text
        text_content = extract_document_text(result)
        text_content = extract_clean_text(text_content)

        # Collect all available structured sections
        if 'ocr_contents' in result:
            for field, content in result['ocr_contents'].items():
                # Skip certain fields that are handled separately
                if field in ["raw_text", "error", "partial_text", "main_text"]:
                    continue

                if content:
                    # Extract clean text from document_content if possible
                    clean_content = extract_clean_text(content)
                    # Add this as a structured section
                    structured_sections[field] = clean_content
    else:
        # Fallback extraction logic
        if 'ocr_contents' in result:
            # First find main text
            for field in ["main_text", "document_content", "text", "transcript", "raw_text"]:
                if field in result['ocr_contents'] and result['ocr_contents'][field]:
                    content = result['ocr_contents'][field]
                    if isinstance(content, str) and content.strip():
                        text_content = content
                        break
                    elif isinstance(content, dict):
                        # Try to convert complex objects to string
                        try:
                            text_content = json.dumps(content, indent=2)
                            break
                        except:
                            pass

            # Then collect all structured sections
            for field, content in result['ocr_contents'].items():
                # Skip certain fields that are handled separately
                if field in ["raw_text", "error", "partial_text", "main_text", "document_content", "text",
                             "transcript"]:
                    continue

                if content:
                    # Add this as a structured section
                    structured_sections[field] = content

    # Add the main text document_content - display raw text without a field label
    if text_content:
        # Check if this is from raw_text (based on document_content match)
        is_raw_text = False
        if 'ocr_contents' in result and 'raw_text' in result['ocr_contents']:
            if result['ocr_contents']['raw_text'] == text_content:
                is_raw_text = True

        # Display document_content without adding a "raw_text:" label
        md.append(text_content + "\n\n")

    # Add structured sections if available
    if structured_sections:
        for section_name, section_content in structured_sections.items():
            # Use proper markdown header for sections - consistently capitalize all section names
            display_name = section_name.replace("_", " ").capitalize()
            # Handle different document_content types
            if isinstance(section_content, str):
                md.append(section_content + "\n\n")
            elif isinstance(section_content, dict):
                # Dictionary document_content - format as key-value pairs
                for key, value in section_content.items():
                    # Treat all values as plain text to maintain document_content purity
                    # This prevents JSON-like structures from being formatted as code blocks
                    md.append(f"**{key}:** {value}\n\n")
            elif isinstance(section_content, list):
                # List document_content - create a markdown list
                for item in section_content:
                    # Treat all items as plain text
                    md.append(f"- {item}\n")
                md.append("\n")

    # Join all markdown parts into a single string
    return "\n".join(md)


def add_result_files_to_zip(zipf, result, prefix=""):
    """
    Add files for a single result to a zip file.
    
    Args:
        zipf: ZipFile instance to add files to
        result: OCR result dictionary
        prefix: Optional prefix for file paths in the zip
    """
    if not result or not isinstance(result, dict):
        return

    # Create a timestamp for filename if not in result
    timestamp = result.get('timestamp', datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

    # Get base name for files
    file_name = result.get('file_name', 'document')
    base_name = Path(file_name).stem

    try:
        # 1. Add JSON file - with base64 data cleaned out
        clean_result = clean_base64_from_result(result)
        json_str = json.dumps(clean_result, indent=2)
        zipf.writestr(f"{prefix}{base_name}.json", json_str)

        # 2. Add markdown file that exactly matches Tab 1 display
        # Use the create_markdown_with_images function to ensure it matches the UI exactly
        try:
            markdown_content = create_markdown_with_images(result)
            zipf.writestr(f"{prefix}{base_name}.md", markdown_content)
        except Exception as e:
            logger.error(f"Error creating markdown: {str(e)}")
            # Fallback to simpler markdown if error occurs
            zipf.writestr(f"{prefix}{base_name}.md", f"# {file_name}\n\nError generating complete markdown output.")

        # Extract and save images first to ensure they exist before creating markdown
        img_paths = {}
        has_images = result.get('has_images', False)

        # 3. Add individual images if available
        if has_images and 'pages_data' in result:
            img_folder = f"{prefix}images/"
            for page_idx, page in enumerate(result['pages_data']):
                if 'images' in page and isinstance(page['images'], list):
                    for img_idx, img in enumerate(page['images']):
                        if 'image_base64' in img and img['image_base64']:
                            # Extract the base64 data
                            try:
                                # Get the base64 data
                                img_data = img['image_base64']

                                # Handle the base64 data carefully
                                if isinstance(img_data, str):
                                    # If it has a data URI prefix, remove it
                                    if ',' in img_data and ';base64,' in img_data:
                                        # Keep the complete data after the comma
                                        img_data = img_data.split(',', 1)[1]

                                    # Make sure we have the complete data (not truncated)
                                    try:
                                        # Decode the base64 data with padding correction
                                        # Add padding if needed to prevent truncation errors
                                        missing_padding = len(img_data) % 4
                                        if missing_padding:
                                            img_data += '=' * (4 - missing_padding)
                                        img_bytes = base64.b64decode(img_data)
                                    except Exception as e:
                                        logger.error(f"Base64 decoding error: {str(e)} for image {page_idx}-{img_idx}")
                                        # Skip this image if we can't decode it
                                        continue
                                else:
                                    # If it's not a string (e.g., already bytes), use it directly
                                    img_bytes = img_data

                                # Create image filename
                                image_filename = f"image_{page_idx + 1}_{img_idx + 1}.jpg"
                                img_paths[(page_idx, img_idx)] = image_filename

                                # Write the image to the zip file
                                zipf.writestr(f"{img_folder}{image_filename}", img_bytes)
                            except Exception as e:
                                logger.warning(f"Could not add image to zip: {str(e)}")

        # 4. Add markdown with file references to images for offline viewing
        try:
            if has_images:
                # Create markdown with file references
                file_ref_markdown = create_markdown_with_file_references(result, "images/")
                zipf.writestr(f"{prefix}{base_name}_with_files.md", file_ref_markdown)
        except Exception as e:
            logger.warning(f"Error creating markdown with file references: {str(e)}")

        # 5. Add README.txt with explanation of file contents
        readme_content = f"""
OCR RESULTS FOR: {file_name}
Processed: {timestamp}

This archive contains the following files:

- {base_name}.json: Complete JSON data with all extracted information
- {base_name}.md: Markdown document with embedded base64 images (exactly as shown in the app)
- {base_name}_with_files.md: Alternative markdown with file references instead of base64 (for offline viewing)
- images/ folder: Contains extracted images from the document (if present)

Generated by Historical OCR using Mistral AI
        """
        zipf.writestr(f"{prefix}README.txt", readme_content.strip())

    except Exception as e:
        logger.error(f"Error adding files to zip: {str(e)}")


def create_markdown_with_images(result):
    """
    Create a clean Markdown document from OCR results that properly preserves 
    image references and text structure, following the principle of document_content purity.
    
    Args:
        result: OCR result dictionary
        
    Returns:
        Markdown document_content as string
    """
    # Similar to create_markdown_with_file_references but embeds base64 images
    # Import document_content utils to use classification functions
    try:
        content_utils_available = True
    except ImportError:
        content_utils_available = False

    # Get document_content classification
    has_text = True
    has_images = False

    if content_utils_available:
        classification = classify_document_content(result)
        has_text = classification['has_content']
        has_images = result.get('has_images', False)
    else:
        # Minimal fallback detection
        if 'has_images' in result:
            has_images = result['has_images']

        # Check for image data more thoroughly
        if 'pages_data' in result and isinstance(result['pages_data'], list):
            for page in result['pages_data']:
                if isinstance(page, dict) and 'images' in page and page['images']:
                    has_images = True
                    break

    # Start building the markdown document
    md = []

    # Add document title/header
    md.append(f"# {result.get('file_name', 'Document')}\n")

    # Add metadata section
    md.append("## Document Metadata\n")

    # Add timestamp
    if 'timestamp' in result:
        md.append(f"**Processed:** {result['timestamp']}\n")

    # Add languages if available
    if 'languages' in result and result['languages']:
        languages = [lang for lang in result['languages'] if lang]
        if languages:
            md.append(f"**Languages:** {', '.join(languages)}\n")

    # Add document type and topics
    if 'detected_document_type' in result:
        md.append(f"**Document Type:** {result['detected_document_type']}\n")

    if 'topics' in result and result['topics']:
        md.append(f"**Topics:** {', '.join(result['topics'])}\n")

    md.append("\n---\n")

    # Document title - extract from result if available
    if 'ocr_contents' in result and 'title' in result['ocr_contents'] and result['ocr_contents']['title']:
        title_content = result['ocr_contents']['title']
        md.append(f"## {title_content}\n")

    # Add images if present - with base64 embedding
    if has_images and 'pages_data' in result:
        md.append("## Images\n")

        # Extract and display all images with embedded base64
        for page_idx, page in enumerate(result['pages_data']):
            if 'images' in page and isinstance(page['images'], list):
                for img_idx, img in enumerate(page['images']):
                    if 'image_base64' in img:
                        # Use the base64 data directly
                        image_caption = f"Image {page_idx + 1}-{img_idx + 1}"
                        img_data = img['image_base64']

                        # Make sure it has proper data URI format
                        if isinstance(img_data, str) and not img_data.startswith('data:'):
                            img_data = f"data:image/jpeg;base64,{img_data}"

                        md.append(f"![{image_caption}]({img_data})\n")

                        # Add image description if available through utils
                        if content_utils_available:
                            description = extract_image_description(result)
                            if description:
                                md.append(f"*{description}*\n")

        md.append("\n---\n")

    # Add document text section
    md.append("## Text Content\n")

    # Extract text document_content systematically
    text_content = ""
    structured_sections = {}

    if content_utils_available:
        # Use the systematic utility function for main text
        text_content = extract_document_text(result)

        # Collect all available structured sections
        if 'ocr_contents' in result:
            for field, content in result['ocr_contents'].items():
                # Skip certain fields that are handled separately
                if field in ["raw_text", "error", "partial_text", "main_text"]:
                    continue

                if content:
                    # Add this as a structured section
                    structured_sections[field] = content
    else:
        # Fallback extraction logic
        if 'ocr_contents' in result:
            # First find main text
            for field in ["main_text", "document_content", "text", "transcript", "raw_text"]:
                if field in result['ocr_contents'] and result['ocr_contents'][field]:
                    content = result['ocr_contents'][field]
                    if isinstance(content, str) and content.strip():
                        text_content = content
                        break
                    elif isinstance(content, dict):
                        # Try to convert complex objects to string
                        try:
                            text_content = json.dumps(content, indent=2)
                            break
                        except:
                            pass

            # Then collect all structured sections
            for field, content in result['ocr_contents'].items():
                # Skip certain fields that are handled separately
                if field in ["raw_text", "error", "partial_text", "main_text", "document_content", "text",
                             "transcript"]:
                    continue

                if content:
                    # Add this as a structured section
                    structured_sections[field] = content

    # Add the main text document_content
    if text_content:
        md.append(text_content + "\n\n")

    # Add structured sections if available
    if structured_sections:
        for section_name, section_content in structured_sections.items():
            # Use proper markdown header for sections - consistently capitalize all section names
            display_name = section_name.replace("_", " ").capitalize()
            md.append(f"### {display_name}\n")
            # Add a separator for clarity
            md.append("\n---\n\n")

            # Handle different document_content types
            if isinstance(section_content, str):
                md.append(section_content + "\n\n")
            elif isinstance(section_content, dict):
                # Dictionary document_content - format as key-value pairs
                for key, value in section_content.items():
                    # Treat all values as plain text to maintain document_content purity
                    md.append(f"**{key}:** {value}\n\n")
            elif isinstance(section_content, list):
                # List document_content - create a markdown list
                for item in section_content:
                    # Keep list items as plain text
                    md.append(f"- {item}\n")
                md.append("\n")

    # Join all markdown parts into a single string
    return "\n".join(md)
