import json
import re
from pathlib import Path

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from .core.config import ROOT_DIR

SOURCE_FOLDER = ROOT_DIR / "data" / "extracted"


def create_chunks_from_dataset(
    dataset_input: str | Path | dict | list[dict] | None = None,
    chunk_size: int = 400,
    overlap: int = 60,
    title: str | None = None,
    document_name: str | None = None,
    dataset_path: str | Path | None = None,
):
    """
    Takes an extracted textbook dataset (file path, dict, or list of page dicts)
    and splits it into safe, metadata-enriched chunks ready for Qdrant.
    """
    input_data = dataset_input if dataset_input is not None else dataset_path
    if input_data is None:
        raise ValueError("Must provide either dataset_input or dataset_path")

    book_title = title or document_name
    meta: dict = {}

    if isinstance(input_data, dict):
        meta = input_data.get("metadata", {})
        pages = input_data.get("pages", [])
        name_for_stem = book_title or meta.get("title") or meta.get("document_name") or "textbook"
        doc_stem = re.sub(r"[^\w\-]", "_", str(name_for_stem))
        display_name = doc_stem
    elif isinstance(input_data, list):
        pages = input_data
        name_for_stem = (
            book_title
            or (pages[0].get("title") or pages[0].get("document_name") if pages else "textbook")
        )
        doc_stem = re.sub(r"[^\w\-]", "_", str(name_for_stem))
        display_name = doc_stem
    else:
        path_obj = Path(input_data)
        if not path_obj.exists():
            raise FileNotFoundError(f"Dataset file not found at {dataset_input}")
        with open(path_obj, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict):
            meta = raw_data.get("metadata", {})
            pages = raw_data.get("pages", [])
            first_title = meta.get("title") or meta.get("document_name")
        else:
            pages = raw_data
            first_title = pages[0].get("title") or pages[0].get("document_name") if pages else None

        doc_stem = re.sub(r"[^\w\-]", "_", str(book_title or first_title or path_obj.stem))
        display_name = path_obj.name

    # 1. Convert pages in to LlamaIndex Documents
    documents: list[Document] = []
    for page in pages:
        text = page.get("text", "")

        # Skip completely blank pages and Front Matter page
        if not text or page.get("chapter_title") == "Front Matter":
            continue

        page_title = (
            page.get("title")
            or meta.get("title")
            or page.get("document_name")
            or meta.get("document_name")
            or doc_stem
        )

        doc = Document(
            text=text,
            metadata={
                "title": page_title,
                "document_name": page_title,
                "grade": page.get("grade") or meta.get("grade"),
                "subject": page.get("subject") or meta.get("subject"),
                "medium": page.get("medium") or meta.get("medium", "English"),
                "edition": page.get("edition") or meta.get("edition"),
                "pdf_page": page.get("pdf_page"),
                "book_page": page.get("book_page"),
                "chapter_number": page.get("chapter_number"),
                "chapter_title": page.get("chapter_title"),
            },
        )
        documents.append(doc)

    # 2. Configure the Safe SentenceSplitter
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        paragraph_separator="\n\n",
        secondary_chunking_regex=r"[^,.;。]+[,.;。]?",
    )

    # 3. Chunk
    raw_nodes = splitter.get_nodes_from_documents(documents)

    # 4. Enrich chunks: Deterministic IDs & Context Headers
    page_chunk_counters: dict[int, int] = {}
    final_chunks: list[TextNode] = []

    for node in raw_nodes:
        meta = node.metadata
        pdf_page = meta.get("pdf_page", 0)

        # Track chunk index per page (e.g. page 16 -> chunk 0, chunk 1)
        chunk_idx = page_chunk_counters.get(pdf_page, 0)
        page_chunk_counters[pdf_page] = chunk_idx + 1

        # Deterministic, unique ID: e.g. "SCIENCE_G-10_P1_E_p16_c0"
        node.id_ = f"{doc_stem}_p{pdf_page}_c{chunk_idx}"
        meta["chunk_index"] = chunk_idx

        final_chunks.append(node)
    print(
        f"[CHUNKING SUCCESS] Dataset '{display_name}' ({len(pages)} pages) "
        f"split into {len(final_chunks)} safe chunks."
    )
    return final_chunks

