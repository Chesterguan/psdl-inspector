# Signal Groups Extension - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `signal_groups` as an optional PSDL section that supports domain-level bulk data requests and custom named signal panels, modeled after OHDSI Concept Sets.

**Architecture:** New `SignalGroup` dataclass in psdl-lang IR, parser support for the YAML section, and display in Inspector's outline tree + bundle panel. Groups are data extraction declarations only -- they do not interact with trends or logic.

**Tech Stack:** Python (psdl-lang, FastAPI), TypeScript/React (Next.js frontend), OMOP ClinicalDomain enum.

**Spec:** `docs/superpowers/specs/2026-04-09-signal-groups-design.md`

**Note:** Tasks 1-3 modify psdl-lang (installed at `backend/.venv/lib/python3.9/site-packages/psdl/`). These changes are prototyped in-place for testing, then ported to the psdl-lang repo as a proper release.

---

### Task 1: Add SignalGroup dataclass to psdl-lang IR

**Files:**
- Modify: `backend/.venv/lib/python3.9/site-packages/psdl/core/ir.py`
- Test: `backend/tests/test_signal_groups.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_signal_groups.py`:

```python
"""Tests for signal_groups extension (RFC 2026-04-09)."""
import pytest
from psdl.core.ir import SignalGroup, ClinicalDomain, PSDLScenario, Signal


def test_signal_group_domain_level():
    """Domain-level group has domain set, no members."""
    group = SignalGroup(
        name="all_labs",
        description="All lab results",
        domain=ClinicalDomain.LABORATORY,
    )
    assert group.name == "all_labs"
    assert group.domain == ClinicalDomain.LABORATORY
    assert group.members is None


def test_signal_group_custom():
    """Custom group has members list, no domain."""
    group = SignalGroup(
        name="renal_panel",
        description="Renal monitoring",
        members=["creatinine", "hemoglobin"],
    )
    assert group.name == "renal_panel"
    assert group.domain is None
    assert group.members == ["creatinine", "hemoglobin"]


def test_scenario_signal_groups_default_empty():
    """PSDLScenario.signal_groups defaults to empty dict."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
    )
    assert scenario.signal_groups == {}


def test_scenario_validate_signal_group_valid_members():
    """Validation passes when group members reference defined signals."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signals={"creatinine": Signal(name="creatinine", ref="creatinine")},
        signal_groups={
            "renal": SignalGroup(
                name="renal",
                description="Renal panel",
                members=["creatinine"],
            )
        },
    )
    errors = scenario.validate()
    assert not any("signal_group" in e.lower() or "Signal group" in e for e in errors)


def test_scenario_validate_signal_group_invalid_member():
    """Validation fails when group member references unknown signal."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signals={"creatinine": Signal(name="creatinine", ref="creatinine")},
        signal_groups={
            "renal": SignalGroup(
                name="renal",
                description="Renal panel",
                members=["creatinine", "nonexistent"],
            )
        },
    )
    errors = scenario.validate()
    assert any("nonexistent" in e for e in errors)


def test_scenario_validate_domain_group_no_member_check():
    """Domain-level groups skip member validation (no members to check)."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signal_groups={
            "all_labs": SignalGroup(
                name="all_labs",
                description="All labs",
                domain=ClinicalDomain.LABORATORY,
            )
        },
    )
    errors = scenario.validate()
    assert not any("signal_group" in e.lower() or "Signal group" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v`

Expected: FAIL with `ImportError: cannot import name 'SignalGroup'`

- [ ] **Step 3: Add SignalGroup dataclass to ir.py**

In `backend/.venv/lib/python3.9/site-packages/psdl/core/ir.py`, after the `Severity` enum (around line 79), add:

```python
@dataclass
class SignalGroup:
    """A named collection of signals or a domain-level data request.
    
    Phase 1 (RFC 2026-04-09): domain and members are mutually exclusive.
    """
    name: str
    description: str
    domain: Optional[ClinicalDomain] = None
    members: Optional[List[str]] = None
```

Add `signal_groups` field to `PSDLScenario` dataclass (after `state` field, around line 278):

```python
    signal_groups: Dict[str, SignalGroup] = field(default_factory=dict)
```

Add validation in `PSDLScenario.validate()` method (after the logic term validation block, around line 333):

```python
        # Check signal groups reference valid signals
        for group_name, group in self.signal_groups.items():
            if group.members:
                for signal_name in group.members:
                    if signal_name not in self.signals:
                        errors.append(
                            f"Signal group '{group_name}' references unknown signal '{signal_name}'"
                        )
```

Export `SignalGroup` from `__init__.py` if needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v`

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_signal_groups.py
git commit -m "test: add signal group IR tests (RFC 2026-04-09)"
```

---

### Task 2: Add signal_groups parsing to psdl-lang parser

**Files:**
- Modify: `backend/.venv/lib/python3.9/site-packages/psdl/core/parser.py`
- Modify: `backend/tests/test_signal_groups.py`

- [ ] **Step 1: Write the failing parser tests**

Append to `backend/tests/test_signal_groups.py`:

```python
from psdl.core.parser import PSDLParser


MINIMAL_YAML = """
scenario: test
version: "1.0.0"
description: "test scenario"

signals:
  creatinine:
    ref: creatinine
    expected_unit: mg/dL
    description: "Serum creatinine"
  hemoglobin:
    ref: hemoglobin
    expected_unit: g/dL
    description: "Hemoglobin"

trends:
  cr_current:
    type: float
    unit: mg/dL
    expr: last(creatinine)
    description: "Current creatinine"
  hgb_current:
    type: float
    unit: g/dL
    expr: last(hemoglobin)
    description: "Current hemoglobin"

logic:
  cr_high:
    when: cr_current >= 4.0
    description: "High creatinine"
"""


def test_parse_no_signal_groups():
    """Scenarios without signal_groups parse normally."""
    parser = PSDLParser()
    scenario = parser.parse_string(MINIMAL_YAML)
    assert scenario.signal_groups == {}


def test_parse_domain_level_group():
    """Parse a domain-level signal group."""
    yaml = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All lab results"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert "all_labs" in scenario.signal_groups
    group = scenario.signal_groups["all_labs"]
    assert group.domain == ClinicalDomain.LABORATORY
    assert group.members is None
    assert group.description == "All lab results"


def test_parse_custom_group():
    """Parse a custom signal group with members."""
    yaml = MINIMAL_YAML + """
signal_groups:
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal monitoring"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert "renal_panel" in scenario.signal_groups
    group = scenario.signal_groups["renal_panel"]
    assert group.domain is None
    assert group.members == ["creatinine", "hemoglobin"]


def test_parse_group_invalid_member_fails_validation():
    """Group referencing unknown signal fails validation."""
    yaml = MINIMAL_YAML + """
signal_groups:
  bad_panel:
    members: [creatinine, nonexistent_signal]
    description: "Bad panel"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    errors = scenario.validate()
    assert any("nonexistent_signal" in e for e in errors)


def test_parse_group_missing_description_fails():
    """Group without description raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  no_desc:
    domain: laboratory
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="description"):
        parser.parse_string(yaml)


def test_parse_group_domain_and_members_fails():
    """Group with both domain and members raises parse error (Phase 1)."""
    yaml = MINIMAL_YAML + """
signal_groups:
  hybrid:
    domain: laboratory
    members: [creatinine]
    description: "Not allowed in Phase 1"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="mutually exclusive"):
        parser.parse_string(yaml)


def test_parse_group_neither_domain_nor_members_fails():
    """Group with neither domain nor members raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  empty:
    description: "Has neither"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="must have either"):
        parser.parse_string(yaml)


def test_parse_group_invalid_domain_fails():
    """Group with invalid domain value raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  bad_domain:
    domain: not_a_real_domain
    description: "Invalid domain"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="unknown domain"):
        parser.parse_string(yaml)


def test_parse_multiple_groups():
    """Parse multiple signal groups of different types."""
    yaml = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All labs"
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal panel"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert len(scenario.signal_groups) == 2
    assert "all_labs" in scenario.signal_groups
    assert "renal_panel" in scenario.signal_groups
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v -k "parse"`

Expected: FAIL -- parser doesn't recognize `signal_groups`

- [ ] **Step 3: Add _parse_signal_groups method to parser**

In `backend/.venv/lib/python3.9/site-packages/psdl/core/parser.py`:

1. Add `SignalGroup` to imports from `.ir` (around line 27-45)

2. Add the parsing method after `_parse_population` (around line 177):

```python
    def _parse_signal_groups(self, data: Optional[dict]) -> Dict[str, 'SignalGroup']:
        """Parse signal_groups section (RFC 2026-04-09)."""
        groups = {}
        if not data:
            return groups

        for name, spec in data.items():
            if not isinstance(spec, dict):
                raise PSDLParseError(f"Invalid signal group specification for '{name}'")

            description = spec.get("description")
            if not description:
                raise PSDLParseError(f"Signal group '{name}' missing 'description'")

            domain_str = spec.get("domain")
            members = spec.get("members")

            if domain_str and members:
                raise PSDLParseError(
                    f"Signal group '{name}': domain and members are mutually exclusive (Phase 1)"
                )
            if not domain_str and not members:
                raise PSDLParseError(
                    f"Signal group '{name}': must have either 'domain' or 'members'"
                )

            domain = None
            if domain_str:
                try:
                    domain = ClinicalDomain(domain_str)
                except ValueError:
                    raise PSDLParseError(
                        f"Signal group '{name}': unknown domain '{domain_str}'"
                    )

            groups[name] = SignalGroup(
                name=name,
                description=description,
                domain=domain,
                members=members if isinstance(members, list) else None,
            )

        return groups
```

3. In `parse_string()` (around line 87-159), after population parsing add:

```python
        # Parse signal groups (optional, RFC 2026-04-09)
        signal_groups = self._parse_signal_groups(data.get("signal_groups"))
```

4. Pass `signal_groups=signal_groups` to the PSDLScenario constructor (around line 137-149).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v`

Expected: All 16 tests PASS

- [ ] **Step 5: Verify the real test case parses**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -c "from psdl.core import parse_scenario; s = parse_scenario(open('../testorg/postop_surgical_cohort/postop_surgical_cohort.yaml').read()); print('Groups:', len(s.signal_groups)); print('Names:', list(s.signal_groups.keys()))"`

Expected: `Groups: 9` and all 9 group names listed.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_signal_groups.py
git commit -m "feat: add signal_groups parsing to psdl-lang (RFC 2026-04-09)"
```

---

### Task 3: Add SignalGroupOutline schema to Inspector backend

**Files:**
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/tests/test_signal_groups.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_signal_groups.py`:

```python
from app.models.schemas import SignalGroupOutline, OutlineResponse


def test_signal_group_outline_schema():
    """SignalGroupOutline model works for domain-level group."""
    outline = SignalGroupOutline(
        name="all_labs",
        description="All lab results",
        domain="laboratory",
        members=[],
    )
    assert outline.name == "all_labs"
    assert outline.domain == "laboratory"


def test_signal_group_outline_custom():
    """SignalGroupOutline model works for custom group."""
    outline = SignalGroupOutline(
        name="renal_panel",
        description="Renal monitoring",
        members=["creatinine", "hemoglobin"],
    )
    assert outline.members == ["creatinine", "hemoglobin"]
    assert outline.domain is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py::test_signal_group_outline_schema -v`

Expected: FAIL with `ImportError: cannot import name 'SignalGroupOutline'`

- [ ] **Step 3: Add SignalGroupOutline to schemas.py**

In `backend/app/models/schemas.py`, after `LogicOutline` (around line 74), add:

```python
class SignalGroupOutline(BaseModel):
    """Signal group in the outline (RFC 2026-04-09)."""

    name: str
    description: str
    domain: Optional[str] = Field(None, description="ClinicalDomain value for domain-level group")
    members: List[str] = Field(default_factory=list, description="Signal names for custom group")
```

Update `OutlineResponse` (around line 83-91) to add:

```python
    signal_groups: List[SignalGroupOutline] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v`

Expected: All 18 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/schemas.py backend/tests/test_signal_groups.py
git commit -m "feat: add SignalGroupOutline schema (RFC 2026-04-09)"
```

---

### Task 4: Wire signal_groups into outline and export services

**Files:**
- Modify: `backend/app/services/outliner.py`
- Modify: `backend/app/services/exporter.py`
- Modify: `backend/tests/test_signal_groups.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_signal_groups.py`:

```python
from app.services.outliner import generate_outline
from app.services.validator import validate_scenario


GROUPS_YAML = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All lab results"
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal monitoring"
"""


def test_outline_includes_signal_groups():
    """Outline response includes signal groups."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    assert scenario is not None
    outline = generate_outline(scenario)
    assert len(outline.signal_groups) == 2
    names = [g.name for g in outline.signal_groups]
    assert "all_labs" in names
    assert "renal_panel" in names


def test_outline_domain_group_has_domain():
    """Domain-level group outline has domain field set."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    outline = generate_outline(scenario)
    all_labs = next(g for g in outline.signal_groups if g.name == "all_labs")
    assert all_labs.domain == "laboratory"
    assert all_labs.members == []


def test_outline_custom_group_has_members():
    """Custom group outline has members list."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    outline = generate_outline(scenario)
    renal = next(g for g in outline.signal_groups if g.name == "renal_panel")
    assert renal.domain is None
    assert renal.members == ["creatinine", "hemoglobin"]


def test_outline_no_groups_when_absent():
    """Outline has empty signal_groups when section not present."""
    scenario, errors, warnings = validate_scenario(MINIMAL_YAML)
    outline = generate_outline(scenario)
    assert outline.signal_groups == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py::test_outline_includes_signal_groups -v`

Expected: FAIL -- `generate_outline()` return doesn't have `signal_groups`

- [ ] **Step 3: Update outliner service**

In `backend/app/services/outliner.py`:

1. Import the new schema:

```python
from app.models.schemas import SignalGroupOutline
```

2. Add after `generate_outline()` function (around line 90):

```python
def _build_signal_group_outlines(scenario) -> list:
    """Build signal group outlines from parsed scenario."""
    groups = []
    for name, group in getattr(scenario, 'signal_groups', {}).items():
        groups.append(SignalGroupOutline(
            name=name,
            description=group.description,
            domain=group.domain.value if group.domain else None,
            members=group.members if group.members else [],
        ))
    return groups
```

3. In `generate_outline()`, add before the return statement:

```python
    signal_group_outlines = _build_signal_group_outlines(scenario)
```

4. Add `signal_groups=signal_group_outlines` to the `OutlineResponse(...)` return.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_signal_groups.py -v`

Expected: All 22 tests PASS

- [ ] **Step 5: Update exporter bundle version and summary**

In `backend/app/services/exporter.py`:

1. Update `BUNDLE_VERSION` (line 36) from `"1.1"` to `"1.2"`.

2. In `_generate_summary()` (around line 186-294), add after the logic summary section:

```python
    # Signal Groups (RFC 2026-04-09)
    if hasattr(scenario, 'signal_groups') and scenario.signal_groups:
        lines.append("")
        if format == "markdown":
            lines.append("## Signal Groups")
            lines.append("")
            for name, group in scenario.signal_groups.items():
                if group.domain:
                    lines.append(f"- **{name}**: domain={group.domain.value} -- {group.description}")
                elif group.members:
                    lines.append(f"- **{name}**: [{', '.join(group.members)}] -- {group.description}")
        else:
            lines.append("SIGNAL GROUPS:")
            for name, group in scenario.signal_groups.items():
                if group.domain:
                    lines.append(f"  - {name}: domain={group.domain.value} -- {group.description}")
                elif group.members:
                    lines.append(f"  - {name}: [{', '.join(group.members)}] -- {group.description}")
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/outliner.py backend/app/services/exporter.py backend/tests/test_signal_groups.py
git commit -m "feat: wire signal_groups into outline and export (RFC 2026-04-09)"
```

---

### Task 5: Add signal_groups to frontend types and OutlineTree

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/OutlineTree.tsx`

- [ ] **Step 1: Add TypeScript interface**

In `frontend/src/lib/api.ts`, after `LogicOutline` (around line 48), add:

```typescript
export interface SignalGroupOutline {
  name: string;
  description: string;
  domain: string | null;
  members: string[];
}
```

Update `OutlineResponse` (around line 50-57) to add:

```typescript
  signal_groups: SignalGroupOutline[];
```

- [ ] **Step 2: Add SignalGroupItem component to OutlineTree**

In `frontend/src/components/OutlineTree.tsx`:

1. Update imports to include `Layers` icon and `SignalGroupOutline` type:

```typescript
import { ChevronRight, ChevronDown, Zap, TrendingUp, GitBranch, Layers } from 'lucide-react';
import type { OutlineResponse, SignalOutline, TrendOutline, LogicOutline, SignalGroupOutline } from '@/lib/api';
```

2. Add `SignalGroupItem` component after `LogicItem` (around line 122):

```typescript
function SignalGroupItem({ group }: { group: SignalGroupOutline }) {
  return (
    <div className="p-2 rounded bg-surface-hover hover:bg-border">
      <div className="flex items-center gap-2">
        <span className="font-mono text-indigo-600 dark:text-indigo-400">{group.name}</span>
      </div>
      {group.domain && (
        <div className="text-xs text-muted mt-1">
          Domain: <span className="font-mono">{group.domain}</span>
        </div>
      )}
      {group.members.length > 0 && (
        <div className="text-xs text-muted mt-1">
          Members: <span className="font-mono">{group.members.join(', ')}</span>
        </div>
      )}
      <div className="text-xs text-muted mt-1">{group.description}</div>
    </div>
  );
}
```

3. Add section in the `OutlineTree` component render, after the Signals section (around line 163):

```typescript
      {/* Signal Groups (RFC 2026-04-09) */}
      {outline.signal_groups && outline.signal_groups.length > 0 && (
        <TreeSection
          title="Signal Groups"
          icon={<Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />}
          count={outline.signal_groups.length}
          defaultOpen={false}
        >
          {outline.signal_groups.map((group) => (
            <SignalGroupItem key={group.name} group={group} />
          ))}
        </TreeSection>
      )}
```

- [ ] **Step 3: Verify frontend compiles**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/frontend && npx next build 2>&1 | tail -20`

Expected: Build succeeds with no type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/components/OutlineTree.tsx
git commit -m "feat: display signal groups in outline tree (RFC 2026-04-09)"
```

---

### Task 6: Add signal_groups to BundlePanel

**Files:**
- Modify: `frontend/src/components/BundlePanel.tsx`

- [ ] **Step 1: Add signal groups section to BundlePanel**

In `frontend/src/components/BundlePanel.tsx`, after the Scenario section (around line 132) and before the Audit Trail section, add:

```typescript
      {/* Signal Groups (RFC 2026-04-09) */}
      {bundle.signal_groups && bundle.signal_groups.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
            Signal Groups
          </h3>
          <div className="bg-surface rounded-lg p-4 space-y-3 border border-border">
            {bundle.signal_groups.map((group) => (
              <div key={group.name} className="border-b border-border pb-3 last:border-b-0 last:pb-0">
                <div className="font-semibold text-foreground">{group.name}</div>
                <div className="text-sm text-muted mt-1">{group.description}</div>
                {group.domain && (
                  <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300">
                    domain: {group.domain}
                  </span>
                )}
                {group.members && group.members.length > 0 && (
                  <div className="text-xs text-muted mt-1 font-mono">
                    [{group.members.join(', ')}]
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
```

- [ ] **Step 2: Update CertifiedBundle type if not already done**

In `frontend/src/lib/api.ts`, verify `CertifiedBundle` (around line 80-88) includes:

```typescript
  signal_groups?: SignalGroupOutline[];
```

- [ ] **Step 3: Verify frontend compiles**

Run: `cd /Volumes/extraSupply/Projects/psdl-inspector/frontend && npx next build 2>&1 | tail -20`

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/BundlePanel.tsx frontend/src/lib/api.ts
git commit -m "feat: display signal groups in bundle panel (RFC 2026-04-09)"
```

---

### Task 7: End-to-end verification with test case

**Files:**
- Test: `testorg/postop_surgical_cohort/postop_surgical_cohort.yaml` (already has groups)

- [ ] **Step 1: Start backend and frontend**

```bash
cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8200 &
cd /Volumes/extraSupply/Projects/psdl-inspector/frontend && npm run dev &
```

- [ ] **Step 2: Validate via API**

```bash
curl -s -X POST http://localhost:8200/api/validate \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(cat testorg/postop_surgical_cohort/postop_surgical_cohort.yaml | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\"}" \
  | python3 -m json.tool | head -20
```

Expected: `"valid": true`

- [ ] **Step 3: Verify outline includes groups**

```bash
curl -s -X POST http://localhost:8200/api/outline \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(cat testorg/postop_surgical_cohort/postop_surgical_cohort.yaml | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Signal groups:', len(d.get('signal_groups',[]))); [print(f'  - {g[\"name\"]}: {g.get(\"domain\") or g.get(\"members\")}') for g in d.get('signal_groups',[])]"
```

Expected: 9 signal groups listed (6 domain-level + 3 custom panels)

- [ ] **Step 4: Verify bundle export includes groups**

```bash
curl -s -X POST http://localhost:8200/api/export/bundle \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(cat testorg/postop_surgical_cohort/postop_surgical_cohort.yaml | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Bundle version:', d['bundle_version']); print('Signal groups in bundle:', 'signal_groups' in d.get('summary',''))"
```

Expected: Bundle version 1.2, signal groups mentioned in summary

- [ ] **Step 5: Manual browser test**

Open http://localhost:9806, load the test YAML in Editor mode:
1. Verify validation passes (green)
2. Click Preview -- verify "Signal Groups" section appears in outline tree
3. Click Export -- verify signal groups appear in bundle panel

- [ ] **Step 6: Run full test suite**

```bash
cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: signal groups extension complete (RFC 2026-04-09)

Adds signal_groups as optional PSDL section supporting:
- Domain-level bulk data requests (all_labs, all_meds, etc.)
- Custom named signal panels (renal_panel, coag_panel, etc.)
Modeled after OHDSI Concept Sets. Groups are data extraction
declarations only - no interaction with trends or logic."
```
