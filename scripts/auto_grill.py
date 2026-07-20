from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_token_ledger.ollama import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run adversarial local-model reviews")
    parser.add_argument("--models", default="spec-analyst:latest,code-assistant:latest")
    parser.add_argument("--output", type=Path, default=Path("artifacts/auto-grill.json"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    evidence = "\n\n".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in [
            "docs/DESIGN.md",
            "docs/LLM_FOOTER_RULE.md",
            "docs/FOOTER_EMISSION_GRILL.md",
            "src/agent_token_ledger/recorder.py",
            "src/agent_token_ledger/report.py",
            "tests/test_attribution.py",
            "tests/test_concurrency.py",
            "tests/test_footer.py",
        ]
    )
    prompt = f"""ADVERSARIAL REVIEW ONLY. Do not summarize the project. Do not praise it.
Find concrete counterexamples that make per-agent percentages, parentage, or footer emission count wrong.
Inspect malformed traces, duplicate instrumentation, nested agents, failed calls, concurrency,
unknown pricing, rounding, ten-agent fan-out, detached agents, and LLM-generated footer recursion.
If a suspected issue is already prevented, omit it.
Output only lines in this format:
FINDING | severity | exact trigger | wrong result | exact repair | missing regression test
Return 3 to 6 findings. If none exist, output exactly NO_FINDINGS.

PROJECT EVIDENCE:
{evidence[:24000]}
"""
    results = []
    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        response = generate(model, prompt, num_predict=512, timeout=300)
        results.append(
            {
                "model": response.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "review": response.content or response.thinking,
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
