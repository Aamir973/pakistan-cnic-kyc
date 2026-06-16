"""
OCR Service for Pakistan CNIC
Uses EasyOCR for text extraction from CNIC front and back images.

Strategy: Run OCR on MULTIPLE versions of the image and merge results.
The green CNIC background kills adaptive thresholding, so we use:
  1. Original color image (best for EasyOCR neural net)
  2. CLAHE-enhanced grayscale (boosts local contrast)
  3. Sharpened color image
Then merge all detections, deduplicate, and return.
"""

import cv2
import numpy as np
import easyocr
import os

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _reader


def _upscale(img, min_width=1200):
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)
    return img


def _sharpen(img):
    kernel = np.array([[0, -1, 0],
                        [-1, 5, -1],
                        [0, -1, 0]])
    return cv2.filter2D(img, -1, kernel)


def _clahe_gray(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _run_ocr_on(reader, img, temp_base, suffix):
    temp_path = f"{temp_base}_{suffix}.png"
    cv2.imwrite(temp_path, img)
    try:
        results = reader.readtext(temp_path, detail=1, paragraph=False)
        return [(text.strip(), conf) for (_, text, conf) in results
                if conf > 0.25 and text.strip()]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def extract_text(image_path: str) -> str:
    reader = get_reader()

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    img = _upscale(img)

    v1 = img.copy()
    v2 = _sharpen(img)
    clahe = _clahe_gray(img)
    v3 = cv2.cvtColor(clahe, cv2.COLOR_GRAY2BGR)

    base = image_path.replace('.', '_').replace(' ', '_')

    r1 = _run_ocr_on(reader, v1, base, "orig")
    r2 = _run_ocr_on(reader, v2, base, "sharp")
    r3 = _run_ocr_on(reader, v3, base, "clahe")

    # Return in detection order from best variant, add extras from others
    ordered = [text for text, _ in r1]
    ordered_lower = {t.lower() for t in ordered}
    for text, conf in r2 + r3:
        if text.lower() not in ordered_lower and conf > 0.35:
            ordered.append(text)
            ordered_lower.add(text.lower())

    return "\n".join(ordered)


def extract_text_with_positions(image_path: str) -> list:
    reader = get_reader()
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    img = _upscale(img)
    temp_path = image_path + "_pos.png"
    cv2.imwrite(temp_path, img)
    try:
        results = reader.readtext(temp_path, detail=1, paragraph=False)
        return [(bbox, text, conf) for (bbox, text, conf) in results if conf > 0.25]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)