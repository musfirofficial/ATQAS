import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag import (
    DEFAULT_COLLECTION_NAME,
    create_chunks_from_dataset,
    get_qdrant_client,
    upsert_chunks,
)
from src.crud.textbook import (
    create_textbook_record,
    get_textbook_by_id,
    get_textbook_by_title,
    get_textbooks,
)
from src.db.models import TextBookStatus
from src.db.session import get_session
from src.schema.textbook import TextBookDatasetCreate, TextBookResponse

router = APIRouter(prefix="/textbooks", tags=["Textbooks"])


@router.post(
    "/upload",
    response_model=TextBookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a textbook dataset JSON file",
)
async def upload_textbook_dataset(
    file: UploadFile = File(..., description="Extracted textbook JSON dataset file"),
    db: AsyncSession = Depends(get_session),
):
    """
    Ingests an extracted textbook JSON dataset file:
    1. Quick check: rejects if textbook title is already in SQL.
    2. Chunks and embeds into Qdrant (Dense BGE-small + Sparse BM25).
    3. Saves textbook record in SQL database.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .json dataset files are accepted.",
        )

    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file format: {e}",
        )

    # Support either list of pages directly or dict with {"metadata": ..., "pages": ...}
    if isinstance(data, list):
        pages = data
        meta = pages[0] if pages else {}
        title = (
            meta.get("title")
            or meta.get("document_name")
            or file.filename.rsplit(".", 1)[0]
        )
    elif isinstance(data, dict):
        pages = data.get("pages", [])
        meta = data.get("metadata", {})
        title = (
            meta.get("title")
            or meta.get("document_name")
            or file.filename.rsplit(".", 1)[0]
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected JSON format. Expected list of pages or object containing 'pages'.",
        )

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset contains no page records.",
        )

    # --------------------------------------------------------------------------
    # 1. Fast SQL Check
    # --------------------------------------------------------------------------
    existing = await get_textbook_by_title(db, title=title)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Textbook '{title}' is already registered in the database.",
        )

    # --------------------------------------------------------------------------
    # 2. Chunk, Embed & Store in Qdrant
    # --------------------------------------------------------------------------
    try:
        dataset_input = {"metadata": meta, "pages": pages} if meta else pages
        chunks = create_chunks_from_dataset(dataset_input, title=title)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chunks could be produced from dataset.",
            )

        qdrant_client = get_qdrant_client()
        upsert_chunks(
            chunks=chunks,
            client=qdrant_client,
            collection_name=DEFAULT_COLLECTION_NAME,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store indexing failed: {e}",
        )

    # ── 3. Create Row in SQL DB ────────────────────────────────
    total_pages = meta.get("total_pages", len(pages))
    book = await create_textbook_record(
        db=db,
        title=title,
        total_pages=total_pages,
        collection_name=DEFAULT_COLLECTION_NAME,
        grade=meta.get("grade"),
        subject=meta.get("subject"),
        medium=meta.get("medium", "english"),
        edition=str(meta.get("edition")) if meta.get("edition") is not None else None,
        path=file.filename,
        status=TextBookStatus.READY,
    )

    return book


@router.post(
    "/",
    response_model=TextBookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register and index a textbook from a JSON dataset payload",
)
async def create_textbook_from_json(
    payload: TextBookDatasetCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Direct JSON payload ingestion:
    1. Checks if title already exists in SQL.
    2. Chunks and embeds pages into Qdrant.
    3. Saves record to SQL.
    """
    # ── 1. Fast SQL Check ──────────────────────────────────────
    existing = await get_textbook_by_title(db, title=payload.title)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Textbook '{payload.title}' is already registered in the database.",
        )

    if not payload.pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload contains no page records.",
        )

    # ── 2. Chunk, Embed & Store in Qdrant ──────────────────────
    try:
        dataset_input = {
            "metadata": {
                "title": payload.title,
                "grade": payload.grade,
                "subject": payload.subject,
                "medium": payload.medium,
                "edition": payload.edition,
            },
            "pages": payload.pages,
        }
        chunks = create_chunks_from_dataset(dataset_input, title=payload.title)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chunks could be produced from pages.",
            )

        qdrant_client = get_qdrant_client()
        upsert_chunks(
            chunks=chunks,
            client=qdrant_client,
            collection_name=DEFAULT_COLLECTION_NAME,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store indexing failed: {e}",
        )

    # ── 3. Create Row in SQL DB ────────────────────────────────
    book = await create_textbook_record(
        db=db,
        title=payload.title,
        total_pages=len(payload.pages),
        collection_name=DEFAULT_COLLECTION_NAME,
        grade=payload.grade,
        subject=payload.subject,
        medium=payload.medium,
        edition=str(payload.edition) if payload.edition is not None else None,
        path=payload.path,
        status=TextBookStatus.READY,
    )

    return book


@router.get(
    "/",
    response_model=list[TextBookResponse],
    summary="List all indexed textbooks",
)
async def list_textbooks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    """Retrieve all textbooks registered in the catalog."""
    return await get_textbooks(db=db, skip=skip, limit=limit)


@router.get(
    "/{textbook_id}",
    response_model=TextBookResponse,
    summary="Get textbook details by ID",
)
async def get_textbook(
    textbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Retrieve metadata of a single textbook."""
    book = await get_textbook_by_id(db=db, textbook_id=textbook_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Textbook with ID {textbook_id} not found.",
        )
    return book
