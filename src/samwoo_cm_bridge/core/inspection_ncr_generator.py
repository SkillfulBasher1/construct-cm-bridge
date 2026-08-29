"""CM Inspection Sheet & Non-Conformance Report (NCR) Generator (Module 15 - Inspection & NCR)

Generates:
1. Standard CM Inspection Request & Result Sheet (검측요청서 및 결과통보서)
2. Non-Conformance Report & Corrective Action Order (부적합 시정지시서 - NCR)
   - Disallowed defects, violated KCS standards, photographic evidence,
     mandatory corrective actions, and re-inspection deadline.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from .doc_parser import SECURE_DATA_DIR
from .docx_exporter import DocxExporter, set_cell_background, set_cell_margins


class InspectionNCRGenerator:
    """Generates Inspection Request/Result Sheets and Non-Conformance Orders (NCR)."""

    def __init__(self, exporter: Optional[DocxExporter] = None):
        self.exporter = exporter or DocxExporter()
        self.output_dir = SECURE_DATA_DIR

    def generate_inspection_sheet(
        self,
        work_type: str,
        location: str,
        contractor_spec: str = "",
        inspection_items: Optional[List[Dict[str, str]]] = None,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        inspector_name: str = "이감리 분야별 책임기술인",
    ) -> Dict[str, Any]:
        """Generates standard CM Inspection Request & Result Sheet."""
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-INSP-{now.strftime('%Y%m%d')}-01"

        # Default inspection checkpoints if not passed
        items = inspection_items or [
            {
                "no": "1",
                "item": "부재 규격 및 치수 일치성",
                "standard": "설계도면 및 KCS 기준 만족",
                "tolerance": "±5mm 이내",
                "contractor_check": "적합 (PASS)",
                "cm_verdict": "적합 (PASS)",
            },
            {
                "no": "2",
                "item": "체결부 볼트 토크치 및 용접 비드 상태",
                "standard": "KCS 14 31 25 기준 소정의 조임력 확보",
                "tolerance": "적정 토크치 100% 만족",
                "contractor_check": "적합 (PASS)",
                "cm_verdict": "적합 (PASS)",
            },
            {
                "no": "3",
                "item": "수직도/수평도 및 변위 발생 여부",
                "standard": "허용오차(1/500) 이내 관리",
                "tolerance": "최대 10mm 미만",
                "contractor_check": "적합 (PASS)",
                "cm_verdict": "적합 (PASS)",
            },
        ]

        has_fail = any("부적합" in i.get("cm_verdict", "") or "FAIL" in i.get("cm_verdict", "") for i in items)
        final_verdict = "검측 부적합 (FAIL)" if has_fail else "검측 승인 (PASS)"

        # Build Markdown content
        md_lines = [
            f"# [검측요청서 및 결과통보서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **검측일자:** {date_str}",
            f"- **검측공종:** {work_type}",
            f"- **검측위치:** {location}",
            f"- **시공사 사양:** {contractor_spec or '설계도서 준용'}",
            f"- **담당 감리원:** {inspector_name}\n",
            f"# 1. 세부 검측 체크리스트 및 판정 결과",
            f"| No | 검측 세부 항목 | 관리 기준 | 허용 오차 | 시공사 점검 | **감리원 판정** |",
            f"|---|---|---|---|---|---|",
        ]

        for it in items:
            md_lines.append(
                f"| {it.get('no')} | {it.get('item')} | {it.get('standard')} | {it.get('tolerance')} | {it.get('contractor_check')} | **{it.get('cm_verdict')}** |"
            )

        md_lines.extend([
            f"\n# 2. 종합 검측 판정 및 지시사항",
            f"- **최종 검측 결과:** **{final_verdict}**",
            f"- **감리의견:** 상기 검측 항목에 대한 현장 실측 결과 설계도서 및 시방 기준을 충족하므로 후속 공정 진행을 승인함.",
        ])

        report_md = "\n".join(md_lines)
        output_filename = f"검측결과통보서_{work_type}_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=output_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=inspector_name,
            discipline=f"검측업무 ({work_type})",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "work_type": work_type,
            "location": location,
            "final_verdict": final_verdict,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }

    def draft_ncr_order(
        self,
        issue_description: str,
        location: str,
        defect_category: str = "시공품질 불량",
        photo_attached: str = "현장 사진 첨부",
        corrective_deadline: str = "",
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
    ) -> Dict[str, Any]:
        """Drafts formal Non-Conformance Report (부적합 시정지시서 - NCR)."""
        now = datetime.now()
        date_str = now.strftime("%Y년 %m월 %d일")
        deadline_str = corrective_deadline or (now.strftime("%Y년 %m월 ") + str(now.day + 5) + "일")
        doc_no = f"SWCM-NCR-{now.strftime('%Y%m%d')}-01"

        md_content = f"""# 주식회사 삼우씨엠건축사사무소
**부적합 시정지시서 (Non-Conformance Report: NCR)**

---
- **관리번호:** {doc_no}
- **발행일자:** {date_str}
- **수　　신:** (주)대우건설 현장소장 (참조: 품질관리팀장, 공사팀장)
- **발　　신:** {project_name} 책임건설사업관리기술인 {chief_cm_name}
- **부적합 유형:** **{defect_category}** (위반 기준: KCS 및 시공시방서)
- **발생위치:** {location}

---

### 1. 부적합 및 지적 사항 내용
{issue_description}

### 2. 현장 실측/사진 증빙 현황
- **현장 증빙:** {photo_attached}
- **확인된 결함 상태:** 설계도면 및 승인된 시공계획서의 품질 기준을 위배하여 구조 안전성 및 내구성에 위해가 우려됨.

### 3. 감리단 시정 및 조치 지시사항
1. 귀 사는 본 지적 구간에 대하여 즉시 후속 공정을 중단하고, 결함 원인 분석 및 **시정조치 계획서(재시공/보강 방안)**를 작성하여 제출할 것.
2. 보강 조치 완료 후 감리원의 **입회 재검측(Re-inspection)**을 필히 득한 후 후속 작업을 재개할 것.
3. 동일 부적합 사례가 재발하지 않도록 작업팀 대상 특별 품질교육을 실시하고 결과를 보고할 것.

### 4. 시정조치 완료 보고 기한
- **이행 기한:** **{deadline_str}까지 (엄수)**

---
**주식회사 삼우씨엠건축사사무소 책임건설사업관리기술인 (직인생략)**
"""
        output_docx = f"시정지시서_{doc_no}.docx"
        output_md = f"시정지시서_{doc_no}.md"
        docx_path = self.output_dir / output_docx
        md_path = self.output_dir / output_md

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        doc = docx.Document()
        for s in doc.sections:
            s.top_margin = Inches(0.8)
            s.bottom_margin = Inches(0.8)
            s.left_margin = Inches(0.8)
            s.right_margin = Inches(0.8)

        # Header Title
        h_p = doc.add_paragraph()
        h_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h_run = h_p.add_run("부적합 시정지시서 (NCR)")
        h_run.font.name = "맑은 고딕"
        h_run.font.size = Pt(18)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0x9B, 0x2C, 0x2C)  # Red accent for NCR

        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(f"주식회사 삼우씨엠건축사사무소 | {project_name}")
        sub_run.font.name = "맑은 고딕"
        sub_run.font.size = Pt(11)
        sub_run.font.bold = True
        sub_run.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

        # Meta table
        meta_table = doc.add_table(rows=4, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_data = [
            ("관리번호", doc_no),
            ("발행일자", date_str),
            ("부적합 유형", f"{defect_category} (발생위치: {location})"),
            ("시정기한", f"{deadline_str}까지"),
        ]
        for r_idx, (lbl, val) in enumerate(meta_data):
            c0 = meta_table.cell(r_idx, 0)
            c1 = meta_table.cell(r_idx, 1)
            c0.text = lbl
            c1.text = val
            set_cell_background(c0, "FED7D7")  # Red tint for NCR
            set_cell_margins(c0, 60, 60, 80, 80)
            set_cell_margins(c1, 60, 60, 80, 80)
            c0.paragraphs[0].runs[0].font.bold = True

        doc.add_paragraph()

        # Body paragraphs
        p1 = doc.add_paragraph()
        p1_r = p1.add_run(f"1. 부적합 및 지적 사항\n   {issue_description}")
        p1_r.font.size = Pt(11)

        p2 = doc.add_paragraph()
        p2_r = p2.add_run(f"2. 현장 증빙 및 결함 상태\n   - 증빙: {photo_attached}\n   - 기준 위반: 설계도서 및 KCS 품질관리기준 미달")
        p2_r.font.size = Pt(11)

        p3 = doc.add_paragraph()
        p3_r = p3.add_run("3. 감리단 시정 및 조치 지시사항\n   가. 지적 구간 후속 작업 즉시 중단 및 안전조치 시행\n   나. 원인 분석 및 보강/재시공 계획서 제출\n   다. 조치 완료 후 감리원 입회 재검측 득할 것")
        p3_r.font.size = Pt(11)

        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sig_run = sig_p.add_run(f"주식회사 삼우씨엠건축사사무소\n책임건설사업관리기술인 {chief_cm_name} (직인생략)")
        sig_run.font.name = "맑은 고딕"
        sig_run.font.size = Pt(12)
        sig_run.font.bold = True
        sig_run.font.color.rgb = RGBColor(0x9B, 0x2C, 0x2C)

        doc.save(str(docx_path))

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "defect_category": defect_category,
            "location": location,
            "deadline": deadline_str,
            "docx_path": str(docx_path),
            "md_path": str(md_path),
        }


# Singleton instance
_inspection_ncr_gen = InspectionNCRGenerator()


def generate_inspection_sheet(
    work_type: str,
    location: str,
    contractor_spec: str = "",
    inspection_items: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    return _inspection_ncr_gen.generate_inspection_sheet(
        work_type=work_type,
        location=location,
        contractor_spec=contractor_spec,
        inspection_items=inspection_items,
    )


def draft_ncr_correction_order(
    issue_description: str,
    location: str,
    defect_category: str = "시공품질 불량",
    photo_attached: str = "현장 사진 첨부",
    corrective_deadline: str = "",
) -> Dict[str, Any]:
    return _inspection_ncr_gen.draft_ncr_order(
        issue_description=issue_description,
        location=location,
        defect_category=defect_category,
        photo_attached=photo_attached,
        corrective_deadline=corrective_deadline,
    )
