import enum
import os
import re
from dataclasses import dataclass
from typing import Generator, List, Optional, Tuple

from dotenv import load_dotenv
from ragflow_sdk import RAGFlow, Session


def patched_retrieve(
    self,
    dataset_ids,
    document_ids=None,
    question="",
    page=1,
    page_size=30,
    similarity_threshold=0.2,
    vector_similarity_weight=0.3,
    top_k=1024,
    rerank_id: str | None = None,
    keyword: bool = False,
):
    if document_ids is None:
        document_ids = []

    data_json = {
        "page": page,
        "page_size": page_size,
        "similarity_threshold": similarity_threshold,
        "vector_similarity_weight": vector_similarity_weight,
        "top_k": top_k,
        "rerank_id": rerank_id,
        "keyword": keyword,
        "question": question,
        "dataset_ids": dataset_ids,
        "documents": document_ids,
    }
    res = self.post("/retrieval", json=data_json)
    res = res.json()

    if res.get("code") == 0:
        chunks = []
        for chunk_data in res["data"].get("chunks"):
            chunks.append(chunk_data)
        return chunks
    raise Exception(res.get("message"))


RAGFlow.retrieve = patched_retrieve


@dataclass
class Dataset:
    name: str
    id: str
    document_count: int
    chunk_count: int


@dataclass
class Document:
    id: str
    name: str
    size: int
    token_count: int
    chunk_count: int
    progress: float
    progress_message: str


@dataclass
class Chunk:
    available: bool
    content: str
    id: str


@dataclass
class ResultChunk:
    id: str
    content: str
    highlighted_content: str
    similarity: float
    term_similarity: float
    vector_similarity: float


@dataclass
class ReferenceChunk:
    id: str
    content: str
    dataset_id: str
    document_id: str
    document_name: str

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "dataset_id": self.dataset_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
        }


class Role(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: Role
    content: str
    references: List[ReferenceChunk]


class RAGService:
    def __init__(self, token: str, endpoint: str):
        self._client = RAGFlow(api_key=token, base_url=endpoint)

    @staticmethod
    def extract_filter_and_reorder(text: str, input_list: List) -> Tuple[List, str]:
        pattern = r"##(\d+)\$\$"
        matches = re.finditer(pattern, text)
        match_info = []
        for match in matches:
            index_value = int(match.group(1))
            match_info.append((match.start(), match.end(), index_value))
        filtered_list = []
        valid_indices = []
        for _, _, idx in match_info:
            if 0 <= idx < len(input_list):
                filtered_list.append(input_list[idx])
                valid_indices.append(idx)
        sorted_match_info = sorted(match_info, key=lambda x: x[0], reverse=True)
        new_text = text
        for i, (start, end, _) in enumerate(sorted_match_info):
            new_index = i
            new_text = new_text[:start] + f"##{new_index}$$" + new_text[end:]
        return filtered_list, new_text

    @staticmethod
    def calculate_page_count(total_items: int, page_size: int) -> int:
        if total_items == 0:
            return 0
        return (total_items - 1) // page_size + 1

    def list_datasets(self) -> List[Dataset]:
        return [
            Dataset(
                name=dataset.name,
                id=dataset.id,
                document_count=dataset.document_count,
                chunk_count=dataset.chunk_count,
            )
            for dataset in self._client.list_datasets()
        ]

    def list_documents(
        self, dataset_id: str, page: int = 1, page_size: int = 30
    ) -> Tuple[List[Document], int]:
        dataset = self._client.list_datasets(id=dataset_id)[0]
        return [
            Document(
                id=document.id,
                name=document.name,
                size=document.size,
                token_count=document.token_count,
                chunk_count=document.chunk_count,
                progress=document.progress,
                progress_message=document.progress_msg,
            )
            for document in dataset.list_documents(page=page, page_size=page_size)
        ], dataset.document_count

    def list_chunks(
        self, dataset_id: str, document_id: str, page: int = 1, page_size: int = 30
    ) -> Tuple[List[Chunk], int]:
        dataset = self._client.list_datasets(id=dataset_id)[0]
        document = dataset.list_documents(id=document_id)[0]
        chunk_count = document.chunk_count
        return [
            Chunk(
                available=chunk.available,
                content=chunk.content,
                id=chunk.id,
            )
            for chunk in document.list_chunks(page=page, page_size=page_size)
        ], chunk_count

    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: List[str],
        document_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
    ) -> List[ResultChunk]:
        chunks = self._client.retrieve(
            dataset_ids=dataset_ids,
            question=question,
            document_ids=document_ids,
            page=page,
            page_size=page_size,
            similarity_threshold=similarity_threshold,
            vector_similarity_weight=vector_similarity_weight,
            top_k=top_k,
        )
        return [
            ResultChunk(
                content=chunk["content"],
                highlighted_content=chunk["highlight"],
                id=chunk["id"],
                similarity=chunk["similarity"],
                term_similarity=chunk["term_similarity"],
                vector_similarity=chunk["vector_similarity"],
            )
            for chunk in chunks
        ]

    def create_conversation(self, chat_id: str, user_id: str, conversation_id: str):
        chat = self._client.list_chats(id=chat_id)[0]
        chat.create_session(name=f"{user_id}:{conversation_id}")

    def get_conversation(
        self, chat_id: str, user_id: str, conversation_id: str
    ) -> Optional[Session]:
        chat = self._client.list_chats(id=chat_id)[0]
        return chat.list_sessions(name=f"{user_id}:{conversation_id}")[0]

    def delete_conversation(self, chat_id: str, user_id: str, conversation_id: str):
        chat = self._client.list_chats(id=chat_id)[0]
        session = chat.list_sessions(name=f"{user_id}:{conversation_id}")[0]
        chat.delete_sessions(ids=[session.id])

    def get_conversation_messages(
        self, chat_id: str, user_id: str, conversation_id: str
    ) -> List[Message]:
        session = self.get_conversation(chat_id, user_id, conversation_id)
        messages = session.messages
        for message in messages:
            if "reference" not in message:
                continue
            new_references, new_message = self.extract_filter_and_reorder(
                message["content"], message["reference"]
            )
            message["content"] = new_message
            message["reference"] = new_references
        return [
            Message(
                role=Role(message["role"]),
                content=message["content"],
                references=(
                    [
                        ReferenceChunk(
                            id=reference["id"],
                            content=reference["content"],
                            dataset_id=reference["dataset_id"],
                            document_id=reference["document_id"],
                            document_name=reference["document_name"],
                        )
                        for reference in message["reference"]
                    ]
                    if "reference" in message
                    else []
                ),
            )
            for message in messages
        ]

    def chat(
        self, chat_id: str, user_id: str, conversation_id: str, message: str
    ) -> Tuple[Generator[str, None, None], List[ReferenceChunk], List[str]]:
        chat = self._client.list_chats(id=chat_id)[0]
        session = chat.list_sessions(name=f"{user_id}:{conversation_id}")[0]
        result = session.ask(question=message, stream=True)

        complete_message = [""]
        references: List[ReferenceChunk] = []

        def message_generator():
            for content in result:
                nonlocal complete_message, references
                current_message = content.content

                if content.reference:
                    new_references, new_message = self.extract_filter_and_reorder(
                        current_message, content.reference
                    )
                    references.extend(
                        [
                            ReferenceChunk(
                                id=reference["id"],
                                content=reference["content"],
                                dataset_id=reference["dataset_id"],
                                document_id=reference["document_id"],
                                document_name=reference["document_name"],
                            )
                            for reference in new_references
                        ]
                    )
                    complete_message[0] = new_message
                else:
                    delta_message = current_message[len(complete_message[0]) :]
                    complete_message[0] = current_message
                    yield delta_message

        generator = message_generator()
        return generator, references, complete_message


if __name__ == "__main__":
    load_dotenv()
    rag_service = RAGService(
        token=os.getenv("RAG_TOKEN"),
        endpoint=os.getenv("RAG_ENDPOINT"),
    )

    ### Example usage
    """
    datasets = rag_service.list_datasets()
    print(f"Datasets: {[dataset.name for dataset in datasets]}")

    dataset = datasets[1]
    pages = rag_service.calculate_page_count(dataset.document_count, 10)
    print(f"Total pages: {pages}")

    documents = rag_service.list_documents(dataset.id, page=2, page_size=10)
    print(f"Documents in page 2: {[document.name for document in documents]}")

    document = documents[0]
    chunks = rag_service.list_chunks(dataset.id, document.id, page=1, page_size=10)
    print(f"Chunks in document {document.name}: {[chunk.content for chunk in chunks]}")

    chunk_results = rag_service.retrieve_chunks(
        "勾股定理", [dataset.id for dataset in rag_service.list_datasets()]
    )
    for chunk in chunk_results:
        print(f"Content: {chunk.content}")
        print(f"Highlighted Content: {chunk.highlighted_content}")
        print(f"ID: {chunk.id}")
        print(f"Similarity: {chunk.similarity}")
        print(f"Term Similarity: {chunk.term_similarity}")
        print(f"Vector Similarity: {chunk.vector_similarity}")
        print("-" * 40)

    messages = rag_service.get_conversation_messages(
        os.getenv("RAG_CHAT_ID"),
        user_id="user_id",
        conversation_id="conversation_id",
    )
    for message in messages:
        print(f"Role: {message.role}")
        print(f"Content: {message.content}")
        print(f"References: {[reference.id for reference in message.references]}")
        print("-" * 40)
    """

    generator, references, complete_message = rag_service.chat(
        os.getenv("RAG_CHAT_ID"),
        user_id="user_id",
        conversation_id="conversation_id",
        message="介绍一下勾股定理",
    )

    for delta_message in generator:
        print(delta_message, end="", flush=True)

    print()
    print("-" * 40)
    print(f"Complete message: {complete_message[0]}")
    print("-" * 40)
    print(f"References: {[reference.document_name for reference in references]}")
    print("-" * 40)
