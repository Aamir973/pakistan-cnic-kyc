"""
Pakistan CNIC Fraud Detection & Validation Service
Checks CNIC format, date logic, and basic authenticity signals.
"""

import re
from datetime import datetime


def validate_cnic_format(cnic: str) -> dict:
    """
    Validate CNIC number format and extract metadata from it.
    Format: PPPPP-NNNNNNN-G
    PPPPP = Province/District code
    NNNNNNN = Unique serial
    G = Gender digit (odd=Male, even=Female)
    """
    result = {
        "valid_format": False,
        "province_code": None,
        "gender_from_cnic": None,
        "issues": []
    }

    if not cnic:
        result["issues"].append("CNIC number not found")
        return result

    clean = re.sub(r'[^0-9]', '', cnic)

    if len(clean) != 13:
        result["issues"].append(f"CNIC should be 13 digits, got {len(clean)}")
        return result

    result["valid_format"] = True
    result["province_code"] = clean[:5]

    # Gender from last digit
    last_digit = int(clean[-1])
    result["gender_from_cnic"] = "Male" if last_digit % 2 == 1 else "Female"

    # Province/district code check (known Pakistan codes)
    known_province_prefixes = {
        '1': 'FATA/KPK',
        '2': 'FATA/KPK',
        '3': 'Punjab',
        '4': 'Sindh',
        '5': 'Balochistan',
        '6': 'Islamabad/AJK',
        '7': 'GB',
    }
    province_digit = clean[0]
    result["province"] = known_province_prefixes.get(province_digit, "Unknown Region")

    return result


def validate_dates(parsed: dict) -> dict:
    """
    Cross-validate dates on the CNIC:
    - DOB should be in the past
    - Issue date should be after DOB (and person should be >= 18)
    - Expiry should be after Issue (typically 10 years)
    """
    issues = []
    warnings = []
    checks = {}

    def parse_dt(s):
        if not s:
            return None
        for fmt in ('%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    today = datetime.today()
    dob = parse_dt(parsed.get("date_of_birth"))
    doi = parse_dt(parsed.get("date_of_issue"))
    doe = parse_dt(parsed.get("date_of_expiry"))

    if dob:
        age = (today - dob).days / 365.25
        checks["dob_valid"] = dob < today
        checks["age_at_check"] = round(age, 1)
        if age < 0:
            issues.append("Date of birth is in the future")
        elif age < 18:
            warnings.append(f"Holder appears to be under 18 (age: {age:.1f})")
        elif age > 120:
            issues.append("Date of birth indicates age over 120")

    if doi and dob:
        age_at_issue = (doi - dob).days / 365.25
        checks["issued_after_dob"] = doi > dob
        if doi <= dob:
            issues.append("Date of Issue is before Date of Birth")
        if age_at_issue < 18:
            warnings.append("CNIC issued when holder was under 18")

    if doe and doi:
        validity_years = (doe - doi).days / 365.25
        checks["expiry_after_issue"] = doe > doi
        checks["validity_years"] = round(validity_years, 1)
        if doe <= doi:
            issues.append("Date of Expiry is before or equal to Date of Issue")
        if validity_years > 15:
            warnings.append("Validity period unusually long (>15 years)")

    if doe:
        checks["is_expired"] = doe < today
        if doe < today:
            issues.append("CNIC is expired")

    return {
        "checks": checks,
        "issues": issues,
        "warnings": warnings,
        "dates_valid": len(issues) == 0
    }


def validate_gender_consistency(parsed: dict, cnic_validation: dict) -> dict:
    """
    Check if gender on card matches gender encoded in CNIC number.
    """
    card_gender = parsed.get("gender")
    cnic_gender = cnic_validation.get("gender_from_cnic")

    if card_gender and cnic_gender:
        consistent = card_gender.lower() == cnic_gender.lower()
        return {
            "card_gender": card_gender,
            "cnic_encoded_gender": cnic_gender,
            "consistent": consistent,
            "issue": None if consistent else f"Gender mismatch: card says {card_gender}, CNIC number encodes {cnic_gender}"
        }
    return {
        "card_gender": card_gender,
        "cnic_encoded_gender": cnic_gender,
        "consistent": None,
        "issue": "Could not verify gender consistency"
    }


def calculate_risk_score(parsed: dict, has_selfie: bool = False) -> dict:
    """
    Calculate a KYC risk score based on available verification signals.
    Returns score 0-100 (higher = more verified / lower risk).
    """
    score = 0
    breakdown = {}

    cnic = parsed.get("cnic_number")
    cnic_val = validate_cnic_format(cnic)
    date_val = validate_dates(parsed)

    # CNIC number present and valid format (+30)
    if cnic and cnic_val["valid_format"]:
        score += 30
        breakdown["cnic_format"] = "+30 (Valid CNIC format)"
    elif cnic:
        score += 10
        breakdown["cnic_format"] = "+10 (CNIC found but format issue)"
    else:
        breakdown["cnic_format"] = "+0 (No CNIC found)"

    # Name extracted (+10)
    if parsed.get("name_english"):
        score += 10
        breakdown["name"] = "+10 (Name extracted)"
    else:
        breakdown["name"] = "+0 (Name not extracted)"

    # Father name extracted (+5)
    if parsed.get("father_name_english"):
        score += 5
        breakdown["father_name"] = "+5 (Father name extracted)"
    else:
        breakdown["father_name"] = "+0 (Father name not extracted)"

    # All dates present and valid (+20)
    if date_val["dates_valid"] and date_val["checks"]:
        score += 20
        breakdown["dates"] = "+20 (Dates valid)"
    elif not date_val["issues"]:
        score += 10
        breakdown["dates"] = "+10 (Partial date validation)"
    else:
        breakdown["dates"] = f"+0 (Date issues: {', '.join(date_val['issues'])})"

    # CNIC not expired (+15)
    if not date_val["checks"].get("is_expired", True):
        score += 15
        breakdown["expiry"] = "+15 (CNIC not expired)"
    else:
        breakdown["expiry"] = "+0 (CNIC expired or unknown)"

    # Selfie uploaded (+20 - face match placeholder)
    if has_selfie:
        score += 20
        breakdown["selfie"] = "+20 (Selfie provided for face verification)"
    else:
        breakdown["selfie"] = "+0 (No selfie)"

    # Determine verdict
    if score >= 75:
        verdict = "LOW RISK — VERIFIED"
        color = "green"
    elif score >= 50:
        verdict = "MEDIUM RISK — REVIEW REQUIRED"
        color = "orange"
    else:
        verdict = "HIGH RISK — FURTHER VERIFICATION NEEDED"
        color = "red"

    return {
        "score": score,
        "max_score": 100,
        "verdict": verdict,
        "color": color,
        "breakdown": breakdown,
        "cnic_validation": cnic_val,
        "date_validation": date_val,
    }


def run_full_analysis(parsed: dict, has_selfie: bool = False) -> dict:
    """
    Run complete fraud & validation analysis on parsed CNIC data.
    """
    cnic_val = validate_cnic_format(parsed.get("cnic_number"))
    date_val = validate_dates(parsed)
    gender_check = validate_gender_consistency(parsed, cnic_val)
    risk = calculate_risk_score(parsed, has_selfie)

    return {
        "cnic_format_check": cnic_val,
        "date_checks": date_val,
        "gender_consistency": gender_check,
        "risk_assessment": risk,
        "overall_status": risk["verdict"]
    }
