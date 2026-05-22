## psdl-vocab-search

Modular vocabulary search engine for the PSDL ecosystem. Provides a pluggable architecture of embedders (MiniLM, SapBERT, BioLORD, OpenAI), retrievers (FAISS, numpy, HNSW), and rerankers (rule-based, string-similarity, hybrid) that can be combined freely. Heavy ML dependencies (sentence-transformers, torch, faiss) are optional extras (`pip install psdl-vocab-search[ml]`); only numpy is required at install time.
