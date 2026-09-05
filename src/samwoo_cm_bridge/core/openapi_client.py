"""External Legal and KCSC Standards Bridge Module

Connects to:
1. National Law Information Center (국가법령정보센터 / law.go.kr) REST API
2. Korea Construction Standards Center (국가건설기준센터 / kcsc.re.kr) OpenAPI
Provides automatic offline caching and Mock fallback for robust judging and demo execution.
"""

import os
import json
import html
import logging
import re
from defusedxml import ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"


class OpenApiClient:
    """Manages real-time API queries with graceful offline caching and mock fallbacks."""

    def __init__(
        self,
        law_oc: Optional[str] = None,
        kcsc_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        # Read from environment variables if not provided
        self.law_oc = law_oc or os.getenv("LAW_API_OC", "")
        self.kcsc_key = kcsc_key or os.getenv("KCSC_API_KEY", "")
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR

        self._load_local_mocks()

    def _load_local_mocks(self):
        """Loads offline mock/cached standards and laws."""
        self.laws_mock: Dict[str, Any] = {}
        self.kcsc_mock: Dict[str, Any] = {}

        laws_path = self.cache_dir / "laws_mock.json"
        kcsc_path = self.cache_dir / "kcsc_mock.json"

        if laws_path.exists():
            try:
                with open(laws_path, "r", encoding="utf-8") as f:
                    self.laws_mock = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load laws_mock.json: {e}")

        if kcsc_path.exists():
            try:
                with open(kcsc_path, "r", encoding="utf-8") as f:
                    self.kcsc_mock = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load kcsc_mock.json: {e}")

    def fetch_national_law(
        self, law_name: str, article_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches statutory articles from law.go.kr or falls back to local cache.

        Args:
            law_name: Name of the law (e.g. '건설기술 진흥법', '건축법')
            article_no: Specific article number (e.g. '62', '53')

        Returns:
            Dict containing law_name, article_no, title, content, and source (api/cache).
        """
        import requests

        if not isinstance(law_name, str) or not law_name.strip():
            return {
                "status": "ERROR",
                "source": "INPUT_VALIDATION",
                "law_name": "",
                "article_no": str(article_no).strip() if article_no is not None else "-",
                "title": "입력 오류",
                "content": "법령명은 비어 있을 수 없습니다.",
                "source_anchor": "법령명 (미입력)",
            }
        clean_name = law_name.strip()
        article_key = str(article_no).strip() if article_no else None

        # 1. Try real API if OC (User ID/API Key) is provided
        if self.law_oc:
            try:
                url = "https://www.law.go.kr/DRF/lawSearch.do"
                params = {
                    "OC": self.law_oc,
                    "target": "law",
                    "type": "XML",
                    "query": clean_name,
                }
                resp = requests.get(url, params=params, timeout=5)
                resp.raise_for_status()
                search_root = ET.fromstring(resp.content)
                candidates = []
                for law in search_root.findall(".//law"):
                    result_name = (law.findtext("법령명한글") or "").strip()
                    if clean_name == result_name or clean_name in result_name:
                        candidates.append(law)
                if candidates:
                    selected = candidates[0]
                    detail_params = {
                        "OC": self.law_oc,
                        "target": "law",
                        "type": "XML",
                    }
                    mst = (selected.findtext("법령일련번호") or "").strip()
                    law_id = (selected.findtext("법령ID") or "").strip()
                    if mst:
                        detail_params["MST"] = mst
                    elif law_id:
                        detail_params["ID"] = law_id
                    else:
                        raise ValueError("법령 검색 결과에 MST/ID가 없습니다.")
                    if article_key:
                        detail_params["JO"] = self._normalize_article_query(article_key)

                    detail_resp = requests.get(
                        "https://www.law.go.kr/DRF/lawService.do",
                        params=detail_params,
                        timeout=5,
                    )
                    detail_resp.raise_for_status()
                    root = ET.fromstring(detail_resp.content)
                    articles_found = []
                    for article in root.findall(".//조문단위"):
                        curr_no = (article.findtext("조문번호") or "").strip()
                        curr_title = (article.findtext("조문제목") or "").strip()
                        content_tag = article.find("조문내용")
                        curr_content = " ".join("".join(content_tag.itertext()).split()) if content_tag is not None else ""

                        if not article_key or self._article_matches(curr_no, article_key):
                            articles_found.append({
                                "article_no": curr_no,
                                "title": curr_title,
                                "content": curr_content,
                            })

                    if articles_found and article_key:
                        target = articles_found[0]
                        return {
                            "status": "SUCCESS",
                            "source": "REAL_OPENAPI",
                            "law_name": clean_name,
                            "article_no": target["article_no"] or article_key or "전체",
                            "title": target["title"],
                            "content": target["content"],
                            "source_anchor": f"{clean_name} 제{target['article_no'] or article_key}조 (국가법령정보센터)",
                        }
                    if articles_found:
                        all_content = "\n\n".join(
                            f"[제{article['article_no']}조 ({article['title']})]\n{article['content']}"
                            for article in articles_found
                        )
                        return {
                            "status": "SUCCESS",
                            "source": "REAL_OPENAPI",
                            "law_name": clean_name,
                            "article_no": "전체",
                            "title": "관련 조항 모음",
                            "content": all_content,
                            "source_anchor": f"{clean_name} 전문 (국가법령정보센터)",
                        }
            except Exception as e:
                logger.warning(f"Real Law API call failed, switching to local cache: {e}")

        # 2. Offline / Mock fallback
        for stored_law, law_data in self.laws_mock.items():
            if clean_name in stored_law or stored_law in clean_name:
                articles = law_data.get("articles", {})
                if article_key and article_key in articles:
                    art = articles[article_key]
                    law_title = law_data.get("law_name", clean_name)
                    art_no = art.get("article_no", article_key)
                    return {
                        "status": "SUCCESS",
                        "source": "LOCAL_CACHE_FALLBACK",
                        "law_name": law_title,
                        "article_no": art_no,
                        "title": art.get("title", ""),
                        "content": art.get("content", ""),
                        "source_anchor": f"{law_title} 제{art_no}조 ({art.get('title', '')})",
                    }
                elif articles and not article_key:
                    all_content = "\n\n".join(
                        f"[제{v.get('article_no')}조 ({v.get('title')})]\n{v.get('content')}"
                        for v in articles.values()
                    )
                    law_title = law_data.get("law_name", clean_name)
                    return {
                        "status": "SUCCESS",
                        "source": "LOCAL_CACHE_FALLBACK",
                        "law_name": law_title,
                        "article_no": "전체",
                        "title": "관련 조항 모음",
                        "content": all_content,
                        "source_anchor": f"{law_title} 전문",
                    }

        return {
            "status": "NOT_FOUND",
            "source": "LOCAL_CACHE_FALLBACK",
            "law_name": clean_name,
            "article_no": article_key or "-",
            "title": "기준 미확인",
            "content": f"해당 법령({clean_name} 제{article_key or ''}조)의 최신 조문 정보를 찾을 수 없습니다. 법령명을 확인해주세요.",
            "source_anchor": f"{clean_name} (미확인)",
        }

    @staticmethod
    def _normalize_article_query(article_no: str) -> str:
        """Converts '62' or '62의2' into the six-digit JO format used by lawService."""
        match = re.fullmatch(r"\s*(\d{1,4})(?:\s*(?:의|-|\.)\s*(\d{1,2}))?\s*", article_no)
        if not match:
            raise ValueError(f"지원하지 않는 조문 번호 형식: {article_no}")
        return f"{int(match.group(1)):04d}{int(match.group(2) or 0):02d}"

    @staticmethod
    def _article_matches(actual: str, requested: str) -> bool:
        actual_numbers = re.findall(r"\d+", actual)
        requested_numbers = re.findall(r"\d+", requested)
        return actual_numbers[:2] == requested_numbers[:2]

    def fetch_kcsc_standard(self, standard_code: str) -> Dict[str, Any]:
        """Fetches KDS/KCS construction standard specifications.

        Args:
            standard_code: Code of the standard (e.g. 'KDS 21 30 00', 'KCS 14 31 25')

        Returns:
            Dict containing standard_code, standard_name, category, discipline, content, source.
        """
        import requests

        if not isinstance(standard_code, str) or not standard_code.strip():
            return {
                "status": "ERROR",
                "source": "INPUT_VALIDATION",
                "standard_code": "",
                "standard_name": "입력 오류",
                "category": "-",
                "discipline": "-",
                "content": "건설기준 코드는 비어 있을 수 없습니다.",
                "source_anchor": "건설기준 코드 (미입력)",
            }
        clean_code = standard_code.strip().upper()

        # 1. Try real KCSC API if Key is provided
        if self.kcsc_key:
            try:
                code_match = re.fullmatch(r"(KDS|KCS)\s*([0-9\s-]{6,})", clean_code)
                if not code_match:
                    raise ValueError("KCSC 실시간 조회는 KDS/KCS 6자리 코드만 지원합니다.")
                code_type = code_match.group(1)
                compact_code = "".join(re.findall(r"\d", code_match.group(2)))
                if len(compact_code) != 6:
                    raise ValueError("KDS/KCS 코드는 숫자 6자리여야 합니다.")
                url = f"https://www.kcsc.re.kr/OpenApi/CodeViewer/{code_type}/{compact_code}"
                params = {"key": self.kcsc_key}
                resp = requests.get(url, params=params, timeout=5)
                resp.raise_for_status()
                payload = resp.json()
                data = payload[0] if isinstance(payload, list) and payload else payload
                if isinstance(data, dict) and data.get("code"):
                    sections = data.get("list") if isinstance(data.get("list"), list) else []
                    content = "\n\n".join(
                        f"### {self._strip_html(str(section.get('title', '')))}\n{self._strip_html(str(section.get('contents', '')))}"
                        for section in sections
                    )
                    return {
                        "status": "SUCCESS",
                        "source": "REAL_KCSC_API",
                        "standard_code": f"{code_type} {' '.join(compact_code[i:i + 2] for i in range(0, 6, 2))}",
                        "standard_name": data.get("name", ""),
                        "category": data.get("codeType", code_type),
                        "discipline": "",
                        "revision_year": data.get("version", ""),
                        "update_date": data.get("updateDate", ""),
                        "content": content,
                        "source_anchor": f"{clean_code} ({data.get('name', '')})",
                    }
            except Exception as e:
                logger.warning(f"KCSC API call failed, switching to local cache: {e}")

        # 2. Offline / Mock fallback
        normalized_clean_code = re.sub(r"[\s-]", "", clean_code)
        for code, standard_data in self.kcsc_mock.items():
            if normalized_clean_code == re.sub(r"[\s-]", "", code.upper()):
                sections = standard_data.get("sections", {})
                section_texts = []
                for s_key, s_val in sections.items():
                    section_texts.append(f"### {s_val.get('title', s_key)}\n{s_val.get('content', '')}")

                full_content = "\n\n".join(section_texts) if section_texts else "본문 내용 없음"
                std_code = standard_data.get("standard_code", clean_code)
                std_name = standard_data.get("standard_name", "")

                return {
                    "status": "SUCCESS",
                    "source": "LOCAL_CACHE_FALLBACK",
                    "standard_code": std_code,
                    "standard_name": std_name,
                    "category": standard_data.get("category", ""),
                    "discipline": standard_data.get("discipline", ""),
                    "revision_year": standard_data.get("revision_year", "최신"),
                    "content": full_content,
                    "source_anchor": f"{std_code} ({std_name})",
                }

        return {
            "status": "NOT_FOUND",
            "source": "LOCAL_CACHE_FALLBACK",
            "standard_code": clean_code,
            "standard_name": "기준 미확인",
            "category": "-",
            "discipline": "-",
            "content": f"해당 국가건설기준({clean_code})의 본문 데이터를 찾을 수 없습니다.",
            "source_anchor": f"{clean_code} (미확인)",
        }

    @staticmethod
    def _strip_html(value: str) -> str:
        value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
        value = re.sub(r"<[^>]+>", "", value)
        return html.unescape(value).strip()


# Module level singleton helpers
_client = OpenApiClient()


def fetch_national_law(law_name: str, article_no: Optional[str] = None) -> Dict[str, Any]:
    return _client.fetch_national_law(law_name, article_no)


def fetch_kcsc_standard(standard_code: str) -> Dict[str, Any]:
    return _client.fetch_kcsc_standard(standard_code)
