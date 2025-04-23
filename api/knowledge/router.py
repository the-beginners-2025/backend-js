from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.knowledge.models import (
    Chunk,
    ChunksResponse,
    Dataset,
    DatasetsResponse,
    Document,
    DocumentsResponse,
    ResultChunk,
    RetrievalRequest,
    RetrievalResponse,
)
from db.database import get_db
from db.models import User, UserStatistics
from middlewares.auth import auth_middleware
from services.uni import rag_service

router = APIRouter(prefix="/knowledge")


@router.get("/", response_model=DatasetsResponse)
async def get_datasets(_: None = Depends(auth_middleware)):
    return DatasetsResponse(
        datasets=[
            Dataset(
                name=dataset.name,
                id=dataset.id,
                document_count=dataset.document_count,
                chunk_count=dataset.chunk_count,
            )
            for dataset in rag_service.list_datasets()
        ]
    )


@router.get("/{dataset_id}", response_model=DocumentsResponse)
async def get_documents(
    dataset_id: str,
    page: int = 1,
    page_size: int = 10,
    _: None = Depends(auth_middleware),
):
    source_documents, document_count = rag_service.list_documents(
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )
    documents = [
        Document(
            id=document.id,
            name=document.name,
            size=document.size,
            token_count=document.token_count,
            chunk_count=document.chunk_count,
            progress=document.progress,
            progress_message=document.progress_message,
        )
        for document in source_documents
    ]
    return DocumentsResponse(
        documents=documents,
        document_count=document_count,
        page=page,
        page_count=rag_service.calculate_page_count(
            total_items=document_count,
            page_size=page_size,
        ),
        page_size=page_size,
    )


@router.get("/{dataset_id}/{document_id}", response_model=ChunksResponse)
async def get_chunks(
    dataset_id: str,
    document_id: str,
    page: int = 1,
    page_size: int = 10,
    _: None = Depends(auth_middleware),
):
    source_chunks, chunk_count = rag_service.list_chunks(
        dataset_id=dataset_id,
        document_id=document_id,
        page=page,
        page_size=page_size,
    )
    chunks = [
        Chunk(
            available=chunk.available,
            content=chunk.content,
            id=chunk.id,
        )
        for chunk in source_chunks
    ]
    return ChunksResponse(
        chunks=chunks,
        chunk_count=chunk_count,
        page=page,
        page_count=rag_service.calculate_page_count(
            total_items=chunk_count,
            page_size=page_size,
        ),
        page_size=page_size,
    )


@router.post("/retrieval", response_model=RetrievalResponse)
async def retrieval(
    retrieval_request: RetrievalRequest,
    user: User = Depends(auth_middleware),
    db: Session = Depends(get_db),
):
    user_stats = (
        db.query(UserStatistics).filter(UserStatistics.user_id == user.id).first()
    )
    user_stats.knowledge_base_search_count += 1
    db.commit()

    return RetrievalResponse(
        chunks=[
            ResultChunk(
                id=result_chunk.id,
                content=result_chunk.content,
                highlighted_content=result_chunk.highlighted_content,
                similarity=result_chunk.similarity,
                term_similarity=result_chunk.term_similarity,
                vector_similarity=result_chunk.vector_similarity,
            )
            for result_chunk in rag_service.retrieve_chunks(
                question=retrieval_request.question,
                dataset_ids=retrieval_request.dataset_ids,
                document_ids=retrieval_request.document_ids,
                page=retrieval_request.page,
                page_size=retrieval_request.page_size,
                similarity_threshold=retrieval_request.similarity_threshold,
                vector_similarity_weight=retrieval_request.vector_similarity_weight,
                top_k=retrieval_request.top_k,
            )
        ],
        page=retrieval_request.page,
        page_count=rag_service.calculate_page_count(
            total_items=retrieval_request.top_k,
            page_size=retrieval_request.page_size,
        ),
        page_size=retrieval_request.page_size,
    )
