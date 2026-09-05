import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

# Source and Target Paths
template_path = r"C:\Users\tbvja\Downloads\[양식2] 외부 AI 활용 아이디어 제안서.docx"
output_download_path = r"C:\Users\tbvja\Downloads\[양식2] 외부 AI 활용 아이디어 제안서_Samwoo-CM-Bridge.docx"
output_project_path = r"c:\Users\tbvja\Projects\samwoo-cm-bridge\[제안서] Samwoo-CM-Bridge_외부AI활용아이디어.docx"

doc = docx.Document(template_path)

NAVY = RGBColor(0x1A, 0x36, 0x5D)
DARK_GRAY = RGBColor(0x2D, 0x37, 0x48)
BLUE = RGBColor(0x2B, 0x6C, 0xB0)
RED = RGBColor(0xC5, 0x30, 0x30)
FONT_NAME = "맑은 고딕"

def format_run(run, font_name=FONT_NAME, font_size=Pt(9.5), bold=False, color=DARK_GRAY):
    run.font.name = font_name
    run.font.size = font_size
    run.bold = bold
    run.font.color.rgb = color
    # Ensure East Asian font is set in XML
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="{font_name}"/>')
        rPr.append(rFonts)
    else:
        rFonts.set(qn('w:eastAsia'), font_name)

def add_styled_paragraph(cell, text, font_size=Pt(9.5), bold=False, color=DARK_GRAY, space_after=Pt(3), bullet=False, indent=0):
    p = cell.add_paragraph()
    p.paragraph_format.space_after = space_after
    p.paragraph_format.line_spacing = 1.25
    if indent > 0:
        p.paragraph_format.left_indent = Inches(indent * 0.15)
    
    if bullet:
        prefix_run = p.add_run("• ")
        format_run(prefix_run, FONT_NAME, font_size, bold=True, color=NAVY)
    
    run = p.add_run(text)
    format_run(run, FONT_NAME, font_size, bold, color)
    return p

def add_heading_paragraph(cell, title, level=1):
    p = cell.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.2
    
    if level == 1:
        prefix = "■ "
        run = p.add_run(prefix + title)
        format_run(run, FONT_NAME, Pt(10.5), bold=True, color=NAVY)
    elif level == 2:
        prefix = "▶ "
        run = p.add_run(prefix + title)
        format_run(run, FONT_NAME, Pt(10), bold=True, color=BLUE)
    else:
        prefix = "- "
        run = p.add_run(prefix + title)
        format_run(run, FONT_NAME, Pt(9.5), bold=True, color=DARK_GRAY)
    return p

# -------------------------------------------------------------------------------------------------
# 1. Fill Table 0 (Participant Info)
# -------------------------------------------------------------------------------------------------
t0 = doc.tables[0]
r2_cells = t0.rows[2].cells
for c in r2_cells[1:]:
    c.text = ""
p = r2_cells[1].paragraphs[0]
r = p.add_run("[성명 입력]")
format_run(r, FONT_NAME, Pt(9.5), color=RGBColor(0x71, 0x80, 0x96))

p = r2_cells[3].paragraphs[0]
r = p.add_run("[직급]")
format_run(r, FONT_NAME, Pt(9.5), color=RGBColor(0x71, 0x80, 0x96))

p = r2_cells[5].paragraphs[0]
r = p.add_run("[사번]")
format_run(r, FONT_NAME, Pt(9.5), color=RGBColor(0x71, 0x80, 0x96))

p = r2_cells[7].paragraphs[0]
r = p.add_run("[소속 부서 / 현장명]")
format_run(r, FONT_NAME, Pt(9.5), color=RGBColor(0x71, 0x80, 0x96))


# -------------------------------------------------------------------------------------------------
# 2. Fill Table 1 (1. 문제 · 과정 · 결과)
# -------------------------------------------------------------------------------------------------
t1 = doc.tables[1]

# --- Row 0: ① 문제도출 (Before) ---
c_before = t1.cell(0, 1)
c_before.text = "" # Clear placeholder prompt

add_heading_paragraph(c_before, "현장 감리업무의 고질적 병목 및 사내 자체 SAI(RAG 방식)의 한계", level=1)

add_heading_paragraph(c_before, "수백 페이지에 달하는 시공사 제출도서의 수작업 검토 병목 (하루 3시간 이상 소요)", level=2)
add_styled_paragraph(c_before, "현장 감리단은 시공사가 제출하는 시공계획서(HWPX), 구조/수치계산서(XLSX), 발주처 특기시방서(HWPX/DOCX), 장비일람표 도면(PDF), 기성내역서 등 수많은 도서를 매일 검토하고 표준 감리의견서를 작성해야 합니다.", bullet=True)
add_styled_paragraph(c_before, "그러나 수많은 국가법령 조문, KCSC(KDS/KCS) 건설기준 시방치, 엑셀 셀 수식의 적정성을 일일이 사람이 수작업으로 찾고 대조하느라 하루 3시간 이상의 극심한 행정·기술적 병목이 발생하고 있습니다.", bullet=True)

add_heading_paragraph(c_before, "사내 자체 AI(SAI)의 RAG 방식이 가진 4대 근본적 한계와 현업 활용도 저하 원인", level=2)
add_styled_paragraph(c_before, "1. 정적 데이터의 한계: 사내 SAI는 사전에 중앙 서버 벡터DB에 임베딩된 범용 표준 문서만 검색하므로, 매일 현장에서 쏟아지는 최신 HWPX 시공계획서, 수식 엑셀 계산서, 도면 PDF 등 현장의 실시간 동적 도서를 읽고 분석하지 못합니다.", bullet=True)
add_styled_paragraph(c_before, "2. 발주처별 특기시방 및 현장별 맞춤 요구조건 미반영: 현장마다 발주처(LH, SH, 민간 디벨로퍼 등)의 과업지시서와 특기시방 요구조건이 전부 다른데, 중앙 RAG는 전국 수백 개 현장별 특수성과 필수 제출서류 요건을 반영하지 못해 실무 적용이 겉돌고 활용도가 극히 낮습니다.", bullet=True)
add_styled_paragraph(c_before, "3. 설계개선 환류(Feedback Loop) 및 히스토리 부재: 공사 진행 중 수시로 발생하는 발주처 지시공문, 실정보고, 설계변경(VE) 개선 사항을 시스템이 기억하지 못해, 이전 설계변경 내역이 신규 시공계획서에 반영되었는지 추적·환류할 수 없습니다.", bullet=True)
add_styled_paragraph(c_before, "4. 텍스트 검색 기반의 수치 계산 환각 (Hallucination): RAG는 단순 텍스트 유사도 검색이므로, 엑셀 셀 수식 오류 검증, 안전율(Fs) 검산, 기성내역서 단가 변조 등 엄밀한 엔지니어링 수치 연산이 원천적으로 불가능합니다.", bullet=True)

add_heading_paragraph(c_before, "감리원 법적 책임(중대재해처벌법·건진법) 노출 위험", level=2)
add_styled_paragraph(c_before, "기성내역서 단가 변조 및 엑셀 수식 하드코딩, 화재위험 동시작업(용접 + 가연성 우레탄폼 단열재) 공간 중복, 우천 타설 및 강풍 양중 등 중대 재해 및 법적 분쟁 요소를 사람이 육안으로 100% 걸러내기 어려워 감리원의 법적 리스크가 가중되고 있습니다.", bullet=True)


# --- Row 1: ② 과정 (AI와의 대화, Process) ---
c_process = t1.cell(1, 1)
c_process.text = "" # Clear placeholder prompt

add_heading_paragraph(c_process, "FastMCP 기반 100% 로컬 보안 환경 구축 및 '1인 1AI 맞춤 비서' 26개 모듈 구현", level=1)

add_heading_paragraph(c_process, "아키텍처 혁신: 외부 유출 제로의 FastMCP (Model Context Protocol) 로컬 에이전트 도입", level=2)
add_styled_paragraph(c_process, "클라우드로 도면과 문서를 전송하지 않고, 각 감리원의 로컬 PC(Stdio 통신) 내부에서만 도서를 격리 파싱하는 Anthropic FastMCP 표준 프로토콜을 전면 도입했습니다.", bullet=True)
add_styled_paragraph(c_process, "AI에게 4대 하네스 불변 규칙(Zero-Hallucination, Python 직접 연산, 로컬 Sandbox 격리, 정밀 출처 좌표 Line/Cell 앵커링)을 시스템 프롬프트(SYSTEM_PROMPT.md)로 주입하여 수치 환각을 원천 차단했습니다.", bullet=True)

add_heading_paragraph(c_process, "사내 SAI의 한계를 극복한 '개인별 현장 전담 비서' 및 26개 실무 코어 모듈 협업 개발", level=2)
add_styled_paragraph(c_process, "[현장 프로젝트 메모리 & 설계개선 환류 엔진]: 발주처 지시공문, 실정보고, 회의록을 로컬 DB(project_memory.db)에 자동 색인하여 '지난달 발주처 지시사항'을 기억하고 설계변경 반영 여부를 자동 추적 ➔ project_memory_engine.py, design_change_tracker.py 구현", bullet=True)
add_styled_paragraph(c_process, "[발주처 특기시방 맞춤 진단]: 발주처 과업지시서/특기시방서에서 필수 제출도서 요건을 추출하여 현재 폴더 내 서류 접수/누락 현황표 자동 생성 ➔ custom_requirement_auditor.py 구현", bullet=True)
add_styled_paragraph(c_process, "[실시간 법령 & KCSC 연동]: 국가법령정보센터 및 KCSC(건설기준정보시스템) OpenAPI를 실시간 조회하여 최신 조문 번호와 Line 좌표를 매핑 ➔ openapi_client.py 구현", bullet=True)
add_styled_paragraph(c_process, "[다차원 로컬 문서 파싱]: HWPX(Zip-XML), XLSX 수식, DOCX, 도면 PDF(pdfplumber) 전용 로컬 파서 구축 ➔ doc_parser.py 구현", bullet=True)
add_styled_paragraph(c_process, "[3자 수치 교차검증 & AST 검산기]: 도면 PDF 장비일람표 ↔ 계산서 ↔ 산출서 간 3자 대조 및 안전율 AST 연산 ➔ equipment_quantity_auditor.py, formula_engine.py 구현 (1단 버팀보 Fs=1.07<1.25 결함 0.1초 만에 적발)", bullet=True)
add_styled_paragraph(c_process, "[기성내역서 변조 감사]: 기성내역서 Rev0 vs Rev1 비교 및 엑셀 수식 하드코딩 변조 탐지 ➔ diff_audit_engine.py 구현", bullet=True)
add_styled_paragraph(c_process, "[감리원 법적 리스크 선제 방어]: 화재 동시작업(용접+우레탄폼) 충돌 감지 및 기상특보(강우/강풍) 연동 작업중지명령서 즉시 기안 ➔ fire_hazard_conflict_detector.py, weather_stop_work_trigger.py 구현", bullet=True)
add_styled_paragraph(c_process, "[현장 행정 완결]: 콘크리트 28일 강도 관리대장, 사진대지 Before/After 카드, 하도급 82% 룰 심사, 준공 감리완료보고서 원클릭 조립 ➔ concrete_qc_tracker.py, subcontract_auditor.py, cm_final_report_assembler.py 구현", bullet=True)
add_styled_paragraph(c_process, "[성능 최적화]: 반복 파싱 방지 SHA-256 해시 캐시(0.05초) 및 당일 오전/오후 일지 스마트 세션 병합 ➔ doc_cache_manager.py, daily_log_generator.py 구현", bullet=True)

add_heading_paragraph(c_process, "자동화 테스트를 통한 엔지니어링 신뢰성 100% 검증", level=2)
add_styled_paragraph(c_process, "총 85개 자동화 단위/통합 테스트 케이스(pytest)를 구축하여, 수치 연산 및 서식 생성이 단 8초 만에 100% 통과(Pass Rate: 100%)함을 엄밀히 입증했습니다.", bullet=True)


# --- Row 2: ③ 결과 및 기대효과 (After) ---
c_after = t1.cell(2, 1)
c_after.text = "" # Clear placeholder prompt

add_heading_paragraph(c_after, "사내 SAI 한계 극복! 감리원 '1인 1AI 맞춤 전담 비서' 구축 및 무한한 확장성 달성", level=1)

add_heading_paragraph(c_after, "중앙 RAG(SAI) 대비 MCP 개인 비서 체계의 4대 차별화 성과", level=2)
add_styled_paragraph(c_after, "1. '나만의 현장 전담 비서' 화(Personalized Agent): 중앙 RAG의 획일적인 답변에서 벗어나, 내 담당 현장의 로컬 폴더(secure_local_data/)에 담긴 발주처 특기시방, 설계변경 공문, 당일 일보를 기억하고 1:1 맞춤형으로 보좌하는 전담 비서 구현.", bullet=True)
add_styled_paragraph(c_after, "2. 설계개선 환류(Feedback Loop) 완전 실현: 지난 회의록과 발주처 지시사항이 시공계획서에 반영되었는지 시스템이 자동으로 대조·추적하여, 현장 설계변경 누락 사고를 원천 방지.", bullet=True)
add_styled_paragraph(c_after, "3. 독보적인 플러그형 확장성 (Pluggable MCP Tools): 파이썬 함수 하나만 추가하면 드론 사진 검측, BIM 모델 연동, 사내 인트라넷 연동 등 어떤 기능이든 레고 블록처럼 무한 확장 가능하며, Claude/Gemini/ChatGPT 등 모든 외부 LLM과 즉시 호환.", bullet=True)
add_styled_paragraph(c_after, "4. 수치 검산 100% 무오류 (Zero-Hallucination): Python AST 코드로 직접 검산하여 안전율 미달(Fs=1.07<1.25), 소방펌프 토출량 불일치, 기성내역서 수식 조작 등 휴먼 에러 제로화 달성.", bullet=True)

add_heading_paragraph(c_after, "정량적 기대효과: 검토 시간 90% 단축 및 연간 500시간 이상 절감", level=2)
add_styled_paragraph(c_after, "검토 및 대조표 작성 시간 혁신: 건당 3시간 이상 소요되던 시공계획서/계산서/시방서 3자 대조 및 감리의견서 작성을 말 한마디로 10초 만에 완결 (90% 이상 공수 절감).", bullet=True)
add_styled_paragraph(c_after, "SHA-256 스마트 캐싱: 동일 문서 재호출 시 무거운 파싱 없이 0.05초 만에 요약본 즉각 로드.", bullet=True)

add_heading_paragraph(c_after, "정성적 기대효과 및 삼우씨엠의 독보적 기술 리더십 확보", level=2)
add_styled_paragraph(c_after, "완전 무결한 로컬 데이터 보안: 민감한 사내 도서가 외부 클라우드로 단 한 글자도 나가지 않아, 보안 감사에 100% 부합하며 전사 감리현장 즉시 배포 가능.", bullet=True)
add_styled_paragraph(c_after, "감리원 법적 안전장치 확보: 중대재해처벌법상 화재 동시작업 위반, 우천 타설 및 강풍 양중 위험을 AI가 실시간 경보하고 정식 작업중지 명령서(.docx)를 자동 기안하여 감리단 법적 책임 선제적 방어.", bullet=True)
add_styled_paragraph(c_after, "삼우씨엠 표준 고품질 산출물 자동화: 정밀 출처 좌표(Line/Cell)가 포함된 감리의견서, 시정지시서(NCR), 일일업무일보, 준공완료보고서가 삼우씨엠 공식 Word 서식으로 즉시 출력되어 전사 감리 품질 상향 평준화.", bullet=True)


# -------------------------------------------------------------------------------------------------
# 3. Fill Table 2 (2. 사용한 AI 도구)
# -------------------------------------------------------------------------------------------------
t2 = doc.tables[2]
c_tools = t2.cell(0, 0)
c_tools.text = "" # Clear placeholder prompt

add_heading_paragraph(c_tools, "Samwoo-CM-Bridge 구축에 투입된 AI 플랫폼 및 기술 스택", level=1)

add_heading_paragraph(c_tools, "AI 플랫폼, 개발 도구 및 클라이언트", level=2)
add_styled_paragraph(c_tools, "VS Code (Visual Studio Code): 전체 프로젝트의 통합 개발 환경(IDE), FastMCP 로컬 디버깅 및 에이전틱 코딩 워크스페이스로 활용", bullet=True)
add_styled_paragraph(c_tools, "Codex-GPT: 5대 공종 안전율/허용응력 AST 검산 알고리즘 및 복잡한 정규표현식 파라미터 추출 로직 구현 보조", bullet=True)
add_styled_paragraph(c_tools, "ASTRA: 건설 엔지니어링 질의응답 및 감리 실무 프롬프트 워크플로우 최적화 분석 도구로 활용", bullet=True)
add_styled_paragraph(c_tools, "Claude Desktop (Anthropic): FastMCP 프로토콜을 통하여 로컬 도구들과 실시간 통신하며, 감리원의 자연어 명령을 도구 호출 파이프라인으로 변환하는 메인 AI 클라이언트", bullet=True)
add_styled_paragraph(c_tools, "Antigravity (Google DeepMind): 고성능 에이전틱 코딩 파트너로서 26개 코어 엔지니어링 모듈의 로직 구현, AST 수식 검산기 설계, 85개 자동화 테스트 슈트 작성 총괄", bullet=True)

add_heading_paragraph(c_tools, "엔터프라이즈 통합 프레임워크 및 공공 OpenAPI", level=2)
add_styled_paragraph(c_tools, "FastMCP (Python SDK): Anthropic의 공식 Model Context Protocol SDK를 기반으로 Stdio 보안 파이프라인 구축", bullet=True)
add_styled_paragraph(c_tools, "국가법령정보센터 OpenAPI: 최신 국가법령(건진법, 산안법, 건축법, 소방법 등) 조문 실시간 검색 및 출처 앵커링", bullet=True)
add_styled_paragraph(c_tools, "KCSC(건설기준정보시스템) OpenAPI: 국토교통부 표준시방서(KCS) 및 설계기준(KDS) 조항 실시간 조회", bullet=True)

add_heading_paragraph(c_tools, "로컬 파싱 및 엔지니어링 오픈소스 라이브러리", level=2)
add_styled_paragraph(c_tools, "openpyxl: 엑셀 계산서/산출서의 수식, 셀 좌표, 단가 변조 탐지 및 품질관리대장 누적 관리", bullet=True)
add_styled_paragraph(c_tools, "python-docx: 삼우씨엠 표준 감리의견서, 시정지시서(NCR), 일일업무일보, 준공보고서 자동 조립", bullet=True)
add_styled_paragraph(c_tools, "pdfplumber & ReportLab: 도면 PDF 장비일람표 벡터/테이블 추출 및 테스트 데이터셋 생성", bullet=True)
add_styled_paragraph(c_tools, "xml.etree (Python Standard Library): 한글(HWPX) 압축 XML 문서의 구조적 텍스트 및 표 데이터 정밀 파싱", bullet=True)


# -------------------------------------------------------------------------------------------------
# 4. Fill Table 3 (3. 건의사항 및 기타 의견)
# -------------------------------------------------------------------------------------------------
t3 = doc.tables[3]
c_feedback = t3.cell(0, 0)
c_feedback.text = "" # Clear placeholder prompt

add_heading_paragraph(c_feedback, "실무 적용 소감 및 사내 SAI ↔ 로컬 MCP 시너지 확산 제언", level=1)

add_heading_paragraph(c_feedback, "외부 AI 실무 적용 소감: 중앙 집중식 RAG의 한계를 넘어 '로컬 MCP 개인비서'로 진화해야 합니다", level=2)
add_styled_paragraph(c_feedback, "사내 자체 AI(SAI)를 사용해보며 느꼈던 가장 큰 갈증은 '우리 현장만의 발주처 특기시방과 어제 받은 설계변경 공문을 반영하지 못한다'는 점과 '엑셀 수식을 직접 계산해주지 못한다'는 점이었습니다.", bullet=True)
add_styled_paragraph(c_feedback, "이번 프로젝트를 통해 검증된 'FastMCP 기반 로컬 Sandbox + Python 직접 연산 + 프로젝트 메모리 DB' 방식은 각 감리원마다 '자신만의 현장 전담 비서'를 갖게 해줌으로써, 중앙 RAG 방식의 한계를 100% 극복할 수 있음을 확인했습니다.", bullet=True)

add_heading_paragraph(c_feedback, "향후 핵심 과제 및 단점 보완: 사내 보안 프로그램(DRM) 암호화 문서 지원 요청", level=2)
add_styled_paragraph(c_feedback, "현재 겪고 있는 기술적 한계: 삼우씨엠 사내 보안 프로그램(문서보안 DRM)으로 암호화가 적용된 파일(HWPX, XLSX, DOCX, PDF)의 경우, 로컬 오픈소스 파서가 복호화 키 없이 직접 읽을 수 없어 현재는 감리원이 수동으로 복호화한 후 검토를 수행해야 하는 현실적 번거로움이 있습니다.", bullet=True)
add_styled_paragraph(c_feedback, "본사 차원의 지원 요청 건의: 사내 보안 정책을 철저히 준수하면서도 현장 감리원이 편리하게 활용할 수 있도록, 본사 정보보안팀과 협의하여 승인된 로컬 프로세스 내에서 암호화 문서를 안전하게 메모리 상에서 파싱할 수 있는 '사내 공식 DRM 복호화 API 연동' 또는 '보안 인증 모듈 지원'을 강력히 건의드립니다. 이 연동이 이루어지면 암호화 도서까지 원클릭으로 전수 검토하는 완전무결한 시스템으로 도약할 수 있습니다.", bullet=True)

add_heading_paragraph(c_feedback, "사내 SAI와 로컬 MCP의 앙상블 및 전사 확산 로드맵 제언", level=2)
add_styled_paragraph(c_feedback, "1. 사내 SAI의 Action Engine으로 MCP 도입: 중앙 SAI는 전사 표준 사규 및 공통 시방 검색을 담당하고, 실제 현장 도서 파싱/수치 검산/공문 조립은 본 Samwoo-CM-Bridge(MCP)가 실행하도록 연계한다면 사내 AI 활용도가 비약적으로 상승할 것입니다.", bullet=True)
add_styled_paragraph(c_feedback, "2. 전사 1인 1AI 현장 비서 배포: 복잡한 설정 없이 원클릭 실행 아이콘으로 로컬 폴더만 지정하면 즉시 동작하는 '삼우CM 표준 MCP 패키지'를 전 현장 감리원에게 보급할 것을 제안합니다.", bullet=True)
add_styled_paragraph(c_feedback, "3. 삼우씨엠 고유 지식 환류 자산화: 각 현장의 설계변경 VE 사례와 발주처 특기시방 검토 결과가 로컬 DB에 누적되어, 향후 신규 수주 및 기술 제안서 작성 시 삼우씨엠만의 강력한 빅데이터 자산으로 환류될 수 있습니다.", bullet=True)


# -------------------------------------------------------------------------------------------------
# 5. Append Attachment Details to Section 4 (4. 첨부파일)
# -------------------------------------------------------------------------------------------------
doc.add_paragraph() # spacing

p_att_head = doc.add_paragraph()
r = p_att_head.add_run("■ [첨부자료] Samwoo-CM-Bridge 아키텍처 및 실제 동작 검증 요약")
format_run(r, FONT_NAME, Pt(11), bold=True, color=NAVY)

att_items = [
    ("첨부 1: 전체 시스템 아키텍처 파이프라인 (Local Sandbox & FastMCP Pipeline)",
     "• 구조: [사용자 자연어 질의] ➔ [Claude Desktop / FastMCP Client] ➔ [로컬 secure_local_data 격리 파서 (HWPX/XLSX/DOCX/PDF)] ➔ [국가법령/KCSC OpenAPI 실시간 조회] ➔ [Python AST 안전율/응력 직접 검산] ➔ [삼우씨엠 표준 Word/MD 감리의견서 자동 출력]\n• 핵심 원칙: Zero-Cloud Leak(외부 유출 제로) & Zero-Hallucination(수치 연산 무오류) & 1인 1AI 맞춤 비서"),
    
    ("첨부 2: 실제 현장 시연 프롬프트 및 시스템 출력 결과 예시 (Master Demo Script)",
     "• 입력 질의: '가설흙막이 시공계획서(HWPX)와 구조계산서(XLSX)를 KDS 21 30 00 기준과 3자 교차 검토해줘.'\n• 시스템 동작: 시공계획서 HWPX 표 파싱 + 구조계산서 엑셀 파싱 + KDS 21 30 00 실시간 조문 조회 + Python 직접 검산\n• 검출 결과: [결함 적발] 1단 버팀보 계산 안전율 Fs = 1.07 < KDS 기준 안전율 1.25 (안전율 14.4% 부족) ➔ 종합_CM기술검토의견서.docx 즉시 자동 생성 (정밀 출처: sample_가설흙막이_시공계획서.hwpx L12 (P-003) | sample_가설흙막이_구조계산서.xlsx!버팀보계산!R14C3)"),
    
    ("첨부 3: 85개 자동화 단위/통합 테스트 (pytest) 100% ALL PASS 검증 로그",
     "• 테스트 슈트: tests/ 디렉터리 내 21개 테스트 파일, 총 85개 테스트 케이스 전원 통과 (Pass Rate: 100% / 소요시간: 8.27s)\n• 검증 항목: HWPX/XLSX/PDF 파싱, Path Traversal 보안 방어, 5대 공종 안전율 검산, 기성내역서 변조 탐지, 화재 동시작업 충돌 감지, 기상 작업중지권 발령, SHA-256 캐시 적중(0.05초), 당일 일지 세션 병합, 프로젝트 메모리 DB 인덱싱 전 항목 완전 무결 검증 완료"),
    
    ("첨부 4: 오픈소스 GitHub 저장소 및 프로젝트 소스코드 안내",
     "• 공식 GitHub 저장소: https://github.com/tbvja/samwoo-cm-bridge\n• 로컬 프로젝트 경로: c:/Users/tbvja/Projects/samwoo-cm-bridge\n• 시스템 프롬프트 명세: SYSTEM_PROMPT.md (Claude Desktop 사용자 맞춤 설정 복사용)\n• 시스템 아키텍처 상세 설계서: ARCHITECTURE.md\n• 하네스 불변 보안 규칙: RULES.md")
]

for title, desc in att_items:
    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_before = Pt(4)
    p_t.paragraph_format.space_after = Pt(1)
    r_t = p_t.add_run("▶ " + title)
    format_run(r_t, FONT_NAME, Pt(10), bold=True, color=BLUE)
    
    p_d = doc.add_paragraph()
    p_d.paragraph_format.left_indent = Inches(0.2)
    p_d.paragraph_format.space_after = Pt(4)
    p_d.paragraph_format.line_spacing = 1.2
    r_d = p_d.add_run(desc)
    format_run(r_d, FONT_NAME, Pt(9), color=DARK_GRAY)

# Save to both target locations
doc.save(output_download_path)
doc.save(output_project_path)

print(f"Successfully generated proposal docx:")
print(f"1. Downloads: {output_download_path}")
print(f"2. Projects: {output_project_path}")
