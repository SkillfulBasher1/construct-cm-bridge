"""External Legal and KCSC Standards Bridge Module

Connects to:
1. National Law Information Center (국가법령정보센터 / law.go.kr) REST API
2. Korea Construction Standards Center (국가건설기준센터 / kcsc.re.kr) OpenAPI
Provides automatic offline caching and Mock fallback for robust judging and demo execution.
"""

import os
import json
import logging
import xml.etree.ElementTree as ET
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
        self.cache_dir = cache_dir or CACHE_DIR

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

        clean_name = law_name.strip()
        article_key = str(article_no).strip() if article_no else None

        # 1. Try real API if OC (User ID/API Key) is provided
        if self.law_oc:
            try:
                url = "http://www.law.go.kr/DRF/lawSearch.do"
                params = {
                    "OC": self.law_oc,
                    "target": "law",
                    "type": "XML",
                    "query": clean_name,
                }
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200 and "<Law" in resp.text:
                    root = ET.fromstring(resp.content)
                    articles_found = []
                    for article in root.findall(".//조문단위"):
                        no_tag = article.find("조문번호")
                        title_tag = article.find("조문제목")
                        content_tag = article.find("조문내용")

                        curr_no = no_tag.text.strip() if no_tag is not None and no_tag.text else ""
                        curr_title = title_tag.text.strip() if title_tag is not None and title_tag.text else ""
                        curr_content = content_tag.text.strip() if content_tag is not None and content_tag.text else ""

                        if not article_key or curr_no == article_key or f"제{article_key}조" in curr_content:
                            articles_found.append({
                                "article_no": curr_no,
                                "title": curr_title,
                                "content": curr_content,
                            })

                    if articles_found:
                        target = articles_found[0]
                        return {
                            "status": "SUCCESS",
                            "source": "REAL_OPENAPI",
                            "law_name": clean_name,
                            "article_no": target["article_no"] or article_key or "전체",
                            "title": target["title"],
                            "content": target["content"],
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
                elif articles:
                    # Return all articles or the first one
                    first_k = next(iter(articles))
                    art = articles[first_k]
                    all_content = "\n\n".join(
                        f"[제{v.get('article_no')}조 ({v.get('title')})]\n{v.get('content')}"
                        for v in articles.values()
                    )
                    law_title = law_data.get("law_name", clean_name)
                    return {
                        "status": "SUCCESS",
                        "source": "LOCAL_CACHE_FALLBACK",
                        "law_name": law_title,
                        "article_no": "전체" if not article_key else article_key,
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

    def fetch_kcsc_standard(self, standard_code: str) -> Dict[str, Any]:
        """Fetches KDS/KCS construction standard specifications.

        Args:
            standard_code: Code of the standard (e.g. 'KDS 21 30 00', 'KCS 14 31 25')

        Returns:
            Dict containing standard_code, standard_name, category, discipline, content, source.
        """
        import requests

        clean_code = standard_code.strip().upper()

        # 1. Try real KCSC API if Key is provided
        if self.kcsc_key:
            try:
                url = "https://www.kcsc.re.kr/openapi/standardDetail"
                params = {"serviceKey": self.kcsc_key, "code": clean_code}
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "status": "SUCCESS",
                        "source": "REAL_KCSC_API",
                        "standard_code": clean_code,
                        "standard_name": data.get("title", ""),
                        "category": data.get("category", ""),
                        "discipline": data.get("discipline", ""),
                        "content": data.get("body", ""),
                        "source_anchor": f"{clean_code} ({data.get('title', '')})",
                    }
            except Exception as e:
                logger.warning(f"KCSC API call failed, switching to local cache: {e}")

        # 2. Offline / Mock fallback
        for code, standard_data in self.kcsc_mock.items():
            if clean_code in code.upper() or code.upper() in clean_code:
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


# Module level singleton helpers
_client = OpenApiClient()


def fetch_national_law(law_name: str, article_no: Optional[str] = None) -> Dict[str, Any]:
    return _client.fetch_national_law(law_name, article_no)


def fetch_kcsc_standard(standard_code: str) -> Dict[str, Any]:
    return _client.fetch_kcsc_standard(standard_code)
