import io
import logging
import math
import tempfile
import time

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageStat
from PIL import ImageEnhance
from pdf2image import convert_from_bytes

from backend.utils.helper.image_utils import detect_skew


def get_document_config(document_format, global_config):
    """
    Get document-specific preprocessing configuration by merging with global settings.

    Args:
        document_format: The type of document (e.g., 'standard', 'newspaper', 'handwritten')
        global_config: The global preprocessing configuration

    Returns:
        A merged configuration dictionary with document-specific overrides
    """
    # Start with a copy of the global config
    config = {
        "deskew": global_config.get("deskew", {}),
        "thresholding": global_config.get("thresholding", {}),
        "morphology": global_config.get("morphology", {}),
        "performance": global_config.get("performance", {}),
        "logging": global_config.get("logging", {})
    }

    # Apply document-specific overrides if they exist
    doc_types = global_config.get("document_formats", {})
    if document_format in doc_types:
        doc_config = doc_types[document_format]

        # Merge document-specific settings into the config
        for section in doc_config:
            if section in config:
                config[section].update(doc_config[section])

    return config


def deskew_image(img_array, config):
    """
    Detect and correct skew in document images.

    Uses a combination of methods (minAreaRect and/or Hough transform)
    to estimate the skew angle more robustly.

    Args:
        img_array: Input image as numpy array
        config: Deskew configuration dict

    Returns:
        Deskewed image as numpy array, estimated angle, success flag
    """
    if not config.get("enabled", False):
        return img_array, 0.0, True

    # Convert to grayscale if needed
    gray = img_array if len(img_array.shape) == 2 else cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Start with a threshold to get binary image for angle detection
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    angles = []
    angle_threshold = config.get("angle_threshold", 0.1)
    max_angle = config.get("max_angle", 45.0)

    # Method 1: minAreaRect approach
    try:
        # Find all contours
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by area to avoid noise
        min_area = binary.shape[0] * binary.shape[1] * 0.0001  # 0.01% of image area
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

        # Get angles from rotated rectangles around contours
        for contour in filtered_contours:
            rect = cv2.minAreaRect(contour)
            width, height = rect[1]

            # Calculate the angle based on the longer side
            # (This is important for getting the orientation right)
            angle = rect[2]
            if width < height:
                angle += 90

            # Normalize angle to -45 to 45 range
            if angle > 45:
                angle -= 90
            if angle < -45:
                angle += 90

            # Clamp angle to max limit
            angle = max(min(angle, max_angle), -max_angle)
            angles.append(angle)
    except Exception as e:
        logger.error(f"Error in minAreaRect skew detection: {str(e)}")

    # Method 2: Hough Transform approach (if enabled)
    if config.get("use_hough", True):
        try:
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Apply Hough lines
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                    threshold=100, minLineLength=100, maxLineGap=10)

            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if x2 - x1 != 0:  # Avoid division by zero
                        # Calculate line angle in degrees
                        angle = math.atan2(y2 - y1, x2 - x1) * 180.0 / np.pi

                        # Normalize angle to -45 to 45 range
                        if angle > 45:
                            angle -= 90
                        if angle < -45:
                            angle += 90

                        # Clamp angle to max limit
                        angle = max(min(angle, max_angle), -max_angle)
                        angles.append(angle)
        except Exception as e:
            logger.error(f"Error in Hough transform skew detection: {str(e)}")

    # If no angles were detected, return original image
    if not angles:
        logger.warning("No skew angles detected, using original image")
        return img_array, 0.0, False

    # Combine angles using the specified consensus method
    consensus_method = config.get("consensus_method", "average")
    if consensus_method == "average":
        final_angle = sum(angles) / len(angles)
    elif consensus_method == "median":
        final_angle = sorted(angles)[len(angles) // 2]
    elif consensus_method == "min":
        final_angle = min(angles, key=abs)
    elif consensus_method == "max":
        final_angle = max(angles, key=abs)
    else:
        final_angle = sum(angles) / len(angles)  # Default to average

    # If angle is below threshold, don't rotate
    if abs(final_angle) < angle_threshold:
        logger.info(f"Detected angle ({final_angle:.2f}°) is below threshold, skipping deskew")
        return img_array, final_angle, True

    # Log the detected angle
    logger.info(f"Deskewing image with angle: {final_angle:.2f}°")

    # Get image dimensions
    h, w = img_array.shape[:2]
    center = (w // 2, h // 2)

    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, final_angle, 1.0)

    # Calculate new image dimensions
    abs_cos = abs(rotation_matrix[0, 0])
    abs_sin = abs(rotation_matrix[0, 1])
    new_w = int(h * abs_sin + w * abs_cos)
    new_h = int(h * abs_cos + w * abs_sin)

    # Adjust the rotation matrix to account for new dimensions
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]

    # Perform the rotation
    try:
        # Determine the number of channels to create the correct output array
        if len(img_array.shape) == 3:
            rotated = cv2.warpAffine(img_array, rotation_matrix, (new_w, new_h),
                                     flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=(255, 255, 255))
        else:
            rotated = cv2.warpAffine(img_array, rotation_matrix, (new_w, new_h),
                                     flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=255)
        return rotated, final_angle, True
    except Exception as e:
        logger.error(f"Error rotating image: {str(e)}")
        if config.get("fallback", {}).get("enabled", True):
            logger.info("Using original image as fallback after rotation failure")
            return img_array, final_angle, False
        return img_array, final_angle, False


def preblur(img_array, config):
    """
    Apply pre-filtering blur to stabilize thresholding results.

    Args:
        img_array: Input image as numpy array
        config: Pre-blur configuration dict

    Returns:
        Blurred image as numpy array
    """
    if not config.get("enabled", False):
        return img_array

    method = config.get("method", "gaussian")
    kernel_size = config.get("kernel_size", 3)

    # Ensure kernel size is odd
    if kernel_size % 2 == 0:
        kernel_size += 1

    try:
        if method == "gaussian":
            return cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)
        elif method == "median":
            return cv2.medianBlur(img_array, kernel_size)
        else:
            logger.warning(f"Unknown blur method: {method}, using gaussian")
            return cv2.GaussianBlur(img_array, (kernel_size, kernel_size), 0)
    except Exception as e:
        logger.error(f"Error applying {method} blur: {str(e)}")
        return img_array


def apply_threshold(img_array, config):
    """
    Apply thresholding to create binary image.

    Supports Otsu's method and adaptive thresholding.
    Includes pre-filtering and fallback mechanisms.

    Args:
        img_array: Input image as numpy array
        config: Thresholding configuration dict

    Returns:
        Binary image as numpy array, success flag
    """
    method = config.get("method", "adaptive")
    if method == "none":
        return img_array, True

    # Convert to grayscale if needed
    gray = img_array if len(img_array.shape) == 2 else cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Apply pre-blur if configured
    preblur_config = config.get("preblur", {})
    if preblur_config.get("enabled", False):
        gray = preblur(gray, preblur_config)

    binary = None
    try:
        if method == "otsu":
            # Apply Otsu's thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == "adaptive":
            # Apply adaptive thresholding
            block_size = config.get("adaptive_block_size", 11)
            constant = config.get("adaptive_constant", 2)

            # Ensure block size is odd
            if block_size % 2 == 0:
                block_size += 1

            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, block_size, constant)
        else:
            logger.warning(f"Unknown thresholding method: {method}, using adaptive")
            block_size = config.get("adaptive_block_size", 11)
            constant = config.get("adaptive_constant", 2)

            # Ensure block size is odd
            if block_size % 2 == 0:
                block_size += 1

            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, block_size, constant)
    except Exception as e:
        logger.error(f"Error applying {method} thresholding: {str(e)}")
        if config.get("fallback", {}).get("enabled", True):
            logger.info("Using original grayscale image as fallback after thresholding failure")
            return gray, False
        return gray, False

    # Calculate percentage of non-zero pixels for logging
    nonzero_pct = np.count_nonzero(binary) / binary.size * 100
    logger.info(f"Binary image has {nonzero_pct:.2f}% non-zero pixels")

    # Check if thresholding was successful (crude check)
    if nonzero_pct < 1 or nonzero_pct > 99:
        logger.warning(f"Thresholding produced extreme result ({nonzero_pct:.2f}% non-zero)")
        if config.get("fallback", {}).get("enabled", True):
            logger.info("Using original grayscale image as fallback after poor thresholding")
            return gray, False

    return binary, True


def apply_morphology(binary_img, config):
    """
    Apply morphological operations to clean up binary image.

    Supports opening, closing, or both operations.

    Args:
        binary_img: Binary image as numpy array
        config: Morphology configuration dict

    Returns:
        Processed binary image as numpy array
    """
    if not config.get("enabled", False):
        return binary_img

    operation = config.get("operation", "close")
    kernel_size = config.get("kernel_size", 1)
    kernel_shape = config.get("kernel_shape", "rect")

    # Create appropriate kernel
    if kernel_shape == "rect":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size * 2 + 1, kernel_size * 2 + 1))
    elif kernel_shape == "ellipse":
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size * 2 + 1, kernel_size * 2 + 1))
    elif kernel_shape == "cross":
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (kernel_size * 2 + 1, kernel_size * 2 + 1))
    else:
        logger.warning(f"Unknown kernel shape: {kernel_shape}, using rect")
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size * 2 + 1, kernel_size * 2 + 1))

    result = binary_img
    try:
        if operation == "open":
            # Opening: Erosion followed by dilation - removes small noise
            result = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
        elif operation == "close":
            # Closing: Dilation followed by erosion - fills small holes
            result = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel)
        elif operation == "both":
            # Both operations in sequence
            result = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
        else:
            logger.warning(f"Unknown morphological operation: {operation}, using close")
            result = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel)
    except Exception as e:
        logger.error(f"Error applying morphological operation: {str(e)}")
        return binary_img

    return result


@st.cache_data(ttl=24 * 3600, show_spinner=False)  # Cache for 24 hours
def convert_pdf_to_images(pdf_bytes, dpi=150, rotation=0):
    """Convert PDF bytes to a list of images with caching"""
    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi)

        # Apply rotation if specified
        if rotation != 0 and images:
            rotated_images = []
            for img in images:
                rotated_img = img.rotate(rotation, expand=True, resample=Image.BICUBIC)
                rotated_images.append(rotated_img)
            return rotated_images

        return images
    except Exception as e:
        st.error(f"Error converting PDF: {str(e)}")
        logger.error(f"PDF conversion error: {str(e)}")
        return []


@st.cache_data(ttl=24 * 3600, show_spinner=False, hash_funcs={dict: lambda x: str(sorted(x.items()))})
def preprocess_image(image_bytes, preprocessing_options):
    """
    Conservative preprocessing function for handwritten documents with early exit for clean scans.
    Implements light processing: grayscale → denoise (gently) → contrast (conservative)

    Args:
        image_bytes: Image document_content as bytes
        preprocessing_options: Dictionary with document_format, grayscale, denoise, contrast options

    Returns:
        Processed image bytes or original image bytes if no processing needed
    """
    # Setup basic console logging
    logger = logging.getLogger("image_preprocessor")
    logger.setLevel(logging.INFO)

    # Log which preprocessing options are being applied
    logger.info(f"Document type: {preprocessing_options.get('document_format', 'STANDARD')}")

    # Check if any preprocessing is actually requested
    has_preprocessing = (
            preprocessing_options.get("grayscale", False) or
            preprocessing_options.get("denoise", False) or
            preprocessing_options.get("contrast", 0) != 0
    )

    # Convert bytes to PIL Image
    image = Image.open(io.BytesIO(image_bytes))

    # Check for minimal skew and exit early if document is already straight
    # This avoids unnecessary processing for clean scans
    try:
        skew_angle = detect_skew(image)
        if abs(skew_angle) < 0.5:
            logger.info(f"Document has minimal skew ({skew_angle:.2f}°), skipping preprocessing")
            # Return original image bytes as is for perfectly straight documents
            if not has_preprocessing:
                return image_bytes
    except Exception as e:
        logger.warning(f"Error in skew detection: {str(e)}, continuing with preprocessing")

    # If no preprocessing options are selected, return the original image
    if not has_preprocessing:
        logger.info("No preprocessing options selected, skipping preprocessing")
        return image_bytes

    # Initialize metrics for logging
    metrics = {
        "file": preprocessing_options.get("filename", "unknown"),
        "document_format": preprocessing_options.get("document_format", "STANDARD"),
        "preprocessing_applied": []
    }
    start_time = time.time()

    # Handle RGBA images (transparency) by converting to RGB
    if image.mode == 'RGBA':
        # Convert RGBA to RGB by compositing onto white background
        logger.info("Converting RGBA image to RGB")
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        image = background
        metrics["preprocessing_applied"].append("alpha_conversion")
    elif image.mode not in ('RGB', 'L'):
        # Convert other modes to RGB
        logger.info(f"Converting {image.mode} image to RGB")
        image = image.convert('RGB')
        metrics["preprocessing_applied"].append("format_conversion")

    # Convert to NumPy array for OpenCV processing
    img_array = np.array(image)

    # Apply grayscale if requested (useful for handwritten text)
    if preprocessing_options.get("grayscale", False):
        if len(img_array.shape) == 3:  # Only convert if it's not already grayscale
            # For handwritten documents, apply gentle CLAHE to enhance contrast locally
            if preprocessing_options.get("document_format") == "HANDWRITTEN":
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))  # Conservative clip limit
                img_array = clahe.apply(img_array)
            else:
                # Standard grayscale for printed documents
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

            metrics["preprocessing_applied"].append("grayscale")

    # Apply light denoising if requested
    if preprocessing_options.get("denoise", False):
        try:
            # Apply very gentle denoising
            is_color = len(img_array.shape) == 3 and img_array.shape[2] == 3
            if is_color:
                # Very light color denoising with conservative parameters
                img_array = cv2.fastNlMeansDenoisingColored(img_array, None, 2, 2, 3, 7)
            else:
                # Very light grayscale denoising
                img_array = cv2.fastNlMeansDenoising(img_array, None, 2, 3, 7)

            metrics["preprocessing_applied"].append("light_denoise")
        except Exception as e:
            logger.error(f"Denoising error: {str(e)}")

    # Apply contrast adjustment if requested (conservative range)
    contrast_value = preprocessing_options.get("contrast", 0)
    if contrast_value != 0:
        # Use a gentler contrast adjustment factor
        contrast_factor = 1 + (contrast_value / 200)  # Conservative scaling factor

        # Convert NumPy array back to PIL Image for contrast adjustment
        if len(img_array.shape) == 2:  # If grayscale, convert to RGB for PIL
            image = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB))
        else:
            image = Image.fromarray(img_array)

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)

        # Convert back to NumPy array
        img_array = np.array(image)
        metrics["preprocessing_applied"].append(f"contrast_{contrast_value}")

    # Convert back to PIL Image
    if len(img_array.shape) == 2:  # If grayscale, convert to RGB for saving
        processed_image = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB))
    else:
        processed_image = Image.fromarray(img_array)

    # Record total processing time
    metrics["processing_time"] = (time.time() - start_time) * 1000  # ms

    # Higher quality for OCR processing
    byte_io = io.BytesIO()
    try:
        # Make sure the image is in RGB mode before saving as JPEG
        if processed_image.mode not in ('RGB', 'L'):
            processed_image = processed_image.convert('RGB')

        processed_image.save(byte_io, format='JPEG', quality=92, optimize=True)
        byte_io.seek(0)

        logger.info(
            f"Preprocessing complete. Original image mode: {image.mode}, processed mode: {processed_image.mode}")
        logger.info(
            f"Original size: {len(image_bytes) / 1024:.1f}KB, processed size: {len(byte_io.getvalue()) / 1024:.1f}KB")
        logger.info(f"Applied preprocessing steps: {', '.join(metrics['preprocessing_applied'])}")

        return byte_io.getvalue()
    except Exception as e:
        logger.error(f"Error saving processed image: {str(e)}")
        # Fallback to original image
        logger.info("Using original image as fallback")
        return image_bytes


def create_temp_file(content, suffix, temp_file_paths):
    """Create a temporary file and track it for cleanup"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        temp_path = tmp.name
        # Track temporary file for cleanup
        temp_file_paths.append(temp_path)
        logger.info(f"Created temporary file: {temp_path}")
        return temp_path


def apply_preprocessing_to_file(file_bytes, file_ext, preprocessing_options, temp_file_paths):
    """
    Apply conservative preprocessing to file and return path to the temporary file.
    Handles format conversion and user-selected preprocessing options.

    Args:
        file_bytes: File document_content as bytes
        file_ext: File extension (e.g., '.jpg', '.pdf')
        preprocessing_options: Dictionary with document_format and preprocessing options
        temp_file_paths: List to track temporary files for cleanup

    Returns:
        Tuple of (temp_file_path, was_processed_flag)
    """
    document_format = preprocessing_options.get("document_format", "STANDARD")

    # Check for user-selected preprocessing
    has_preprocessing = (
            preprocessing_options.get("grayscale", False) or
            preprocessing_options.get("denoise", False) or
            preprocessing_options.get("contrast", 0) != 0
    )

    # Check for RGBA/transparency that needs conversion
    format_needs_conversion = False

    # Only check formats that might have transparency
    if file_ext.lower() in ['.png', '.tif', '.tiff']:
        try:
            # Check if image has transparency
            image = Image.open(io.BytesIO(file_bytes))
            if image.mode == 'RGBA' or image.mode not in ('RGB', 'L'):
                format_needs_conversion = True
        except Exception as e:
            logger.warning(f"Error checking image format: {str(e)}")

    # Process if user requested preprocessing OR format needs conversion
    needs_processing = has_preprocessing or format_needs_conversion

    if needs_processing:
        # Apply preprocessing
        logger.info(f"Applying preprocessing with options: {preprocessing_options}")
        logger.info(f"Using document type '{document_format}' with advanced preprocessing options")

        # Add filename to preprocessing options for logging if available
        if hasattr(file_bytes, 'name'):
            preprocessing_options["filename"] = file_bytes.name

        processed_bytes = preprocess_image(file_bytes, preprocessing_options)

        # Save processed image to temp file
        temp_path = create_temp_file(processed_bytes, file_ext, temp_file_paths)
        return temp_path, True  # Return path and flag indicating preprocessing was applied
    else:
        # No preprocessing needed, just save the original file
        logger.info("No preprocessing applied - using original image")
        temp_path = create_temp_file(file_bytes, file_ext, temp_file_paths)
        return temp_path, False  # Return path and flag indicating no preprocessing was applied


def analyze_image_quality(image_bytes):
    """Analyze image and auto-generate preprocessing config."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    stat = ImageStat.Stat(image)

    # --- Blur detection ---
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = laplacian_var < 50  # Threshold can be tuned

    # --- Brightness detection ---
    brightness = stat.mean[0]  # PIL's mean brightness
    is_dark = brightness < 80
    is_bright = brightness > 200

    # --- Contrast detection ---
    contrast = stat.stddev[0]
    is_low_contrast = contrast < 25

    # --- Skew detection (simple) ---
    # Optional: Use your existing detect_skew or a quick check

    config = {
        "grayscale": True,  # Always grayscale for OCR
        "denoise": is_blurry,  # Apply denoise if blurry
        "contrast": 20 if is_low_contrast else 0,  # Adjust contrast up if needed
        "brightness": 20 if is_dark else (-20 if is_bright else 0),  # Fix brightness
        "deskew": {
            "enabled": True  # Always deskew, or add angle threshold if you like
        }
    }

    # Optionally, log/print detected properties
    print(
        f"Blur: {laplacian_var:.1f}, Bright: {brightness:.1f}, Contrast: {contrast:.1f}, Blurry: {is_blurry}, LowContrast: {is_low_contrast}, Dark: {is_dark}, Bright: {is_bright}")

    return config


def dynamic_preprocess_image(image_bytes):
    # 1. Auto-analyze and get config
    preprocessing_options = analyze_image_quality(image_bytes)
    # 2. Run your usual preprocessing
    return preprocess_image(image_bytes, preprocessing_options)
