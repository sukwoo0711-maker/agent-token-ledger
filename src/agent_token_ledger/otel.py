from __future__ import annotations

from typing import Any


def to_otel_like(trace: dict[str, Any]) -> dict[str, Any]:
    """Return an OTLP-friendly envelope without requiring an OTel SDK.

    GenAI semantic conventions are still evolving, so the canonical trace is
    preserved and mapped at export time.
    """
    spans = []
    metrics = []
    for source in trace["spans"]:
        attributes: dict[str, Any] = {
            "atl.span.kind": source["kind"],
            "atl.workflow.name": trace.get("workflow_name"),
        }
        if source.get("agent_name"):
            attributes["gen_ai.agent.name"] = source["agent_name"]
        if source.get("model"):
            attributes["gen_ai.request.model"] = source["model"]
        if source.get("provider"):
            attributes["gen_ai.provider.name"] = source["provider"]
        if source["kind"] == "agent":
            attributes["gen_ai.operation.name"] = "invoke_agent"
        elif source["kind"] == "llm":
            attributes["gen_ai.operation.name"] = "generate_content"
        attributes.update(source.get("attributes", {}))
        spans.append(
            {
                "trace_id": source["trace_id"],
                "span_id": source["span_id"],
                "parent_span_id": source.get("parent_span_id"),
                "name": source["name"],
                "start_time": source["started_at"],
                "end_time": source.get("ended_at"),
                "attributes": attributes,
            }
        )
        usage = source.get("usage", {})
        for token_type, key in (("input", "input_tokens"), ("output", "output_tokens")):
            value = int(usage.get(key, 0))
            if value:
                metrics.append(
                    {
                        "name": "gen_ai.client.token.usage",
                        "unit": "{token}",
                        "value": value,
                        "attributes": {
                            "gen_ai.operation.name": "generate_content",
                            "gen_ai.provider.name": source.get("provider") or "unknown",
                            "gen_ai.request.model": source.get("model") or "unknown",
                            "gen_ai.token.type": token_type,
                            "atl.trace_id": source["trace_id"],
                            "atl.span_id": source["span_id"],
                        },
                    }
                )
    return {"spans": spans, "metrics": metrics}
