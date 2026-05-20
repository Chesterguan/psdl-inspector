"""`psdl-meds` command-line entry point.

Two subcommands:

- `convert`: Read a CSV (or SQL-result JSON) of `(subject_id, time, code,
  numeric_value)` rows and emit a validated MEDS Parquet shard.
- `preview`: Read anchored signals JSON and emit a synthetic preview
  shard for Inspector-style UX.

Both subcommands print a JSON summary `{n_events, n_subjects, path}` to
stdout so they're easy to chain in shell pipelines.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from psdl_meds.preview import synthesize_preview
from psdl_meds.validator import validate_shard
from psdl_meds.writer import write_meds_shard


def _parse_csv(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "subject_id": int(r["subject_id"]),
                    "time": datetime.fromisoformat(r["time"]),
                    "code": r["code"],
                    "numeric_value": (
                        float(r["numeric_value"])
                        if r.get("numeric_value") not in (None, "", "null")
                        else None
                    ),
                }
            )
    return rows


def _cmd_convert(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.out)
    if src.suffix.lower() == ".csv":
        rows = _parse_csv(src)
    elif src.suffix.lower() == ".json":
        rows_raw = json.loads(src.read_text())
        rows = [
            {
                **r,
                "time": datetime.fromisoformat(r["time"]),
            }
            for r in rows_raw
        ]
    else:
        print(f"unsupported input extension: {src.suffix}", file=sys.stderr)
        return 2

    summary = write_meds_shard(rows, out)
    validate_shard(out)
    print(json.dumps({**summary, "path": str(out)}))
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    anchors = json.loads(Path(args.anchors).read_text())
    rows = synthesize_preview(anchors, n=args.n)
    summary = write_meds_shard(rows, Path(args.out))
    validate_shard(Path(args.out))
    print(json.dumps({**summary, "path": args.out}))
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="psdl-meds")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_convert = sub.add_parser("convert", help="Convert CSV/JSON rows to a MEDS Parquet shard")
    p_convert.add_argument("--input", required=True, help="Path to .csv or .json input")
    p_convert.add_argument("--out", required=True, help="Path to output .parquet")
    p_convert.set_defaults(func=_cmd_convert)

    p_preview = sub.add_parser("preview", help="Synthesize a preview shard from anchored signals JSON")
    p_preview.add_argument("--anchors", required=True, help="Path to anchors .json")
    p_preview.add_argument("--out", required=True, help="Path to output .parquet")
    p_preview.add_argument("-n", type=int, default=10, help="Number of preview rows (default 10)")
    p_preview.set_defaults(func=_cmd_preview)

    ns = parser.parse_args(list(argv) if argv is not None else None)
    return ns.func(ns)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
