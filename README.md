# Samwoo-CM-Bridge (Construct-MCP-Korea)

> **삼우씨엠 사내 AI 활용 아이디어 공모전 [Track 2] 외부 AI 활용 아이디어 부문**
> **실시간 법령·KCSC 연동 및 HWPX 파싱 기반 CM 3자 교차 검토 FastMCP 엔진**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 프로젝트 소개 (Introduction)

**Samwoo-CM-Bridge**는 건설사업관리(CM) 제출도서를 로컬에서 파싱하고, 공식 법령·KCSC 조회 결과 및 사용자가 입력한 기준값과 교차 검토하는 FastMCP 서버입니다. 자동 생성 결과는 근거 발견과 산술 선별을 제공하는 **검토 초안**이며, 승인·법적 적합 판정은 책임기술인의 원문 및 현장 확인이 필요합니다.

---

## 🌟 주요 특징 (Key Features)

1. **실시간 국가법령 및 KCSC 건설기준 연동 (Module 1)**
   - 국가법령정보센터(`law.go.kr`) 및 국가건설기준센터(`kcsc.re.kr`) 실시간 REST API 연동.
   - API 자격증명이 없거나 조회에 실패하면 번들된 오프라인 샘플을 사용하고, 응답의 `source` 필드로 실시간/로컬 출처를 구분.

2. **로컬 격리 샌드박스 & HWPX 다차원 문서 파서 (Module 2)**
   - 사내 민감 도면·시방 데이터 외부 유출 제로 (`secure_local_data/` 격리).
   - **HWPX(한글 표준 XML)** 내 본문 단락 및 `hp:tbl` 표 데이터를 마크다운 표로 구조화 파싱.
   - Excel(`.xlsx`, `.xlsm`), Word(`.docx`), PowerPoint(`.pptx`), PDF(`.pdf`), HWPX, TXT/MD/JSON 텍스트 추출 지원.

3. **5대 공종 다분야 수치 검산 엔진 (Module 3)**
   - **토목/구조**: 일반 허용치 안전율, 버팀보 좌굴 안전율, 그라운드앵커 인장 안전율.
   - **기계/설비**: 펌프 양정 여유율, 필요 환기량.
   - **소방**: 옥내소화전 유효저수량, 스프링클러 헤드 토출량($K\sqrt{10P}$).
   - **전기/통신**: 3상 선로 전압강하율, 변압기 부하율.
   - **건축**: 외벽 열관류율($U$-value).
   - Python AST 기반 안전 커스텀 수식 검산 지원.

4. **삼우씨엠 표준 감리/CM 검토의견서 자동 생성**
   - 근거 대조표와 검산 상세를 포함한 `.docx` 및 `.md` 검토 초안 생성. 입력 근거가 없으면 `REVIEW_REQUIRED`로 표시.

5. **사내 AI(SAI) 시스템 즉시 이식성**
   - 코어 모듈(`core/`)이 FastMCP와 완전히 분리되어 있어 사내 FastAPI 백엔드에 코드 수정 없이 바로 이식 가능.

---

## 📂 프로젝트 디렉토리 구조

```
samwoo-cm-bridge/
├── pyproject.toml                     # 프로젝트 종속성 및 메타데이터
├── requirements.txt                   # pip 설치용 종속성 목록
├── README.md                          # 프로젝트 안내서
├── ARCHITECTURE.md                    # 제안서용 상세 아키텍처 다이어그램 및 시퀀스
├── RULES.md                           # Zero-Hallucination 하네스 룰
├── mcp_configs/                       # MCP 클라이언트 연동 설정 스니펫
│   ├── claude_desktop_config.json
│   ├── cursor_mcp_config.json
│   └── antigravity_mcp_config.json
├── secure_local_data/                 # 로컬 보안 격리 폴더 (샘플 입력 및 출력 리포트)
│   ├── sample_과업지시서_특기시방.hwpx
│   ├── sample_가설흙막이_구조계산서.xlsx
│   ├── sample_소방_소화수조및펌프계산서.xlsx
│   ├── sample_전기_전압강하및변압기계산서.xlsx
│   └── sample_건축_단열및시공계획서.docx
├── src/samwoo_cm_bridge/
│   ├── cli.py                         # CLI 도구 (serve, list, parse, check-bundle, law, kcsc, demo)
│   ├── server.py                      # FastMCP 서버 및 31개 도구 정의
│   ├── core/                          # 독립 코어 라이브러리 (SAI 이식용)
│   │   ├── openapi_client.py          # 국가법령정보 & KCSC API 연동
│   │   ├── doc_parser.py              # HWPX, XLSX, DOCX, PDF 파서
│   │   ├── batch_cross_checker.py     # 다중 도서 일괄 교차 검토 및 불일치 전수검사기
│   │   ├── formula_engine.py          # 5대 분야별 공식 레지스트리 및 AST 검산기
│   │   └── docx_exporter.py           # 삼우씨엠 표준 서식 Word/MD 생성기
│   └── data_cache/                    # 오프라인/Fallback 데이터셋
└── tests/                             # 단위 및 E2E 테스트 슈트
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 설정 및 종속성 설치
```bash
git clone https://github.com/samwoo-cm/samwoo-cm-bridge.git
cd samwoo-cm-bridge

pip install -r requirements.txt
```

실시간 조회를 사용하려면 `LAW_API_OC`와 `KCSC_API_KEY`를 설정합니다. 미설정 시 로컬 샘플 데이터만 사용합니다. 보안 데이터 폴더는 `SAMWOO_DATA_DIR`로 변경할 수 있습니다.

### 2. 다중 제출도서 일괄 교차 전수검사 (Batch Cross-Check)
```bash
python -m samwoo_cm_bridge.cli check-bundle sample_과업지시서_특기시방.hwpx sample_가설흙막이_구조계산서.xlsx
```

### 3. 종합 데모(3대 시나리오 교차 검토 및 감리의견서 생성) 실행
```bash
python -m samwoo_cm_bridge.cli demo
```

### 4. CLI 개별 기능 테스트
```bash
# 로컬 보안 폴더 파일 목록 조회
python -m samwoo_cm_bridge.cli list

# HWPX 문서 파싱
python -m samwoo_cm_bridge.cli parse sample_과업지시서_특기시방.hwpx

# 국가법령 검색
python -m samwoo_cm_bridge.cli law "건설기술 진흥법" --article 62

# KCSC 건설기준 검색
python -m samwoo_cm_bridge.cli kcsc "KDS 21 30 00"
```

---

## 🔌 MCP 클라이언트 연동 (Claude Desktop / Cursor)

### Claude Desktop 연동
`%APPDATA%\Claude\claude_desktop_config.json`에 다음 설정을 추가합니다:

```json
{
  "mcpServers": {
    "samwoo-cm-bridge": {
      "command": "python",
      "args": [
        "-m",
        "samwoo_cm_bridge.cli",
        "serve"
      ],
      "env": {
        "PYTHONPATH": "c:\\Users\\tbvja\\Projects\\samwoo-cm-bridge\\src"
      }
    }
  }
}
```

---

## 🧪 테스트 실행

```bash
python -m pytest tests/ -v
```

---

## 📄 License
MIT License. Copyright (c) 2026 Samwoo CM Architecture.
