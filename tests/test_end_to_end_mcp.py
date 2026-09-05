"""End-to-End Tests for Construct-CM-Bridge MCP Server Tools"""

import json
from pathlib import Path
from samwoo_cm_bridge.server import (
    fetch_national_law,
    fetch_kcsc_standard,
    read_local_project_file,
    list_secure_local_files,
    verify_calculation_safety,
    export_review_document,
)


def test_e2e_mcp_tools_flow():
    # 1. List files
    files_json = list_secure_local_files()
    files_data = json.loads(files_json)
    assert files_data["status"] == "SUCCESS"
    assert files_data["count"] >= 5

    # 2. Read HWPX file
    hwpx_json = read_local_project_file("sample_과업지시서_특기시방.hwpx")
    hwpx_data = json.loads(hwpx_json)
    assert hwpx_data["status"] == "SUCCESS"
    assert "특기시방서" in hwpx_data["markdown"]

    # 3. Read XLSX file
    xlsx_json = read_local_project_file("sample_가설흙막이_구조계산서.xlsx")
    xlsx_data = json.loads(xlsx_json)
    assert xlsx_data["status"] == "SUCCESS"

    # 4. Fetch Law
    law_json = fetch_national_law(law_name="건설기술 진흥법", article_no="62")
    law_data = json.loads(law_json)
    assert law_data["status"] == "SUCCESS"
    assert "62" in str(law_data["article_no"])

    # 5. Fetch KCSC
    kcsc_json = fetch_kcsc_standard(standard_code="KDS 21 30 00")
    kcsc_data = json.loads(kcsc_json)
    assert kcsc_data["status"] == "SUCCESS"

    # 6. Verify Math
    math_json = verify_calculation_safety(
        item_name="1단 버팀보(Strut H-300x300)",
        domain="토목/구조",
        design_val=205.4,
        allowable_val=220.0,
        req_sf=1.25,
    )
    math_data = json.loads(math_json)
    assert math_data["status"] == "SUCCESS"
    assert "FAIL" in math_data["judgement"]

    # 7. Export Document
    report_md = """# 1. 검토 개요
- 가설 흙막이 1단 버팀보 3자 교차 검토

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 법령/KDS 기준 | 발주처 시방 | 시공사 제출 | 판정 |
|---|---|---|---|---|
| 버팀보 안전율 | KDS 21 30 00 (Fs >= 1.25) | Fs >= 1.25 | Fs = 1.07 | FAIL |

# 3. 종합 의견
- 버팀보 단면 상향(H-350x350) 조치 지시
"""
    export_json = export_review_document(
        output_filename="E2E_가설흙막이_검토의견서.docx",
        report_text=report_md,
        project_name="E2E 테스트 공사",
        reviewer_name="테스트 감리원",
    )
    export_data = json.loads(export_json)
    assert export_data["status"] == "SUCCESS"
    assert Path(export_data["docx_path"]).stem.startswith("E2E_가설흙막이_검토의견서")
