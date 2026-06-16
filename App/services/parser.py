from App.services.extractor import extract_cnic_front, extract_cnic_back


def detect_side(text: str) -> str:
    tl = text.lower()
    back_kw = ['registrar', 'registrar general', 'mustaqil', 'present address', 'permanent address']
    front_kw = ['father', 'date of birth', 'date of issue', 'date of expiry',
                 'identity number', 'national identity', 'country of stay']
    bs = sum(1 for kw in back_kw  if kw in tl)
    fs = sum(1 for kw in front_kw if kw in tl)
    if bs > fs:
        return "BACK"
    return "FRONT"


def parse_document(text: str) -> dict:
    side = detect_side(text)
    if side == "BACK":
        return extract_cnic_back(text)
    return extract_cnic_front(text)