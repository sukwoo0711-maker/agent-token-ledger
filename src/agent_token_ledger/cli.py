from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report import build_report, render_footer, render_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Report hierarchical agent token attribution")
    parser.add_argument("trace", type=Path, help="Canonical trace JSON")
    parser.add_argument("--json", action="store_true", help="Emit the aggregate report as JSON")
    parser.add_argument("--footer", action="store_true", help="Emit only the portable LLM usage footer")
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    report = build_report(trace)
    if args.json and args.footer:
        parser.error("--json and --footer are mutually exclusive")
    output = json.dumps(report, indent=2) if args.json else render_footer(report) if args.footer else render_markdown(report)
    print(output, end="")


if __name__ == "__main__":
    main()
