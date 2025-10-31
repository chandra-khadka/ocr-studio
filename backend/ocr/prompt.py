from __future__ import annotations

from typing import Optional, List

from backend.models.enums import DocumentFormat, DocumentType
from backend.models.mappings import DOCUMENT_FIELD_MAP


def _fields_list_for(document_type: DocumentType) -> List[str]:
    return DOCUMENT_FIELD_MAP.get(document_type, [])


def _json_envelope_intro(document_type: DocumentType, fields_list: List[str]) -> str:
    fields_csv = ", ".join(fields_list)
    return f"""You are an expert OCR system. Extract data from this {document_type.value} image.

        CRITICAL INSTRUCTIONS:
        1) Return ONLY a valid JSON object with the specified fields (no Markdown, no comments).
        2) Extract text exactly as it appears in the document (preserve original script/digits).
        3) Use null for fields that are not visible or cannot be determined.
        4) Do not infer or normalize digits; copy visually.
        5) Preserve Nepali/English exactly as printed (no translation).
        6) If a value is partially unclear, prefer null over guessing.
        
        Required JSON fields: {fields_csv}
        
        The JSON must be:
        
        {{
          "field1": "value_or_null",
          "field2": null
        }}
        
        Do not include any key not requested, unless specifically allowed below.
        """


def _extras_rule() -> str:
    return """
    "extras" (optional):
    - If there are clearly labeled fields that are NOT in the required list, include an "extras" object at the end:
      "extras": { "snake_cased_label": "exact_text", ... }
    - Do not duplicate keys already present in the main JSON.
    """


def _plain_text_base_instruction() -> str:
    return """
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
    """.strip()


def _generic_fallback(document_type: DocumentType, document_format: DocumentFormat,
                      custom_prompt: Optional[str]) -> str:
    if custom_prompt:
        return custom_prompt
    return (
        f"Extract all visible text from this {document_format.value} {document_type.value} image. "
        "Preserve the original structure and formatting. "
        "Do not add explanations or comments."
    )


def prompt_ctzn_front(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.CTZN_FRONT, fields) + _extras_rule() + """
    Document-specific rules:
    - Extract ONLY in Nepali (Devanagari) as printed.
    - "ctzn_no": from "ना.प्र.नं." as-is (keep dashes/slashes).
    - "date_of_birth": from "जन्म मिति" → format yyyy/mm/dd but keep Nepali digits (e.g., २०५४/१२/३०).
    - "gender": from "लिङ्ग": "पुरुष" => "M", "महिला" => "F".
    - "citizenship_type": exact text after "ना.कि".
    - "place_of_birth": exact text after "जन्म स्थान".
    - If unclear, return null. Do not guess.
    """


def prompt_ctzn_back(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.CTZN_BACK, fields) + _extras_rule() + """
    Document-specific rules:
    - "issue_date": strictly from "जारी मिति:"; keep Nepali digits and separators as printed.
    - "full_name": from "Full Name".
    - "date_of_birth": from "Date of Birth" / "AD" / "Year: Month: Day:" (keep script as printed).
    - "gender": from "Gender" → "M" or "F" (also map Male/Female to M/F).
    - Never normalize doubtful digits; if uncertain, use null.
    """


def prompt_voter_id(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.VOTER_ID, fields) + _extras_rule() + """
    Document-specific rules:
    - Extract ONLY in Nepali script.
    - "date_of_birth": yyyy-mm-dd with Nepali digits (e.g., २०४५-११-०५).
    - "citizenship_no": from "ना.प्र.नं." as-is.
    - "gender": "पुरुष" => "M", "महिला" => "F" (map Male/Female to M/F if printed in English).
    - "document_number": from "मतदाता नम्बर".
    - For all numeric fields: keep Nepali digits and any separators exactly.
    - If unclear, return null (do not guess).
    """


def prompt_license(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.LICENSE, fields) + _extras_rule() + """
    Document-specific rules:
    - "blood_group": extract as printed (e.g., "B+" or label variants).
    - "document_number": value after D.L.No (do not include the label itself).
    - "date_of_birth": D.O.B as printed (do not normalize; if multiple dates, see next rule).
    - "expiry_date": D.O.E as printed.
    - "issue_date": D.O.I as printed.
    - If only dates are visible without labels: oldest = date_of_birth, latest = expiry_date, remaining = issue_date.
    - "citizenship_no": from "Citizenship No" (exact).
    """


def prompt_passport_front(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.PASSPORT_FRONT, fields) + _extras_rule() + """
    Document-specific rules:
    - "full_name": combine "GIVEN NAMES" + "SURNAME" (exact casing/spaces).
    - If front text missing, use MRZ to fill missing fields.
    - "passport_number": from "Passport No." (exact).
    - "citizenship_no": from "Personal No"; if not found, pick a numeric value (length > 3) that is NOT passport_number.
    - "gender": "M" or "F" (map Male/Female to M/F when printed).
    """


def prompt_passport_back(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.PASSPORT_BACK, fields) + _extras_rule() + """
    Document-specific rules:
    - "old_passport_number": extract as printed if present.
    - "emergency_contact_name": exact label/value (e.g., "Emergency contact/person to notify").
    - "emergency_contact_address": exact address text next to contact.
    - "remarks": any remarks/observations area (verbatim).
    - "district": if a district field/label is present, copy as-is.
    - Preserve original script/digits; null if not visible.
    """


def prompt_national_id_front(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.NATIONAL_ID_FRONT, fields) + _extras_rule() + r"""
    Document-specific rules:
    - "nationality": as printed.
    - "date_of_issue": exact as printed (keep separators/digits in same script).
    - "NIN(राष्ट्रिय परिचय नम्बर)": exact—do not normalize digits.
    - "full_name": exact casing/spaces.
    - "date_of_birth": exact as printed (preserve script/digits).
    - "gender": exact but if Male/Female, map to "M"/"F".
    - "issuing_authority": exact label value (e.g., "Issuer/Authority").
    """


def prompt_national_id_back(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.NATIONAL_ID_BACK, fields) + _extras_rule() + r"""
    Document-specific rules:
    - "permanent_address": exact text; if multi-line, join with a single space.
    - "citizenship_type": exact phrase if printed (do not infer).
    - "citizenship_number(cc number)": exact digits/format (do not normalize).
    - "remarks": verbatim (if empty/unclear => null).
    - "district": as printed.
    """


def prompt_government_document(fields: List[str]) -> str:
    return _json_envelope_intro(DocumentType.GOVERNMENT_DOCUMENT, fields) + _extras_rule() + """
    Document-specific rules:
    - This is a generic government document prompt combining common fields.
    - For any date fields, keep separators and digit scripts exactly as printed.
    - For gender, map Male/Female or पुरुष/महिला to "M"/"F" when clearly stated; otherwise keep exact text or null.
    - Do not invent fields. Only include "extras" if the label is clearly printed.
    """


# --------- Plain-text prompts for non-JSON docs ----------

def _plain_text_for(document_type: DocumentType, document_format: DocumentFormat, custom_prompt: Optional[str]) -> str:
    base = _plain_text_base_instruction()

    if document_type == DocumentType.GENERAL:
        return "Extract all visible text from this image. Return only the plain text. Do not add explanations or comments."

    if document_type == DocumentType.NEWSPAPER:
        return base + """
Focus on extracting:
- Headlines and subheadings
- Article text in column order
- Bylines and dates
- Photo captions
- Any advertisements or notices
"""

    if document_type == DocumentType.LETTER:
        return (
                base
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

    if document_type == DocumentType.FORM:
        return (
                base
                + "\nOutput strictly in valid Markdown format:\n\n"
                  "- Use a level-1 heading (`#`) for the form title\n"
                  "- Use a two-column Markdown table for field labels and their values (columns: *Field*, *Value*)\n"
                  "- For checkboxes, include a column with `[x]` (checked) or `[ ]` (unchecked)\n"
                  "- Clearly mark signature lines and official stamps/seals in separate sections\n\n"
                  "Do not add explanations or text outside the Markdown structure."
        )

    if document_type == DocumentType.BOOK:
        return (
            "Extract all visible text from this book page image. "
            "Preserve chapter headings, subheadings, paragraphs, and page numbers as they appear. "
            "Maintain original formatting, line breaks, and special symbols. "
            "Do not add explanations or comments."
        )

    if document_type == DocumentType.RECIPE:
        return (
            "Extract all visible text from this recipe image. "
            "Output strictly in valid Markdown format:\n\n"
            "- Use a level-1 heading (`#`) for the recipe title\n"
            "- Use a bullet list (`-`) for the ingredients\n"
            "- Use a numbered list (`1.`, `2.`, etc.) for preparation steps\n\n"
            "Preserve the original order and formatting. "
            "Do not add explanations, comments, or any text outside the recipe content."
        )

    if document_type == DocumentType.HANDWRITTEN:
        return (
            "Extract all visible handwritten text from this image as accurately as possible. "
            "Preserve original formatting, line breaks, and spacing. "
            "Do not add explanations or comments."
        )

    if document_type == DocumentType.MAP:
        return (
            "Extract all visible text, labels, place names, legends, and annotations from this map or illustration."
            "Maintain the original order and grouping as much as possible. "
            "Do not add explanations or comments."
        )

    if document_type == DocumentType.table if hasattr(DocumentType, "table") else False:
        # Guard if someone had a lowercased enum by mistake
        return (
            "Extract all visible text and numbers from this table or spreadsheet image. "
            "Preserve the exact row and column structure. "
            "Output the result strictly as a valid Markdown table:\n\n"
            "- Use `|` as column separators\n"
            "- Use `-` for the header row separator\n"
            "- Ensure the first row is treated as headers (if headers exist)\n"
            "- Do not add any explanations, comments, or text outside the table."
        )

    if document_type == DocumentType.TABLE:
        return (
            "Extract all visible text and numbers from this table or spreadsheet image. "
            "Preserve the exact row and column structure. "
            "Output the result strictly as a valid Markdown table:\n\n"
            "- Use `|` as column separators\n"
            "- Use `-` for the header row separator\n"
            "- Ensure the first row is treated as headers (if headers exist)\n"
            "- Do not add any explanations, comments, or text outside the table."
        )

    if document_type == DocumentType.OTHER:
        if custom_prompt is not None:
            return custom_prompt
        return (
            "Extract all visible text from this image. "
            "Preserve the original formatting, line breaks, and order. "
            "Do not add explanations or comments."
        )

    # Fallback for any unknown types
    return (
        f"Extract all visible text from this {document_format.value} {document_type.value} image. "
        "Preserve the original structure and formatting. "
        "Do not add explanations or comments."
    )


def create_extraction_prompt(
        document_type: DocumentType,
        document_format: DocumentFormat,
        custom_prompt: Optional[str] = None,
) -> str:
    """
    Returns a complete instruction string. For ID-like types in DOCUMENT_FIELD_MAP,
    returns a JSON-extraction prompt; otherwise returns a plain-text extraction prompt.
    """

    # JSON path for structured government/ID-like documents
    fields = _fields_list_for(document_type)
    if fields:
        if document_type == DocumentType.CTZN_FRONT:
            return prompt_ctzn_front(fields)
        if document_type == DocumentType.CTZN_BACK:
            return prompt_ctzn_back(fields)
        if document_type == DocumentType.VOTER_ID:
            return prompt_voter_id(fields)
        if document_type == DocumentType.LICENSE:
            return prompt_license(fields)
        if document_type == DocumentType.PASSPORT_FRONT:
            return prompt_passport_front(fields)
        if document_type == DocumentType.PASSPORT_BACK:
            return prompt_passport_back(fields)
        if document_type == DocumentType.NATIONAL_ID_FRONT:
            return prompt_national_id_front(fields)
        if document_type == DocumentType.NATIONAL_ID_BACK:
            return prompt_national_id_back(fields)
        if hasattr(DocumentType, "GOVERNMENT_DOCUMENT") and document_type == DocumentType.GOVERNMENT_DOCUMENT:
            return prompt_government_document(fields)

        # If some other mapped type exists, still use the generic JSON envelope
        return _json_envelope_intro(document_type, fields) + _extras_rule()

    # Plain-text path for everything else
    return _plain_text_for(document_type, document_format, custom_prompt)
