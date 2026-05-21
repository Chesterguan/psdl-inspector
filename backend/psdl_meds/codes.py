"""Format `<vocabulary>/<concept_code>` strings for MEDS shards.

The MEDS spec stores the `code` column as a single string of the form
`VOCAB/code`. This module is the single place that enforces that format —
both Inspector preview and Workbench live export route through here.
"""


def format_code(vocabulary: str, concept_code: str) -> str:
    """Return a normalized MEDS code string, e.g. `"LOINC/2160-0"`.

    Vocabularies are uppercased; concept codes preserve case (some source
    vocabularies are case-sensitive, e.g. SNOMED descriptions).
    """
    vocab = (vocabulary or "").strip()
    code = (concept_code or "").strip()

    if not vocab:
        raise ValueError("vocabulary must not be empty")
    if not code:
        raise ValueError("concept_code must not be empty")
    if "/" in vocab:
        raise ValueError("vocabulary must not contain a slash")

    return f"{vocab.upper()}/{code}"
