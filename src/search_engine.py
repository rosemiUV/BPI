"""Block C: Semantic search scaffold with LangChain and ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievedContext:
    """A retrieved chunk and optional metadata."""

    content: str
    metadata: dict[str, Any]


class SemanticSearchEngine:
    """Simple scaffold for chunking, indexing, and retrieval."""

    def __init__(self) -> None:
        self._chunks: list[str] = []
        self._vectordb: Any | None = None

    def index_transcript(self, transcript_text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """Chunk transcript text and prepare vector storage.

        Falls back to in-memory chunks if embedding backend is unavailable.
        """
        if not transcript_text.strip():
            self._chunks = []
            self._vectordb = None
            return

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain_community.vectorstores import Chroma
            from langchain_core.documents import Document

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            docs = [Document(page_content=transcript_text)]
            split_docs = splitter.split_documents(docs)
            self._chunks = [doc.page_content for doc in split_docs]

            embedding = self._build_embedding(len(self._chunks))
            if embedding is None:
                self._vectordb = None
                return

            self._vectordb = Chroma.from_texts(
                texts=self._chunks,
                embedding=embedding,
                metadatas=[{"source": "transcript"} for _ in self._chunks],
            )
        except (ImportError, ValueError, TypeError):
            self._chunks = self._simple_chunks(transcript_text, chunk_size=chunk_size)
            self._vectordb = None

    def retrieve_context(self, query: str, top_k: int = 3) -> list[RetrievedContext]:
        """Retrieve relevant context chunks for a semantic query."""
        if not query.strip() or not self._chunks:
            return []

        if self._vectordb is not None:
            try:
                docs = self._vectordb.similarity_search(query, k=top_k)
                return [
                    RetrievedContext(content=doc.page_content, metadata=doc.metadata)
                    for doc in docs
                ]
            except (ValueError, TypeError, RuntimeError):
                self._vectordb = None

        # Fallback mock retrieval for scaffold usage.
        selected = self._chunks[:top_k]
        return [RetrievedContext(content=text, metadata={"source": "fallback"}) for text in selected]

    @staticmethod
    def _build_embedding(chunks_count: int) -> Any | None:
        """Return a lightweight embedding model if available."""
        try:
            from langchain.embeddings import FakeEmbeddings
        except ImportError:
            return None

        return FakeEmbeddings(size=max(8, min(64, chunks_count * 8)))

    @staticmethod
    def _simple_chunks(text: str, chunk_size: int) -> list[str]:
        """Small fallback chunker for environments without LangChain setup."""
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
