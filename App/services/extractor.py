import re
from datetime import datetime

CNIC_RE = re.compile(r'\b(\d{5})\s*[-\s]\s*(\d{7})\s*[-\s]\s*(\d)\b')
DATE_RE = re.compile(r'\b(\d{1,2}[.,\-/]\d{1,2}[.,\-/]\d{4})\b')
NAME_RE = re.compile(r'^[A-Za-z][A-Za-z\s\-\.]{3,}$')


def _norm_date(raw: str):
    raw = raw.strip().replace(',', '.').replace(' ', '')
    for fmt in ('%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            obj = datetime.strptime(raw, fmt)
            if 1920 <= obj.year <= 2100 and 1 <= obj.month <= 12 and 1 <= obj.day <= 31:
                return obj.strftime('%d.%m.%Y'), obj
        except ValueError:
            continue
    return None


def _extract_dates_from_line(line: str):
    results = []
    for m in DATE_RE.finditer(line):
        r = _norm_date(m.group(1))
        if r:
            results.append(r)
    return results


def _is_name(text: str) -> bool:
    text = text.strip()
    if not NAME_RE.match(text):
        return False
    words = text.split()
    if not 2 <= len(words) <= 5:
        return False
    return all(re.match(r'^[A-Za-z\-\.]+$', w) for w in words)


def _clean_name(text: str) -> str:
    text = re.sub(r'[^A-Za-z\s\-\.]', '', text)
    return re.sub(r'\s+', ' ', text).strip().title()


def _cut_at_holder(lines):
    clean = []
    for line in lines:
        if re.search(r'\bholder\b', line, re.IGNORECASE):
            break
        clean.append(line)
    return clean


def _find_label(lines, *keywords):
    for i, line in enumerate(lines):
        ll = line.lower()
        if all(kw in ll for kw in keywords):
            return i
    return -1


def _next_date_after(lines, start_idx, limit=5):
    for j in range(start_idx + 1, min(start_idx + limit, len(lines))):
        dates = _extract_dates_from_line(lines[j])
        if dates:
            return dates[0][0]
    return None


def _next_name_after(lines, start_idx, limit=5):
    for j in range(start_idx + 1, min(start_idx + limit, len(lines))):
        candidate = _clean_name(lines[j])
        if _is_name(candidate):
            return candidate
    return None


def extract_cnic_front(ocr_text: str) -> dict:
    all_lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
    lines = _cut_at_holder(all_lines)
    full = ' '.join(lines)

    result = {
        "document_type": "PAKISTAN_CNIC",
        "side": "FRONT",
        "cnic_number": None,
        "name_english": None,
        "father_name_english": None,
        "gender": None,
        "country_of_stay": None,
        "date_of_birth": None,
        "date_of_issue": None,
        "date_of_expiry": None,
        "valid": False,
        "raw_lines": all_lines,
    }

    # 1. CNIC Number
    for line in lines:
        m = CNIC_RE.search(line)
        if m:
            result["cnic_number"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            break
    if not result["cnic_number"]:
        m = CNIC_RE.search(full)
        if m:
            result["cnic_number"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 2. Name
    for i, line in enumerate(lines):
        if line.lower().strip() == 'name':
            result["name_english"] = _next_name_after(lines, i)
            break
    if not result["name_english"]:
        for line in lines:
            m = re.match(r'^name\s+([A-Za-z].+)$', line, re.IGNORECASE)
            if m:
                candidate = _clean_name(m.group(1))
                if _is_name(candidate):
                    result["name_english"] = candidate
                    break

    # 3. Father Name
    for i, line in enumerate(lines):
        if 'father name' in line.lower() or line.lower().strip() == 'father name':
            result["father_name_english"] = _next_name_after(lines, i)
            break
    if not result["father_name_english"]:
        for line in lines:
            m = re.match(r'^father\s+name\s+([A-Za-z].+)$', line, re.IGNORECASE)
            if m:
                candidate = _clean_name(m.group(1))
                if _is_name(candidate):
                    result["father_name_english"] = candidate
                    break

    # 4. Gender
    for i, line in enumerate(lines):
        if line.lower().strip() == 'gender':
            for j in range(i+1, min(i+4, len(lines))):
                if re.fullmatch(r'M', lines[j].strip()):
                    result["gender"] = "Male"; break
                if re.fullmatch(r'F', lines[j].strip()):
                    result["gender"] = "Female"; break
                if re.search(r'\bMale\b', lines[j], re.IGNORECASE):
                    result["gender"] = "Male"; break
                if re.search(r'\bFemale\b', lines[j], re.IGNORECASE):
                    result["gender"] = "Female"; break
            break
    if not result["gender"]:
        for line in lines:
            if re.fullmatch(r'M', line.strip()):
                result["gender"] = "Male"; break
            if re.fullmatch(r'F', line.strip()):
                result["gender"] = "Female"; break

    # 5. Country of Stay
    for line in lines:
        if re.search(r'\bpakistan\b', line, re.IGNORECASE):
            if not re.search(r'islamic|republic|national|identity', line, re.IGNORECASE):
                result["country_of_stay"] = "Pakistan"
                break

    # 6. Dates
    dob_idx = _find_label(lines, 'date of birth')
    doi_idx = _find_label(lines, 'date of issue')
    doe_idx = _find_label(lines, 'date of expiry')

    if dob_idx >= 0:
        result["date_of_birth"] = _next_date_after(lines, dob_idx)

    if doi_idx >= 0 and doe_idx >= 0:
        # Both labels present — collect all dates after first label
        first_label = min(doi_idx, doe_idx)
        all_dates_after = []
        for j in range(first_label + 1, min(first_label + 8, len(lines))):
            for d_str, d_obj in _extract_dates_from_line(lines[j]):
                if d_str not in [x[0] for x in all_dates_after]:
                    all_dates_after.append((d_str, d_obj))
        all_dates_after.sort(key=lambda x: x[1])
        if len(all_dates_after) >= 2:
            result["date_of_issue"]  = all_dates_after[0][0]
            result["date_of_expiry"] = all_dates_after[1][0]
        elif len(all_dates_after) == 1:
            result["date_of_issue"] = all_dates_after[0][0]
    elif doi_idx >= 0:
        result["date_of_issue"]  = _next_date_after(lines, doi_idx)
    elif doe_idx >= 0:
        result["date_of_expiry"] = _next_date_after(lines, doe_idx)

    # Fallback — sort all valid dates
    if not (result["date_of_birth"] and result["date_of_issue"] and result["date_of_expiry"]):
        seen = {}
        for line in lines:
            for d_str, d_obj in _extract_dates_from_line(line):
                if d_str not in seen:
                    seen[d_str] = d_obj
        if len(seen) >= 3:
            sd = sorted(seen.items(), key=lambda x: x[1])
            result["date_of_birth"]  = result["date_of_birth"]  or sd[0][0]
            result["date_of_issue"]  = result["date_of_issue"]  or sd[1][0]
            result["date_of_expiry"] = result["date_of_expiry"] or sd[2][0]
        elif len(seen) == 2:
            sd = sorted(seen.items(), key=lambda x: x[1])
            result["date_of_birth"] = result["date_of_birth"] or sd[0][0]
            result["date_of_issue"] = result["date_of_issue"] or sd[1][0]

    if result["cnic_number"] and re.match(r'^\d{5}-\d{7}-\d$', result["cnic_number"]):
        result["valid"] = True

    return result


def extract_cnic_back(ocr_text: str) -> dict:
    lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
    full = ' '.join(lines)

    result = {
        "document_type": "PAKISTAN_CNIC",
        "side": "BACK",
        "cnic_number": None,
        "present_address": "Detected (Urdu text visible on card)",
        "permanent_address": "Detected (Urdu text visible on card)",
        "registrar_info": None,
        "raw_lines": lines,
    }

    for line in lines:
        m = CNIC_RE.search(line)
        if m:
            result["cnic_number"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            break
    if not result["cnic_number"]:
        m = CNIC_RE.search(full)
        if m:
            result["cnic_number"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    for line in lines:
        if 'registrar' in line.lower():
            result["registrar_info"] = "Registrar General of Pakistan"
            break

    return result