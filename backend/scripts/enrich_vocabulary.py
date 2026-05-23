#!/usr/bin/env python3
"""
OMOP Vocabulary Enrichment Pipeline

This script:
1. Extracts relevant concepts from Athena OMOP vocabulary
2. Enriches them with LLM-generated metadata via OpenAI Batch API
3. Builds a searchable vocabulary for PSDL Inspector

Usage:
    python enrich_vocabulary.py extract --vocab-zip /path/to/vocabulary.zip --output concepts.json
    python enrich_vocabulary.py prepare-batch --concepts concepts.json --output batch_requests.jsonl
    python enrich_vocabulary.py submit-batch --requests batch_requests.jsonl
    python enrich_vocabulary.py check-batch --batch-id batch_xxx
    python enrich_vocabulary.py process-results --batch-id batch_xxx --concepts concepts.json --output vocabulary.json

    # Or run full pipeline:
    python enrich_vocabulary.py full-pipeline --vocab-zip /path/to/vocabulary.zip --output vocabulary.json
"""

import argparse
import csv
import json
import os
import sys
import time
import zipfile
from dataclasses import dataclass, asdict
from io import TextIOWrapper
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass
class Concept:
    """OMOP Concept representation."""
    concept_id: int
    concept_name: str
    domain_id: str
    vocabulary_id: str
    concept_class_id: str
    standard_concept: str
    concept_code: str
    synonyms: list[str] = None

    def __post_init__(self):
        if self.synonyms is None:
            self.synonyms = []


@dataclass
class EnrichedConcept:
    """Enriched concept with LLM-generated metadata."""
    concept_id: int
    concept_name: str
    domain_id: str
    vocabulary_id: str
    concept_class_id: str
    concept_code: str
    synonyms: list[str]
    # LLM-enriched fields
    abbreviations: list[str]
    search_terms: list[str]
    category: str
    typical_units: list[dict]  # [{"code": "mg/dL", "name": "...", "concept_id": 8840}]


# Enrichment prompt template
ENRICHMENT_PROMPT = """You are generating search metadata for a clinical OMOP concept.

CRITICAL: Be conservative and precise. Only include information you are 100% certain about.
If unsure about ANY field, return null for that field. Precision is more important than coverage.

Given:
- Name: {concept_name}
- Domain: {domain_id}
- Vocabulary: {vocabulary_id} ({concept_code})
- Class: {concept_class_id}
- Known synonyms: {synonyms}

Generate ONLY:

1. abbreviations: List of 2-5 common clinical abbreviations.
   ONLY include widely recognized, standard abbreviations used in clinical practice.
   For Drug concepts, abbreviations must be recognized short names for the drug itself (e.g., APAP for acetaminophen, HCTZ for hydrochlorothiazide), NOT administration routes (IV, PO) or clinical parameters (BP, HR).
   If unsure or no standard abbreviations exist, return null.

2. search_terms: List of 3-7 alternate search terms.
   Focus on exact variations of the concept name, NOT clinical interpretations or related concepts.
   If unsure, return null.

3. category: One of [lab_chemistry, lab_hematology, lab_microbiology, lab_urinalysis,
   vital_sign, imaging, procedure, observation, medication, other]
   If unsure, return "other".

4. typical_units: List of 1-3 units using EXACT UCUM codes only.
   STRICT UCUM format required. Examples of valid UCUM codes:
   - "mg/dL" (milligram per deciliter)
   - "mmol/L" (millimole per liter)
   - "g/dL" (gram per deciliter)
   - "mEq/L" (milliequivalent per liter)
   - "/min" (per minute, for rates like heart rate)
   - "mm[Hg]" (millimeter of mercury)
   - "%" (percent)
   - "umol/L" (micromole per liter - use ASCII 'u', NOT Unicode 'µ')

   Format: [{{"code": "mg/dL", "name": "milligram per deciliter"}}]
   If qualitative test (no units), unsure, or cannot provide exact UCUM code, return null.

Return valid JSON only. No explanations. Use null for uncertain fields."""


# Common UCUM units with their concept IDs
UCUM_UNITS = {
    "mg/dL": {"concept_id": 8840, "name": "milligram per deciliter"},
    "mmol/L": {"concept_id": 8753, "name": "millimole per liter"},
    "g/dL": {"concept_id": 8713, "name": "gram per deciliter"},
    "g/L": {"concept_id": 8636, "name": "gram per liter"},
    "/min": {"concept_id": 8541, "name": "per minute"},
    "mL/min": {"concept_id": 8795, "name": "milliliter per minute"},
    "mL/min/1.73m2": {"concept_id": 720870, "name": "milliliter per minute per 1.73 square meter"},
    "%": {"concept_id": 8554, "name": "percent"},
    "10*3/uL": {"concept_id": 8848, "name": "thousand per microliter"},
    "10*6/uL": {"concept_id": 8815, "name": "million per microliter"},
    "10*12/L": {"concept_id": 8734, "name": "trillion per liter"},
    "ng/mL": {"concept_id": 8842, "name": "nanogram per milliliter"},
    "ng/dL": {"concept_id": 8817, "name": "nanogram per deciliter"},
    "pg/mL": {"concept_id": 8845, "name": "picogram per milliliter"},
    "ug/dL": {"concept_id": 8837, "name": "microgram per deciliter"},
    "ug/L": {"concept_id": 8829, "name": "microgram per liter"},
    "mEq/L": {"concept_id": 9557, "name": "milliequivalent per liter"},
    "U/L": {"concept_id": 8645, "name": "unit per liter"},
    "IU/L": {"concept_id": 8923, "name": "international unit per liter"},
    "IU/mL": {"concept_id": 8985, "name": "international unit per milliliter"},
    "mm[Hg]": {"concept_id": 8876, "name": "millimeter of mercury"},
    "mmHg": {"concept_id": 8876, "name": "millimeter of mercury"},
    "kg": {"concept_id": 9529, "name": "kilogram"},
    "cm": {"concept_id": 8582, "name": "centimeter"},
    "kg/m2": {"concept_id": 9531, "name": "kilogram per square meter"},
    "Cel": {"concept_id": 586323, "name": "degree Celsius"},
    "degC": {"concept_id": 586323, "name": "degree Celsius"},
    "[degF]": {"concept_id": 9289, "name": "degree Fahrenheit"},
    "s": {"concept_id": 8555, "name": "second"},
    "umol/L": {"concept_id": 8749, "name": "micromole per liter"},
    "fL": {"concept_id": 8583, "name": "femtoliter"},
    "pg": {"concept_id": 8564, "name": "picogram"},
}


def extract_concepts(vocab_zip_path: str, output_path: str,
                     domains: list[str] = None,
                     vocabularies: list[str] = None,
                     concept_classes: list[str] = None,
                     limit: int = None) -> list[Concept]:
    """
    Extract relevant concepts from Athena vocabulary zip.

    Args:
        vocab_zip_path: Path to vocabulary_download_v5.zip
        output_path: Path to save extracted concepts JSON
        domains: Filter by domain_id (default: Measurement, Observation)
        vocabularies: Filter by vocabulary_id (default: LOINC)
        concept_classes: Filter by concept_class_id (default: Lab Test, Clinical Observation).
            Pass None (or an empty list) to skip the concept-class filter entirely and accept
            any class within the specified domains/vocabularies.
        limit: Limit number of concepts (for testing)

    Returns:
        List of extracted Concept objects
    """
    if domains is None:
        domains = ["Measurement", "Observation"]
    if vocabularies is None:
        vocabularies = ["LOINC"]
    # NOTE: concept_classes=None means "no class filter" (accept any class).
    # Only apply the default when the caller passes a sentinel value — we use
    # the empty-list sentinel so existing callers that pass None explicitly get
    # the any-class behaviour they asked for.  The legacy default is preserved
    # by keeping the original default in the signature.
    _apply_class_filter = bool(concept_classes)
    if concept_classes is None:
        concept_classes = []  # normalise for display only

    print(f"Extracting concepts from {vocab_zip_path}")
    print(f"  Domains: {domains}")
    print(f"  Vocabularies: {vocabularies}")
    print(f"  Concept classes: {'(any)' if not _apply_class_filter else concept_classes}")

    concepts = {}
    synonyms_map = {}

    with zipfile.ZipFile(vocab_zip_path, 'r') as zf:
        # First, load synonyms
        print("Loading synonyms...")
        with zf.open('CONCEPT_SYNONYM.csv') as f:
            reader = csv.DictReader(TextIOWrapper(f, 'utf-8'), delimiter='\t')
            for row in reader:
                concept_id = int(row['concept_id'])
                synonym = row['concept_synonym_name']
                # Filter to English synonyms (language_concept_id 4180186)
                lang_id = row.get('language_concept_id', '')
                if lang_id == '4180186' or not lang_id:  # English or unknown
                    if concept_id not in synonyms_map:
                        synonyms_map[concept_id] = []
                    synonyms_map[concept_id].append(synonym)

        print(f"Loaded {len(synonyms_map)} concept synonyms")

        # Load concepts
        print("Loading concepts...")
        with zf.open('CONCEPT.csv') as f:
            reader = csv.DictReader(TextIOWrapper(f, 'utf-8'), delimiter='\t')
            count = 0
            for row in reader:
                # Filter by standard concept
                if row['standard_concept'] != 'S':
                    continue

                # Filter by domain
                if row['domain_id'] not in domains:
                    continue

                # Filter by vocabulary
                if row['vocabulary_id'] not in vocabularies:
                    continue

                # Filter by concept class (skip filter if none specified)
                if _apply_class_filter and row['concept_class_id'] not in concept_classes:
                    continue

                concept_id = int(row['concept_id'])
                concept = Concept(
                    concept_id=concept_id,
                    concept_name=row['concept_name'],
                    domain_id=row['domain_id'],
                    vocabulary_id=row['vocabulary_id'],
                    concept_class_id=row['concept_class_id'],
                    standard_concept=row['standard_concept'],
                    concept_code=row['concept_code'],
                    synonyms=synonyms_map.get(concept_id, [])
                )
                concepts[concept_id] = concept
                count += 1

                if limit and count >= limit:
                    break

                if count % 10000 == 0:
                    print(f"  Processed {count} concepts...")

    print(f"Extracted {len(concepts)} concepts")

    # Save to JSON
    concepts_list = [asdict(c) for c in concepts.values()]
    with open(output_path, 'w') as f:
        json.dump(concepts_list, f, indent=2)

    print(f"Saved to {output_path}")
    return list(concepts.values())


def prepare_batch_requests(concepts_path: str, output_path: str,
                           batch_size: int = 1000) -> str:
    """
    Prepare OpenAI Batch API requests in JSONL format.

    Args:
        concepts_path: Path to concepts JSON file
        output_path: Path to save batch requests JSONL
        batch_size: Number of concepts per batch file (for splitting large jobs)

    Returns:
        Path to the JSONL file
    """
    print(f"Preparing batch requests from {concepts_path}")

    with open(concepts_path, 'r') as f:
        concepts = json.load(f)

    print(f"Loaded {len(concepts)} concepts")

    requests = []
    for concept in concepts:
        # Build prompt
        synonyms_str = ", ".join(concept['synonyms'][:10]) if concept['synonyms'] else "None"
        prompt = ENRICHMENT_PROMPT.format(
            concept_name=concept['concept_name'],
            domain_id=concept['domain_id'],
            vocabulary_id=concept['vocabulary_id'],
            concept_code=concept['concept_code'],
            concept_class_id=concept['concept_class_id'],
            synonyms=synonyms_str
        )

        # Create batch request
        request = {
            "custom_id": f"concept_{concept['concept_id']}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a clinical terminology expert. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 500,
                "temperature": 0.1
            }
        }
        requests.append(request)

    # Write JSONL
    with open(output_path, 'w') as f:
        for req in requests:
            f.write(json.dumps(req) + '\n')

    print(f"Wrote {len(requests)} requests to {output_path}")
    return output_path


def submit_batch(requests_path: str) -> str:
    """
    Submit batch requests to OpenAI Batch API.

    Args:
        requests_path: Path to JSONL file with batch requests

    Returns:
        Batch ID
    """
    client = OpenAI()

    print(f"Uploading {requests_path} to OpenAI...")

    # Upload file
    with open(requests_path, 'rb') as f:
        batch_file = client.files.create(file=f, purpose="batch")

    print(f"Uploaded file: {batch_file.id}")

    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "PSDL Inspector vocabulary enrichment"
        }
    )

    print(f"Created batch: {batch.id}")
    print(f"Status: {batch.status}")

    return batch.id


def check_batch_status(batch_id: str) -> dict:
    """
    Check the status of a batch job.

    Args:
        batch_id: The batch ID

    Returns:
        Batch status dict
    """
    client = OpenAI()
    batch = client.batches.retrieve(batch_id)

    status = {
        "id": batch.id,
        "status": batch.status,
        "created_at": batch.created_at,
        "completed_at": batch.completed_at,
        "failed_at": batch.failed_at,
        "request_counts": {
            "total": batch.request_counts.total,
            "completed": batch.request_counts.completed,
            "failed": batch.request_counts.failed
        }
    }

    if batch.output_file_id:
        status["output_file_id"] = batch.output_file_id
    if batch.error_file_id:
        status["error_file_id"] = batch.error_file_id

    return status


def download_batch_results(batch_id: str, output_dir: str) -> str:
    """
    Download batch results from OpenAI.

    Args:
        batch_id: The batch ID
        output_dir: Directory to save results

    Returns:
        Path to downloaded results file
    """
    client = OpenAI()
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        raise ValueError(f"Batch not completed. Status: {batch.status}")

    if not batch.output_file_id:
        raise ValueError("No output file available")

    # Download output file
    output_path = os.path.join(output_dir, f"batch_results_{batch_id}.jsonl")

    print(f"Downloading results to {output_path}")

    content = client.files.content(batch.output_file_id)
    with open(output_path, 'wb') as f:
        f.write(content.read())

    print(f"Downloaded {output_path}")
    return output_path


def process_results(results_path: str, concepts_path: str, output_path: str) -> list[EnrichedConcept]:
    """
    Process batch results and build final vocabulary.

    Args:
        results_path: Path to batch results JSONL
        concepts_path: Path to original concepts JSON
        output_path: Path to save final vocabulary JSON

    Returns:
        List of EnrichedConcept objects
    """
    print(f"Processing results from {results_path}")

    # Load original concepts
    with open(concepts_path, 'r') as f:
        concepts = {c['concept_id']: c for c in json.load(f)}

    # Load results
    results = {}
    failed_requests = []
    with open(results_path, 'r') as f:
        for line in f:
            result = json.loads(line)
            custom_id = result['custom_id']
            concept_id = int(custom_id.replace('concept_', ''))

            if result['response']['status_code'] == 200:
                try:
                    content = result['response']['body']['choices'][0]['message']['content']
                    enrichment = json.loads(content)
                    results[concept_id] = enrichment
                except (KeyError, json.JSONDecodeError) as e:
                    print(f"Error parsing result for concept {concept_id}: {e}")
                    failed_requests.append({"concept_id": concept_id, "error": str(e)})
            else:
                print(f"Request failed for concept {concept_id}: {result['response']}")
                failed_requests.append({
                    "concept_id": concept_id,
                    "error": f"HTTP {result['response']['status_code']}"
                })

    print(f"Parsed {len(results)} successful results, {len(failed_requests)} failures")

    # Build enriched concepts with null tracking
    enriched = []
    null_tracking = {
        "abbreviations": [],
        "search_terms": [],
        "typical_units": [],
        "unmatched_units": [],
        "failed_requests": failed_requests,
        "missing_results": []  # Concepts with no result at all
    }

    for concept_id, concept in concepts.items():
        enrichment = results.get(concept_id)

        if enrichment is None:
            null_tracking['missing_results'].append(concept_id)
            enrichment = {}

        # Track null values
        if enrichment.get('abbreviations') is None:
            null_tracking['abbreviations'].append(concept_id)
        if enrichment.get('search_terms') is None:
            null_tracking['search_terms'].append(concept_id)
        if enrichment.get('typical_units') is None:
            null_tracking['typical_units'].append(concept_id)

        # Process units - add concept_ids from our mapping, track unmatched
        typical_units = []
        raw_units = enrichment.get('typical_units') or []
        for unit in raw_units:
            if unit is None:
                continue
            unit_code = unit.get('code', '')
            if unit_code in UCUM_UNITS:
                typical_units.append({
                    "code": unit_code,
                    "name": UCUM_UNITS[unit_code]['name'],
                    "concept_id": UCUM_UNITS[unit_code]['concept_id']
                })
            else:
                # Track unmatched unit for post-processing
                null_tracking['unmatched_units'].append({
                    "concept_id": concept_id,
                    "concept_name": concept['concept_name'],
                    "unit_code": unit_code,
                    "unit_name": unit.get('name', '')
                })
                # Still include it but without concept_id
                typical_units.append(unit)

        enriched_concept = EnrichedConcept(
            concept_id=concept_id,
            concept_name=concept['concept_name'],
            domain_id=concept['domain_id'],
            vocabulary_id=concept['vocabulary_id'],
            concept_class_id=concept['concept_class_id'],
            concept_code=concept['concept_code'],
            synonyms=concept.get('synonyms', []),
            abbreviations=enrichment.get('abbreviations') or [],
            search_terms=enrichment.get('search_terms') or [],
            category=enrichment.get('category') or 'other',
            typical_units=typical_units
        )
        enriched.append(enriched_concept)

    # Save enriched vocabulary
    enriched_list = [asdict(c) for c in enriched]
    with open(output_path, 'w') as f:
        json.dump(enriched_list, f, indent=2)

    # Save null tracking report for post-processing
    null_report_path = output_path.replace('.json', '_null_report.json')
    null_summary = {
        "total_concepts": len(concepts),
        "successful_enrichments": len(results),
        "null_counts": {
            "abbreviations": len(null_tracking['abbreviations']),
            "search_terms": len(null_tracking['search_terms']),
            "typical_units": len(null_tracking['typical_units']),
            "unmatched_units": len(null_tracking['unmatched_units']),
            "failed_requests": len(null_tracking['failed_requests']),
            "missing_results": len(null_tracking['missing_results'])
        },
        "details": null_tracking
    }
    with open(null_report_path, 'w') as f:
        json.dump(null_summary, f, indent=2)

    print(f"\nSaved {len(enriched)} enriched concepts to {output_path}")
    print(f"Null report saved to {null_report_path}")
    print(f"\nSummary:")
    print(f"  - Total concepts: {len(concepts)}")
    print(f"  - Successful enrichments: {len(results)}")
    print(f"  - Failed requests: {len(failed_requests)}")
    print(f"  - Null abbreviations: {null_summary['null_counts']['abbreviations']}")
    print(f"  - Null search_terms: {null_summary['null_counts']['search_terms']}")
    print(f"  - Null typical_units: {null_summary['null_counts']['typical_units']}")
    print(f"  - Unmatched units: {null_summary['null_counts']['unmatched_units']}")

    return enriched


def wait_for_batch(batch_id: str, poll_interval: int = 60) -> dict:
    """
    Wait for a batch to complete, polling periodically.

    Args:
        batch_id: The batch ID
        poll_interval: Seconds between status checks

    Returns:
        Final batch status
    """
    print(f"Waiting for batch {batch_id} to complete...")

    while True:
        status = check_batch_status(batch_id)
        print(f"  Status: {status['status']} "
              f"({status['request_counts']['completed']}/{status['request_counts']['total']} completed)")

        if status['status'] in ['completed', 'failed', 'cancelled', 'expired']:
            return status

        time.sleep(poll_interval)


def enrich_sync(concepts_path: str, output_path: str,
                requests_per_minute: int = 50) -> list[EnrichedConcept]:
    """
    Enrich concepts synchronously using standard API (for testing small batches).

    Args:
        concepts_path: Path to concepts JSON file
        output_path: Path to save enriched vocabulary JSON
        requests_per_minute: Rate limit (default 50 RPM, OpenAI allows 500+ for gpt-4o-mini)

    Returns:
        List of EnrichedConcept objects
    """
    client = OpenAI()

    # Calculate delay between requests for rate limiting
    delay_between_requests = 60.0 / requests_per_minute

    with open(concepts_path, 'r') as f:
        concepts = json.load(f)

    print(f"Enriching {len(concepts)} concepts synchronously...")

    enriched = []
    null_tracking = {
        "abbreviations": [],
        "search_terms": [],
        "typical_units": [],
        "unmatched_units": []  # Units returned but not in our UCUM mapping
    }

    for i, concept in enumerate(concepts):
        print(f"  [{i+1}/{len(concepts)}] {concept['concept_name'][:50]}...")

        # Build prompt
        synonyms_str = ", ".join(concept.get('synonyms', [])[:10]) or "None"
        prompt = ENRICHMENT_PROMPT.format(
            concept_name=concept['concept_name'],
            domain_id=concept['domain_id'],
            vocabulary_id=concept['vocabulary_id'],
            concept_code=concept['concept_code'],
            concept_class_id=concept['concept_class_id'],
            synonyms=synonyms_str
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a clinical terminology expert. Return valid JSON only. Use null for any field you are not 100% certain about."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.1
            )

            enrichment = json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"    Error: {e}")
            enrichment = {}

        # Rate limiting - sleep between requests
        if i < len(concepts) - 1:  # Don't sleep after last request
            time.sleep(delay_between_requests)

        # Track null values
        if enrichment.get('abbreviations') is None:
            null_tracking['abbreviations'].append(concept['concept_id'])
        if enrichment.get('search_terms') is None:
            null_tracking['search_terms'].append(concept['concept_id'])
        if enrichment.get('typical_units') is None:
            null_tracking['typical_units'].append(concept['concept_id'])

        # Process units - add concept_ids from our mapping, track unmatched
        typical_units = []
        raw_units = enrichment.get('typical_units') or []
        for unit in raw_units:
            if unit is None:
                continue
            unit_code = unit.get('code', '')
            if unit_code in UCUM_UNITS:
                typical_units.append({
                    "code": unit_code,
                    "name": UCUM_UNITS[unit_code]['name'],
                    "concept_id": UCUM_UNITS[unit_code]['concept_id']
                })
            else:
                # Track unmatched unit for post-processing
                null_tracking['unmatched_units'].append({
                    "concept_id": concept['concept_id'],
                    "concept_name": concept['concept_name'],
                    "unit_code": unit_code,
                    "unit_name": unit.get('name', '')
                })
                # Still include it but without concept_id
                typical_units.append(unit)

        enriched_concept = EnrichedConcept(
            concept_id=concept['concept_id'],
            concept_name=concept['concept_name'],
            domain_id=concept['domain_id'],
            vocabulary_id=concept['vocabulary_id'],
            concept_class_id=concept['concept_class_id'],
            concept_code=concept['concept_code'],
            synonyms=concept.get('synonyms', []),
            abbreviations=enrichment.get('abbreviations') or [],
            search_terms=enrichment.get('search_terms') or [],
            category=enrichment.get('category') or 'other',
            typical_units=typical_units
        )
        enriched.append(enriched_concept)

    # Save enriched vocabulary
    enriched_list = [asdict(c) for c in enriched]
    with open(output_path, 'w') as f:
        json.dump(enriched_list, f, indent=2)

    # Save null tracking report for post-processing
    null_report_path = output_path.replace('.json', '_null_report.json')
    null_summary = {
        "total_concepts": len(concepts),
        "null_counts": {
            "abbreviations": len(null_tracking['abbreviations']),
            "search_terms": len(null_tracking['search_terms']),
            "typical_units": len(null_tracking['typical_units']),
            "unmatched_units": len(null_tracking['unmatched_units'])
        },
        "details": null_tracking
    }
    with open(null_report_path, 'w') as f:
        json.dump(null_summary, f, indent=2)

    print(f"\nSaved {len(enriched)} enriched concepts to {output_path}")
    print(f"Null report saved to {null_report_path}")
    print(f"\nNull summary:")
    print(f"  - abbreviations: {null_summary['null_counts']['abbreviations']} nulls")
    print(f"  - search_terms: {null_summary['null_counts']['search_terms']} nulls")
    print(f"  - typical_units: {null_summary['null_counts']['typical_units']} nulls")
    print(f"  - unmatched_units: {null_summary['null_counts']['unmatched_units']} unmatched")

    return enriched


def run_full_pipeline(vocab_zip_path: str, output_path: str,
                      limit: int = None, wait: bool = True) -> str:
    """
    Run the full enrichment pipeline.

    Args:
        vocab_zip_path: Path to Athena vocabulary zip
        output_path: Path to save final vocabulary JSON
        limit: Limit concepts for testing
        wait: Whether to wait for batch completion

    Returns:
        Path to final vocabulary or batch ID if not waiting
    """
    output_dir = os.path.dirname(output_path) or '.'
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Extract concepts
    concepts_path = os.path.join(output_dir, 'extracted_concepts.json')
    extract_concepts(vocab_zip_path, concepts_path, limit=limit)

    # Step 2: Prepare batch requests
    requests_path = os.path.join(output_dir, 'batch_requests.jsonl')
    prepare_batch_requests(concepts_path, requests_path)

    # Step 3: Submit batch
    batch_id = submit_batch(requests_path)

    if not wait:
        print(f"\nBatch submitted: {batch_id}")
        print(f"Run 'python {__file__} check-batch --batch-id {batch_id}' to check status")
        print(f"Run 'python {__file__} process-results --batch-id {batch_id} "
              f"--concepts {concepts_path} --output {output_path}' when complete")
        return batch_id

    # Step 4: Wait for completion
    status = wait_for_batch(batch_id)

    if status['status'] != 'completed':
        raise RuntimeError(f"Batch failed with status: {status['status']}")

    # Step 5: Download and process results
    results_path = download_batch_results(batch_id, output_dir)
    process_results(results_path, concepts_path, output_path)

    print(f"\nPipeline complete! Vocabulary saved to {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='OMOP Vocabulary Enrichment Pipeline')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract concepts from Athena vocabulary')
    extract_parser.add_argument('--vocab-zip', required=True, help='Path to vocabulary zip file')
    extract_parser.add_argument('--output', required=True, help='Output JSON path')
    extract_parser.add_argument('--domains', nargs='+', default=None, help='Domain IDs to filter')
    extract_parser.add_argument('--vocabularies', nargs='+', default=None, help='Vocabulary IDs to filter')
    extract_parser.add_argument('--concept-classes', nargs='+', default=None, help='Concept class IDs to filter')
    extract_parser.add_argument('--limit', type=int, default=None, help='Limit number of concepts')

    # Prepare batch command
    prepare_parser = subparsers.add_parser('prepare-batch', help='Prepare OpenAI batch requests')
    prepare_parser.add_argument('--concepts', required=True, help='Concepts JSON path')
    prepare_parser.add_argument('--output', required=True, help='Output JSONL path')

    # Submit batch command
    submit_parser = subparsers.add_parser('submit-batch', help='Submit batch to OpenAI')
    submit_parser.add_argument('--requests', required=True, help='Batch requests JSONL path')

    # Check batch command
    check_parser = subparsers.add_parser('check-batch', help='Check batch status')
    check_parser.add_argument('--batch-id', required=True, help='Batch ID')

    # Download results command
    download_parser = subparsers.add_parser('download-results', help='Download batch results')
    download_parser.add_argument('--batch-id', required=True, help='Batch ID')
    download_parser.add_argument('--output-dir', required=True, help='Output directory')

    # Process results command
    process_parser = subparsers.add_parser('process-results', help='Process batch results')
    process_parser.add_argument('--results', help='Results JSONL path (or use --batch-id)')
    process_parser.add_argument('--batch-id', help='Batch ID to download results from')
    process_parser.add_argument('--concepts', required=True, help='Original concepts JSON path')
    process_parser.add_argument('--output', required=True, help='Output vocabulary JSON path')

    # Sync enrichment command (for testing)
    sync_parser = subparsers.add_parser('enrich-sync', help='Enrich concepts synchronously (for testing)')
    sync_parser.add_argument('--concepts', required=True, help='Concepts JSON path')
    sync_parser.add_argument('--output', required=True, help='Output vocabulary JSON path')

    # Full pipeline command
    pipeline_parser = subparsers.add_parser('full-pipeline', help='Run full enrichment pipeline')
    pipeline_parser.add_argument('--vocab-zip', required=True, help='Path to vocabulary zip file')
    pipeline_parser.add_argument('--output', required=True, help='Output vocabulary JSON path')
    pipeline_parser.add_argument('--limit', type=int, default=None, help='Limit concepts for testing')
    pipeline_parser.add_argument('--no-wait', action='store_true', help='Do not wait for batch completion')

    args = parser.parse_args()

    if args.command == 'extract':
        extract_concepts(
            args.vocab_zip,
            args.output,
            domains=args.domains,
            vocabularies=args.vocabularies,
            concept_classes=args.concept_classes,
            limit=args.limit
        )

    elif args.command == 'prepare-batch':
        prepare_batch_requests(args.concepts, args.output)

    elif args.command == 'submit-batch':
        batch_id = submit_batch(args.requests)
        print(f"Batch ID: {batch_id}")

    elif args.command == 'check-batch':
        status = check_batch_status(args.batch_id)
        print(json.dumps(status, indent=2))

    elif args.command == 'download-results':
        path = download_batch_results(args.batch_id, args.output_dir)
        print(f"Downloaded to: {path}")

    elif args.command == 'process-results':
        if args.batch_id:
            output_dir = os.path.dirname(args.output) or '.'
            results_path = download_batch_results(args.batch_id, output_dir)
        elif args.results:
            results_path = args.results
        else:
            parser.error("Either --results or --batch-id is required")

        process_results(results_path, args.concepts, args.output)

    elif args.command == 'enrich-sync':
        enrich_sync(args.concepts, args.output)

    elif args.command == 'full-pipeline':
        run_full_pipeline(
            args.vocab_zip,
            args.output,
            limit=args.limit,
            wait=not args.no_wait
        )

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
