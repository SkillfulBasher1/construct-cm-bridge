# Construct-CM-Bridge (Construct-MCP-Korea)

> **건설사업관리(CM) 외부 AI 실무 연동 및 업무 자동화 오픈 프레임워크**  
> **실시간 국가법령·KCSC 건설기준 연동 및 HWPX/도면 3자 수치 교차검증 기반 FastMCP 엔진**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 85 Passed](https://img.shields.io/badge/Tests-85%20Passed%20(100%25)-success.svg)](tests/)

---

## 📌 프로젝트 소개 (Introduction)

**Construct-CM-Bridge**는 건설사업관리(CM) 현장 감리단의 제출도서(시공계획서, 구조/수치계산서, 발주처 특기시방서, 기성내역서 등)를 로컬 격리 환경에서 안전하게 파싱하고, 공식 국가법령(법제처) 및 KCSC 건설기준(국토부)과 대조하여 3자 수치 교차 검증을 수행하는 오픈소스 FastMCP 서버입니다.

기존 중앙 집중형 사내 AI(RAG 방식)가 해결하지 못했던 **"현장별 발주처 특기시방 미반영", "빈번한 현장 설계변경 추적 부재", "엑셀 수식 및 역학 계산 불가(LLM 텍스트 환각)"** 문제를 극복하여, 각 현장 기술인 개개인을 보좌하는 **1:1 맞춤형 전담 비서(Personalized CM Agent)** 체계를 제공합니다.

> **안내**: 자동 생성 결과는 근거 발견(Source Anchoring)과 산술 선별을 제공하는 **검토 초안**이며, 승인·법적 적합 판정은 책임기술인의 원문 및 현장 확인이 필요합니다.

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

4. **CM 표준 감리/기술검토의견서 자동 생성**
   - 근거 대조표와 검산 상세를 포함한 `.docx` 및 `.md` 검토 초안 생성. 입력 근거가 없으면 `REVIEW_REQUIRED`로 표시.

5. **기존 사내 AI 시스템(FastAPI/RAG) 즉시 이식성**
   - 코어 모듈(`core/`)이 FastMCP와 완전히 분리되어 있어 사내 FastAPI 백엔드에 코드 수정 없이 Action Engine으로 바로 이식 가능.

6. **팬텀 문서 및 허위 근거 차단 하네스 (Anti-Phantom & Direct-Quote Protocol)**
   - **실존 디렉터리 검증 선행(Fail-Closed)**: `list_secure_local_files`로 실제 파일 실존이 확인되지 않으면 검토 착수 및 가상 파일 상상 원천 금지.
   - **원문 20자 이상 직인용(Verbatim Quote)**: 임의로 조항 번호나 수치를 날조하지 못하도록 파싱된 원문 문장을 큰따옴표(`"..."`)로 직접 인용한 근거만 유효 처리.
   - **근거 부재 공식 인정**: 원문에 근거가 없으면 지어내지 않고 `NO_EVIDENCE_FOUND` 및 `REVIEW_REQUIRED`로 정직하게 종결.

---

## 📂 프로젝트 디렉토리 구조

```
construct-cm-bridge/
├── pyproject.toml                     # 프로젝트 종속성 및 메타데이터
├── requirements.txt                   # pip 설치용 종속성 목록
├── README.md                          # 프로젝트 안내서
├── ARCHITECTURE.md                    # 제안서용 상세 아키텍처 다이어그램 및 시퀀스
├── SYSTEM_PROMPT.md                   # AI 클라이언트용 시스템 프롬프트 명세
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
├── src/construct_cm_bridge/
│   ├── cli.py                         # CLI 도구 (serve, list, parse, check-bundle, law, kcsc, demo)
│   ├── server.py                      # FastMCP 서버 및 31개 도구 정의
│   ├── core/                          # 독립 코어 라이브러리 (사내 AI 이식용)
│   │   ├── openapi_client.py          # 국가법령정보 & KCSC API 연동
│   │   ├── doc_parser.py              # HWPX, XLSX, DOCX, PDF 파서
│   │   ├── batch_cross_checker.py     # 다중 도서 일괄 교차 검토 및 불일치 전수검사기
│   │   ├── formula_engine.py          # 5대 분야별 공식 레지스트리 및 AST 검산기
│   │   └── docx_exporter.py           # CM 표준 서식 Word/MD 생성기
│   └── data_cache/                    # 오프라인/Fallback 데이터셋
└── tests/                             # 단위 및 E2E 테스트 슈트
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 설정 및 종속성 설치
```bash
git clone https://github.com/SkillfulBasher1/construct-cm-bridge.git
cd construct-cm-bridge

pip install -r requirements.txt
```

실시간 조회를 사용하려면 `LAW_API_OC`와 `KCSC_API_KEY`를 설정합니다. 미설정 시 로컬 샘플 데이터만 사용합니다.

### 2. 다중 제출도서 일괄 교차 전수검사 (Batch Cross-Check)
```bash
python -m construct_cm_bridge.cli check-bundle sample_과업지시서_특기시방.hwpx sample_가설흙막이_구조계산서.xlsx
```

### 3. 종합 데모(3대 시나리오 교차 검토 및 감리의견서 생성) 실행
```bash
python -m construct_cm_bridge.cli demo
```

### 4. CLI 개별 기능 테스트
```bash
# 로컬 보안 폴더 파일 목록 조회
python -m construct_cm_bridge.cli list

# HWPX 문서 파싱
python -m construct_cm_bridge.cli parse sample_과업지시서_특기시방.hwpx

# 국가법령 검색
python -m construct_cm_bridge.cli law "건설기술 진흥법" --article 62

# KCSC 건설기준 검색
python -m construct_cm_bridge.cli kcsc "KDS 21 30 00"
```

---

## 💬 AI Agent 대화형 자연어 연동 안내 (Natural Language Prompts)

현장 감리원이나 일반 사용자는 복잡한 CLI 명령어나 설정 파일을 다룰 필요 없이, **AI Agent(Claude, Cursor, 사내 AI 등) 채팅창에 평소 말하듯 자연어로 명령**하여 API를 연결하고 로컬 문서를 검토할 수 있습니다.

### 1. 외부 공인 API 연결 명령
> **사용자 프롬프트**:  
> *"GitHub(`SkillfulBasher1/construct-cm-bridge`)에 있는 국가법령정보센터 및 KCSC 건설기준 API를 연결해줘."*

* **AI Agent 동작**:
  * GitHub 저장소의 표준 MCP 명세(`server.py`) 및 공인 API 클라이언트를 호출 가능한 도구로 자동 인식.
  * 최신 법제처 법령 및 국토부 KDS/KCS 건설기준을 실시간 질의·검색할 수 있는 상태로 즉시 활성화합니다.

---

### 2. 로컬 문서 검토 폴더 지정 및 교차 검토 명령
> **사용자 프롬프트**:  
> *"내 PC의 `secure_local_data/`(현장도서 폴더)를 지정해서, 이번에 시공사가 제출한 시공계획서(HWPX)와 구조계산서(XLSX)를 읽고 KDS 기준과 교차 검토해줘."*

* **AI Agent 동작**:
  * 지정된 로컬 격리 폴더(`secure_local_data/`) 내 HWPX(표/본문), XLSX(수식/수치) 파일을 로컬에서 안전하게 파싱 (외부 서버 전송 Zero).
  * KDS 기준과 특기시방서 요구조건을 대조 검증하고, 오차나 위반 사항을 정리한 **표준 4단 대비표(검토항목 | 법령·기준 | 시방서 | 시공사제출값 | 판정) 형태의 감리의견서 초안**을 자동 작성합니다.

---

### 3. 실무 대표 대화 시나리오 예시
```text
[사용자] "construct-cm-bridge API 연결하고, 현장 폴더의 'sample_과업지시서_특기시방.hwpx'와 'sample_가설흙막이_구조계산서.xlsx' 읽어서 버팀보 좌굴 안전율 검산해줘."

[AI Agent]
1. 국가건설기준 KDS 21 30 00 API 실시간 조회 (기준 안전율: 1.50 이상)
2. 로컬 HWPX 시방서 파싱: 발주처 특기시방 안전율 규정 확인 (F.S = 1.60)
3. 로컬 XLSX 구조계산서 파싱 및 AST 수치 검산: 산출 안전율 1.35 감지
4. 결과: [부적합 판정] - 발주처 시방(1.60) 및 KDS 기준(1.50) 미달 상세 4단 대비표 및 조치요구서 초안 자동 출력
```

---

## 🔌 MCP 클라이언트 연동 (Claude Desktop / Cursor / Antigravity)

AI Agent가 위의 자연어 명령을 도구 호출(Tool Calling)로 수행할 수 있도록 클라이언트 설정에 등록합니다.

### Claude Desktop 연동
`%APPDATA%\Claude\claude_desktop_config.json`에 다음 설정을 추가합니다:

```json
{
  "mcpServers": {
    "construct-cm-bridge": {
      "command": "python",
      "args": [
        "-m",
        "construct_cm_bridge.cli",
        "serve"
      ],
      "env": {
        "PYTHONPATH": "c:\\Projects\\construct-cm-bridge\\src"
      }
    }
  }
}
```

### Cursor / VS Code 연동 (`mcp_configs/cursor_mcp_config.json`)
```json
{
  "mcpServers": {
    "construct-cm-bridge": {
      "command": "python",
      "args": ["-m", "construct_cm_bridge.cli", "serve"]
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
MIT License. Copyright (c) 2026 Construct-CM-Bridge Contributors.
