"""Evidence and arithmetic screening for subcontract agreement spreadsheets."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import openpyxl

from .doc_parser import DocumentParser
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class SubcontractAuditor:
    """Audits subcontractor contract ratios and legal requirements."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def audit_subcontract(
        self,
        subcontract_excel_file: str,
        contractor_name: str = "미입력 시공사",
        subcontractor_name: str = "미입력 하수급인",
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
    ) -> Dict[str, Any]:
        """Parses subcontract spreadsheet and performs 4-pillar statutory compliance review."""
        excel_path = self.parser._validate_path(subcontract_excel_file)
        if excel_path.suffix.lower() not in [".xlsx", ".xlsm"]:
            raise ValueError("하도급 검토 입력은 XLSX/XLSM 파일이어야 합니다.")

        wb = openpyxl.load_workbook(excel_path, data_only=True)
        
        # Extract contract numbers
        contract_work_name = "미확인"
        original_contract_amount: Optional[float] = None
        subcontract_amount: Optional[float] = None
        license_registered: Optional[str] = None
        has_resubcontract: Optional[bool] = None

        # Parse Excel cells if available
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                if not row or not any(row):
                    continue
                row_str = " ".join([str(c) for c in row if c is not None])
                numeric_values = [
                    float(val)
                    for val in row
                    if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0
                ]
                
                # Check for amounts
                if any(k in row_str for k in ["원도급", "도급금액", "원도급액"]) and "하도급 계약금액" not in row_str and numeric_values:
                    original_contract_amount = max(numeric_values)
                elif "하도급" in row_str and any(k in row_str for k in ["금액", "계약액"]) and numeric_values:
                    subcontract_amount = max(numeric_values)
                if "공사명" in row_str or "하도급 공종" in row_str:
                    for val in row:
                        if isinstance(val, str) and len(val) > 4 and "공사명" not in val and "기본정보" not in val:
                            contract_work_name = val
                if any(k in row_str for k in ["면허", "등록증", "전문건설업"]):
                    text_values = [str(val).strip() for val in row if isinstance(val, str)]
                    license_registered = " / ".join(text_values[1:]) or row_str
                if "재하도급" in row_str:
                    if any(k in row_str for k in ["해당 없음", "없음", "미실시"]):
                        has_resubcontract = False
                    elif any(k in row_str for k in ["있음", "실시", "해당"]):
                        has_resubcontract = True

        if original_contract_amount is None or subcontract_amount is None:
            raise ValueError("원도급 금액과 하도급 계약금액을 문서에서 확인할 수 없습니다.")
        if original_contract_amount <= 0 or subcontract_amount < 0:
            raise ValueError("계약금액은 유효한 0 이상의 값이어야 합니다.")

        # Arithmetic screening only; legal applicability depends on the current rules and contract.
        subcontract_ratio = (subcontract_amount / original_contract_amount) * 100.0
        sub_ratio_pass = subcontract_ratio >= 82.0

        # This residual is not evidence of the contractor's actual direct-construction ratio.
        residual_ratio = ((original_contract_amount - subcontract_amount) / original_contract_amount) * 100.0

        if subcontract_ratio > 100.0:
            ratio_status = "원도급액 초과 (REVIEW_REQUIRED)"
            ratio_action = "원도급액보다 큰 하도급액의 입력 셀과 계약 범위를 재확인"
        elif sub_ratio_pass:
            ratio_status = "선별 기준 이상 (SCREENING_ONLY)"
            ratio_action = "금액비율만 확인됨. 적용 법령과 심사대상 여부는 계약조건을 포함해 확인"
        else:
            ratio_status = "선별 기준 미달 (REVIEW_REQUIRED)"
            ratio_action = "기준 미달 가능성에 대한 법령·계약조건 검토 필요"

        # 3. Overall Verdict
        review_items: List[Dict[str, Any]] = [
            {
                "no": 1,
                "review_topic": "하도급 계약비율 적정성",
                "legal_criteria": "82% 선별 기준(실제 적용 법령·산식은 담당자 확인 필요)",
                "submitted_value": f"{subcontract_ratio:.2f}% ({subcontract_amount:,.0f}원 / {original_contract_amount:,.0f}원)",
                "status": ratio_status,
                "action": ratio_action,
            },
            {
                "no": 2,
                "review_topic": "원수급인 직접시공 의무비율",
                "legal_criteria": "직접시공 의무 적용 여부는 공사금액·공종·현행 기준 확인 필요",
                "submitted_value": f"원도급액 대비 단순 차액 {residual_ratio:.2f}% (직접시공률 산정값 아님)",
                "status": "산술값 확인 (REVIEW_REQUIRED)",
                "action": "직접시공계획서와 적용 기준을 별도 확인",
            },
            {
                "no": 3,
                "review_topic": "하수급인 전문건설업 면허 등록",
                "legal_criteria": "해당 공종 등록 요건과 현행 법령 확인 필요",
                "submitted_value": license_registered or "문서에서 확인되지 않음",
                "status": "기재 근거 발견 (REVIEW_REQUIRED)" if license_registered else "미확인 (REVIEW_REQUIRED)",
                "action": "등록증 원본·유효기간·해당 업종을 별도 확인",
            },
            {
                "no": 4,
                "review_topic": "불법 재하도급(일괄/무단) 금지",
                "legal_criteria": "재하도급 허용·금지 요건과 현행 법령 확인 필요",
                "submitted_value": "재하도급 없음 기재" if has_resubcontract is False else ("재하도급 있음 기재" if has_resubcontract else "문서에서 확인되지 않음"),
                "status": "위험 확인 (REVIEW_REQUIRED)" if has_resubcontract else "미확인/증빙필요 (REVIEW_REQUIRED)",
                "action": "계약서·인력투입·대금지급 자료로 재하도급 여부 확인",
            },
        ]

        overall_verdict = "산술 선별 완료, 법정 적정성 최종 검토 필요 (REVIEW_REQUIRED)"

        # 4. Generate Word Document (.docx) & Markdown (.md)
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-SUB-{now.strftime('%Y%m%d')}-01"

        md_lines = [
            f"# [하도급계약 통보서 및 적정성 검토의견서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **하도급 공종:** {contract_work_name}",
            f"- **원도급자:** {contractor_name} / **하도급자:** {subcontractor_name}",
            f"- **검토일자:** {date_str}",
            f"- **책임감리원:** {chief_cm_name}\n",
            f"# 1. 하도급계약 적정성 종합 판정",
            f"- **원도급금액:** **{original_contract_amount:,.0f}원**",
            f"- **하도급금액:** **{subcontract_amount:,.0f}원**",
            f"- **하도급 비율:** **{subcontract_ratio:.2f}%** (82.0% 선별 기준, 적용 여부 별도 확인)",
            f"- **최종 검토결과:** **{overall_verdict}**\n",
            f"# 2. 법정 심사기준별 세부 검토 대조표",
            f"| No | 심사 항목 | 법적 근거 및 기준 | 시공사 제출 내용 | 판정 | 감리의견 및 조치사항 |",
            f"|---|---|---|---|---|---|",
        ]

        for item in review_items:
            sym = "✔" if "PASS" in item["status"] or "적합" in item["status"] else "⚠️"
            md_lines.append(
                f"| {item['no']} | {item['review_topic']} | {item['legal_criteria']} | {item['submitted_value']} | {sym} **{item['status']}** | {item['action']} |"
            )

        report_md = "\n".join(md_lines)
        docx_filename = f"하도급적정성검토의견서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="계약 / 하도급관리",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "contract_work_name": contract_work_name,
            "original_contract_amount": original_contract_amount,
            "subcontract_amount": subcontract_amount,
            "subcontract_ratio_pct": subcontract_ratio,
            "overall_verdict": overall_verdict,
            "review_matrix": review_items,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{excel_path.name} [하도급계약서!R1]",
        }


# Singleton instance
_subcontract_auditor = SubcontractAuditor()


def audit_subcontract_agreement(
    subcontract_excel_file: str,
    contractor_name: str = "미입력 시공사",
    subcontractor_name: str = "미입력 하수급인",
    project_name: str = "미입력 프로젝트",
) -> Dict[str, Any]:
    return _subcontract_auditor.audit_subcontract(
        subcontract_excel_file=subcontract_excel_file,
        contractor_name=contractor_name,
        subcontractor_name=subcontractor_name,
        project_name=project_name,
    )
