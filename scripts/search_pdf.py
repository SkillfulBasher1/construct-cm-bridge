"""Generic PDF Document Search CLI Tool
Usage:
  python scripts/search_pdf.py <query> [--db <db_path>] [--top <count>]

Examples:
  python scripts/search_pdf.py "스프링클러"
  python scripts/search_pdf.py "배관 구배" --top 5
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir / "src") not in sys.path:
    sys.path.insert(0, str(root_dir / "src"))

from construct_cm_bridge.core.pdf_indexer import PdfDocumentIndexer

def main():
    parser = argparse.ArgumentParser(description="Search indexed PDF documents using FTS5 full-text search.")
    parser.add_argument("query", help="Keyword or phrase to search")
    parser.add_argument("--db", help="SQLite database path", default=None)
    parser.add_argument("--top", help="Maximum number of results to return", type=int, default=5)

    args = parser.parse_args()
    db_path = Path(args.db).resolve() if args.db else None

    indexer = PdfDocumentIndexer(db_path=db_path)
    if not indexer.db_path.exists():
        print(f"[Error] Database not found at {indexer.db_path}.")
        print("Please index documents first using 'python scripts/index_pdf.py <pdf_path>'.")
        sys.exit(1)

    results = indexer.search(args.query, top_k=args.top)

    print(f"\n======================================================================")
    print(f" [PDF Document Search] Query: '{args.query}' (Found: {len(results)})")
    print(f"======================================================================\n")

    if not results:
        print("No matching documents found.")
        return

    for idx, r in enumerate(results, 1):
        print(f"[{idx}] {r['filename']} - p.{r['page_no']} | {r['heading']} (Score: {r['score']})")
        print(f"    Excerpt: {r['excerpt']}")
        print("-" * 70)

if __name__ == "__main__":
    main()
