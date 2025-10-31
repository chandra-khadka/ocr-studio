# OCR API Documentation

A powerful OCR (Optical Character Recognition) API that supports document processing with multiple providers and
correction capabilities.

## Base URL

```
http://0.0.0.0:8000
```

## Endpoints

### 1. Process Image URL or Base64

**Endpoint:**

```http
POST /process-image-url-or-base64/
```

Process documents from either a URL or base64 encoded image.

#### Request Headers

```http
Content-Type: application/json
```

#### Request Body Parameters

| Parameter             | Type    | Description                                                        | Required |
|-----------------------|---------|--------------------------------------------------------------------|----------|
| `image_url`           | string  | URL of the image to process                                        | No*      |
| `base64_image`        | string  | Base64 encoded image data                                          | No*      |
| `ocr_provider`        | string  | OCR provider to use (`gemini`, `gemini_opensource`)                | Yes      |
| `correction_provider` | string  | Text correction provider (`none`, `gemini`, etc.)                  | Yes      |
| `document_type`       | string  | Type of document (`passport_front`, `citizenship_back`, `general`) | Yes      |
| `document_format`     | string  | Document format (default: `standard`)                              | Yes      |
| `language`            | string  | Document language (`nepali`, `english`)                            | Yes      |
| `enable_json_parsing` | boolean | Enable JSON structure parsing                                      | No       |
| `use_segmentation`    | boolean | Use image segmentation                                             | No       |
| `max_pdf_pages`       | integer | Maximum PDF pages to process                                       | No       |
| `pdf_dpi`             | integer | PDF resolution DPI                                                 | No       |
| `provider_config`     | object  | Provider-specific configuration                                    | No       |

*Either `image_url` or `base64_image` must be provided.

#### Provider Configuration Options

For **gemini_opensource**:

```json
{
  "ocr_model": "models/gemma-3-4b-it",
  "correction_model": "models/gemma-3-4b-it"
}
```

For **gemini**:

```json
{
  "gemini_ocr_model": "gemini-1.5-flash",
  "gemini_correction_model": "gemini-1.5-flash"
}
```

#### Example Request - Base64 Image (Passport)

```bash
curl --location 'http://0.0.0.0:8000/process-image-url-or-base64/' \
--header 'Content-Type: application/json' \
--data '{
  "base64_image": "base64 encoded image",
  "ocr_provider": "gemini_opensource",
  "correction_provider": "none",
  "document_type": "passport_front",
  "document_format": "standard",
  "language": "nepali",
  "enable_json_parsing": true,
  "use_segmentation": false,
  "max_pdf_pages": 5,
  "pdf_dpi": 300,
  "provider_config": {
    "ocr_model": "models/gemma-3-4b-it",
    "correction_model": "models/gemma-3-4b-it"
  }
}'
```

#### Example Request - Image URL (Citizenship)

```bash
curl --location 'http://0.0.0.0:8000/process-image-url-or-base64/' \
--header 'Content-Type: application/json' \
--data '{
  "image_url": "https://i.ibb.co/DVrp73n/viber-image-2024-03-16-13-31-18-900.jpg",
  "ocr_provider": "gemini_opensource",
  "correction_provider": "none",
  "document_type": "citizenship_back",
  "document_format": "standard",
  "language": "nepali",
  "enable_json_parsing": true,
  "use_segmentation": false,
  "max_pdf_pages": 5,
  "pdf_dpi": 300,
  "provider_config": {
    "ocr_model": "models/gemma-3-4b-it",
    "correction_model": "models/gemma-3-4b-it"
  }
}'
```

### 2. Upload Document

**Endpoint:**

```http
POST /upload-document/
```

Upload and process document files directly.

#### Request Format

```http
Content-Type: multipart/form-data
```

#### Form Data Parameters

- **file**: Document file to upload
- **request**: JSON string containing processing parameters

#### Example Request

```bash
curl --location 'http://0.0.0.0:8000/upload-document/' \
--form 'file=@"/path/to/your/document.png"' \
--form 'request="{
  \"ocr_provider\": \"gemini\",
  \"correction_provider\": \"none\",
  \"document_type\": \"general\",
  \"document_format\": \"standard\",
  \"language\": \"english\",
  \"enable_json_parsing\": true,
  \"use_segmentation\": false,
  \"max_pdf_pages\": 5,
  \"pdf_dpi\": 300,
  \"provider_config\": {
    \"gemini_ocr_model\": \"gemini-1.5-flash\",
    \"gemini_correction_model\": \"gemini-1.5-flash\"
  }
}"'
```

## Response Format

### Basic Response (correction_provider = "none")

```json
{
  "raw_text": "Extracted text from the document",
  "pdf_content": null,
  "status": "success",
  "structured_json": {
    "structured_data": {
      "field1": "value1",
      "field2": "value2"
    }
  }
}
```

### Enhanced Response (correction_provider != "none")

```json
{
  "raw_text": "Original extracted text",
  "pdf_content": null,
  "status": "success",
  "structured_json": {
    "structured_data": {
      "raw_text": "Original extracted text",
      "corrected_text": "Corrected and formatted text",
      "structured_data": {
        "field1": "value1",
        "field2": "value2"
      },
      "confidence": null,
      "language_detected": null
    }
  },
  "corrected_text": "Corrected version of extracted text",
  "improvements": [
    "List of improvements made"
  ],
  "improvement_score": 50,
  "json_summary": {
    "Text Fields": ["list", "of", "text", "fields"],
    "Number Fields": ["list", "of", "number", "fields"],
    "Date Fields": ["list", "of", "date", "fields"],
    "List Fields": ["list", "of", "array", "fields"],
    "Object Fields": ["list", "of", "object", "fields"]
  }
}
```

## Document Types

### Supported Document Types

- **passport_front** - Front page of passport
- **citizenship_back** - Back side of citizenship certificate
- **general** - General document type
- **driving_license** - Driving license documents

### Document Fields by Type

#### Passport Front

- **full_name** - Full name of passport holder
- **citizenship_no** - Citizenship number
- **passport_number** - Passport number
- **nationality** - Nationality
- **date_of_birth** - Date of birth
- **place_of_birth** - Place of birth
- **gender** - Gender (M/F)
- **issue_date** - Passport issue date
- **expiry_date** - Passport expiry date
- **issuing_authority** - Issuing authority

#### Driving License

- **D.L.No.** - License number
- **B.G.** - Blood group
- **Name** - Full name
- **Address** - Full address
- **License Office** - Issuing office
- **D.O.B.** - Date of birth
- **D.O.I.** - Date of issue
- **D.O.E.** - Date of expiry
- **F/H Name** - Father/Husband name
- **Citizenship No.** - Citizenship number
- **Passport No.** - Passport number (if available)
- **Contact No.** - Contact number
- **Category** - License category (A, B, etc.)

## OCR Providers

### Available Providers

1. **gemini** - Google Gemini API
2. **gemini_opensource** - Open source Gemini models

### Provider Models

- **Gemini**: `gemini-1.5-flash`
- **Gemini Opensource**: `models/gemma-3-4b-it`

## Error Handling

The API returns appropriate HTTP status codes:

- **200** - Success
- **400** - Bad Request
- **500** - Internal Server Error

Error responses include details about what went wrong:

```json
{
  "status": "error",
  "message": "Error description",
  "details": "Additional error details if available"
}
```

## Language Support

Currently supported languages:

- **english** - English language documents
- **nepali** - Nepali language documents

## Features

### Text Correction

When `correction_provider` is not set to `"none"`, the API provides:

- **Raw Text**: Original OCR output
- **Corrected Text**: Improved and formatted text
- **Improvements**: List of corrections made
- **Improvement Score**: Numerical score of improvements
- **Structured Data**: Organized field extraction

### JSON Parsing

When `enable_json_parsing` is `true`, the API attempts to structure the extracted data into relevant fields based on the
document type.

### Segmentation

The `use_segmentation` option enables advanced image processing to improve OCR accuracy on complex documents.

### PDF Support

- Process multi-page PDFs with `max_pdf_pages` parameter
- Control PDF resolution with `pdf_dpi` parameter

## Usage Tips

1. **Document Quality**: Higher quality images produce better OCR results
2. **Document Type**: Specify the correct document type for better field extraction
3. **Language Setting**: Set the appropriate language for better accuracy
4. **Correction Provider**: Use correction providers for improved text quality
5. **File Formats**: Supports common image formats (PNG, JPG, JPEG) and PDF files

## Rate Limits

Please check with your API provider for current rate limits and usage quotas.

# Load and run the model:

# Install vLLM from pip:

pip install vllm
vllm serve "google/gemma-3-4b-it" --max-model-len 4096

or
export VLLM_CPU_KVCACHE_SPACE=16
vllm serve "google/gemma-3-4b-it"

182.93.90.21 8000


