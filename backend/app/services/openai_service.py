"""OpenAI service for AI-assisted PSDL scenario generation."""

from __future__ import annotations

import os
import httpx
from typing import Optional


class OpenAIService:
    """Client for OpenAI API for PSDL generation."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini"  # Fast, capable, cost-effective

    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)

    async def generate_scenario(
        self,
        prompt: str,
        clinical_context: Optional[str] = None,
    ) -> str:
        """Generate PSDL scenario from natural language description.

        Args:
            prompt: User's description of the clinical scenario
            clinical_context: Optional clinical guidelines or reference text

        Returns:
            Generated PSDL YAML string
        """
        system_prompt = self._build_system_prompt()
        few_shot_examples = self._get_few_shot_examples()

        # Build user message with optional clinical context
        context_section = ""
        if clinical_context and clinical_context.strip():
            context_section = f"""
CLINICAL REFERENCE (Use these guidelines for accurate thresholds):
{clinical_context.strip()}

"""

        user_message = f"{context_section}User request: {prompt}\n\nGenerate PSDL YAML:"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": f"{system_prompt}\n\n{few_shot_examples}"},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._extract_yaml(content)

    async def correct_scenario(
        self,
        original_yaml: str,
        errors: list[str],
        original_prompt: str,
    ) -> str:
        """Correct a generated PSDL scenario based on validation errors.

        Args:
            original_yaml: The YAML that failed validation
            errors: List of error messages from the validator
            original_prompt: The user's original request

        Returns:
            Corrected PSDL YAML string
        """
        correction_prompt = self._build_correction_prompt(
            original_yaml, errors, original_prompt
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": correction_prompt},
                    ],
                    "temperature": 0.2,  # Lower temp for corrections
                    "max_tokens": 2000,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._extract_yaml(content)

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

PSDL STRUCTURE:

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

state:                       # Optional: State machine for progression
  initial: state_name        # Starting state
  states:
    - stable
    - warning
    - critical
  transitions:
    - from: stable
      to: warning
      when: logic_rule_name  # Reference to logic rule

outputs:                     # What downstream systems consume - REQUIRED!
  decision:                  # Boolean clinical decisions
    output_name:
      type: boolean
      from: logic.rule_name  # Reference to a logic rule
      description: "..."
  features:                  # Numeric values for ML/analytics
    feature_name:
      type: float
      from: trends.trend_name
      description: "..."
  evidence:                  # Supporting info - ALWAYS include timestamp!
    timestamp:
      type: datetime
      expr: evaluation_time()  # When this evaluation was performed
      description: "Evaluation timestamp"
    current_state:
      type: string
      from: state.current    # Current state machine state (if using state machine)

EXPRESSION SYNTAX:

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

POINTWISE OPERATORS (Signal only, no window):
  last(Signal)               - Most recent value
  exists(Signal)             - True if signal has value
  missing(Signal)            - True if signal is missing

WINDOW FORMAT:
  INTEGER + UNIT where unit is: s (seconds), m (minutes), h (hours), d (days), w (weeks)
  Examples: 48h, 24h, 7d, 30m, 1w

COMPARISON OPERATORS (logic layer ONLY):
  ==  !=  <  <=  >  >=

BOOLEAN OPERATORS (MUST be uppercase):
  AND   OR   NOT

NOT SUPPORTED (DO NOT USE - these will cause validation errors):
- time_since()       - No temporal event tracking in PSDL
- time_in_state()    - No state duration queries
- onset()            - No event onset detection
- duration()         - No duration calculations
- avg()              - Use sma() instead

CRITICAL RULES:
1. TRENDS = computations only. NO comparisons (>=, <=, >, <, ==) in trends!
2. LOGIC = comparisons go here. Reference trend names or inline comparisons.
3. Boolean operators MUST be uppercase: AND, OR, NOT
4. Window format is strict: 48h not 48 hours, 7d not 7 days
5. Use sma() for averages. avg() is NOT a valid operator!
6. Severity must be one of: low, medium, high, critical
7. ALWAYS include outputs section - this is the interface for downstream systems!
8. Include state machine if user asks for progression/staging/state transitions
9. Output valid YAML wrapped in ```yaml code blocks
10. If user asks for time-based event tracking, use sma/min/max over windows as proxy"""

    def _get_few_shot_examples(self) -> str:
        return """
EXAMPLE 1: Acute Kidney Injury Detection
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
  aki_present:
    when: aki_stage1 OR aki_severe
    severity: high
    description: "AKI detected by any criterion"

outputs:
  decision:
    has_aki:
      type: boolean
      from: logic.aki_present
      description: "Patient has acute kidney injury"
    is_severe:
      type: boolean
      from: logic.aki_severe
      description: "Patient has severe AKI requiring urgent attention"
  features:
    creatinine_change:
      type: float
      from: trends.cr_delta_48h
      description: "48-hour creatinine change for risk modeling"
    creatinine_current:
      type: float
      from: trends.cr_current
      description: "Current creatinine level"
  evidence:
    timestamp:
      type: datetime
      expr: evaluation_time()
      description: "When this evaluation was performed"
```

EXAMPLE 2: SIRS/Sepsis Screening
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

outputs:
  decision:
    sirs_positive:
      type: boolean
      from: logic.sirs_criteria
      description: "Patient meets SIRS criteria"
    has_fever:
      type: boolean
      from: logic.fever
      description: "Patient has fever"
    has_leukocyte_abnormality:
      type: boolean
      from: logic.leukocytosis
      description: "Abnormal WBC count"
  features:
    temperature:
      type: float
      from: trends.temp_current
      description: "Current body temperature"
    heart_rate:
      type: float
      from: trends.hr_current
      description: "Current heart rate"
    wbc_count:
      type: float
      from: trends.wbc_current
      description: "Current WBC count"
  evidence:
    timestamp:
      type: datetime
      expr: evaluation_time()
      description: "When this evaluation was performed"
```

EXAMPLE 3: ICU Deterioration with State Machine
User: "Monitor ICU patient deterioration with state transitions from stable to critical"

```yaml
scenario: ICU_Deterioration_Monitor
version: "1.0.0"
description: "Monitor ICU patient with progressive deterioration staging"

signals:
  MAP:
    ref: mean_arterial_pressure
    expected_unit: mmHg
    description: "Mean arterial pressure"
  Lactate:
    ref: lactate
    expected_unit: mmol/L
    description: "Serum lactate"
  SpO2:
    ref: oxygen_saturation
    expected_unit: percent
    description: "Oxygen saturation"

trends:
  map_current:
    expr: last(MAP)
    description: "Current MAP"
  map_avg_1h:
    expr: sma(MAP, 1h)
    description: "1-hour average MAP"
  lactate_current:
    expr: last(Lactate)
    description: "Current lactate"
  spo2_min_1h:
    expr: min(SpO2, 1h)
    description: "Minimum SpO2 in 1 hour"

logic:
  hypotension:
    when: map_avg_1h < 65
    severity: medium
    description: "Sustained hypotension"
  lactate_elevated:
    when: lactate_current > 2.0
    severity: medium
    description: "Elevated lactate"
  lactate_critical:
    when: lactate_current > 4.0
    severity: critical
    description: "Critical lactate level"
  hypoxemia:
    when: spo2_min_1h < 90
    severity: medium
    description: "Hypoxemia"
  early_warning:
    when: hypotension OR lactate_elevated OR hypoxemia
    severity: medium
    description: "Early signs of deterioration"
  shock:
    when: hypotension AND lactate_elevated
    severity: high
    description: "Developing shock"
  critical_state:
    when: shock AND (lactate_critical OR hypoxemia)
    severity: critical
    description: "Critical condition"
  stable:
    when: NOT (hypotension OR lactate_elevated OR hypoxemia)
    severity: low
    description: "Patient stable"

state:
  initial: stable
  states:
    - stable
    - early_warning
    - deteriorating
    - critical
  transitions:
    - from: stable
      to: early_warning
      when: early_warning
      description: "Initial signs of concern"
    - from: early_warning
      to: deteriorating
      when: shock
      description: "Condition worsening"
    - from: deteriorating
      to: critical
      when: critical_state
      description: "Critical state reached"
    - from: early_warning
      to: stable
      when: stable
      description: "Recovery to stable"
    - from: deteriorating
      to: early_warning
      when: NOT shock
      description: "Partial recovery"

outputs:
  decision:
    needs_intervention:
      type: boolean
      from: logic.early_warning
      description: "Patient needs clinical attention"
    is_critical:
      type: boolean
      from: logic.critical_state
      description: "Patient in critical condition"
  features:
    map_value:
      type: float
      from: trends.map_avg_1h
      description: "Average MAP for trending"
    lactate_value:
      type: float
      from: trends.lactate_current
      description: "Current lactate for severity"
  evidence:
    timestamp:
      type: datetime
      expr: evaluation_time()
      description: "When this evaluation was performed"
    current_state:
      type: string
      from: state.current
      description: "Current deterioration stage"
    triggered_rules:
      type: string[]
      expr: rules_fired()
      description: "List of logic rules that fired"
```
"""

    async def enrich_irb_document(
        self,
        scenario_info: dict,
        governance_data: dict,
    ) -> dict:
        """Enrich IRB document content with AI-generated narrative.

        Takes the scenario info and user-provided governance data and generates
        professional, human-readable content for each section.

        Args:
            scenario_info: Auto-derived info from PSDL scenario
            governance_data: User-provided governance narrative (clinical_summary, justification, risk_assessment)

        Returns:
            dict with enriched content for each section
        """
        system_prompt = """You are a clinical informatics expert writing IRB (Institutional Review Board) documentation.
Your task is to generate professional, clear, human-readable content for a clinical algorithm review document.

WRITING STYLE:
- Professional and formal, suitable for IRB review
- Clear and accessible to non-technical reviewers
- Use plain language to explain technical concepts
- Highlight clinical relevance and patient safety considerations
- Be concise but comprehensive

OUTPUT FORMAT:
Return a JSON object with the following sections (all values are strings):
{
  "executive_summary": "2-3 paragraph overview of the algorithm's purpose and clinical value",
  "clinical_background": "Explanation of the clinical condition being monitored and why automated detection is valuable",
  "data_elements_narrative": "Plain language description of what patient data is used and why",
  "algorithm_explanation": "Step-by-step explanation of how the algorithm works in plain language",
  "clinical_workflow": "How this algorithm integrates into clinical workflow and what actions it triggers",
  "safety_considerations": "Analysis of potential risks, false positives/negatives, and mitigation strategies",
  "limitations": "Known limitations and appropriate use cases",
  "recommendation": "Final recommendation for IRB consideration"
}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks or explanations."""

        # Build context from scenario
        signals_desc = ", ".join([
            f"{s['name']} ({s.get('unit', 'no unit')})"
            for s in scenario_info.get('signals', [])
        ])

        trends_desc = "; ".join([
            f"{t['name']}: {t.get('description', t.get('expr', ''))}"
            for t in scenario_info.get('trends', [])
        ])

        logic_desc = "; ".join([
            f"{r['name']} ({r.get('severity', 'info')}): {r.get('description', r.get('expr', ''))}"
            for r in scenario_info.get('logic', [])
        ])

        user_prompt = f"""Generate enriched IRB documentation for the following clinical algorithm:

ALGORITHM NAME: {scenario_info.get('name', 'Unknown')}
VERSION: {scenario_info.get('version', 'N/A')}
DESCRIPTION: {scenario_info.get('description', 'Not provided')}

DATA ELEMENTS MONITORED:
{signals_desc}

COMPUTED TRENDS:
{trends_desc}

DETECTION RULES:
{logic_desc}

USER-PROVIDED GOVERNANCE NOTES:

Clinical Summary (from user):
{governance_data.get('clinical_summary', 'Not provided')}

Justification (from user):
{governance_data.get('justification', 'Not provided')}

Risk Assessment (from user):
{governance_data.get('risk_assessment', 'Not provided')}

Based on this information, generate professional IRB documentation. Expand on the user's notes with clinical expertise, but stay faithful to the algorithm's actual functionality."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.4,
                        "max_tokens": 3000,
                    },
                    timeout=90.0,
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON response
                import json
                # Clean up response if it has markdown code blocks
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()

                return json.loads(content)

        except Exception as e:
            # Return empty enrichment on error - document will use fallback content
            return {
                "error": str(e),
                "executive_summary": None,
                "clinical_background": None,
                "data_elements_narrative": None,
                "algorithm_explanation": None,
                "clinical_workflow": None,
                "safety_considerations": None,
                "limitations": None,
                "recommendation": None,
            }

    def _extract_yaml(self, response: str) -> str:
        """Extract YAML from LLM response."""
        # Look for ```yaml ... ``` blocks
        if "```yaml" in response:
            start = response.find("```yaml") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Fall back to any ``` ... ``` block
        if "```" in response:
            start = response.find("```") + 3
            # Skip language identifier if present
            newline_pos = response.find("\n", start)
            if newline_pos != -1 and newline_pos - start < 10:
                start = newline_pos + 1
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Return raw response as last resort
        return response.strip()


# Singleton instance
openai_service = OpenAIService()
