from datetime import datetime

from backend.config import logger


def parse_passport_date(date_str: str) -> str:
    """Convert '06 MAY 1966' to '1966-05-06' (YYYY-mm-dd)"""
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%d %B %Y").strftime("%Y-%m-%d")
        except Exception:
            logger.error(f"Error while parsing date")
            return date_str


def normalize_passport_dates(results: dict) -> dict:
    for field in ["date_of_birth", "issue_date", "expiry_date"]:
        if field in results and results[field]:
            results[field] = parse_passport_date(results[field])
    return results


if __name__ == '__main__':
    # Example usage:
    results = {
        "full_name": "LOT BAHADUR GURUNG",
        "citizenship_no": "72298",
        "passport_number": "BA0113006",
        "nationality": "NEPALI",
        "date_of_birth": "06 MAY 1966",
        "place_of_birth": "RUPANDEHI",
        "gender": "M",
        "issue_date": "20 JUL 2023",
        "expiry_date": "19 JUL 2033",
        "issuing_authority": "MOFA, DEPARTMENT OF PASSPORTS"
    }

    results = normalize_passport_dates(results)
    print(results)
