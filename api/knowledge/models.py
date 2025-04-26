from typing import List, Optional

from pydantic import BaseModel


class Dataset(BaseModel):
    name: str
    id: str
    document_count: int
    chunk_count: int


class Document(BaseModel):
    id: str
    name: str
    size: int
    token_count: int
    chunk_count: int
    progress: float
    progress_message: str


class Chunk(BaseModel):
    available: bool
    content: str
    id: str


class ResultChunk(BaseModel):
    id: str
    content: str
    highlighted_content: str
    similarity: float
    term_similarity: float
    vector_similarity: float


class DatasetsResponse(BaseModel):
    datasets: List[Dataset]


class PaginationResponse(BaseModel):
    page: int
    page_count: int
    page_size: int


class DocumentsResponse(PaginationResponse):
    documents: List[Document]
    document_count: int


class ChunksResponse(PaginationResponse):
    chunks: List[Chunk]
    chunk_count: int


class RetrievalResponse(PaginationResponse):
    chunks: List[ResultChunk]


class RetrievalRequest(BaseModel):
    page: int
    page_size: int
    question: str
    dataset_ids: List[str]
    document_ids: Optional[List[str]] = None
    similarity_threshold: float = 0.2
    vector_similarity_weight: float = 0.3
    top_k: int = 1024


class NodeProperties(BaseModel):
    description: str
    entity_id: str
    entity_type: str
    file_path: str
    source_id: str


class Node(BaseModel):
    id: str
    labels: List[str]
    properties: NodeProperties


class EdgeProperties(BaseModel):
    description: str
    file_path: str
    keywords: str
    source_id: str
    weight: float


class Edge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: EdgeProperties


class GraphResponse(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    is_truncated: bool = False
