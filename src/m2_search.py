from __future__ import annotations

"""Module 2: Hybrid Search — BM25 (Vietnamese) + Dense + RRF."""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    BM25_TOP_K,
    COLLECTION_NAME,
    DENSE_TOP_K,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    HYBRID_TOP_K,
    QDRANT_HOST,
    QDRANT_PORT,
)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str  # "bm25", "dense", "hybrid"


def segment_vietnamese(text: str) -> str:
    """Segment Vietnamese text into words."""
    if not text.strip():
        return ""

    from underthesea import word_tokenize

    return word_tokenize(text, format="text").replace("_", " ")


class BM25Search:
    def __init__(self):
        self.corpus_tokens: list[list[str]] = []
        self.documents: list[dict] = []
        self.bm25 = None

    def index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks."""
        self.documents = list(chunks)
        self.corpus_tokens = [
            segment_vietnamese(chunk["text"]).casefold().split()
            for chunk in self.documents
        ]
        self.bm25 = None
        if any(self.corpus_tokens):
            from rank_bm25 import BM25Okapi

            self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Search using BM25."""
        if self.bm25 is None or top_k <= 0 or not query.strip():
            return []

        tokenized_query = segment_vietnamese(query).casefold().split()
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )
        return [
            SearchResult(
                text=self.documents[index]["text"],
                score=float(scores[index]),
                metadata=self.documents[index].get("metadata", {}),
                method="bm25",
            )
            for index in ranked_indices
            if scores[index] > 0
        ][:top_k]


class DenseSearch:
    def __init__(self):
        from qdrant_client import QdrantClient

        try:
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=2)
            self.client.get_collections()
        except Exception as exc:
            print(
                f"  Qdrant unavailable at {QDRANT_HOST}:{QDRANT_PORT}; "
                f"using in-memory storage: {exc}",
                flush=True,
            )
            self.client = QdrantClient(":memory:")
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Index chunks into Qdrant."""
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if self.client.collection_exists(collection):
            self.client.delete_collection(collection_name=collection)
        self.client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        if not chunks:
            return

        texts = [chunk["text"] for chunk in chunks]
        vectors = self._get_encoder().encode(texts, show_progress_bar=True)
        if len(vectors) != len(chunks):
            raise ValueError("Embedding count must match the number of chunks")

        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            vector_values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            if len(vector_values) != EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding at index {index} has size {len(vector_values)}; "
                    f"expected {EMBEDDING_DIM}"
                )
            payload = {**chunk.get("metadata", {}), "text": chunk["text"]}
            points.append(PointStruct(id=index, vector=vector_values, payload=payload))

        self.client.upsert(collection_name=collection, points=points)

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        """Search using dense vectors."""
        if top_k <= 0 or not query.strip() or not self.client.collection_exists(collection):
            return []

        query_vector = self._get_encoder().encode(query)
        query_vector = query_vector.tolist() if hasattr(query_vector, "tolist") else list(query_vector)
        points = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )
        results = []
        for point in points:
            payload = point.payload or {}
            text = payload.get("text")
            if isinstance(text, str):
                results.append(
                    SearchResult(
                        text=text,
                        score=float(point.score),
                        metadata=payload,
                        method="dense",
                    )
                )
        return results


def reciprocal_rank_fusion(results_list: list[list[SearchResult]], k: int = 60,
                           top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
    """Merge ranked lists using RRF: score(d) = Σ 1/(k + rank + 1)."""
    if k <= 0:
        raise ValueError("k must be positive")
    if top_k <= 0:
        return []

    fused_scores: dict[str, float] = {}
    representative_results: dict[str, SearchResult] = {}
    for results in results_list:
        for rank, result in enumerate(results):
            fused_scores[result.text] = fused_scores.get(result.text, 0.0) + 1.0 / (k + rank + 1)
            representative_results.setdefault(result.text, result)

    ranked_texts = sorted(fused_scores, key=fused_scores.__getitem__, reverse=True)[:top_k]
    return [
        SearchResult(
            text=text,
            score=fused_scores[text],
            metadata=representative_results[text].metadata,
            method="hybrid",
        )
        for text in ranked_texts
    ]


class HybridSearch:
    """Combines BM25 + Dense + RRF. (Đã implement sẵn — dùng classes ở trên)"""
    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        dense_results = self.dense.search(query, top_k=DENSE_TOP_K)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)


if __name__ == "__main__":
    print("Original:  Nhân viên được nghỉ phép năm")
    print(f"Segmented: {segment_vietnamese('Nhân viên được nghỉ phép năm')}")
