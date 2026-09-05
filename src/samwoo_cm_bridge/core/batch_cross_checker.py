"""Batch Cross-Checker Module for Multiple Project Documents

Scans multiple submitted project documents (HWPX, XLSX, DOCX, etc.) in batch,
extracts core technical parameters (steel sections, safety factors, concrete strength,
design stresses, monitoring frequencies) via regex & natural language patterns,
and performs exhaustive 3-way cross-discrepancy inspection.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import DocumentParser, SECURE_DATA_DIR


class BatchCrossChecker:
    """Performs multi-document batch cross-checking and discrepancy detection."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()

    def _extract_numeric_entities(self, text: str, source_label: str) -> Dict[str, Any]:
        """Extracts key engineering parameters and numeric entities from text and markdown tables."""
        entities: Dict[str, Any] = {
            "safety_factors": [],
            "steel_sections": [],
            "concrete_strength": [],
            "stresses": [],
            "monitoring_frequency": [],
            "explicit_failures": [],
        }

        # --- A. Markdown Table Column Analysis ---
        lines = text.strip().split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("|") and line.endswith("|"):
                table_rows = []
                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    t_line = lines[i].strip()
                    # skip delimiter line |---|---|
                    if not set(t_line.replace("|", "").strip()) <= {"-", ":"}:
                        cells = [c.strip() for c in t_line.strip("|").split("|")]
                        table_rows.append(cells)
                    i += 1

                if len(table_rows) >= 2:
                    headers = [h.strip() for h in table_rows[0]]
                    for row in table_rows[1:]:
                        for col_idx, cell_val in enumerate(row):
                            if col_idx >= len(headers):
                                continue
                            header = headers[col_idx]
                            val_str = cell_val.strip()

                            # 1. Column is Safety Factor (안전율 / Fs / SF)
                            if any(k in header for k in ["안전율", "Fs", "F.S", "SF", "Safety"]):
                                # Extract float
                                m = re.search(r'([0-9]+\.?[0-9]*)', val_str)
                                if m:
                                    try:
                                        fv = float(m.group(1))
                                        if 0.1 <= fv <= 50.0:
                                            entities["safety_factors"].append(fv)
                                    except ValueError:
                                        pass

                            # 2. Column is Steel Section (규격 / 단면 / 부재)
                            if any(k in header for k in ["규격", "단면", "부재", "형강"]):
                                sm = re.findall(r'(H-[0-9]{3,4}\s*[xX*]\s*[0-9]{3,4}(?:\s*[xX*]\s*[0-9]{1,2}\s*[xX*]\s*[0-9]{1,2})?)', val_str)
                                for s in sm:
                                    entities["steel_sections"].append(re.sub(r'\s+', '', s).replace('*', 'X').upper())

                            # 3. Column is Stress (응력 / 작용응력 / 허용응력)
                            if "응력" in header:
                                m = re.search(r'([0-9]+\.?[0-9]*)', val_str)
                                if m:
                                    try:
                                        entities["stresses"].append(float(m.group(1)))
                                    except ValueError:
                                        pass

                            # 4. Explicit FAIL / 부적합 in Judgement column
                            if any(k in header for k in ["판정", "결과", "적합여부", "Status"]):
                                if any(fail_word in val_str.upper() for fail_word in ["FAIL", "부적합", "불합격", "미달"]):
                                    row_desc = " ".join([f"{headers[j]}:{row[j]}" for j in range(min(len(headers), len(row)))])
                                    entities["explicit_failures"].append(row_desc)
            else:
                i += 1

        # --- B. Plain Text Pattern Extraction ---
        # 1. 안전율 패턴 (Fs, 안전율, Safety Factor)
        fs_matches = re.findall(
            r'(?:안전율|Fs|F\.s|Safety\s*Factor)\s*[:=~>=<]*\s*([0-9]+\.?[0-9]*)',
            text,
            re.IGNORECASE,
        )
        for v in fs_matches:
            try:
                val = float(v)
                if 0.1 <= val <= 50.0:
                    entities["safety_factors"].append(val)
            except ValueError:
                pass

        # 2. 강재/부재 규격 패턴 (H-300x300, H-350x350 등)
        steel_matches = re.findall(
            r'(H-[0-9]{3,4}\s*[xX*]\s*[0-9]{3,4}(?:\s*[xX*]\s*[0-9]{1,2}\s*[xX*]\s*[0-9]{1,2})?)',
            text,
        )
        for s in steel_matches:
            entities["steel_sections"].append(re.sub(r'\s+', '', s).replace('*', 'X').upper())

        # 3. 콘크리트 압축강도 (24MPa, fck = 27MPa 등)
        fck_matches = re.findall(
            r'(?:fck|압축강도|설계기준강도|콘크리트\s*강도)\s*[:=~]?\s*([0-9]{2,3})\s*(?:MPa)?',
            text,
            re.IGNORECASE,
        )
        for v in fck_matches:
            iv = int(v)
            if 10 <= iv <= 150:
                entities["concrete_strength"].append(iv)

        # 4. 허용응력 / 작용응력 (MPa)
        stress_matches = re.findall(
            r'(?:허용응력|작용응력|응력|축응력|휨응력)\s*[:=~]?\s*([0-9]+\.?[0-9]*)\s*MPa',
            text,
        )
        for v in stress_matches:
            entities["stresses"].append(float(v))

        # 5. 계측 주기 (주 N회, 일 N회, 월 N회)
        mon_matches = re.findall(r'((?:주|일|월)\s*[0-9]+\s*회)', text)
        for m in mon_matches:
            entities["monitoring_frequency"].append(re.sub(r'\s+', '', m))

        # Clean duplicates & sort
        entities["safety_factors"] = list(dict.fromkeys(entities["safety_factors"]))
        entities["steel_sections"] = sorted(list(set(entities["steel_sections"])))
        entities["concrete_strength"] = sorted(list(set(entities["concrete_strength"])))
        entities["stresses"] = list(dict.fromkeys(entities["stresses"]))
        entities["monitoring_frequency"] = sorted(list(set(entities["monitoring_frequency"])))

        return {k: v for k, v in entities.items() if v}

    def cross_check_bundle(self, filenames: List[str]) -> Dict[str, Any]:
        """Parses multiple documents and inspects cross-discrepancies."""
        extracted_bundle: Dict[str, Any] = {}
        parsed_summaries: Dict[str, Any] = {}

        for fname in filenames:
            try:
                parsed = self.parser.parse_document(fname)
                raw_text = parsed.get("markdown", "") or parsed.get("text", "")
                parsed_summaries[fname] = {
                    "file_type": parsed.get("format", "UNKNOWN"),
                    "text_length": len(raw_text),
                }
                extracted_bundle[fname] = self._extract_numeric_entities(raw_text, fname)
            except Exception as e:
                parsed_summaries[fname] = {"error": str(e)}
                extracted_bundle[fname] = {}

        discrepancies: List[Dict[str, Any]] = []
        matches: List[str] = []

        # 1) 부재 규격 대조 (Steel Sections)
        all_steels = {
            fname: data.get("steel_sections", [])
            for fname, data in extracted_bundle.items()
            if data.get("steel_sections")
        }
        if len(all_steels) > 1:
            base_file, base_secs = next(iter(all_steels.items()))
            for target_file, target_secs in list(all_steels.items())[1:]:
                diff = set(base_secs).symmetric_difference(set(target_secs))
                if diff:
                    discrepancies.append({
                        "category": "부재 규격 불일치",
                        "description": f"[{base_file}] 규격({base_secs})과 [{target_file}] 규격({target_secs}) 상충 발생 (차이: {sorted(list(diff))})",
                        "severity": "HIGH",
                        "action": "시공계획서 본문과 구조계산서 간 적용 부재 규격 일치화 지시 필요",
                    })
                else:
                    matches.append(f"부재 규격 일치 확인: {base_secs}")
        elif len(all_steels) == 1:
            fname, secs = next(iter(all_steels.items()))
            matches.append(f"[{fname}] 부재 규격 추출: {secs}")

        # 2) Extract safety factors. Applicability thresholds must come from supplied evidence.
        all_fs = {
            fname: data.get("safety_factors", [])
            for fname, data in extracted_bundle.items()
            if data.get("safety_factors")
        }
        for fname, fs_list in all_fs.items():
            for fs in fs_list:
                if fs <= 0:
                    discrepancies.append({
                        "category": "설계 안전율(Fs) 비정상 값",
                        "description": f"[{fname}] 0 이하 안전율 {fs} 검출",
                        "severity": "CRITICAL",
                        "action": "원 계산식·단위·입력값을 확인하고 재산정",
                    })
                else:
                    matches.append(f"[{fname}] 안전율 Fs={fs} 추출 (적용 기준과 별도 대조 필요)")

        # 3) 계측 관리 주기 대조 (Monitoring Frequency)
        all_mon = {
            fname: data.get("monitoring_frequency", [])
            for fname, data in extracted_bundle.items()
            if data.get("monitoring_frequency")
        }
        if len(all_mon) > 1:
            base_file, base_freq = next(iter(all_mon.items()))
            for target_file, target_freq in list(all_mon.items())[1:]:
                if set(base_freq) != set(target_freq):
                    discrepancies.append({
                        "category": "계측 주기 불일치",
                        "description": f"[{base_file}] 주기({base_freq})와 [{target_file}] 주기({target_freq}) 불일치",
                        "severity": "MEDIUM",
                        "action": "발주처 특기시방서 기준(더 엄격한 주기)으로 통일 수정 지시",
                    })
                else:
                    matches.append(f"계측 주기 일치 확인: {base_freq}")

        # 4) 콘크리트 강도 대조 (Concrete Strength)
        all_fck = {
            fname: data.get("concrete_strength", [])
            for fname, data in extracted_bundle.items()
            if data.get("concrete_strength")
        }
        if len(all_fck) > 1:
            base_file, base_strengths = next(iter(all_fck.items()))
            for target_file, target_strengths in list(all_fck.items())[1:]:
                if set(base_strengths) != set(target_strengths):
                    discrepancies.append({
                        "category": "콘크리트 설계강도(fck) 불일치",
                        "description": f"[{base_file}] 강도({base_strengths} MPa)와 [{target_file}] 강도({target_strengths} MPa) 불일치",
                        "severity": "HIGH",
                        "action": "구조계산서 강도와 시방서/시공계획서 기재 강도 일치화 필요",
                    })
        # 5) 계산서 명시적 판정 결과(FAIL / 부적합) 대조
        for fname, data in extracted_bundle.items():
            for fail_item in data.get("explicit_failures", []):
                # Avoid duplicate if already covered
                discrepancies.append({
                    "category": "구조계산서 부적합(FAIL) 항목 검출",
                    "description": f"[{fname}] 계산서 내 부적합 검토항목 발견: {fail_item}",
                    "severity": "CRITICAL",
                    "action": "시공사에 부재 단면 상향 보강 및 구조계산서 재산정 지시",
                })

        # Overall verdict determination
        has_critical = any(d["severity"] == "CRITICAL" for d in discrepancies)
        has_high = any(d["severity"] == "HIGH" for d in discrepancies)
        overall_status = "REJECT_OR_MODIFY" if (has_critical or has_high) else "REVIEW_REQUIRED"

        return {
            "status": "SUCCESS",
            "inspected_files": filenames,
            "overall_verdict": "보완 후 재제출 (FAIL)" if overall_status == "REJECT_OR_MODIFY" else "자동 검출 범위 외 수동검토 필요 (REVIEW_REQUIRED)",
            "total_discrepancies": len(discrepancies),
            "discrepancies": discrepancies,
            "verified_matches": matches,
            "extracted_entities_by_file": extracted_bundle,
            "parsed_summaries": parsed_summaries,
        }


# Singleton instance
_cross_checker = BatchCrossChecker()


def batch_cross_check_documents(filenames: List[str]) -> Dict[str, Any]:
    return _cross_checker.cross_check_bundle(filenames)
