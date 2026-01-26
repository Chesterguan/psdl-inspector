"""Vocabulary API endpoints for OMOP concept lookup and search."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.services.vocabulary import get_vocabulary_service

# Try to import semantic service (may not be available if dependencies missing)
try:
    from app.services.vocabulary_sqlite import get_semantic_vocabulary_service
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


router = APIRouter()


# --- Response Models ---


class UnitInfo(BaseModel):
    """Unit information for a concept."""
    code: str = Field(..., description="UCUM unit code")
    name: str = Field(..., description="Unit name")
    concept_id: Optional[int] = Field(None, description="OMOP concept ID for the unit")


class ConceptResponse(BaseModel):
    """Full concept response with all enriched data."""
    concept_id: int = Field(..., description="OMOP concept ID")
    concept_name: str = Field(..., description="Concept name")
    concept_code: Optional[str] = Field(None, description="Source vocabulary code (e.g., LOINC)")
    domain_id: Optional[str] = Field(None, description="OMOP domain")
    vocabulary_id: Optional[str] = Field(None, description="Source vocabulary")
    concept_class_id: Optional[str] = Field(None, description="Concept class")
    synonyms: Optional[List[str]] = Field(None, description="Known synonyms")
    abbreviations: Optional[List[str]] = Field(None, description="Common abbreviations")
    search_terms: Optional[List[str]] = Field(None, description="Search terms")
    category: Optional[str] = Field(None, description="Category (lab_chemistry, vital_sign, etc.)")
    typical_units: Optional[List[UnitInfo]] = Field(None, description="Typical measurement units")


class AutocompleteItem(BaseModel):
    """Lightweight item for autocomplete dropdown."""
    concept_id: int
    concept_name: str
    concept_code: Optional[str] = None
    category: Optional[str] = None
    abbreviations: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search results response."""
    query: str
    total: int
    results: List[ConceptResponse]


class AutocompleteResponse(BaseModel):
    """Autocomplete suggestions response."""
    prefix: str
    suggestions: List[AutocompleteItem]


class VocabularyStats(BaseModel):
    """Vocabulary statistics."""
    total_concepts: int
    indexed_terms: int
    categories: dict


class VocabularyVersion(BaseModel):
    """Vocabulary version and source information."""
    vocabulary_source: str
    omop_cdm_version: str
    athena_download_date: str
    loinc_version: str
    enrichment_date: str
    enriched_concepts: int
    total_concepts: int


# --- Helper Functions ---


def clean_concept(concept: dict) -> dict:
    """Clean concept data by removing None values from lists."""
    cleaned = concept.copy()
    # Filter None values from list fields
    if cleaned.get("abbreviations"):
        cleaned["abbreviations"] = [a for a in cleaned["abbreviations"] if a is not None]
    if cleaned.get("search_terms"):
        cleaned["search_terms"] = [t for t in cleaned["search_terms"] if t is not None]
    if cleaned.get("synonyms"):
        cleaned["synonyms"] = [s for s in cleaned["synonyms"] if s is not None]
    return cleaned


# --- Endpoints ---


@router.get("/vocabulary/search", response_model=SearchResponse)
async def search_vocabulary(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
) -> SearchResponse:
    """Search the vocabulary by name, abbreviation, or search terms.

    Returns concepts matching the query, ranked by relevance.
    Supports filtering by category (e.g., lab_chemistry, vital_sign)
    and domain (e.g., Measurement, Observation).
    """
    service = get_vocabulary_service()

    try:
        results = service.search(q, limit=limit, category=category, domain=domain)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vocabulary not loaded: {e}")

    return SearchResponse(
        query=q,
        total=len(results),
        results=[ConceptResponse(**clean_concept(r)) for r in results],
    )


@router.get("/vocabulary/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_vocabulary(
    prefix: str = Query(..., min_length=2, description="Search prefix"),
    limit: int = Query(10, ge=1, le=50, description="Max suggestions"),
) -> AutocompleteResponse:
    """Get autocomplete suggestions for the vocabulary.

    Returns lightweight suggestions optimized for dropdown display.
    Use this for real-time autocomplete in the editor.
    """
    service = get_vocabulary_service()

    try:
        suggestions = service.autocomplete(prefix, limit=limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vocabulary not loaded: {e}")

    return AutocompleteResponse(
        prefix=prefix,
        suggestions=[AutocompleteItem(**s) for s in suggestions],
    )


@router.get("/vocabulary/concept/{concept_id}", response_model=ConceptResponse)
async def get_concept(concept_id: int) -> ConceptResponse:
    """Get a concept by its OMOP concept ID.

    Returns the full enriched concept data including abbreviations,
    search terms, category, and typical units.
    """
    service = get_vocabulary_service()

    try:
        concept = service.get_by_id(concept_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vocabulary not loaded: {e}")

    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")

    return ConceptResponse(**clean_concept(concept))


@router.get("/vocabulary/stats", response_model=VocabularyStats)
async def get_vocabulary_stats() -> VocabularyStats:
    """Get vocabulary statistics.

    Returns total concepts, indexed terms, and category distribution.
    """
    service = get_vocabulary_service()

    try:
        stats = service.get_stats()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vocabulary not loaded: {e}")

    return VocabularyStats(**stats)


@router.get("/vocabulary/version", response_model=VocabularyVersion)
async def get_vocabulary_version() -> VocabularyVersion:
    """Get vocabulary version and source information.

    Returns OMOP CDM version, LOINC version, download date, and enrichment info.
    Important for reproducibility and audit trails in certified bundles.
    """
    import json
    from pathlib import Path

    metadata_file = Path(__file__).parent.parent.parent / "data" / "vocabulary" / "vocabulary_metadata.json"

    if not metadata_file.exists():
        raise HTTPException(status_code=503, detail="Vocabulary metadata not found")

    with open(metadata_file) as f:
        metadata = json.load(f)

    loinc_version = "unknown"
    for vocab in metadata.get("vocabularies_included", []):
        if vocab.get("vocabulary_id") == "LOINC":
            loinc_version = vocab.get("vocabulary_version", "unknown")
            break

    return VocabularyVersion(
        vocabulary_source=metadata.get("vocabulary_source", "unknown"),
        omop_cdm_version=metadata.get("omop_cdm_version", "unknown"),
        athena_download_date=metadata.get("athena_download_date", "unknown"),
        loinc_version=loinc_version,
        enrichment_date=metadata.get("enrichment", {}).get("enrichment_date", "unknown"),
        enriched_concepts=metadata.get("enrichment", {}).get("enriched_concepts", 0),
        total_concepts=metadata.get("enrichment", {}).get("total_concepts", 0),
    )


# --- Population Concept Response ---

class PopulationConceptResponse(BaseModel):
    """Population concept response (SNOMED conditions, RxNorm medications)."""
    concept_id: int = Field(..., description="OMOP concept ID")
    concept_name: str = Field(..., description="Concept name")
    concept_code: Optional[str] = Field(None, description="Source vocabulary code")
    vocabulary_id: Optional[str] = Field(None, description="Source vocabulary (SNOMED, RxNorm)")
    domain_id: Optional[str] = Field(None, description="OMOP domain")
    concept_class_id: Optional[str] = Field(None, description="Concept class")
    abbreviations: Optional[List[str]] = Field(None, description="Common abbreviations")
    search_terms: Optional[List[str]] = Field(None, description="Search terms")
    category: Optional[str] = Field(None, description="Category")


class PopulationSearchResponse(BaseModel):
    """Population search results response."""
    query: str
    vocab_type: Optional[str]
    total: int
    results: List[PopulationConceptResponse]


class PopulationStats(BaseModel):
    """Population vocabulary statistics."""
    total_concepts: int
    concepts_with_embeddings: int
    vocabularies: dict


# --- Semantic Search Endpoints ---

@router.get("/vocabulary/semantic/search", response_model=SearchResponse)
async def semantic_search_vocabulary(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    category: Optional[str] = Query(None, description="Filter by category"),
) -> SearchResponse:
    """Semantic search LOINC vocabulary using embeddings.

    Uses text-embedding-3-small embeddings for semantic similarity search.
    Falls back to text search if embeddings unavailable.
    """
    if not SEMANTIC_AVAILABLE:
        raise HTTPException(status_code=503, detail="Semantic search not available")

    service = get_semantic_vocabulary_service()

    try:
        results = service.search_loinc(q, limit=limit, category=category, use_semantic=True)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Vocabulary database not loaded: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")

    return SearchResponse(
        query=q,
        total=len(results),
        results=[ConceptResponse(**clean_concept(r)) for r in results],
    )


@router.get("/vocabulary/population/search", response_model=PopulationSearchResponse)
async def search_population(
    q: str = Query(..., min_length=2, description="Search query"),
    type: Optional[str] = Query(None, description="Type: 'conditions' (SNOMED) or 'medications' (RxNorm)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    semantic: bool = Query(True, description="Use semantic search (embeddings)"),
) -> PopulationSearchResponse:
    """Search population vocabulary (SNOMED conditions, RxNorm medications).

    Args:
        q: Search query string
        type: Filter by 'conditions' (SNOMED) or 'medications' (RxNorm)
        limit: Maximum number of results
        semantic: Use semantic (embedding) search if available

    Returns:
        Matching concepts ranked by relevance
    """
    if not SEMANTIC_AVAILABLE:
        raise HTTPException(status_code=503, detail="Population search not available - semantic service missing")

    service = get_semantic_vocabulary_service()

    try:
        results = service.search_population(q, vocab_type=type, limit=limit, use_semantic=semantic)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Population database not loaded: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")

    return PopulationSearchResponse(
        query=q,
        vocab_type=type,
        total=len(results),
        results=[PopulationConceptResponse(**clean_concept(r)) for r in results],
    )


@router.get("/vocabulary/population/concept/{concept_id}", response_model=PopulationConceptResponse)
async def get_population_concept(concept_id: int) -> PopulationConceptResponse:
    """Get a population concept by its OMOP concept ID.

    Returns SNOMED condition or RxNorm medication concept.
    """
    if not SEMANTIC_AVAILABLE:
        raise HTTPException(status_code=503, detail="Population service not available")

    service = get_semantic_vocabulary_service()

    try:
        concept = service.get_population_by_id(concept_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Population database not loaded: {e}")

    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")

    return PopulationConceptResponse(**clean_concept(concept))


@router.get("/vocabulary/population/stats", response_model=PopulationStats)
async def get_population_stats() -> PopulationStats:
    """Get population vocabulary statistics.

    Returns total concepts, embedding coverage, and vocabulary distribution.
    """
    if not SEMANTIC_AVAILABLE:
        raise HTTPException(status_code=503, detail="Population service not available")

    service = get_semantic_vocabulary_service()

    try:
        stats = service.get_population_stats()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Population database not loaded: {e}")

    return PopulationStats(**stats)
