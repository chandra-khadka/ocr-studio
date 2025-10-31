# OCR Image Segmentation and Processing Utility

This utility provides a comprehensive solution for preprocessing images for Optical Character Recognition (OCR) using
document-aware adaptive segmentation. It is designed to improve OCR accuracy on mixed-content documents by separating
text and image regions, handling skew correction, and generating structured outputs compatible with Mistral AI's OCR
pipeline.

## Overview

The codebase consists of two main Python modules:

1. **Image Segmentation Utility** (`segmentation_utility.py`): Focuses on separating text and image regions in documents
   to enhance OCR accuracy.
2. **OCR Helper Functions** (`ocr_utils.py`): Provides utility functions for processing OCR responses, handling images,
   and generating structured outputs.

Both modules work together to preprocess images, analyze text density, detect document skew, clean OCR results, and
package outputs in a user-friendly format.

## Features

- **Adaptive Segmentation**: Uses document-content-aware techniques to identify and separate text and image regions
  based on text density analysis.
- **Skew Detection**: Detects and estimates image skew using efficient edge detection and Hough Line Transform (OpenCV)
  or a fallback PIL-based approach.
- **OCR Result Cleaning**: Removes markdown/HTML conflicts and base64 image data to produce clean, structured text
  outputs.
- **Output Packaging**: Generates zip archives containing JSON data, markdown documents with embedded or file-referenced
  images, and a README for clarity.
- **Mistral AI Compatibility**: Integrates seamlessly with Mistral AI's OCR pipeline, handling OCRImageObject and
  structured responses.
- **Flexible Image Handling**: Supports multiple image formats (JPEG, PNG, GIF, PDF) and provides base64 encoding for
  API submissions.
- **Robust Error Handling**: Includes logging and fallback mechanisms for missing dependencies or processing failures.

### Main Execution

The main entry point is in the `segmentation_utility.py` module. Update the `image_path` and `output_dir` in
the `__main__` block to point to your image and desired output directory:

```python
if __name__ == "__main__":
    image_path = "path/to/your/image.png"
    output_dir = Path("path/to/output")
    results = process_segmented_image(image_path, output_dir)
    logger.info(f"Segmentation complete. Found {results.get('text_regions_count', 0)} text regions.")
    logger.info(f"Output files saved to: {[path for path in results.get('output_files', {}).values()]}")
```

Run the script:

```bash
python segmentation_utility.py
```

### Key Functions

#### Image Segmentation (`segmentation_utility.py`)

- **`segment_image_for_ocr(image_path, vision_enabled=True, preserve_content=True)`**
    - **Purpose**: Segments an image into text and image regions for OCR preprocessing.
    - **Process**:
        1. Loads the image using PIL.
        2. Checks image entropy to detect low-complexity images (e.g., blank pages or illustrations).
        3. Analyzes text density to determine if adaptive segmentation is needed.
        4. For varied text density, uses adaptive region detection; otherwise, uses a simplified approach.
        5. Generates visualizations with green borders around text regions and a text mask.
    - **Returns**: A dictionary with:
        - `text_regions`: Visualization of text regions (PIL Image)
        - `image_regions`: Visualization of image regions (PIL Image)
        - `text_mask_base64`: Base64-encoded text mask
        - `combined_result`: Original image (PIL Image)
        - `text_regions_coordinates`: List of region coordinates
        - `region_images`: List of extracted region images
        - `segmentation_type`: 'adaptive' or 'simplified'

- **`process_segmented_image(image_path, output_dir=None)`**
    - **Purpose**: Processes an image and saves segmentation visualizations to an output directory.
    - **Process**:
        1. Calls `segment_image_for_ocr` to get segmentation results.
        2. Saves visualizations (text regions, image regions, combined result, text mask) as files.
    - **Returns**: A dictionary with file paths and segmentation metadata.

#### OCR Helper Functions (`ocr_utils.py`)

- **`detect_skew(image)`**
    - Detects image skew using Hough Line Transform (OpenCV) or edge analysis (PIL fallback).
    - Returns skew angle in degrees (-45 to 45).

- **`replace_images_in_markdown(md, images)`**
    - Replaces markdown image placeholders with base64-encoded images.
    - Uses regex to handle variations in image IDs.

- **`get_combined_markdown(ocr_response)`**
    - Combines OCR text and images into a single markdown document.
    - Processes each page of the OCR response, embedding base64 images.

- **`encode_image_for_api(image_path)`**
    - Encodes an image file as a base64 data URL for API submission.
    - Supports JPEG, PNG, GIF, and PDF formats.

- **`calculate_image_entropy(pil_img)`**
    - Calculates image entropy to determine complexity (low for blank pages, high for text-heavy documents).

- **`estimate_text_density(image_np)`**
    - Analyzes text density patterns using grayscale conversion and binary thresholding.
    - Returns metrics like mean density, variation, and uppercase section count.

- **`clean_ocr_result(result, use_segmentation=False, vision_enabled=True, preprocessing_options=None)`**
    - Cleans OCR results by removing markdown/HTML conflicts and base64 data.
    - Preserves original structure and prioritizes segmentation text when available.

- **`create_results_zip(results, output_dir=None, zip_name=None)`**
    - Creates a zip file containing OCR results (JSON, markdown, images, README).
    - Supports single or multiple results with subdirectories.

- **`create_markdown_with_file_references(result, image_path_prefix="images/")`**
    - Generates markdown with file references to images instead of base64 embedding.
    - Ideal for zip archives with separate image files.

- **`create_markdown_with_images(result)`**
    - Generates markdown with embedded base64 images, matching the app's UI display.

## Output Structure

Running `process_segmented_image` produces:

- **Output Directory** (`output/segmentation/`):
    - `<image_name>_text_regions.jpg`: Visualization of detected text regions.
    - `<image_name>_image_regions.jpg`: Visualization of image regions.
    - `<image_name>_combined.jpg`: Original image with processing annotations.
    - `<image_name>_text_mask.png`: Binary mask highlighting text regions.
- **Results Dictionary**:
    - `original_image`: Path to the input image.
    - `output_files`: Paths to saved visualizations.
    - `segmentation_type`: Type of segmentation used ('adaptive' or 'simplified').
    - `text_regions_count`: Number of detected text regions.
    - `text_regions_coordinates`: Coordinates of text regions.

Running `create_results_zip` produces a zip file containing:

- `<base_name>.json`: Cleaned JSON data (base64 removed).
- `<base_name>.md`: Markdown with embedded base64 images.
- `<base_name>_with_files.md`: Markdown with file references to images.
- `images/`: Folder with extracted images.
- `README.txt`: Explanation of archive contents.

## Example Workflow

1. **Preprocess Image**:
   ```python
   results = process_segmented_image("sample.png", output_dir=Path("output"))
   ```
   This segments the image, saves visualizations, and returns results.

2. **Process OCR Results**:
   ```python
   cleaned_results = clean_ocr_result(ocr_result, use_segmentation=True, preprocessing_options={'segmentation_data': results})
   ```

3. **Create Zip Archive**:
   ```python
   zip_path = create_results_zip(cleaned_results, output_dir=Path("output"), zip_name="sample_results.zip")
   ```

## Notes

- **Dependencies**: Ensure OpenCV is installed for optimal skew detection and segmentation. Without OpenCV, fallback
  methods use PIL but may be less accurate.
- **Mistral AI Integration**: The utility assumes compatibility with Mistral AI's OCR response
  format (`OCRImageObject`).
- **Error Handling**: Comprehensive logging is implemented to diagnose issues. Check logs for debugging.
- **Customization**: Adjust `IMAGE_PREPROCESSING` settings in `config.py` for specific use cases (e.g., contrast
  enhancement, DPI).

## Limitations

- Requires valid image paths and sufficient disk space for outputs.
- Adaptive segmentation may struggle with extremely low-contrast or noisy images.
- Some utility functions (`classify_document_content`, `extract_document_text`) are assumed to exist in external modules
  and may need implementation.
- Large images or base64 strings may increase memory usage during processing.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.