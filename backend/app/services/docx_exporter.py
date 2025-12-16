"""Word document generator for IRB preparation."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


def generate_irb_document(
    scenario_info: Dict[str, Any],
    governance_data: Dict[str, Optional[str]],
) -> bytes:
    """Generate Word document for IRB preparation.

    Args:
        scenario_info: Auto-derived info from PSDL scenario
        governance_data: User-provided governance narrative

    Returns:
        bytes: Word document content
    """
    doc = Document()

    # Set default font
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)

    # Title
    title = doc.add_heading('Algorithm Documentation for IRB Review', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Generation metadata
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    meta.add_run("\n")
    meta.add_run(f"PSDL Inspector - psdl-lang v{scenario_info.get('psdl_lang_version', 'N/A')}")
    doc.add_paragraph()

    # Section 1: Algorithm Overview
    doc.add_heading('1. Algorithm Overview', level=1)
    overview_table = doc.add_table(rows=3, cols=2)
    overview_table.style = 'Table Grid'
    _add_table_row(overview_table.rows[0], 'Name', scenario_info.get('name', 'N/A'))
    _add_table_row(overview_table.rows[1], 'Version', scenario_info.get('version', 'N/A'))
    _add_table_row(overview_table.rows[2], 'Description', scenario_info.get('description', 'N/A'))
    doc.add_paragraph()

    # Section 2: Clinical Summary
    doc.add_heading('2. Clinical Summary', level=1)
    clinical_summary = governance_data.get('clinical_summary')
    if clinical_summary:
        doc.add_paragraph(clinical_summary)
    else:
        p = doc.add_paragraph()
        p.add_run('[Not provided]').italic = True
    doc.add_paragraph()

    # Section 3: Data Elements Required
    doc.add_heading('3. Data Elements Required', level=1)
    signals = scenario_info.get('signals', [])
    if signals:
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text = 'Signal Name'
        hdr[1].text = 'Reference'
        hdr[2].text = 'Unit'
        hdr[3].text = 'Concept ID'
        for cell in hdr:
            cell.paragraphs[0].runs[0].bold = True

        for signal in signals:
            row = table.add_row().cells
            row[0].text = signal.get('name', '-')
            row[1].text = signal.get('ref', '-') or '-'
            row[2].text = signal.get('unit', '-') or '-'
            row[3].text = str(signal.get('concept_id', '-')) if signal.get('concept_id') else '-'
    else:
        p = doc.add_paragraph()
        p.add_run('No data elements defined.').italic = True
    doc.add_paragraph()

    # Section 4: Trend Definitions
    doc.add_heading('4. Trend Definitions', level=1)
    trends = scenario_info.get('trends', [])
    if trends:
        for trend in trends:
            p = doc.add_paragraph()
            p.add_run(f"{trend.get('name', 'Unknown')}").bold = True
            doc.add_paragraph(f"Expression: {trend.get('expr', 'N/A')}")
            if trend.get('description'):
                doc.add_paragraph(f"Description: {trend.get('description')}")
            doc.add_paragraph()
    else:
        p = doc.add_paragraph()
        p.add_run('No trends defined.').italic = True
    doc.add_paragraph()

    # Section 5: Detection Logic
    doc.add_heading('5. Detection Logic', level=1)
    logic_rules = scenario_info.get('logic', [])
    if logic_rules:
        for rule in logic_rules:
            p = doc.add_paragraph()
            p.add_run(f"{rule.get('name', 'Unknown')}").bold = True
            severity = rule.get('severity')
            if severity:
                p.add_run(f" [{severity.upper()}]")
            doc.add_paragraph(f"Condition: {rule.get('expr', 'N/A')}")
            if rule.get('description'):
                doc.add_paragraph(f"Description: {rule.get('description')}")
            if rule.get('recommendation'):
                doc.add_paragraph(f"Recommendation: {rule.get('recommendation')}")
            doc.add_paragraph()
    else:
        p = doc.add_paragraph()
        p.add_run('No logic rules defined.').italic = True
    doc.add_paragraph()

    # Section 6: Justification
    doc.add_heading('6. Justification', level=1)
    justification = governance_data.get('justification')
    if justification:
        doc.add_paragraph(justification)
    else:
        p = doc.add_paragraph()
        p.add_run('[Not provided]').italic = True
    doc.add_paragraph()

    # Section 7: Risk Assessment
    doc.add_heading('7. Risk Assessment', level=1)
    risk_assessment = governance_data.get('risk_assessment')
    if risk_assessment:
        doc.add_paragraph(risk_assessment)
    else:
        p = doc.add_paragraph()
        p.add_run('[Not provided]').italic = True
    doc.add_paragraph()

    # Section 8: Algorithm Summary
    doc.add_heading('8. Algorithm Summary', level=1)
    doc.add_paragraph(
        f"This algorithm monitors {len(signals)} data element(s) and defines "
        f"{len(trends)} trend calculation(s) to detect conditions through "
        f"{len(logic_rules)} logic rule(s)."
    )
    doc.add_paragraph()

    # Footer note
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(
        "This document was generated by PSDL Inspector for IRB preparation purposes. "
        "The algorithm specification was validated against psdl-lang standards."
    )
    run.italic = True
    run.font.size = Pt(9)

    # Save to bytes
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _add_table_row(row, label: str, value: str) -> None:
    """Helper to add a row to a table."""
    row.cells[0].text = label
    row.cells[0].paragraphs[0].runs[0].bold = True
    row.cells[1].text = value or 'N/A'
