"""Retriever implementations for vocabulary search.

Available retrievers:
- FAISSRetriever: Fast similarity search with FAISS
- NumpyRetriever: Simple brute-force (no dependencies, good for small vocab)

To add a new retriever:
1. Subclass BaseRetriever
2. Implement build_index(), search(), save(), load()
3. Register in factory.py
"""

from __future__ import annotations

from typing import List, Optional, Dict
import numpy as np

from psdl_vocab_search.base import BaseRetriever


class FAISSRetriever(BaseRetriever):
    """Fast retriever using Facebook's FAISS library.

    Uses IndexFlatIP (inner product) for cosine similarity on normalized vectors.
    """

    def __init__(self):
        self._index = None
        self._concept_ids: List[int] = []
        self._id_to_idx: Dict[int, int] = {}

    def build_index(self, embeddings: np.ndarray, concept_ids: List[int]) -> None:
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss not installed. Run: pip install faiss-cpu")

        self._concept_ids = concept_ids
        self._id_to_idx = {cid: idx for idx, cid in enumerate(concept_ids)}

        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(embeddings.astype(np.float32))

    def search(self, query_embedding: np.ndarray, k: int) -> List[tuple[int, float]]:
        if self._index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        # Reshape for FAISS
        query = query_embedding.reshape(1, -1).astype(np.float32)

        scores, indices = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self._concept_ids):
                concept_id = self._concept_ids[idx]
                results.append((concept_id, float(score)))

        return results

    def save(self, path: str) -> None:
        import faiss
        import pickle

        faiss.write_index(self._index, path)

        # Save concept IDs mapping
        meta_path = path + ".meta"
        with open(meta_path, 'wb') as f:
            pickle.dump(self._concept_ids, f)

    def load(self, path: str) -> bool:
        import faiss
        import pickle
        from pathlib import Path

        if not Path(path).exists():
            return False

        meta_path = path + ".meta"
        if not Path(meta_path).exists():
            return False

        try:
            self._index = faiss.read_index(path)
            with open(meta_path, 'rb') as f:
                self._concept_ids = pickle.load(f)
            self._id_to_idx = {cid: idx for idx, cid in enumerate(self._concept_ids)}
            return True
        except Exception:
            return False


class NumpyRetriever(BaseRetriever):
    """Simple brute-force retriever using numpy.

    No external dependencies. Good for small vocabularies (<10k concepts).
    """

    def __init__(self):
        self._embeddings: Optional[np.ndarray] = None
        self._concept_ids: List[int] = []

    def build_index(self, embeddings: np.ndarray, concept_ids: List[int]) -> None:
        self._embeddings = embeddings.astype(np.float32)
        self._concept_ids = concept_ids

    def search(self, query_embedding: np.ndarray, k: int) -> List[tuple[int, float]]:
        if self._embeddings is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        # Compute similarities (dot product on normalized vectors = cosine)
        query = query_embedding.astype(np.float32)
        similarities = self._embeddings @ query

        # Get top k
        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_indices:
            concept_id = self._concept_ids[idx]
            score = float(similarities[idx])
            results.append((concept_id, score))

        return results

    def save(self, path: str) -> None:
        import pickle

        with open(path, 'wb') as f:
            pickle.dump({
                "embeddings": self._embeddings,
                "concept_ids": self._concept_ids,
            }, f)

    def load(self, path: str) -> bool:
        import pickle
        from pathlib import Path

        if not Path(path).exists():
            return False

        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self._embeddings = data["embeddings"]
            self._concept_ids = data["concept_ids"]
            return True
        except Exception:
            return False


class HNSWRetriever(BaseRetriever):
    """Approximate nearest neighbor using HNSW (via hnswlib).

    Faster than FAISS for large vocabularies, slightly less accurate.
    """

    def __init__(self, ef_construction: int = 200, M: int = 16):
        self._index = None
        self._concept_ids: List[int] = []
        self._ef_construction = ef_construction
        self._M = M
        self._dimension: Optional[int] = None

    def build_index(self, embeddings: np.ndarray, concept_ids: List[int]) -> None:
        try:
            import hnswlib
        except ImportError:
            raise ImportError("hnswlib not installed. Run: pip install hnswlib")

        self._concept_ids = concept_ids
        self._dimension = embeddings.shape[1]
        num_elements = len(concept_ids)

        self._index = hnswlib.Index(space='ip', dim=self._dimension)
        self._index.init_index(
            max_elements=num_elements,
            ef_construction=self._ef_construction,
            M=self._M
        )
        self._index.add_items(embeddings.astype(np.float32), list(range(num_elements)))
        self._index.set_ef(50)  # Search-time parameter

    def search(self, query_embedding: np.ndarray, k: int) -> List[tuple[int, float]]:
        if self._index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        labels, distances = self._index.knn_query(
            query_embedding.reshape(1, -1).astype(np.float32),
            k=k
        )

        results = []
        for idx, dist in zip(labels[0], distances[0]):
            if 0 <= idx < len(self._concept_ids):
                concept_id = self._concept_ids[idx]
                # HNSW returns distances, convert to similarity for IP space
                results.append((concept_id, float(dist)))

        return results

    def save(self, path: str) -> None:
        import pickle

        self._index.save_index(path)

        meta_path = path + ".meta"
        with open(meta_path, 'wb') as f:
            pickle.dump({
                "concept_ids": self._concept_ids,
                "dimension": self._dimension,
            }, f)

    def load(self, path: str) -> bool:
        import hnswlib
        import pickle
        from pathlib import Path

        if not Path(path).exists():
            return False

        meta_path = path + ".meta"
        if not Path(meta_path).exists():
            return False

        try:
            with open(meta_path, 'rb') as f:
                meta = pickle.load(f)

            self._concept_ids = meta["concept_ids"]
            self._dimension = meta["dimension"]

            self._index = hnswlib.Index(space='ip', dim=self._dimension)
            self._index.load_index(path, max_elements=len(self._concept_ids))
            self._index.set_ef(50)
            return True
        except Exception:
            return False


class PreloadedFAISSRetriever(BaseRetriever):
    """FAISS retriever that loads a pre-built index from disk.

    Unlike FAISSRetriever (which builds the index from embeddings), this
    retriever reads an already-built index.faiss + index.faiss.meta file pair
    produced by the offline BioLORD build script.  The *index_dir* argument is
    primarily an injection point for tests; production code resolves it via
    ``_index_loader.get_index_dir()``.

    ``build_index()`` is intentionally a no-op because the index is pre-built.
    """

    def __init__(self, index_dir=None):
        # index_dir: Path | str | None.  None → resolved lazily on first search.
        self._index_dir = index_dir
        self._index = None
        self._concept_ids: List[int] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        import faiss
        import pickle
        from pathlib import Path

        if self._index_dir is None:
            from psdl_vocab_search._index_loader import get_index_dir
            self._index_dir = get_index_dir()

        index_dir = Path(self._index_dir)
        index_path = index_dir / "index.faiss"
        meta_path = index_dir / "index.faiss.meta"

        self._index = faiss.read_index(str(index_path))
        with open(meta_path, "rb") as f:
            self._concept_ids = pickle.load(f)

        self._loaded = True

    # build_index is a no-op — the index is pre-built offline.
    def build_index(self, embeddings, concept_ids: List[int]) -> None:  # type: ignore[override]
        pass

    def search(self, query_embedding, k: int) -> List[tuple[int, float]]:
        self._ensure_loaded()

        query = query_embedding.reshape(1, -1).astype("float32")
        scores, indices = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self._concept_ids):
                results.append((self._concept_ids[idx], float(score)))

        return results

    def save(self, path: str) -> None:
        # Pre-built index — saving is a no-op (the source-of-truth is the cached files).
        pass

    def load(self, path: str) -> bool:
        # Pre-built index — the standard path-based load is not used.
        return False


# Registry of available retrievers
RETRIEVER_REGISTRY = {
    "faiss": FAISSRetriever,
    "faiss-preloaded": PreloadedFAISSRetriever,
    "numpy": NumpyRetriever,
    "hnsw": HNSWRetriever,
}


def get_retriever(name: str) -> BaseRetriever:
    """Get retriever by name."""
    if name not in RETRIEVER_REGISTRY:
        raise ValueError(f"Unknown retriever: {name}. Available: {list(RETRIEVER_REGISTRY.keys())}")
    return RETRIEVER_REGISTRY[name]()
