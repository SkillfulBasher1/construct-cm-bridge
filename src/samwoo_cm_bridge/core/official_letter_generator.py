"""Official CM Letter & Outward Notice Generator (Module 8 - Official Letter Drafter)

Generates official CM outward notification letters to Contractor or Owner:
- [수신: 시공사 현장소장, 참조: 발주처 감독관, 제목: OO 시공계획서 검토결과 통보 및 보완 지시의 건]
- Formatted with official letterhead, document numbers, legal references, and signature blocks in Word (.docx) and Markdown (.md).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from .doc_parser import SECURE_DATA_DIR, DocumentParser
from .docx_exporter import set_cell_background, set_cell_margins


class OfficialLetterGenerator:
    """Generates official CM outward notification letters."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()
        self.output_dir = SECURE_DATA_DIR

    def draft_notice(
        self,
        doc_title: str,
        recipient: str = "(주)대우건설 현장소장",
        reference: str = "발주처 감독관, 품질관리팀장",
        review_result_file: Optional[str] = None,
        action_items: Optional[List[str]] = None,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
    ) -> Dict[str, Any]:
        """Generates formal CM official notice document."""
        now = datetime.now()
        date_str = now.strftime("%Y년 %m월 %d일")
        doc_no = f"SWCM-NOTI-{now.strftime('%Y%m%d')}-01"

        # If review_result_file is provided, extract summary
        review_summary = ""
        if review_result_file:
            try:
                parsed = self.parser.parse_document(review_result_file)
                review_summary = parsed.get("markdown", "")[:400]
            except Exception as e:
                review_summary = f"검토결과 파일({review_result_file}) 참조"

        # Build Markdown content
        actions = action_items or [
            "1단 버팀보 안전율(Fs >= 1.25) 미달에 따른 부재 단면 상향(H-350 계열) 구조계산서 재작성",
            "발주처 지시사항에 따른 지표 침하계 및 경사계 계측 주기(주 2회) 계획서 반영",
            "보완된 시공계획서 및 관련 성적서를 기한 내 감리단에 재제출하여 승인을 득할 것",
        ]

        md_content = f"""# 주식회사 삼우씨엠건축사사무소
**{project_name} 건설사업관리단**

---
- **문서번호:** {doc_no}
- **시행일자:** {date_str}
- **수　　신:** {recipient}
- **참　　조:** {reference}
- **제　　목:** {doc_title}

---

### 1. 관련 근거
1. 건설기술 진흥법 제62조 (안전관리계획의 수립 및 이행)
2. 국가건설기준 KDS 21 30 00 (가설 흙막이 설계기준)
3. 당 현장 공사도급계약조건 및 특기시방서

### 2. 검토 결과 요약
귀 사에서 제출한 시공계획서 및 수치계산서에 대한 3자 교차 검토(국가법령-KCSC기준-발주처시방) 결과, 일부 주요 구조부재의 허용 안전율 기준 미달 및 변경 지시사항 미반영이 확인되어 **[보완 후 재제출 (FAIL)]** 처리되었음을 통보합니다.

### 3. 감리단 시정 및 조치 요구사항
귀 사는 아래 항목에 대하여 즉시 보완 조치를 시행하고, 수정된 시공계획서를 제출하여 감리원의 사전 승인을 득한 후 시공에 임하여 주시기 바랍니다.

"""
        for a in actions:
            md_content += f"- {a}\n"

        md_content += f"""
### 4. 제출 기한
- **조치 기한:** {date_str}로부터 7일 이내 (별도 협의 시 조정 가능)

---
**주식회사 삼우씨엠건축사사무소 책임건설사업관리기술인 (직인생략)**
"""

        # Generate Word (.docx)
        docx_filename = f"공문_{doc_no}.docx"
        md_filename = f"공문_{doc_no}.md"
        docx_path = self.output_dir / docx_filename
        md_path = self.output_dir / md_filename

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
        h_run = h_p.add_run("주식회사 삼우씨엠건축사사무소")
        h_run.font.name = "맑은 고딕"
        h_run.font.size = Pt(18)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(f"{project_name} 건설사업관리단")
        sub_run.font.name = "맑은 고딕"
        sub_run.font.size = Pt(12)
        sub_run.font.bold = True
        sub_run.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

        # Meta table
        meta_table = doc.add_table(rows=4, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_data = [
            ("문서번호", doc_no),
            ("시행일자", date_str),
            ("수　　신", recipient),
            ("참　　조", reference),
        ]
        for r_idx, (lbl, val) in enumerate(meta_data):
            c0 = meta_table.cell(r_idx, 0)
            c1 = meta_table.cell(r_idx, 1)
            c0.text = lbl
            c1.text = val
            set_cell_background(c0, "EDF2F7")
            set_cell_margins(c0, 60, 60, 80, 80)
            set_cell_margins(c1, 60, 60, 80, 80)
            c0.paragraphs[0].runs[0].font.bold = True

        doc.add_paragraph()

        # Subject line
        subj_p = doc.add_paragraph()
        subj_run = subj_p.add_run(f"제　　목 : {doc_title}")
        subj_run.font.name = "맑은 고딕"
        subj_run.font.size = Pt(12)
        subj_run.font.bold = True
        subj_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        doc.add_paragraph("─" * 45)

        # Body paragraphs
        p1 = doc.add_paragraph()
        p1.add_run("1. 관련 근거\n   가. 건설기술 진흥법 제62조 (안전관리계획의 수립 및 이행)\n   나. 국가건설기준 KDS 21 30 00 (가설 흙막이 설계기준)\n   다. 당 현장 공사도급계약조건 및 특기시방서")

        p2 = doc.add_paragraph()
        p2.add_run("2. 검토 결과 요약\n   귀 사에서 제출한 시공계획서 및 수치계산서에 대한 3자 교차 검토(국가법령-KCSC기준-발주처시방) 결과, 일부 주요 구조부재의 허용 안전율 기준 미달 및 변경 지시사항 미반영이 확인되어 [보완 후 재제출 (FAIL)] 처리되었음을 통보합니다.")

        p3 = doc.add_paragraph()
        p3.add_run("3. 감리단 시정 및 조치 요구사항\n   귀 사는 아래 항목에 대하여 즉시 보완 조치를 시행하고, 수정된 시공계획서를 제출하여 감리원의 사전 승인을 득한 후 시공에 임하여 주시기 바랍니다.\n")
        for a in actions:
            ap = doc.add_paragraph(style="List Bullet")
            ap.add_run(a).font.bold = True

        p4 = doc.add_paragraph()
        p4.add_run("4. 제출 기한: 본 공문 수신일로부터 7일 이내 제출 요망.")

        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sig_run = sig_p.add_run(f"주식회사 삼우씨엠건축사사무소\n책임건설사업관리기술인 {chief_cm_name} (직인생략)")
        sig_run.font.name = "맑은 고딕"
        sig_run.font.size = Pt(13)
        sig_run.font.bold = True
        sig_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        doc.save(str(docx_path))

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "doc_title": doc_title,
            "recipient": recipient,
            "docx_path": str(docx_path),
            "md_path": str(md_path),
        }


# Singleton instance
_letter_generator = OfficialLetterGenerator()


def draft_official_notice(
    doc_title: str,
    recipient: str = "(주)대우건설 현장소장",
    reference: str = "발주처 감독관, 품질관리팀장",
    review_result_file: Optional[str] = None,
    action_items: Optional[List[str]] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> Dict[str, Any]:
    return _letter_generator.draft_notice(
        doc_title=doc_title,
        recipient=recipient,
        reference=reference,
        review_result_file=review_result_file,
        action_items=action_items,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
    )
