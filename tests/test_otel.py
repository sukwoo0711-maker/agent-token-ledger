from agent_token_ledger import TraceRecorder, Usage
from agent_token_ledger.otel import to_otel_like


def test_otel_export_has_token_metrics_and_agent_parentage():
    recorder = TraceRecorder("otel")
    with recorder.span("root", kind="workflow"):
        with recorder.span("agent", kind="agent", agent_name="researcher") as agent:
            with recorder.span("call", kind="llm", provider="ollama", model="qwen") as llm:
                recorder.record_usage(llm, Usage(input_tokens=8, output_tokens=2))
    payload = to_otel_like(recorder.to_dict())
    assert len(payload["metrics"]) == 2
    exported_agent = next(item for item in payload["spans"] if item["span_id"] == agent.span_id)
    assert exported_agent["attributes"]["gen_ai.operation.name"] == "invoke_agent"
    assert any(metric["name"] == "gen_ai.client.token.usage" for metric in payload["metrics"])
