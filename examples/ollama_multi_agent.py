from __future__ import annotations

import argparse
from pathlib import Path

from agent_token_ledger import TraceRecorder, build_report, render_markdown
from agent_token_ledger.ollama import generate


def run_model(recorder: TraceRecorder, layer: str, model: str, prompt: str) -> str:
    with recorder.span(
        f"generate {model}", kind="llm", provider="ollama", model=model, layer=layer
    ) as llm_span:
        result = generate(model, prompt, num_predict=64)
        recorder.record_usage(llm_span, result.usage)
        llm_span.attributes["ollama.total_duration_ns"] = result.total_duration_ns
        llm_span.attributes["response.preview"] = (result.content or result.thinking)[:160]
        return result.content or result.thinking


def run_agent(recorder: TraceRecorder, name: str, layer: str, model: str, prompt: str) -> str:
    with recorder.span(name, kind="agent", agent_name=name, layer=layer):
        return run_model(recorder, layer, model, prompt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast-model", default="hermes3:3b")
    parser.add_argument("--deep-model", default="qwen3.5:9b")
    parser.add_argument("--verify-model", default="qwen2.5-coder:7b")
    parser.add_argument("--output", type=Path, default=Path("artifacts/local-trace.json"))
    args = parser.parse_args()

    recorder = TraceRecorder("local-model-switching-demo")
    with recorder.span("user query", kind="workflow"):
        with recorder.span("orchestrator", kind="agent", agent_name="orchestrator", layer="planning"):
            plan = run_model(
                recorder,
                "planning",
                args.fast_model,
                "Plan a concise answer: Why must nested agent token reports separate exclusive and subtree usage?",
            )
            analysis = run_agent(
                recorder,
                "researcher",
                "analysis",
                args.deep_model,
                f"Give two rigorous reasons and one example. Plan context: {plan[:300]}",
            )
            verification = run_agent(
                recorder,
                "verifier",
                "verification",
                args.verify_model,
                f"Find one accounting flaw in this explanation and correct it: {analysis[:500]}",
            )
            run_agent(
                recorder,
                "synthesizer",
                "synthesis",
                args.fast_model,
                f"Write a two-sentence final answer using this analysis and verification: {analysis[:350]} {verification[:350]}",
            )

    recorder.export_json(args.output)
    report = build_report(recorder.to_dict())
    report_path = args.output.with_suffix(".md")
    report_path.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    print(f"Trace: {args.output}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
