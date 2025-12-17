"""Ollama service for AI-assisted PSDL scenario generation."""

from __future__ import annotations

import httpx
from typing import Optional


class OllamaService:
    """Client for local Ollama LLM for PSDL generation."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "mistral-small"  # 24B model - best quality for complex scenarios

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=2.0)
                return resp.status_code == 200
        except Exception:
            return False

    async def get_models(self) -> list[str]:
        """Get list of available models."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def generate_scenario(
        self,
        prompt: str,
        model: Optional[str] = None,
        clinical_context: Optional[str] = None,
    ) -> str:
        """Generate PSDL scenario from natural language description.

        Args:
            prompt: User's description of the clinical scenario
            model: Optional model override
            clinical_context: Optional clinical guidelines or reference text

        Returns:
            Generated PSDL YAML string
        """
        system_prompt = self._build_system_prompt()
        few_shot_examples = self._get_few_shot_examples()

        # Build full prompt with optional clinical context
        context_section = ""
        if clinical_context and clinical_context.strip():
            context_section = f"""
═══════════════════════════════════════════════════════════════
CLINICAL REFERENCE (Use these guidelines for accurate thresholds)
═══════════════════════════════════════════════════════════════
{clinical_context.strip()}

"""

        full_prompt = f"{system_prompt}\n\n{few_shot_examples}\n\n{context_section}User request: {prompt}\n\nGenerate PSDL YAML:"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model or self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=300.0  # Larger models need more time
            )
            response.raise_for_status()
            result = response.json()
            return self._extract_yaml(result["response"])

    async def correct_scenario(
        self,
        original_yaml: str,
        errors: list[str],
        original_prompt: str,
        model: Optional[str] = None
    ) -> str:
        """Correct a generated PSDL scenario based on validation errors.

        Args:
            original_yaml: The YAML that failed validation
            errors: List of error messages from the validator
            original_prompt: The user's original request
            model: Optional model override

        Returns:
            Corrected PSDL YAML string
        """
        correction_prompt = self._build_correction_prompt(
            original_yaml, errors, original_prompt
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model or self.model,
                    "prompt": correction_prompt,
                    "stream": False,
                    "options": {"temperature": 0.2}  # Lower temp for corrections
                },
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            return self._extract_yaml(result["response"])

    def _build_correction_prompt(
        self, original_yaml: str, errors: list[str], original_prompt: str
    ) -> str:
        """Build a prompt to correct validation errors."""
        error_list = "\n".join(f"  - {e}" for e in errors)

        return f"""You are a PSDL expert. The following PSDL YAML has validation errors that need to be fixed.

ORIGINAL USER REQUEST:
{original_prompt}

GENERATED YAML WITH ERRORS:
```yaml
{original_yaml}
```

VALIDATION ERRORS:
{error_list}

COMMON FIXES:
1. Duplicate keys (trends:, logic:, signals:) - YAML only allows ONE of each! Merge all items under a single key.
2. Unknown term references - Make sure all terms in logic rules are defined in trends or other logic rules.
3. Invalid operators - Use sma() not avg(). Use delta(), slope(), last(), min(), max(), etc.
4. Boolean operators - Must be uppercase: AND, OR, NOT (not lowercase).
5. Window format - Must be INTEGER + UNIT like 48h, 7d, 30m (not "48 hours").

INSTRUCTIONS:
1. Fix ALL the errors listed above
2. Keep the same clinical intent as the original
3. Output ONLY the corrected YAML in a ```yaml code block
4. Do NOT add explanations before or after the YAML

Generate the CORRECTED PSDL YAML:"""

    def _build_system_prompt(self) -> str:
        return """You are an expert in PSDL (Patient Scenario Definition Language) v0.3.
Your task is to generate syntactically correct PSDL YAML based on user descriptions.

═══════════════════════════════════════════════════════════════
PSDL STRUCTURE
═══════════════════════════════════════════════════════════════

scenario: ScenarioName       # CamelCase, no spaces
version: "1.0.0"             # Semantic version
description: "..."           # What this scenario detects

population:                  # Optional: patient selection criteria
  include:
    - age >= 18
  exclude:
    - condition == "excluded"

signals:                     # Clinical data inputs
  SignalName:
    ref: semantic_reference  # Abstract reference (e.g., creatinine, heart_rate)
    expected_unit: unit      # Expected unit (mg/dL, bpm, mmHg, etc.)
    description: "..."

trends:                      # Computed metrics - NUMERIC VALUES ONLY
  trend_name:
    expr: <expression>       # Must produce a number
    description: "..."

logic:                       # Decision rules - COMPARISONS GO HERE
  rule_name:
    when: <condition>        # Comparisons and boolean expressions
    severity: low|medium|high|critical
    description: "..."

═══════════════════════════════════════════════════════════════
EXPRESSION SYNTAX (CRITICAL - FOLLOW EXACTLY)
═══════════════════════════════════════════════════════════════

WINDOWED OPERATORS (require Signal + window):
  delta(Signal, window)      - Change over time window
  slope(Signal, window)      - Rate of change (unit/time)
  sma(Signal, window)        - Simple moving average
  ema(Signal, window)        - Exponential moving average
  min(Signal, window)        - Minimum value in window
  max(Signal, window)        - Maximum value in window
  count(Signal, window)      - Count of values in window
  first(Signal, window)      - First value in window
  std(Signal, window)        - Standard deviation
  stddev(Signal, window)     - Standard deviation (alias)
  percentile(Signal, window, N) - Nth percentile

POINTWISE OPERATORS (Signal only, no window):
  last(Signal)               - Most recent value
  exists(Signal)             - True if signal has value
  missing(Signal)            - True if signal is missing

WINDOW FORMAT:
  INTEGER + UNIT where unit is: s (seconds), m (minutes), h (hours), d (days), w (weeks)
  Examples: 48h, 24h, 7d, 30m, 1w

ARITHMETIC IN TRENDS:
  You can combine operators: (SBP + 2*DBP) / 3
  You can reference signals directly: Cr (current value)

COMPARISON OPERATORS (logic layer ONLY):
  ==  !=  <  <=  >  >=

BOOLEAN OPERATORS (MUST be uppercase):
  AND   OR   NOT
  Example: condition1 AND condition2 OR NOT condition3

═══════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════

1. TRENDS = computations only. NO comparisons (>=, <=, >, <, ==) in trends!
   ✓ expr: delta(Cr, 48h)
   ✓ expr: sma(HR, 1h)
   ✓ expr: last(Temp)
   ✗ expr: delta(Cr, 48h) >= 0.3  ← WRONG! Comparison in trend!

2. LOGIC = comparisons go here. Reference trend names or inline comparisons.
   ✓ when: cr_delta_48h >= 0.3
   ✓ when: rule1 AND rule2
   ✓ when: last(Temp) > 38.3

3. Boolean operators MUST be uppercase: AND, OR, NOT (not 'and', 'or', 'not')

4. Window format is strict: 48h not 48 hours, 7d not 7 days

5. Use sma() for averages. avg() is NOT a valid operator!

6. Severity must be one of: low, medium, high, critical

7. Output valid YAML wrapped in ```yaml code blocks"""

    def _get_few_shot_examples(self) -> str:
        return """
═══════════════════════════════════════════════════════════════
EXAMPLE 1: Acute Kidney Injury Detection
═══════════════════════════════════════════════════════════════
User: "Detect acute kidney injury using creatinine changes over 48 hours"

```yaml
scenario: AKI_Detection
version: "1.0.0"
description: "Detect acute kidney injury based on KDIGO creatinine criteria"

signals:
  Cr:
    ref: creatinine
    expected_unit: mg/dL
    description: "Serum creatinine level"

trends:
  cr_delta_48h:
    expr: delta(Cr, 48h)
    description: "Creatinine change over 48 hours"
  cr_current:
    expr: last(Cr)
    description: "Current creatinine value"

logic:
  aki_stage1:
    when: cr_delta_48h >= 0.3
    severity: medium
    description: "AKI Stage 1: Cr rise >= 0.3 mg/dL in 48h"
  aki_severe:
    when: cr_current >= 4.0
    severity: critical
    description: "Severe AKI: Cr >= 4.0 mg/dL"
```

═══════════════════════════════════════════════════════════════
EXAMPLE 2: Hypotension Monitoring
═══════════════════════════════════════════════════════════════
User: "Monitor for hypotension with MAP below 65"

```yaml
scenario: Hypotension_Monitor
version: "1.0.0"
description: "Monitor for sustained hypotension based on MAP"

signals:
  SBP:
    ref: systolic_blood_pressure
    expected_unit: mmHg
    description: "Systolic blood pressure"
  DBP:
    ref: diastolic_blood_pressure
    expected_unit: mmHg
    description: "Diastolic blood pressure"

trends:
  map_current:
    expr: (SBP + 2*DBP) / 3
    description: "Mean arterial pressure calculation"
  map_avg_1h:
    expr: sma(SBP, 1h)
    description: "1-hour SBP average"

logic:
  hypotension_alert:
    when: map_current < 65
    severity: high
    description: "MAP below 65 mmHg"
  sustained_hypotension:
    when: map_avg_1h < 70
    severity: critical
    description: "Sustained low blood pressure over 1 hour"
```

═══════════════════════════════════════════════════════════════
EXAMPLE 3: SIRS/Sepsis Screening
═══════════════════════════════════════════════════════════════
User: "Detect sepsis using temperature, heart rate, and WBC"

```yaml
scenario: SIRS_Sepsis_Screen
version: "1.0.0"
description: "Screen for SIRS criteria suggesting possible sepsis"

signals:
  Temp:
    ref: body_temperature
    expected_unit: C
    description: "Body temperature"
  HR:
    ref: heart_rate
    expected_unit: bpm
    description: "Heart rate"
  WBC:
    ref: white_blood_cell_count
    expected_unit: x10^9/L
    description: "White blood cell count"

trends:
  temp_current:
    expr: last(Temp)
    description: "Current temperature"
  hr_current:
    expr: last(HR)
    description: "Current heart rate"
  wbc_current:
    expr: last(WBC)
    description: "Current WBC count"

logic:
  fever:
    when: temp_current > 38.3
    severity: low
    description: "Temperature above 38.3C"
  hypothermia:
    when: temp_current < 36.0
    severity: low
    description: "Temperature below 36C"
  tachycardia:
    when: hr_current > 90
    severity: low
    description: "Heart rate above 90 bpm"
  leukocytosis:
    when: wbc_current > 12
    severity: low
    description: "WBC above 12"
  leukopenia:
    when: wbc_current < 4
    severity: low
    description: "WBC below 4"
  sirs_criteria:
    when: (fever OR hypothermia) AND tachycardia AND (leukocytosis OR leukopenia)
    severity: high
    description: "Multiple SIRS criteria met - evaluate for sepsis"
```

═══════════════════════════════════════════════════════════════
EXAMPLE 4: ICU Deterioration with Population Filter
═══════════════════════════════════════════════════════════════
User: "Monitor ICU patients for clinical deterioration using vitals"

```yaml
scenario: ICU_Deterioration
version: "1.0.0"
description: "Early warning for clinical deterioration in ICU"

population:
  include:
    - age >= 18
    - location == "ICU"
  exclude:
    - comfort_care == true

signals:
  HR:
    ref: heart_rate
    expected_unit: bpm
  SBP:
    ref: systolic_blood_pressure
    expected_unit: mmHg
  RR:
    ref: respiratory_rate
    expected_unit: breaths/min
  SpO2:
    ref: oxygen_saturation
    expected_unit: percent

trends:
  hr_current:
    expr: last(HR)
    description: "Current heart rate"
  hr_change_4h:
    expr: delta(HR, 4h)
    description: "Heart rate change over 4 hours"
  sbp_current:
    expr: last(SBP)
    description: "Current systolic BP"
  sbp_min_6h:
    expr: min(SBP, 6h)
    description: "Minimum SBP in 6 hours"
  rr_current:
    expr: last(RR)
    description: "Current respiratory rate"
  spo2_current:
    expr: last(SpO2)
    description: "Current oxygen saturation"

logic:
  tachycardia:
    when: hr_current > 120
    severity: medium
    description: "Heart rate above 120 bpm"
  hr_increasing:
    when: hr_change_4h > 20
    severity: low
    description: "HR increased by >20 bpm in 4h"
  hypotension:
    when: sbp_current < 90
    severity: high
    description: "Systolic BP below 90 mmHg"
  hypoxemia:
    when: spo2_current < 92
    severity: high
    description: "SpO2 below 92%"
  tachypnea:
    when: rr_current > 24
    severity: medium
    description: "Respiratory rate above 24"
  deterioration_warning:
    when: (tachycardia OR hr_increasing) AND (hypotension OR hypoxemia)
    severity: critical
    description: "Multiple signs of clinical deterioration"
```
"""

    def _extract_yaml(self, response: str) -> str:
        """Extract YAML from LLM response.

        Looks for ```yaml ... ``` code blocks first, then falls back
        to any ``` ... ``` block, then returns raw response.
        """
        # Look for ```yaml ... ``` blocks
        if "```yaml" in response:
            start = response.find("```yaml") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Fall back to any ``` ... ``` block
        if "```" in response:
            start = response.find("```") + 3
            # Skip language identifier if present (e.g., ```yml)
            newline_pos = response.find("\n", start)
            if newline_pos != -1 and newline_pos - start < 10:
                start = newline_pos + 1
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Return raw response as last resort
        return response.strip()


# Singleton instance
ollama_service = OllamaService()
