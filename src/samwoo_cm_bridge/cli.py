import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .server import run_server
from .core.openapi_client import fetch_national_law, fetch_kcsc_standard
from .core.doc_parser import read_local_project_file, list_secure_local_files, SECURE_DATA_DIR
from .core.formula_engine import verify_calculation_safety
from .core.docx_exporter import export_review_document
from .core.batch_cross_checker import batch_cross_check_documents, BatchCrossChecker


def cmd_serve(args):
    """Run FastMCP Server over stdio."""
    print("Starting Samwoo-CM-Bridge FastMCP Server (stdio)...", file=sys.stderr)
    run_server()


def cmd_list(args):
    """List files in secure_local_data/."""
    files = list_secure_local_files()
    print(f"\n[Secure Local Storage: {SECURE_DATA_DIR}]")
    print(f"Total files: {len(files)}")
    print("-" * 65)
    for f in files:
        print(f" - {f['filename']:<40} | {f['size_bytes']:>8} bytes | {f['extension']}")
    print("-" * 65)


def cmd_parse(args):
    """Parse local project file."""
    res = read_local_project_file(args.filename)
    print(f"\n=== [Parsed Document: {args.filename}] ===")
    print(res.get("markdown", ""))


def cmd_law(args):
    """Query national law."""
    res = fetch_national_law(args.law_name, args.article_no)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_kcsc(args):
    """Query KCSC standard."""
    res = fetch_kcsc_standard(args.code)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_demo(args):
    """Run comprehensive 3-way cross examination CM demo across 3 scenarios."""
    print("\n" + "=" * 70)
    print(" 🚀 Samwoo-CM-Bridge: 3자 교차 검토(Law-KCSC-Local) 종합 데모 시작")
    print("=" * 70)

    # -------------------------------------------------------------
    # Scenario 1: 토목/가설 흙막이 구조안전성 검토 (KDS 21 30 00)
    # -------------------------------------------------------------
    print("\n[시나리오 1: 토목/가설 흙막이 버팀보 및 안전율 3자 검토]")
    law1 = fetch_national_law("건설기술 진흥법", "62")
    kcsc1 = fetch_kcsc_standard("KDS 21 30 00")
    print(f" ✔ [국가법령] {law1.get('law_name')} 제{law1.get('article_no')}조 ({law1.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc1.get('standard_code')} ({kcsc1.get('standard_name')}) 수신 완료 (요구안전율 Fs >= 1.25)")

    # Math Verification
    math1 = verify_calculation_safety(
        item_name="1단 버팀보(Strut H-300x300x10x15)",
        domain="토목/구조",
        design_val=205.4,
        allowable_val=220.0,
        req_sf=1.25,
        formula_type="civil_safety_factor",
    )
    print(f" ✔ [수치검산] 작용응력: 205.4 MPa, 허용응력: 220.0 MPa -> 계산 Fs: {math1.get('calculated_value')} (판정: {math1.get('judgement')})")

    report1_md = f"""# 1. 검토 개요
- **검토 대상:** 가설 흙막이 지보공 1단 버팀보(H-300x300x10x15) 단면 적정성
- **근거 기준:** {law1.get('law_name')} 제{law1.get('article_no')}조 및 {kcsc1.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 국가법령 및 KDS 기준 | 발주처 시방조건 | 시공사 제출값 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 버팀보 안전율(Fs) | KDS 21 30 00 (Fs >= 1.25) | 특기시방 4.1조 (Fs >= 1.25) | Fs = 1.07 (작용 205.4 / 허용 220.0) | **FAIL (부적합)** | 단면 증대(H-350계열) 또는 설치간격 축소 필요 |
| 강재 품질 규격 | KCS 14 31 25 (SS275/SM355) | KS 정품 및 밀시트 제출 | KS D 3503 SS275 제출 | **PASS (적합)** | 공장 성적서 일치 확인 |
| 안전관리계획 대상 | 건진법 제62조 (10m 이상 굴착) | 굴착깊이 12.5m 승인필요 | 안전관리계획서 초안 제출 | **PASS (적합)** | 인허가청 승인 절차 진행 |

# 3. 세부 수치 검산 내역
- **연산 공식:** $F_s = \\frac{{\\sigma_{{allowable}}}}{{\\sigma_{{design}}}} = \\frac{{220.0}}{{205.4}} = 1.071$
- **요구 안전율:** $1.25$
- **검토 판정:** 기준 안전율 대비 -14.3% 부족으로 **부적합(FAIL)** 판정.

# 4. 종합 감리의견 및 조치 지시사항
- 본 가설 흙막이 1단 버팀보는 시공 중 토압 증가 시 좌굴 위험이 상존하므로 **[반려 및 보완]** 조치함.
- 시공사는 버팀보 부재 규격을 상향(H-350x350x12x19 등)하거나 수평 지지간격을 재조정하여 구조계산서를 재작성 후 제출할 것.
"""
    doc1 = export_review_document(
        output_filename="가설흙막이_CM검토의견서.docx",
        report_text=report1_md,
        project_name="삼우씨엠 강남 복합빌딩 신축공사",
        reviewer_name="김수석 건설사업관리기술인 (토목/구조)",
        discipline="토목 / 가설구조",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc1.get('docx_path')}")

    # -------------------------------------------------------------
    # Scenario 2: 소방/기계 소화수조 및 펌프 검토 (KCS 31 10 00)
    # -------------------------------------------------------------
    print("\n[시나리오 2: 소방/기계 소화수조 유효수량 및 펌프 용량 3자 검토]")
    law2 = fetch_national_law("소방시설 설치 및 관리에 관한 법률", "12")
    kcsc2 = fetch_kcsc_standard("KCS 31 10 00")
    print(f" ✔ [국가법령] {law2.get('law_name')} 제{law2.get('article_no')}조 ({law2.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc2.get('standard_code')} ({kcsc2.get('standard_name')}) 수신 완료")

    math2 = verify_calculation_safety(
        item_name="옥내소화전 소화수조 유효저수량",
        domain="소방",
        formula_type="fire_reservoir_hydrant",
        variables={"actual_reservoir_vol": 15.0, "hydrant_count": 5},
    )
    print(f" ✔ [수치검산] 소화수조 유효용량 검토: {math2.get('judgement')} (실제 15.0 m³ >= 요구 13.0 m³)")

    report2_md = f"""# 1. 검토 개요
- **검토 대상:** 지하 2층 기계실 옥내소화전 소화수조 용량 및 가압송수펌프 양정
- **근거 기준:** {law2.get('law_name')} 제{law2.get('article_no')}조 및 {kcsc2.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 법령 및 KCSC 기준 | 발주처 요구조건 | 시공사 제출 설계치 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 소화수조 유효수량 | KCS 31 10 00 (V >= 5 x 2.6 = 13.0 m³) | 유효용량 15.0 m³ 이상 | 설계용량 15.0 m³ | **PASS (적합)** | 기준 대비 +15.4% 여유 확보 |
| 소화펌프 방수압력 | 소방시설법 (P >= 0.17 MPa) | 최상층 방수압 0.25 MPa | 정격토출압 0.32 MPa | **PASS (적합)** | 규격 적정 |
| 펌프 정격 토출량 | KCS 31 10 00 (Q >= 650 L/min) | 토출량 700 L/min | 설계 토출량 700 L/min | **PASS (적합)** | 적정 |

# 3. 세부 수치 검산 내역
- **소화수조 용량 산정식:** $V = N \\times 2.6 = 5 \\times 2.6 = 13.0\\text{{ m}}^3$
- **설계 저수량:** $15.0\\text{{ m}}^3$ (여유율 $+15.38\\%$) -> **적합(PASS)**

# 4. 종합 감리의견
- 소방 수조 및 펌프 용량 계산 결과 관련 법령 및 발주처 시방기준을 모두 만족하므로 **[원안 승인]**함.
"""
    doc2 = export_review_document(
        output_filename="소방설비_CM검토의견서.docx",
        report_text=report2_md,
        project_name="삼우씨엠 판교 데이터센터 신축공사",
        reviewer_name="박수석 건설사업관리기술인 (기계/소방)",
        discipline="기계 / 소방",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc2.get('docx_path')}")

    # -------------------------------------------------------------
    # Scenario 3: 전기/건축 전압강하 및 외벽 열관류율 검토 (KEC 232 / KDS 41 10 00)
    # -------------------------------------------------------------
    print("\n[시나리오 3: 전기/건축 전압강하율 및 외벽 열관류율 3자 검토]")
    law3 = fetch_national_law("전기사업법", "67")
    kcsc3 = fetch_kcsc_standard("KEC 232")
    print(f" ✔ [국가법령] {law3.get('law_name')} 제{law3.get('article_no')}조 ({law3.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc3.get('standard_code')} ({kcsc3.get('standard_name')}) 수신 완료")

    math3 = verify_calculation_safety(
        item_name="지하주차장 동력 간선 전압강하율",
        domain="전기/통신",
        formula_type="elec_voltage_drop_pct",
        variables={"length_m": 85, "current_a": 150, "wire_area_sqmm": 50, "nominal_voltage": 380, "max_drop_pct": 3.0},
    )
    print(f" ✔ [수치검산] 선로 전압강하율 검토: {math3.get('calculated_value')}% (허용: 3.0%, 판정: {math3.get('judgement')})")

    report3_md = f"""# 1. 검토 개요
- **검토 대상:** 지하주차장 동력 배선 간선 전압강하율 및 외벽 단열 성능
- **근거 기준:** {law3.get('law_name')} 제{law3.get('article_no')}조 및 {kcsc3.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 기준 및 KEC 규정 | 발주처 요구조건 | 시공사 제출 설계치 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 간선 전압강하율 | KEC 232 (허용강하율 <= 3.0%) | 조명/동력 공통 2.5% 이하 | e = 1.19% (CV 50sq, 85m) | **PASS (적합)** | 허용치(3.0%) 대비 충분한 여유 |
| 외벽 열관류율(U) | KDS 41 10 00 (U <= 0.170 W/m²K) | 특기시방 0.160 이하 | U = 0.155 (압출보온판 160mm) | **PASS (적합)** | 단열성능 만족 |

# 3. 세부 수치 검산 내역
- **3상 4선식 전압강하율 산정식:**
  $$e(\\%) = \\frac{{17.8 \\times L \\times I}}{{1000 \\times A \\times V}} \\times 100 = \\frac{{17.8 \\times 85 \\times 150}}{{1000 \\times 50 \\times 380}} \\times 100 = 1.194\\%$$
- **판정:** 규격 기준 $3.0\\%$ 이하 만족 -> **PASS (적합)**

# 4. 종합 감리의견
- 전기 간선 굵기 산정 및 단열재 열관류율 계산 결과 기준치를 충분히 만족하므로 **[원안 승인]**함.
"""
    doc3 = export_review_document(
        output_filename="전기및건축_CM검토의견서.docx",
        report_text=report3_md,
        project_name="삼우씨엠 마곡 R&D센터 신축공사",
        reviewer_name="이수석 건설사업관리기술인 (전기/건축)",
        discipline="전기 / 건축",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc3.get('docx_path')}")

    print("\n" + "=" * 70)
    print(" 🎉 3대 시나리오 3자 교차 검토 및 감리의견서 자동 생성 데모 완료!")
    print(f" 📂 결과 문서 저장소: {SECURE_DATA_DIR}")
    print("=" * 70 + "\n")


def cmd_check_bundle(args):
    """Run batch cross-check across multiple submitted documents."""
    files = args.files
    if not files:
        print("Error: Please provide at least one filename to check.", file=sys.stderr)
        return

    checker = BatchCrossChecker()
    result = checker.cross_check_bundle(list(files))

    is_fail = "FAIL" in result["overall_verdict"] or result["total_discrepancies"] > 0
    verdict_str = f"보완 후 재제출 (FAIL)" if is_fail else f"적합 (PASS)"

    print("\n" + "=" * 65)
    print(f"[일괄 전수검사 결과] 최종 판정: {verdict_str}")
    print("=" * 65)
    print(f"- 검토 대상 파일: {', '.join(result['inspected_files'])}")
    print(f"- 검출된 불일치/미달 건수: {result['total_discrepancies']}건\n")

    if result["discrepancies"]:
        print("=== [발견된 불일치 및 결함 항목] ===")
        for idx, item in enumerate(result["discrepancies"], 1):
            print(f"{idx}. [{item['category']}] (심각도: {item['severity']})")
            print(f"   - 내용: {item['description']}")
            print(f"   - 조치사항: {item['action']}")
        print()

    if result["verified_matches"]:
        print("=== [검증된 일치/충족 항목] ===")
        for m in result["verified_matches"]:
            print(f" ✔ {m}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Samwoo-CM-Bridge CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve
    subparsers.add_parser("serve", help="Run FastMCP stdio server")

    # list
    subparsers.add_parser("list", help="List files in secure_local_data/")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse a local project file")
    p_parse.add_argument("filename", help="Name of file in secure_local_data/")

    # check-bundle
    p_bundle = subparsers.add_parser("check-bundle", help="Batch cross-check multiple documents")
    p_bundle.add_argument("files", nargs="+", help="Filenames to cross-check")

    # law
    p_law = subparsers.add_parser("law", help="Query national law article")
    p_law.add_argument("law_name", help="Name of law")
    p_law.add_argument("--article", "-a", dest="article_no", default="", help="Article number")

    # kcsc
    p_kcsc = subparsers.add_parser("kcsc", help="Query KCSC standard")
    p_kcsc.add_argument("code", help="Standard code (e.g. 'KDS 21 30 00')")

    # demo
    subparsers.add_parser("demo", help="Run full 3-way CM review demo")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "parse":
        cmd_parse(args)
    elif args.command == "check-bundle":
        cmd_check_bundle(args)
    elif args.command == "law":
        cmd_law(args)
    elif args.command == "kcsc":
        cmd_kcsc(args)
    elif args.command == "demo":
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
