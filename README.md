# 🇵🇰 Pakistan CNIC KYC Verification System

## Overview

An AI-powered Know Your Customer (KYC) verification system designed specifically for **Pakistan National Identity Cards (CNIC)**. The system extracts and validates information from both the **front** and **back** sides of the CNIC using OCR, applies fraud detection logic, and produces a risk-scored verification decision.

---

## Features

### ✅ Current Features

- **CNIC Front OCR** — Extracts all printed English fields:
  - Full Name (English)
  - Father's Name (English)
  - Gender
  - Country of Stay
  - Identity Number (XXXXX-XXXXXXX-X format)
  - Date of Birth
  - Date of Issue
  - Date of Expiry

- **CNIC Back OCR** — Extracts:
  - CNIC number (top-right)
  - Address fields (English context clues)
  - Registrar General info

- **CNIC Format Validation**:
  - 13-digit structure check
  - Province/district code detection
  - Gender digit parity check (odd = Male, even = Female)

- **Date Logic Validation**:
  - Age calculation
  - Issue date after DOB check
  - Expiry after issue check
  - Expiry status (is the CNIC expired?)

- **Front/Back Cross-Verification**:
  - CNIC number must match on both sides

- **Risk Scoring System** (0–100):
  - Score ≥ 75 → LOW RISK (Verified)
  - Score 50–74 → MEDIUM RISK (Manual Review)
  - Score < 50 → HIGH RISK (Verification Failed)

- **Face Verification UI** (ready, model pending)

---

### 🔜 Upcoming Features

- Face matching (DeepFace / InsightFace)
- Liveness detection
- QR code decoding (back of CNIC)
- Urdu OCR for address extraction
- Duplicate CNIC check (database integration)
- Document tampering detection (CNN-based)
- FastAPI backend
- PostgreSQL storage

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit |
| OCR | EasyOCR |
| Image Processing | OpenCV |
| Image Handling | Pillow |
| ML Framework | PyTorch (via EasyOCR) |
| Language | Python 3.10+ |

---

## Pakistan CNIC Structure

```
Front:
  ┌─────────────────────────────────────────────┐
  │  PAKISTAN — National Identity Card           │
  │  Islamic Republic of Pakistan                │
  │                                              │
  │  Name          [English Name]                │
  │  Father Name   [Father's English Name]       │
  │  Gender [M/F]  Country of Stay [Pakistan]    │
  │  Identity Number   [XXXXX-XXXXXXX-X]         │
  │  Date of Birth     [DD.MM.YYYY]              │
  │  Date of Issue     [DD.MM.YYYY]              │
  │  Date of Expiry    [DD.MM.YYYY]              │
  └─────────────────────────────────────────────┘

CNIC Number Format:
  P P P P P - N N N N N N N - G
  └──┬──┘     └─────┬─────┘   └ Gender digit (odd=M, even=F)
     │               └─ Unique serial
     └─ Province/District code (first digit = province)

Province Codes:
  1x, 2x → KPK / FATA
  3x     → Punjab
  4x     → Sindh
  5x     → Balochistan
  6x     → Islamabad / AJK
  7x     → Gilgit-Baltistan

Back:
  ┌─────────────────────────────────────────────┐
  │  [Photo]   موجودہ پتہ: [Present Address]     │
  │            [CNIC Number top-right]           │
  │            مستقل پتہ: [Permanent Address]    │
  │  [Registrar General Signature]   [QR Code]  │
  └─────────────────────────────────────────────┘
```

---

## Project Structure

```
pakistan_cnic_kyc/
├── app.py                          # Streamlit main application
├── requirements.txt
├── pyproject.toml
├── README.md
│
└── App/
    ├── __init__.py
    └── services/
        ├── __init__.py
        ├── ocr_services.py         # EasyOCR + OpenCV preprocessing
        ├── parser.py               # CNIC field extraction & parsing
        └── validator.py            # Fraud detection & risk scoring
```

---

## Installation

### 1. Clone / Download

```bash
git clone <your-repo-url>
cd pakistan_cnic_kyc
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

```bash
# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** EasyOCR will automatically download its model files (~100MB) on first run.
> PyTorch is a dependency of EasyOCR. GPU is supported but not required.

### 4. Run the App

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`

---

## Usage

1. Open the app in your browser
2. Upload the **CNIC Front Side** image (JPG/PNG)
3. Optionally upload the **CNIC Back Side** image
4. Optionally upload a **Selfie** for face verification (UI ready)
5. Click **"🚀 Start KYC Verification"**
6. Review the extracted fields, validation checks, and risk score

---

## Risk Scoring Logic

| Signal | Points |
|--------|--------|
| CNIC number found + valid format | +30 |
| Full name extracted | +10 |
| Father's name extracted | +5 |
| All dates present and valid | +20 |
| CNIC not expired | +15 |
| Selfie provided | +20 |
| **Total possible** | **100** |

| Score Range | Decision |
|------------|---------|
| 75 – 100 | ✅ LOW RISK — VERIFIED |
| 50 – 74 | ⚠️ MEDIUM RISK — MANUAL REVIEW |
| 0 – 49 | ❌ HIGH RISK — FAILED |

---

## Author

Built for Pakistan CNIC KYC automation using open-source AI/ML tools.

---

## License

MIT License — free for personal and commercial use.
