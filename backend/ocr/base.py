from typing import Optional

from backend.models.enums import DocumentFormat, DocumentType, StructuredOCRResult
from backend.models.mappings import DOCUMENT_FIELD_MAP
from backend.ocr.prompt import create_extraction_prompt


class BaseOCRProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.configure()

    def configure(self):
        raise NotImplementedError

    def extract_text(self, image_data: bytes, document_type: DocumentType,
                     document_format: DocumentFormat, custom_prompt: Optional[str] = None) -> StructuredOCRResult:
        raise NotImplementedError

    @staticmethod
    def _create_extraction_prompt(document_type: DocumentType,
                                  document_format: DocumentFormat, custom_prompt: Optional[str] = None) -> str:
        if document_type in DOCUMENT_FIELD_MAP:
            return create_extraction_prompt(document_type, document_format, custom_prompt)

        base_instruction = """
            You are an expert OCR engine.

            Your task is to extract the **exact visible text** from the uploaded document image.

            ⚠️ CRITICAL INSTRUCTIONS:
            1. Transcribe **all visible text** exactly as it appears — **no corrections, no translations, no interpretations.**
            2. **Preserve original language** (Nepali/English/Mixed). Do not convert numbers, script, or spelling.
            3. **Keep line breaks, spacing, and alignment** as much as possible.
            4. Do **not add** labels, comments, summaries, or JSON — only extract the raw text as seen in the image.
            5. If any part is unclear or partially visible, extract the readable part **as-is**. Do not guess.

            🎯 Goal:
            Provide a **faithful, character-perfect text representation** of what is printed in the document.

            📝 Output:
            """
        # Add specific instructions for different document types
        if document_type == DocumentType.GENERAL:
            return ("Extract all visible text from this image. Return only the plain text. Do not add explanations or "
                    "comments.")

        elif document_type == DocumentType.NEWSPAPER:
            return base_instruction + """
                Focus on extracting:
                - Headlines and subheadings
                - Article text in column order
                - Bylines and dates
                - Photo captions
                - Any advertisements or notices
                """
        elif document_type == DocumentType.LETTER:
            return (
                    base_instruction
                    + "\nOutput strictly in valid Markdown format:\n\n"
                      "- Use bold text for letterhead or header information\n"
                      "- Always include the date (never omit it). Place it on the right side (use `>` blockquote if alignment isn’t possible)\n"
                      "- Show the recipient address as plain text lines\n"
                      "- Use an italicized salutation (e.g., *Dear Sir/Madam,*)\n"
                      "- Keep the body as normal Markdown paragraphs\n"
                      "- End with an italicized closing (e.g., *Sincerely,*)\n"
                      "- Place the sender’s name/signature below the closing\n\n"
                      "Do not add explanations, comments, or extra text outside the letter."
            )

        elif document_type == DocumentType.FORM:
            return (
                    base_instruction
                    + "\nOutput strictly in valid Markdown format:\n\n"
                      "- Use a level-1 heading (`#`) for the form title\n"
                      "- Use a two-column Markdown table for field labels and their values (columns: *Field*, *Value*)\n"
                      "- For checkboxes, include a column with `[x]` (checked) or `[ ]` (unchecked)\n"
                      "- Clearly mark signature lines and official stamps/seals in separate sections\n\n"
                      "Do not add explanations or text outside the Markdown structure."
            )
        elif document_type == DocumentType.BOOK:
            return (
                "Extract all visible text from this book page image. "
                "Preserve chapter headings, subheadings, paragraphs, and page numbers as they appear. "
                "Maintain original formatting, line breaks, and special symbols. "
                "Do not add explanations or comments."
            )
        elif document_type == DocumentType.RECIPE:
            return (
                "Extract all visible text from this recipe image. "
                "Output strictly in valid Markdown format:\n\n"
                "- Use a level-1 heading (`#`) for the recipe title\n"
                "- Use a bullet list (`-`) for the ingredients\n"
                "- Use a numbered list (`1.`, `2.`, etc.) for preparation steps\n\n"
                "Preserve the original order and formatting. "
                "Do not add explanations, comments, or any text outside the recipe content."
            )
        elif document_type == DocumentType.HANDWRITTEN:
            return (
                "Extract all visible handwritten text from this image as accurately as possible. "
                "Preserve original formatting, line breaks, and spacing. "
                "Do not add explanations or comments."
            )
        elif document_type == DocumentType.MAP:
            return (
                "Extract all visible text, labels, place names, legends, and annotations from this map or illustration."
                "Maintain the original order and grouping as much as possible. "
                "Do not add explanations or comments."
            )
        elif document_type == DocumentType.TABLE:
            return (
                "Extract all visible text and numbers from this table or spreadsheet image. "
                "Preserve the exact row and column structure. "
                "Output the result strictly as a valid Markdown table:\n\n"
                "- Use `|` as column separators\n"
                "- Use `-` for the header row separator\n"
                "- Ensure the first row is treated as headers (if headers exist)\n"
                "- Do not add any explanations, comments, or text outside the table."
            )
        elif document_type == DocumentType.OTHER:
            if custom_prompt is not None:
                return custom_prompt
            return (
                "Extract all visible text from this image. "
                "Preserve the original formatting, line breaks, and order. "
                "Do not add explanations or comments."
            )
        # Fallback for any other unknown types
        return (
            f"Extract all visible text from this {document_format.value} {document_type.value} image. "
            "Preserve the original structure and formatting. "
            "Do not add explanations or comments."
        )
