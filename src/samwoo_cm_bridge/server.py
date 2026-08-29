"""Samwoo-CM-Bridge FastMCP Server Definition

Exposes CM 3-way Cross Verification Tools to Claude Desktop, Cursor, OpenClaw, and local agents.
"""

import json
import logging
from typing import Optional, Dict, Any

from fastmcp import FastMCP

from .core.openapi_client import fetch_national_law as _fetch_law, fetch_kcsc_standard as _fetch_kcsc
from .core.doc_parser import read_local_project_file as _read_file, list_secure_local_files as _list_files
from .core.formula_engine import verify_calculation_safety as _verify_math
from .core.docx_exporter import export_review_document as _export_doc
from .core.batch_cross_checker import batch_cross_check_documents as _batch_cross_check
from .core.diff_audit_engine import audit_document_diff as _audit_diff
from .core.adaptive_checklist_engine import generate_and_evaluate_checklist as _checklist_eval
from .core.semantic_standard_searcher import search_standards_by_keyword as _search_standards

logger = logging.getLogger("samwoo_cm_bridge")

# Initialize FastMCP Server
mcp = FastMCP(
    name="Samwoo-CM-Bridge",
    instructions=(
        "Samwoo-CM-Bridge는 삼우씨엠 건설사업관리(CM) 3자 교차 검토(국가법령-KCSC기준-시공사제출서류) "
        "엔진입니다. 로컬 보안 격리 폴더 내 문서를 읽고, 국가법령/KCSC 기준을 조회하며, "
        "파이썬 기반의 엄밀한 수치 검산(Zero-Hallucination)을 거쳐 삼우씨엠 표준 감리의견서를 자동 생성합니다."
    ),
)


@mcp.tool()
def fetch_national_law(law_name: str, article_no: str = "") -> str:
    """국가법령정보센터(law.go.kr) REST API를 호출하여 최신 개정 법률·시행령·시행규칙 조문을 실시간 검색합니다.
    API 키 미설정 또는 오프라인 환경에서는 정밀 로컬 캐시/Mock 데이터를 자동으로 반환합니다.

    Args:
        law_name: 검색할 법령명 (예: '건설기술 진흥법', '건축법', '주택법', '소방시설 설치 및 관리에 관한 법률', '전기사업법')
        article_no: 특정 조문 번호 (선택 사항, 예: '62', '53', '12')
    """
    res = _fetch_law(law_name=law_name, article_no=article_no if article_no else None)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def fetch_kcsc_standard(standard_code: str) -> str:
    """국가건설기준센터(kcsc.re.kr)로부터 KDS(설계기준) 및 KCS(표준시방서) 최신 규격 본문과 허용 기준치를 호출합니다.
    API 키 미설정 또는 오프라인 환경에서는 정밀 로컬 캐시/Mock 데이터를 자동으로 반환합니다.

    Args:
        standard_code: 검색할 건설기준 코드 (예: 'KDS 21 30 00', 'KCS 14 31 25', 'KCS 31 10 00', 'KEC 232', 'KDS 41 10 00')
    """
    res = _fetch_kcsc(standard_code=standard_code)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def read_local_project_file(filename: str) -> str:
    """로컬 보안 격리 폴더(secure_local_data/) 내의 프로젝트 파일(HWPX, XLSX, DOCX, PPTX, PDF, TXT)을 읽어
    구조화된 마크다운 본문 및 수치 테이블 메타데이터로 변환합니다. 외부 유출 없이 로컬에서만 격리 파싱됩니다.

    Args:
        filename: 읽을 파일명 (예: '과업지시서_특기시방.hwpx', '가설구조계산서.xlsx', '시공계획서.docx')
    """
    try:
        res = _read_file(filename=filename)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "filename": filename, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def list_secure_local_files() -> str:
    """로컬 보안 격리 작업 폴더(secure_local_data/)에 존재하는 검토 대상 파일 목록과 메타데이터(크기, 확장자 등)를 조회합니다."""
    files = _list_files()
    return json.dumps({"status": "SUCCESS", "count": len(files), "files": files}, ensure_ascii=False, indent=2)


@mcp.tool()
def verify_calculation_safety(
    item_name: str,
    domain: str = "토목/구조",
    design_val: float = 0.0,
    allowable_val: float = 0.0,
    req_sf: float = 1.25,
    formula_type: str = "civil_safety_factor",
    custom_formula: str = "",
    variables_json: str = "{}",
) -> str:
    """AI의 임의 추론(환각)을 배제하고 파이썬 코드로 안전율 및 공학 수식을 직접 연산하여 PASS/FAIL 및 여유율을 판정합니다.
    5대 공종(구조·토목, 기계·설비, 소방, 전기·통신, 건축) 표준 공식 및 AST 기반 커스텀 수식을 지원합니다.

    Args:
        item_name: 검토 대상 부재 또는 장비명 (예: '1단 버팀보(H-300x300)', '소화펌프 주펌프', '간선 케이블')
        domain: 공학 분야 ('토목/구조', '기계/설비', '소방', '전기/통신', '건축')
        design_val: 시공사 설계 작용치 / 작용응력
        allowable_val: 허용치 / 허용응력
        req_sf: 요구 안전율 또는 기준 임계치 (예: 1.25, 1.5, 3.0)
        formula_type: 내장 공식 키 ('civil_safety_factor', 'civil_strut_buckling', 'mep_pump_head_margin', 'fire_reservoir_hydrant', 'elec_voltage_drop_pct', 'arch_u_value' 등)
        custom_formula: 커스텀 수식 문자열 (선택 사항)
        variables_json: 추가 수식 변수 JSON 문자열 (선택 사항, 예: '{"length_m": 50, "current_a": 120, "wire_area_sqmm": 70, "nominal_voltage": 380, "max_drop_pct": 3.0}')
    """
    try:
        vars_dict = json.loads(variables_json) if variables_json and variables_json.strip() != "{}" else {}
    except Exception:
        vars_dict = {}

    res = _verify_math(
        item_name=item_name,
        domain=domain,
        design_val=design_val if design_val != 0.0 else None,
        allowable_val=allowable_val if allowable_val != 0.0 else None,
        req_sf=req_sf if req_sf != 0.0 else None,
        formula_type=formula_type if formula_type else None,
        custom_formula=custom_formula if custom_formula else None,
        variables=vars_dict,
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def export_review_document(
    output_filename: str,
    report_text: str,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    reviewer_name: str = "수석 건설사업관리기술인",
    discipline: str = "토목 / 구조 / 기계 / 소방 / 전기",
    doc_no: str = "",
) -> str:
    """3자 대조 및 수치 검산이 완료된 최종 마크다운 검토 의견을 삼우씨엠 표준 서식의 Word(.docx) 및 Markdown(.md) 문서로 로컬 저장합니다.

    Args:
        output_filename: 저장할 파일명 (예: '가설흙막이_CM검토의견서.docx')
        report_text: 마크다운 형식의 전체 검토의견서 본문 (4단 3자 교차 대조표, 수치 검산 상세, 종합 조치 의견 포함)
        project_name: 프로젝트명
        reviewer_name: 검토자(건설사업관리기술인) 이름
        discipline: 검토 공종 분야
        doc_no: 문서번호 (미지정 시 자동 채번)
    """
    try:
        res = _export_doc(
            output_filename=output_filename,
            report_text=report_text,
            project_name=project_name,
            reviewer_name=reviewer_name,
            discipline=discipline,
            doc_no=doc_no if doc_no else None,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def batch_cross_check_documents(filenames: list[str]) -> str:
    """로컬 보안 격리 폴더(secure_local_data/) 내 여러 문서(시공계획서 HWPX, 계산서 XLSX, 특기시방서 DOCX 등)를
    동시에 스캔하여 부재 규격, 안전율(Fs), 설계 하중, 허용응력, 콘크리트 강도, 계측 주기의 수치 상충 및 기준 미달을 일괄 전수 검사합니다.

    Args:
        filenames: 검사할 파일명 목록 (예: ['sample_과업지시서_특기시방.hwpx', 'sample_가설흙막이_구조계산서.xlsx'])
    """
    try:
        res = _batch_cross_check(filenames=filenames)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def audit_document_diff(base_file: str, target_file: str, file_category: str = "AUTO") -> str:
    """기성내역서(XLSX) 단가/수량/금액 변조 및 도서(HWPX/DOCX) 개정본(Revision) 변경점 전수 감사 도구입니다.
    - 기성내역서: 전회 승인단가 대비 임의 인상, 수식 하드코딩 과대청구, 도급수량 초과, 미승인 비목 자동 탐지
    - 설계도서/시방서: 삭제/추가/수정 조항 추출 및 설계 안전율/기준 완화(CRITICAL) 감지

    Args:
        base_file: 기준 파일명 (예: 'sample_기성내역서_Rev0.xlsx', '특기시방서_Rev0.hwpx')
        target_file: 변경/검토 대상 파일명 (예: 'sample_기성내역서_Rev1.xlsx', '특기시방서_Rev1.hwpx')
        file_category: 파일 구분 ('AUTO', 'EXCEL', 'TEXT')
    """
    try:
        res = _audit_diff(base_file=base_file, target_file=target_file, file_category=file_category)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_and_evaluate_checklist(
    work_type: str,
    site_conditions: str = "",
    spec_file: str = "",
    plan_file: str = "",
) -> str:
    """현장 특성(도심지, 고지하수위, 암반, 동절기 등) 및 특기시방서 기반으로 15~20개 맞춤형 CM 체크리스트를
    동적으로 생성하고, 시공사 제출 시공계획서(HWPX/DOCX)를 자동 스캔하여 적합/보완 판정 및 근거를 매핑합니다.

    Args:
        work_type: 대상 공종 ('토공/가설', '골조/콘크리트', '기계/소방', '전기/통신', '마감/방수')
        site_conditions: 현장 특수 조건 (예: '도심지 인접, 고지하수위, 암반발파, 동절기')
        spec_file: 발주처 특기시방서 파일명 (선택 사항, 예: 'sample_과업지시서_특기시방.hwpx')
        plan_file: 시공사 제출 시공계획서 파일명 (선택 사항, 예: 'sample_건축_단열및시공계획서.docx')
    """
    try:
        res = _checklist_eval(
            work_type=work_type,
            site_conditions=site_conditions,
            spec_file=spec_file if spec_file else None,
            plan_file=plan_file if plan_file else None,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def search_standards_by_keyword(query: str, domain: str = "", top_k: int = 3) -> str:
    """자연어 공학 질의(예: '버팀보 허용응력', '피난계단 보행거리', '소화수조 유효수량', '간선 전압강하율')를 분석하여
    관련 국가건설기준(KDS/KCS) 및 법령 조항을 연관도 순으로 역추적 검색하고 수치 검산 공식 힌트를 제공합니다.

    Args:
        query: 자연어 검색 질의어 (예: '버팀보 안전율 기준', '소화수조 용량 계산', '저압 간선 전압강하')
        domain: 공종 분야 필터 (선택 사항, 예: '토목/구조', '기계/소방', '전기/통신', '건축')
        top_k: 반환할 상위 결과 개수 (기본값: 3)
    """
    try:
        res = _search_standards(query=query, domain=domain if domain else None, top_k=top_k)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


def run_server():
    """Starts the FastMCP Stdio Server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
