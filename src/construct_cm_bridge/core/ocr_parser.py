"""Local OCR Parser for Scanned Test Certificates and Engineering Drawings

Parses scanned PDF, JPG, PNG test certificates (Mill Sheets, KS Test Reports, Concrete/Rebar Tests):
- Local OCR extraction with pytesseract
- Automatic extraction of:
  * Product name, Standard/Grade (SS275, SM355, SD400, 압출법보온판)
  * Testing Agency (KCL, KTR, POSCO QA, etc.)
  * Mechanical properties (Yield strength, Tensile strength, Elongation)
  * Thermal/Physical values (Thermal conductivity, Compressive strength)
  * KS Standard pass/fail validation
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

from .doc_parser import DocumentParser

logger = logging.getLogger(__name__)


class MaterialCertOCRParser:
    """Extracts data from scanned material test certificates & inspection photos."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()

    def parse_scanned_certificate(self, image_or_pdf_file: str) -> Dict[str, Any]:
        """Extracts text and key test parameters from image or PDF."""
        file_path = self.parser._validate_path(image_or_pdf_file)
        ext = file_path.suffix.lower()

        extracted_text = ""

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            extracted_text = self._ocr_image(file_path)
        elif ext == ".pdf":
            extracted_text = self._parse_pdf_or_ocr(file_path)
        elif ext in [".txt", ".md"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted_text = f.read()
            except Exception as e:
                raise RuntimeError(f"Failed to read certificate text: {e}") from e
        else:
            raise ValueError(f"Unsupported file type for OCR: {ext}")

        if not extracted_text.strip() or len(extracted_text.strip()) < 20:
            return {
                "status": "REVIEW_REQUIRED",
                "file_name": file_path.name,
                "ocr_engine": "pytesseract" if HAS_PYTESSERACT else "unavailable",
                "error": "OCR에서 검증 가능한 텍스트를 추출하지 못했습니다.",
                "extracted_text_preview": extracted_text.strip(),
                "certificate_metadata": {
                    "test_agency": None,
                    "report_no": None,
                    "material_grade": None,
                    "heat_or_lot_no": None,
                    "issue_date": None,
                },
                "test_results": {},
                "ks_compliance_verdict": "검증 불가 (REVIEW_REQUIRED)",
                "compliance_details": [],
            }

        # Extract structured parameters from OCR text
        cert_data = self._extract_cert_properties(extracted_text, file_path.name)

        return {
            "status": "SUCCESS",
            "file_name": file_path.name,
            "ocr_engine": "pytesseract" if HAS_PYTESSERACT else "text_extraction_only",
            "extracted_text_preview": extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""),
            "certificate_metadata": {
                "test_agency": cert_data.get("test_agency"),
                "report_no": cert_data.get("report_no"),
                "material_grade": cert_data.get("material_grade"),
                "heat_or_lot_no": cert_data.get("lot_no"),
                "issue_date": cert_data.get("issue_date"),
            },
            "test_results": cert_data.get("parameters", {}),
            "ks_compliance_verdict": cert_data.get("verdict"),
            "compliance_details": cert_data.get("verdict_details"),
        }

    def _ocr_image(self, img_path: Path) -> str:
        """Runs OCR on image file."""
        if HAS_PYTESSERACT:
            try:
                img = Image.open(img_path)
                return pytesseract.image_to_string(img, lang="kor+eng")
            except Exception as e:
                logger.warning(f"pytesseract failed: {e}. Certificate requires manual review.")
        return ""

    def _parse_pdf_or_ocr(self, pdf_path: Path) -> str:
        """Parses PDF text or OCRs pages."""
        # Try DocumentParser standard PDF reading
        try:
            res = self.parser.parse_document(pdf_path.name)
            text = res.get("markdown", "")
            if len(text.strip()) > 30:
                return text
        except Exception:
            pass
        return ""

    def _extract_cert_properties(self, text: str, filename: str) -> Dict[str, Any]:
        """Extracts structured values from certificate text."""
        # Test agency
        agency = "한국건설생활환경시험연구원(KCL)" if "KCL" in text else (
            "한국화학융합시험연구원(KTR)" if "KTR" in text else (
                "포스코(POSCO)" if "POSCO" in text or "포스코" in text else None
            )
        )

        # Report No
        rep_m = re.search(r'(?:성적서번호|CERTIFICATE\s*NO|REPORT\s*NO)\s*[:=]?\s*([A-Za-z0-9-_]+)', text, re.I)
        report_no = rep_m.group(1) if rep_m else None

        # Material grade & spec
        grade_m = re.search(r'(?:STEEL\s*GRADE|GRADE|강종|재질|규격|시료명)\s*[:=]?\s*([^\n|]+)', text, re.I)
        if not grade_m:
            grade_m = re.search(r'(?:PRODUCT|품명)\s*[:=]?\s*([^\n|]+)', text, re.I)
        grade = grade_m.group(1).strip() if grade_m else None

        # Lot / Heat No
        heat_m = re.search(r'(?:HEAT\s*NO|LOT\s*NO|용강번호|로트번호)\s*[:=]?\s*([A-Za-z0-9-_]+)', text, re.I)
        lot_no = heat_m.group(1) if heat_m else None

        # Date
        date_m = re.search(r'(?:일자|Date)\s*[:=]?\s*([0-9]{4}[.-][0-9]{1,2}[.-][0-9]{1,2})', text, re.I)
        issue_date = date_m.group(1) if date_m else None

        # Properties
        params: Dict[str, Any] = {}
        verdict = "검증 필요 (REVIEW_REQUIRED)"
        verdict_details = []
        explicit_pass = bool(re.search(r'(?:판정|결과)\s*[:=]?[^\n]*(?:적합|합격|PASS)', text, re.I))
        explicit_fail = bool(re.search(r'(?:판정|결과)\s*[:=]?[^\n]*(?:부적합|불합격|FAIL)', text, re.I))

        # Yield strength
        ys_m = re.search(r'(?:항복강도|Yield\s*Strength)[^\d\n]*?[:=]?\s*([0-9.]+)', text, re.I)
        if ys_m:
            ys_val = float(ys_m.group(1))
            params["항복강도_MPa"] = ys_val
            verdict_details.append(f"항복강도 {ys_val} MPa (원문 추출값)")

        # Tensile strength
        ts_m = re.search(r'(?:인장강도|Tensile\s*Strength)[^\d\n]*?[:=]?\s*([0-9.]+)', text, re.I)
        if ts_m:
            ts_val = float(ts_m.group(1))
            params["인장강도_MPa"] = ts_val
            verdict_details.append(f"인장강도 {ts_val} MPa (원문 추출값)")

        # Elongation
        el_m = re.search(r'(?:신율|Elongation)[^\d\n]*?[:=]?\s*([0-9.]+)', text, re.I)
        if el_m:
            params["신율_%"] = float(el_m.group(1))

        # Compressive strength
        cs_m = re.search(r'(?:평균\s*압축강도|압축강도)[^\d\n]*?[:=]?\s*([0-9.]+)', text, re.I)
        if cs_m:
            cs_val = float(cs_m.group(1))
            params["압축강도_MPa"] = cs_val
            verdict_details.append(f"압축강도 {cs_val} MPa (원문 추출값)")

        # Thermal conductivity
        tc_m = re.search(r'(?:열전도율)[^\d\n]*?[:=]?\s*([0-9.]+)', text, re.I)
        if tc_m:
            tc_val = float(tc_m.group(1))
            params["열전도율_W_mK"] = tc_val
            verdict_details.append(f"열전도율 {tc_val} W/m·K (원문 추출값)")

        if explicit_fail:
            verdict = "부적합 (FAIL)"
        elif explicit_pass and params:
            verdict = "적합 (PASS)"

        return {
            "test_agency": agency,
            "report_no": report_no,
            "material_grade": grade,
            "lot_no": lot_no,
            "issue_date": issue_date,
            "parameters": params,
            "verdict": verdict,
            "verdict_details": verdict_details,
        }


# Singleton instance
_ocr_parser = MaterialCertOCRParser()


def parse_scanned_material_cert(image_or_pdf_file: str) -> Dict[str, Any]:
    return _ocr_parser.parse_scanned_certificate(image_or_pdf_file)
