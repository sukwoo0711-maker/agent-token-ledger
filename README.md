# Agent Token Ledger

Trace one user request across nested agents and models, then attribute measured tokens and cost without double-counting.

```text
User query: 184,200 tokens
├─ orchestrator · exclusive 12,400 · subtree 184,200
├─ researcher · exclusive 54,100 · subtree 54,100
├─ reviewer · exclusive 78,600 · subtree 78,600
└─ synthesizer · exclusive 39,100 · subtree 39,100
```

`exclusive` usage partitions the trace exactly once and is safe for percentages. `subtree` usage includes descendants and is useful for diagnosing expensive branches, but overlaps by design.

## Why this exists

Provider dashboards usually stop at account, API key, or request totals. Multi-agent systems need a stricter ledger:

- one root trace per user request;
- parent-child agent and tool spans;
- provider-reported input/output/cache/reasoning token counts;
- exclusive agent ownership for valid percentages;
- subtree totals for branch diagnostics;
- model, layer, retry, latency, status, and optional cost attribution.

## Quick start

Python 3.11+ is required. The core has no runtime dependencies.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python examples/ollama_multi_agent.py
python -m agent_token_ledger artifacts/local-trace.json
python -m agent_token_ledger artifacts/local-trace.json --footer
```

The Ollama demo switches between a fast orchestrator model, a deeper analysis model, a verifier, and a final synthesizer. Override models as needed:

```powershell
python examples/ollama_multi_agent.py `
  --fast-model hermes3:3b `
  --deep-model qwen3.5:9b `
  --verify-model qwen2.5-coder:7b
```

## Minimal instrumentation

```python
from agent_token_ledger import TraceRecorder, Usage, build_report

recorder = TraceRecorder("answer-user-query")
with recorder.span("request", kind="workflow"):
    with recorder.span("researcher", kind="agent", agent_name="researcher", layer="research"):
        with recorder.span("model call", kind="llm", provider="ollama", model="qwen3.5:9b") as call:
            response = provider_call()
            recorder.record_usage(call, Usage(input_tokens=1200, output_tokens=400))

report = build_report(recorder.to_dict())
```

## OpenTelemetry alignment

The exporter maps agent spans to `gen_ai.operation.name=invoke_agent` and emits `gen_ai.client.token.usage` metric points with input/output token types. The canonical trace stays independent because the GenAI semantic conventions are still evolving.

See [DESIGN.md](docs/DESIGN.md) for accounting rules and [AUTO_GRILL.md](docs/AUTO_GRILL.md) for adversarial review findings.

For personal AI stacks, copy the provider-neutral [Portable LLM Footer rule](docs/LLM_FOOTER_RULE.md). The [1:1 gap analysis](docs/RULE_GAP_ANALYSIS.md) explains how it extends a basic per-agent/model/token footer with coverage, enforcement, and privacy requirements.
The [footer emission auto-grill](docs/FOOTER_EMISSION_GRILL.md) defines why ten subagents still produce one terminal root footer.

## Evidence and references

- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- [OpenTelemetry GenAI token usage metric](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-metrics.md)
- [Ollama generate API](https://docs.ollama.com/api/generate)

## Status

Experimental alpha. The local Ollama integration provides real token counts, but distributed context propagation and a production OTLP exporter remain future work.

## License

MIT
