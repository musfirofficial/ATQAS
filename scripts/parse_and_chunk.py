import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from rag import create_chunks_from_dataset, parse_and_prepare_textbook


def main():
    parser = argparse.ArgumentParser(
        description="Textbook Ingestion Step 1: Parse PDF textbook and generate safe chunks."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Path to the source PDF textbook file.",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default=None,
        help="Human-readable textbook title (e.g. 'Science Grade 10 Part 1'). Inferred if omitted.",
    )
    parser.add_argument(
        "--grade",
        type=int,
        default=None,
        help="Grade level (e.g. 10). Auto-inferred if omitted.",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Subject name (e.g. 'Science', 'Commerce'). Auto-inferred if omitted.",
    )
    parser.add_argument(
        "--medium",
        type=str,
        default="english",
        help="Language medium (default: 'english').",
    )
    parser.add_argument(
        "--edition",
        type=str,
        default=None,
        help="Edition or syllabus year (e.g. '2024').",
    )
    parser.add_argument(
        "--auto-ingest",
        action="store_true",
        default=False,
        help="Automatically proceed without interactive confirmation prompt.",
    )
    parser.add_argument(
        "--no-include-images",
        action="store_true",
        help="Cost-optimized mode: do not send pages with raster photos to Gemini vision (only tables & drawings).",
    )
    parser.add_argument(
        "--force-reextract",
        action="store_true",
        help="Force re-extraction even if data/extracted/<stem>.json already exists.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=400,
        help="Chunk token size limit (default: 400).",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=60,
        help="Chunk token overlap (default: 60).",
    )

    args = parser.parse_args()

    pdf_path = Path(args.file).resolve()
    if not pdf_path.exists():
        print(f"[ERROR] PDF file does not exist: {pdf_path}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print(f"  TEXTBOOK PARSER & CHUNKER: {pdf_path.name}")
    print("=" * 65)

    # 1. Parse and extract textbook pages
    extracted_pages = parse_and_prepare_textbook(
        file_path=str(pdf_path),
        title=args.title,
        grade=args.grade,
        subject=args.subject,
        medium=args.medium,
        edition=args.edition,
        auto_ingest=args.auto_ingest,
        include_images=not args.no_include_images,
        force_reextract=args.force_reextract,
    )

    if not extracted_pages:
        print("\n[INFO] Extraction was cancelled or returned 0 pages. Exiting cleanly.\n")
        sys.exit(0)

    from rag.parser.util import get_extracted_path
    extracted_json_path = get_extracted_path(str(pdf_path))

    # 2. Chunk textbook dataset
    print(f"\n[CHUNKING] Generating chunks from '{extracted_json_path.name}'...")
    chunks = create_chunks_from_dataset(
        dataset_path=str(extracted_json_path),
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        title=args.title,
    )

    page_count = (
        len(extracted_pages["pages"])
        if isinstance(extracted_pages, dict)
        else len(extracted_pages)
    )
    print("\n" + "=" * 65)
    print(f"✅ STEP 1 COMPLETE: {pdf_path.name}")
    print(f"   • Extracted Pages: {page_count}")
    print(f"   • Generated Chunks: {len(chunks)}")
    print(f"   • Saved Dataset:   {extracted_json_path}")
    print(
        f"\nNext: Run 'python scripts/index_to_qdrant.py --dataset {extracted_json_path.name}' to embed & store."
    )
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
