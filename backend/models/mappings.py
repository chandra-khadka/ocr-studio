from backend.models.enums import DocumentType

DOCUMENT_FIELD_MAP = {
    DocumentType.CTZN_FRONT: [
        "full_name", "citizenship_no", "date_of_birth", "place_of_birth",
        "gender", "father_name", "mother_name", "grandfather_name", "permanent_address", "father_address",
        "mother_address", "citizenship_type"
    ],
    DocumentType.CTZN_BACK: [
        "full_name", "citizenship_no", "date_of_birth", "place_of_birth",
        "gender", "issue_date", "permanent_address"
    ],
    DocumentType.VOTER_ID: [
        "full_name", "voter_id_number", "date_of_birth", "citizenship_no",
        "father_name/mother_name", "husband_name/wife_name", "gender",
        "address", "polling_station", "district"
    ],

    DocumentType.LICENSE: [
        "full_name", "document_number", "date_of_birth", "citizenship_no", "father_name",
        "gender", "address", "issue_date", "expiry_date", "contact_number", "category", "blood_group"
    ],
    DocumentType.PASSPORT_FRONT: [
        "full_name", "citizenship_no", "passport_number", "nationality",
        "date_of_birth", "place_of_birth", "gender", "issue_date", "expiry_date", "issuing_authority", "country"
    ],
    DocumentType.PASSPORT_BACK: [
        "old_passport_number", "emergency_contact_name", "emergency_contact_address", "remarks", "district"
    ],
    DocumentType.NATIONAL_ID_FRONT: [
        "nationality", "date_of_issue", "NIN(राष्ट्रिय परिचय नम्बर)", "full_name",
        "date_of_birth", "gender", "issuing_authority"
    ],
    DocumentType.NATIONAL_ID_BACK: [
        "permanent_address", "citizenship_type", "citizenship_number(cc number)", "remarks", "district"
    ],
    DocumentType.GOVERNMENT_DOCUMENT: [
        "address", "blood_group", "category", "citizenship_no",
        "citizenship_number(cc number)", "citizenship_type", "contact_number",
        "country", "date_of_birth", "date_of_issue", "district",
        "document_number", "emergency_contact_address", "emergency_contact_name",
        "expiry_date", "father_address", "father_name",
        "father_name/mother_name", "full_name", "gender",
        "grandfather_name", "husband_name/wife_name", "issuing_authority",
        "issue_date", "mother_address", "mother_name", "nationality",
        "NIN(राष्ट्रिय परिचय नम्बर)", "old_passport_number", "passport_number",
        "permanent_address", "place_of_birth", "polling_station",
        "remarks", "voter_id_number"
    ]
}
