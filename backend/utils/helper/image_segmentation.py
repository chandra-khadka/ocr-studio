"""
Image segmentation utility for OCR preprocessing.
Separates text regions from image regions to improve OCR accuracy on mixed-document_content documents.
Uses document_content-aware adaptive segmentation for improved results across document types.
"""

import base64
from pathlib import Path
from typing import Dict, Union, Optional

import cv2
import numpy as np
from PIL import Image

from backend.config import logger
from backend.utils.helper.image_utils import estimate_text_density
from backend.utils.helper.text_utils import detect_content_regions


def segment_image_for_ocr(image_path: Union[str, Path], vision_enabled: bool = True, preserve_content: bool = True) -> \
        Dict[str, Union[Image.Image, str]]:
    """
    Prepare image for OCR processing using document_content-aware segmentation.
    Uses adaptive region detection based on text density analysis.

    Args:
        image_path: Path to the image file
        vision_enabled: Whether the vision model is enabled
        preserve_content: Whether to preserve original document_content without enhancement

    Returns:
        Dict containing segmentation results
    """
    # Convert to Path object if string
    image_file = Path(image_path) if isinstance(image_path, str) else image_path

    # Log start of processing
    logger.info(f"Preparing image for Mistral OCR: {image_file.name}")

    try:
        # Open original image with PIL
        with Image.open(image_file) as pil_img:
            # Check for low entropy images when vision is disabled
            if not vision_enabled:
                from backend.utils.helper.image_utils import calculate_image_entropy
                ent = calculate_image_entropy(pil_img)
                if ent < 3.5:  # Likely line-art or blank page
                    logger.info(f"Low entropy image detected ({ent:.2f}), classifying as illustration")
                    return {
                        'text_regions': None,
                        'image_regions': pil_img,
                        'text_mask_base64': None,
                        'combined_result': None,
                        'text_regions_coordinates': []
                    }

            # Convert to RGB if needed
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')

            # Get image dimensions
            img_np = np.array(pil_img)
            img_width, img_height = pil_img.size

            # Analyze text density to determine if advanced segmentation is needed
            # This replaces document-specific logic with document_content-aware analysis
            text_density = estimate_text_density(img_np)

            # Use adaptive approach for documents with unusual text distribution
            if text_density['pattern'] == 'varied' or text_density['uppercase_sections'] > 0:
                logger.info(
                    f"Using adaptive segmentation for document with varied text density pattern={text_density['pattern']}, uppercase_sections={text_density['uppercase_sections']}")

                # Detect document_content regions based on text density
                regions = detect_content_regions(img_np)

                # Create visualization with green borders around the text regions
                vis_img = img_np.copy()

                # Draw regions on visualization
                for x, y, w, h in regions:
                    cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 255, 0), 3)

                # Add text to indicate we're using adaptive processing
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(vis_img, "Adaptive region processing", (30, 60), font, 1, (0, 255, 0), 2)

                # Create visualization images
                text_regions_vis = Image.fromarray(vis_img)
                image_regions_vis = text_regions_vis.copy()

                # Create a mask highlighting the text regions
                text_mask = np.zeros((img_height, img_width), dtype=np.uint8)
                for x, y, w, h in regions:
                    text_mask[y:y + h, x:x + w] = 255

                _, buffer = cv2.imencode('.png', text_mask)
                text_mask_base64 = base64.b64encode(buffer).decode('utf-8')

                # Extract region images
                region_images = []
                for i, (x, y, w, h) in enumerate(regions):
                    region = img_np[y:y + h, x:x + w].copy()
                    region_pil = Image.fromarray(region)

                    region_info = {
                        'image': region,
                        'pil_image': region_pil,
                        'coordinates': (x, y, w, h),
                        'padded_coordinates': (x, y, w, h),
                        'order': i
                    }
                    region_images.append(region_info)

                # Return the adaptive segmentation results
                return {
                    'text_regions': text_regions_vis,
                    'image_regions': image_regions_vis,
                    'text_mask_base64': f"data:image/png;base64,{text_mask_base64}",
                    'combined_result': pil_img,
                    'text_regions_coordinates': regions,
                    'region_images': region_images,
                    'segmentation_type': 'adaptive'
                }
            else:
                # SIMPLIFIED APPROACH for most documents
                # Let Mistral OCR handle the entire document understanding process
                logger.info(f"Using standard approach for document with uniform text density")

                # For visualization, mark the entire image as a text region
                full_image_region = [(0, 0, img_width, img_height)]

                # Create visualization with a simple border
                vis_img = img_np.copy()
                cv2.rectangle(vis_img, (5, 5), (img_width - 5, img_height - 5), (0, 255, 0), 5)

                # Add text to indicate this is using Mistral's native processing
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(vis_img, "Processed by Mistral OCR", (30, 60), font, 1, (0, 255, 0), 2)

                # Create visualizations and masks
                text_regions_vis = Image.fromarray(vis_img)
                image_regions_vis = text_regions_vis.copy()

                # Create a mask of the entire image (just for visualization)
                text_mask = np.ones((img_height, img_width), dtype=np.uint8) * 255
                _, buffer = cv2.imencode('.png', text_mask)
                text_mask_base64 = base64.b64encode(buffer).decode('utf-8')

                # Return the original image as the combined result
                return {
                    'text_regions': text_regions_vis,
                    'image_regions': image_regions_vis,
                    'text_mask_base64': f"data:image/png;base64,{text_mask_base64}",
                    'combined_result': pil_img,
                    'text_regions_coordinates': full_image_region,
                    'region_images': [{
                        'image': img_np,
                        'pil_image': pil_img,
                        'coordinates': (0, 0, img_width, img_height),
                        'padded_coordinates': (0, 0, img_width, img_height),
                        'order': 0
                    }],
                    'segmentation_type': 'simplified'
                }

    except Exception as e:
        logger.error(f"Error segmenting image {image_file.name}: {str(e)}")
        # Return None values if processing fails
        return {}


def process_segmented_image(image_path: Union[str, Path], output_dir: Optional[Path] = None) -> Dict:
    """
    Process an image using segmentation for improved OCR, saving visualization outputs.

    Args:
        image_path: Path to the image file
        output_dir: Optional directory to save visualization outputs

    Returns:
        Dictionary with processing results and paths to output files
    """
    # Convert to Path object if string
    image_file = Path(image_path) if isinstance(image_path, str) else image_path

    # Create output directory if not provided
    if output_dir is None:
        output_dir = Path("output") / "segmentation"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the image with segmentation
    segmentation_results = segment_image_for_ocr(image_file)

    # Prepare results dictionary
    results = {
        'original_image': str(image_file),
        'output_files': {},
        'segmentation_type': segmentation_results.get('segmentation_type', 'failed')
    }

    # Check if segmentation was successful
    if segmentation_results.get('text_regions') is not None:
        # Save text regions visualization
        text_regions_path = output_dir / f"{image_file.stem}_text_regions.jpg"
        segmentation_results['text_regions'].save(text_regions_path)
        results['output_files']['text_regions'] = str(text_regions_path)

        # Save image regions visualization
        image_regions_path = output_dir / f"{image_file.stem}_image_regions.jpg"
        segmentation_results['image_regions'].save(image_regions_path)
        results['output_files']['image_regions'] = str(image_regions_path)

        # Save combined result
        combined_path = output_dir / f"{image_file.stem}_combined.jpg"
        segmentation_results['combined_result'].save(combined_path)
        results['output_files']['combined_result'] = str(combined_path)

        # Save text mask visualization
        text_mask_path = output_dir / f"{image_file.stem}_text_mask.png"
        # Save text mask from base64
        if segmentation_results['text_mask_base64']:
            base64_data = segmentation_results['text_mask_base64'].split(',')[1]
            with open(text_mask_path, 'wb') as f:
                f.write(base64.b64decode(base64_data))
            results['output_files']['text_mask'] = str(text_mask_path)

        # Add detected text regions count
        results['text_regions_count'] = len(segmentation_results['text_regions_coordinates'])
        results['text_regions_coordinates'] = segmentation_results['text_regions_coordinates']
    else:
        logger.warning(f"No valid segmentation results for {image_file.name}. Skipping visualization output.")

    return results


if __name__ == "__main__":
    # Use a valid image file path
    image_path = "/Users/chandrabahadurkhadka/PycharmProjects/esewa-ocr/3pCHbPFnHdfHX1fmFr53cKbzWjuD5zP3.png"  # Update to a valid image
    logger.info(f"Testing image segmentation on {image_path}")
    output_dir = Path("/output")
    results = process_segmented_image(image_path, output_dir)

    # Print results summary
    logger.info(f"Segmentation complete. Found {results.get('text_regions_count', 0)} text regions.")
    logger.info(f"Output files saved to: {[path for path in results.get('output_files', {}).values()]}")
