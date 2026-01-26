"""Embedder implementations for vocabulary search.

Available embedders:
- SentenceTransformerEmbedder: General sentence-transformers models
- SapBERTEmbedder: Medical entity linking (UMLS-trained)
- BioLORDEmbedder: Ontology-grounded biomedical embeddings

To add a new embedder:
1. Subclass BaseEmbedder
2. Implement model_name, dimension, and embed()
3. Register in factory.py
"""

from __future__ import annotations

from typing import List, Optional
import numpy as np

from app.services.vocabulary_search.base import BaseEmbedder


class SentenceTransformerEmbedder(BaseEmbedder):
    """Embedder using sentence-transformers library.

    Supports any model from sentence-transformers:
    - all-MiniLM-L6-v2 (fast, general purpose)
    - all-mpnet-base-v2 (higher quality, slower)
    - BioLORD-2023 (biomedical ontology-grounded)
    """

    # Known model dimensions
    KNOWN_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "FremyCompany/BioLORD-2023": 768,
        "FremyCompany/BioLORD-2023-S": 768,
    }

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._dimension: Optional[int] = self.KNOWN_DIMENSIONS.get(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Load model to get dimension
            self._load_model()
        return self._dimension

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self._model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        model = self._load_model()
        return model.encode(texts, show_progress_bar=len(texts) > 100, convert_to_numpy=True)


class SapBERTEmbedder(BaseEmbedder):
    """Embedder using SapBERT for medical entity linking.

    SapBERT was trained on UMLS to align medical concept synonyms.
    Better for matching medical abbreviations and synonyms.

    Models:
    - cambridgeltl/SapBERT-from-PubMedBERT-fulltext (English, recommended)
    - cambridgeltl/SapBERT-UMLS-2020AB-all-lang-from-XLMR (multilingual)
    """

    def __init__(self, model_name: str = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None
        self._dimension = 768  # PubMedBERT dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_model(self):
        if self._model is None:
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
            except ImportError:
                raise ImportError(
                    "transformers not installed. "
                    "Run: pip install transformers torch"
                )

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModel.from_pretrained(self._model_name)

            # Use GPU if available
            if torch.cuda.is_available():
                self._model = self._model.cuda()

            self._model.eval()

        return self._model, self._tokenizer

    def embed(self, texts: List[str]) -> np.ndarray:
        import torch

        model, tokenizer = self._load_model()
        device = next(model.parameters()).device

        all_embeddings = []
        batch_size = 128

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize
            inputs = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=25,  # SapBERT uses short max length
                return_tensors="pt"
            )

            # Move to device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Get embeddings
            with torch.no_grad():
                outputs = model(**inputs)
                # Use CLS token embedding
                cls_embeddings = outputs.last_hidden_state[:, 0, :]

            all_embeddings.append(cls_embeddings.cpu().numpy())

        return np.vstack(all_embeddings)


class BioLORDEmbedder(SentenceTransformerEmbedder):
    """Embedder using BioLORD-2023 for ontology-grounded embeddings.

    BioLORD is trained on concept definitions from UMLS and SNOMED-CT,
    producing embeddings that better match ontology structure.

    This is a convenience wrapper around SentenceTransformerEmbedder.
    """

    def __init__(self):
        super().__init__(model_name="FremyCompany/BioLORD-2023")


class OpenAIEmbedder(BaseEmbedder):
    """Embedder using OpenAI's embedding API.

    Requires OPENAI_API_KEY environment variable.
    """

    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self._model_name = model_name
        self._dimension = self.DIMENSIONS.get(model_name, 1536)
        self._client = None

    @property
    def model_name(self) -> str:
        return f"openai/{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai not installed. Run: pip install openai")

            self._client = OpenAI()
        return self._client

    def embed(self, texts: List[str]) -> np.ndarray:
        client = self._get_client()

        all_embeddings = []
        batch_size = 100  # OpenAI limit

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = client.embeddings.create(
                model=self._model_name,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings)


# Registry of available embedders
EMBEDDER_REGISTRY = {
    "minilm": lambda: SentenceTransformerEmbedder("all-MiniLM-L6-v2"),
    "minilm-l12": lambda: SentenceTransformerEmbedder("all-MiniLM-L12-v2"),
    "mpnet": lambda: SentenceTransformerEmbedder("all-mpnet-base-v2"),
    "sapbert": lambda: SapBERTEmbedder(),
    "biolord": lambda: BioLORDEmbedder(),
    "openai": lambda: OpenAIEmbedder(),
    "openai-large": lambda: OpenAIEmbedder("text-embedding-3-large"),
}


def get_embedder(name: str) -> BaseEmbedder:
    """Get embedder by name."""
    if name not in EMBEDDER_REGISTRY:
        raise ValueError(f"Unknown embedder: {name}. Available: {list(EMBEDDER_REGISTRY.keys())}")
    return EMBEDDER_REGISTRY[name]()
