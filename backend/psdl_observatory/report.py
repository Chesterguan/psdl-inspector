"""Render a self-contained static HTML report from a ScanResult.

Single-file HTML (inline CSS, no JS deps) so it can be opened directly or
bundled with the scan output. All dynamic text is HTML-escaped.
"""

from __future__ import annotations

from html import escape

from psdl_observatory.models import ScanResult


def render_html_report(result: ScanResult) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(f.relative_path)}</td>"
        f"<td>{f.num_rows}</td>"
        f"<td>{f.num_row_groups}</td>"
        f"<td>{f.num_columns}</td>"
        f"<td><code>{escape(f.schema_signature)}</code></td>"
        f"<td>{escape('|'.join(f.columns))}</td>"
        "</tr>"
        for f in result.files
    )
    dup_rows = "\n".join(
        f"<tr><td>{escape(name)}</td><td>{len(paths)}</td><td>{escape(', '.join(paths))}</td></tr>"
        for name, paths in sorted(result.duplicate_filenames().items())
    ) or '<tr><td colspan="3">none</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PSDL Observatory — Inventory</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
 h1 {{ font-size: 1.4rem; }}
 .stats {{ display: flex; gap: 2rem; margin: 1rem 0; flex-wrap: wrap; }}
 .stat {{ background: #f4f4f7; border-radius: 8px; padding: 0.75rem 1rem; }}
 .stat b {{ display: block; font-size: 1.5rem; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.85rem; }}
 th, td {{ border: 1px solid #ddd; padding: 4px 8px; text-align: left; }}
 th {{ background: #f0f0f3; }}
 code {{ font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>PSDL Observatory — Inventory Scan</h1>
<p>Root: <code>{escape(result.root)}</code></p>
<div class="stats">
  <div class="stat"><b>{result.total_files}</b>Total files</div>
  <div class="stat"><b>{result.total_rows}</b>Total rows</div>
  <div class="stat"><b>{result.distinct_schema_count}</b>Distinct schemas</div>
  <div class="stat"><b>{len(result.duplicate_filenames())}</b>Duplicate filenames</div>
  <div class="stat"><b>{len(result.errors)}</b>Errors</div>
</div>
<h2>Files</h2>
<table>
<tr><th>Relative path</th><th>Rows</th><th>Row groups</th><th>Cols</th><th>Schema sig</th><th>Columns</th></tr>
{rows}
</table>
<h2>Duplicate filenames</h2>
<table>
<tr><th>Filename</th><th>Count</th><th>Paths</th></tr>
{dup_rows}
</table>
</body>
</html>
"""
