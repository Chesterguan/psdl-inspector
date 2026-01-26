"""Vocabulary enrichment service for AI-generated PSDL scenarios.

Takes generated PSDL YAML and enriches signal definitions with real
OMOP concept IDs, codes, and units from the vocabulary database.
"""

from __future__ import annotations

import re
import yaml
from typing import Dict, List, Any, Optional, Tuple

from app.services.vocabulary import get_vocabulary_service


class VocabEnrichmentService:
    """Service to enrich generated PSDL with real vocabulary data."""

    # Common signal reference mappings to help with search
    SIGNAL_ALIASES = {
        "creatinine": ["creatinine", "serum creatinine", "cr"],
        "bun": ["blood urea nitrogen", "bun", "urea nitrogen"],
        "heart_rate": ["heart rate", "pulse", "hr"],
        "body_temperature": ["body temperature", "temperature", "temp"],
        "blood_pressure": ["blood pressure", "bp"],
        "systolic_bp": ["systolic blood pressure", "systolic bp", "sbp"],
        "diastolic_bp": ["diastolic blood pressure", "diastolic bp", "dbp"],
        "mean_arterial_pressure": ["mean arterial pressure", "map"],
        "oxygen_saturation": ["oxygen saturation", "spo2", "o2 sat"],
        "respiratory_rate": ["respiratory rate", "rr", "respiration"],
        "glucose": ["glucose", "blood glucose", "blood sugar"],
        "white_blood_cell_count": ["white blood cell", "wbc", "leukocyte"],
        "hemoglobin": ["hemoglobin", "hgb", "hb"],
        "platelet_count": ["platelet", "plt", "thrombocyte"],
        "sodium": ["sodium", "na"],
        "potassium": ["potassium", "k"],
        "lactate": ["lactate", "lactic acid"],
        "ph": ["ph", "blood ph", "arterial ph"],
        "pco2": ["pco2", "partial pressure co2", "carbon dioxide"],
        "po2": ["po2", "partial pressure o2", "oxygen"],
        "bicarbonate": ["bicarbonate", "hco3", "bicarb"],
        "troponin": ["troponin", "cardiac troponin", "trop"],
        "bnp": ["bnp", "brain natriuretic peptide", "b-type natriuretic"],
        "inr": ["inr", "international normalized ratio"],
        "ptt": ["ptt", "partial thromboplastin time"],
        "ast": ["ast", "aspartate aminotransferase", "sgot"],
        "alt": ["alt", "alanine aminotransferase", "sgpt"],
        "bilirubin": ["bilirubin", "total bilirubin"],
        "albumin": ["albumin", "serum albumin"],
        "gfr": ["gfr", "glomerular filtration rate", "egfr"],
    }

    def enrich_yaml(self, yaml_content: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Enrich generated YAML with vocabulary data.

        Args:
            yaml_content: Generated PSDL YAML string

        Returns:
            Tuple of (enriched YAML string, list of enrichment details)
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            if not data or not isinstance(data, dict):
                return yaml_content, []

            signals = data.get("signals", {})
            if not signals or not isinstance(signals, dict):
                return yaml_content, []

            enrichments = []

            # Enrich each signal
            for signal_name, signal_def in signals.items():
                if not isinstance(signal_def, dict):
                    continue

                ref = signal_def.get("ref", signal_name)

                # Search for matching concept
                concept = self._find_best_concept(ref)

                if concept:
                    # Update signal definition with real data
                    signal_def["concept_id"] = concept["concept_id"]

                    # Add concept code if available
                    if concept.get("concept_code"):
                        signal_def["concept_code"] = concept["concept_code"]

                    # Add vocabulary ID
                    if concept.get("vocabulary_id"):
                        signal_def["vocabulary_id"] = concept["vocabulary_id"]

                    # Update unit if we have typical units and no expected_unit set
                    if concept.get("typical_units") and not signal_def.get("expected_unit"):
                        # Use first typical unit
                        first_unit = concept["typical_units"][0]
                        if isinstance(first_unit, dict):
                            signal_def["expected_unit"] = first_unit.get("code", first_unit.get("name", ""))
                        else:
                            signal_def["expected_unit"] = str(first_unit)

                    enrichments.append({
                        "signal": signal_name,
                        "ref": ref,
                        "matched_concept": concept["concept_name"],
                        "concept_id": concept["concept_id"],
                        "concept_code": concept.get("concept_code"),
                        "vocabulary_id": concept.get("vocabulary_id"),
                        "unit": signal_def.get("expected_unit"),
                    })
                else:
                    enrichments.append({
                        "signal": signal_name,
                        "ref": ref,
                        "matched_concept": None,
                        "concept_id": None,
                        "error": f"No vocabulary match found for '{ref}'"
                    })

            # Convert back to YAML
            enriched_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

            return enriched_yaml, enrichments

        except yaml.YAMLError as e:
            # Return original if YAML parsing fails
            return yaml_content, [{"error": f"YAML parse error: {str(e)}"}]
        except Exception as e:
            return yaml_content, [{"error": f"Enrichment error: {str(e)}"}]

    def _find_best_concept(self, ref: str) -> Optional[Dict[str, Any]]:
        """Find the best matching concept for a signal reference.

        Args:
            ref: The signal reference (e.g., "creatinine", "heart_rate")

        Returns:
            Best matching concept dict or None
        """
        # Normalize ref
        ref_lower = ref.lower().strip()
        ref_normalized = ref_lower.replace("_", " ").replace("-", " ")

        # Build search queries from ref and aliases
        search_queries = [ref_normalized, ref_lower]

        # Check if we have known aliases for this reference
        for alias_key, aliases in self.SIGNAL_ALIASES.items():
            if ref_lower == alias_key or ref_normalized in aliases:
                search_queries.extend(aliases)
                break

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in search_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        # Try each query until we find a good match
        vocab_service = get_vocabulary_service()
        for query in unique_queries:
            results = vocab_service.search(query, limit=5)

            if results:
                # Return the top result
                return results[0]

        return None

    def get_enrichment_summary(self, enrichments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of enrichment results.

        Args:
            enrichments: List of enrichment details

        Returns:
            Summary dict with stats and details
        """
        total = len(enrichments)
        matched = sum(1 for e in enrichments if e.get("concept_id"))
        unmatched = total - matched

        return {
            "total_signals": total,
            "matched": matched,
            "unmatched": unmatched,
            "success_rate": round(matched / total * 100, 1) if total > 0 else 0,
            "details": enrichments
        }


# Singleton instance
vocab_enrichment_service = VocabEnrichmentService()
