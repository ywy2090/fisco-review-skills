#!/usr/bin/env python3
"""verify_findings.py — the aggregation gate's mechanical floor (v2.2.0).

Validates every finding in a findings JSON against the materialized head tree:
  FILE_OK          the file exists under <tree-dir>
  LINE_OK          line_start/line_end fall inside the file
  QUOTE_AT         evidence_quote appears verbatim at/near the claimed lines (±15)
  QUOTE_ELSEWHERE  verbatim elsewhere in the file (line number wrong, quote real)
  QUOTE_FUZZY      only whitespace-normalized match (report, don't drop silently)
  QUOTE_NOT_FOUND  the quote does not exist — hallucinated or hand-edited evidence
  FILE_NOT_FOUND   the cited file is absent from the tree

Input format: either the ledger's findings.json (array of objects with
`location` "file:line") or a module/aggregate output (object with a
`findings` array carrying `file`, `line_start`, `evidence_quote`).
Both forms may carry the quote under `evidence_quote` or an `evidence` block.

Exit code: 0 when no QUOTE_NOT_FOUND / FILE_NOT_FOUND, 2 otherwise — wire it
into the aggregation gate so a non-zero run blocks the report, and treat
QUOTE_ELSEWHERE / QUOTE_FUZZY as fix-the-line-number, not drop-the-finding.
"""
import json
import re
import sys
from pathlib import Path

WINDOW = 15


def load_findings(path):
    data = json.loads(Path(path).read_text(errors="replace"))
    if isinstance(data, dict) and "findings" not in data and "output" in data:
        data = data["output"]  # a raw run record wrapping {findings, ...}
    items = data if isinstance(data, list) else data.get("findings", [])
    out = []
    for f in items:
        loc = f.get("location") or f.get("file") or ""
        file = f.get("file") or loc.rsplit(":", 1)[0]
        ls = f.get("line_start")
        if ls is None and ":" in loc:
            head = loc.rsplit(":", 1)[1]
            ls = int(head) if head.isdigit() else None
        quote = f.get("evidence_quote")
        if not quote:  # F-block prose form: strip **Evidence:** markers/code fences
            quote = f.get("evidence") or ""
            quote = re.sub(r"^```[a-z]*\s*|\s*```$", "", str(quote).strip(), flags=re.M)
        out.append({"id": f.get("id") or f.get("title", "?"),
                    "file": file, "line_start": ls,
                    "quote": str(quote).strip("\n")})
    return out


def normalize(s):
    return re.sub(r"\s+", "", s)


def check(f, tree):
    p = tree / f["file"]
    if not p.is_file():
        return "FILE_NOT_FOUND", ""
    lines = p.read_text(errors="replace").splitlines()
    if not f["quote"].strip():
        # ledger form carries no quote: verify existence + bounds only
        if f["line_start"] and not (1 <= f["line_start"] <= len(lines)):
            return "LINE_OUT_OF_RANGE", f"n_lines={len(lines)}"
        return "FILE_OK_NO_QUOTE", f"n_lines={len(lines)}"
    qlines = [l.rstrip() for l in f["quote"].splitlines() if l.strip()]
    joined = "\n".join(qlines)
    text = "\n".join(l.rstrip() for l in lines)
    if joined in text:
        at = text[:text.find(joined)].count("\n") + 1
        claimed = f["line_start"] or 0
        if abs(at - claimed) <= WINDOW:
            return "QUOTE_AT", f"actual~{at}"
        return "QUOTE_ELSEWHERE", f"actual~{at} claimed {claimed}"
    if normalize(joined) and normalize(joined) in normalize(text):
        return "QUOTE_FUZZY", ""
    return "QUOTE_NOT_FOUND", f"n_lines={len(lines)}"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    tree = Path(sys.argv[2])
    verdicts = {}
    for f in load_findings(sys.argv[1]):
        v, detail = check(f, tree)
        verdicts.setdefault(v, []).append(f["id"])
        if v in ("QUOTE_NOT_FOUND", "FILE_NOT_FOUND", "QUOTE_FUZZY", "QUOTE_ELSEWHERE"):
            print(f"  [{v}] {f['file']}:{f['line_start']} {str(f['id'])[:60]} {detail}")
    total = sum(len(v) for v in verdicts.values())
    print(f"{sys.argv[1]}: {total} findings → " +
          ", ".join(f"{k}:{len(v)}" for k, v in sorted(verdicts.items())))
    sys.exit(2 if (verdicts.get("QUOTE_NOT_FOUND") or verdicts.get("FILE_NOT_FOUND")) else 0)


if __name__ == "__main__":
    main()
