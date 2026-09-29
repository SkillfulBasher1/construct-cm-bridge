"""Generic PDF Document Indexing CLI Tool
Usage:
  python scripts/index_pdf.py <path_to_pdf_or_directory> [--db <db_path>] [--title <doc_title>]

Examples:
  python scripts/index_pdf.py "docs/technical_spec.pdf"
  python scripts/index_pdf.py "C:/Users/cmuser/Desktop/project_manuals"
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
    parser = argparse.ArgumentParser(description="Index PDF engineering documents into local SQLite FTS5 database.")
    parser.add_argument("path", help="Path to a PDF file or a directory containing PDFs")
    parser.add_argument("--db", help="Target SQLite database path", default=None)
    parser.add_argument("--title", help="Optional document title", default=None)

    args = parser.parse_args()
    target_path = Path(args.path).resolve()
    db_path = Path(args.db).resolve() if args.db else None

    if not target_path.exists():
        print(f"[Error] Target path does not exist: {target_path}")
        sys.exit(1)

    indexer = PdfDocumentIndexer(db_path=db_path)
    print(f"Target Database: {indexer.db_path}")

    if target_path.is_file():
        if target_path.suffix.lower() != ".pdf":
            print(f"[Error] Target file is not a PDF: {target_path}")
            sys.exit(1)
        print(f"Indexing PDF: {target_path.name}...")
        res = indexer.index_pdf_file(str(target_path), doc_title=args.title)
        print(f"[Done] Indexed {res['total_pages']} pages ({res['pages_with_text']} with text, {res['total_characters']} chars).")

    elif target_path.is_dir():
        pdf_files = list(target_path.glob("*.pdf"))
        if not pdf_files:
            print(f"[Warning] No PDF files found in {target_path}")
            return
        print(f"Found {len(pdf_files)} PDF files in {target_path.name}. Starting indexing...")
        for pdf_file in pdf_files:
            try:
                res = indexer.index_pdf_file(str(pdf_file))
                print(f" - {pdf_file.name}: {res['total_pages']} pages ({res['total_characters']} chars)")
            except Exception as e:
                print(f" - [Failed] {pdf_file.name}: {e}")
        print("[Done] All PDF files processed.")

if __name__ == "__main__":
    main()
