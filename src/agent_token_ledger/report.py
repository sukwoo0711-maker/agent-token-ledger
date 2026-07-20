from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any


def _usage_total(span: dict[str, Any]) -> int:
    return int(span.get("usage", {}).get("input_tokens", 0)) + int(
        span.get("usage", {}).get("output_tokens", 0)
    )


def build_report(trace: dict[str, Any]) -> dict[str, Any]:
    spans = trace["spans"]
    by_id = {span["span_id"]: span for span in spans}
    children: dict[str | None, list[str]] = defaultdict(list)
    for span in spans:
        children[span.get("parent_span_id")].append(span["span_id"])

    subtree_cache: dict[str, int] = {}

    def subtree_tokens(span_id: str) -> int:
        if span_id not in subtree_cache:
            subtree_cache[span_id] = _usage_total(by_id[span_id]) + sum(
                subtree_tokens(child) for child in children.get(span_id, [])
            )
        return subtree_cache[span_id]

    measured_spans = [span for span in spans if _usage_total(span) > 0]
    total = sum(_usage_total(span) for span in measured_spans)
    priced_spans = [span for span in measured_spans if span.get("cost_usd") is not None]
    priced_tokens = sum(_usage_total(span) for span in priced_spans)
    total_cost = sum(float(span["cost_usd"]) for span in priced_spans) if priced_spans else None
    agents = [span for span in spans if span["kind"] == "agent"]
    agent_ids = {span["span_id"] for span in agents}

    def parent_agent_id(span: dict[str, Any]) -> str | None:
        parent_id = span.get("parent_span_id")
        while parent_id:
            if parent_id in agent_ids:
                return parent_id
            parent_id = by_id[parent_id].get("parent_span_id")
        return None

    def agent_depth(span: dict[str, Any]) -> int:
        depth = 0
        parent_id = parent_agent_id(span)
        while parent_id:
            depth += 1
            parent_id = parent_agent_id(by_id[parent_id])
        return depth

    agent_rows = []
    for agent in agents:
        exclusive_spans = [s for s in measured_spans if s.get("owner_agent_span_id") == agent["span_id"]]
        exclusive = sum(_usage_total(span) for span in exclusive_spans)
        subtree = subtree_tokens(agent["span_id"])
        agent_rows.append(
            {
                "span_id": agent["span_id"],
                "parent_agent_span_id": parent_agent_id(agent),
                "depth": agent_depth(agent),
                "agent_name": agent.get("agent_name") or agent["name"],
                "layer": agent.get("layer") or "unassigned",
                "exclusive_tokens": exclusive,
                "subtree_tokens": subtree,
                "exclusive_share_pct": round(exclusive * 100 / total, 2) if total else 0.0,
                "subtree_share_pct": round(subtree * 100 / total, 2) if total else 0.0,
                "cost_usd": (
                    sum(float(span["cost_usd"]) for span in exclusive_spans)
                    if exclusive_spans and all(span.get("cost_usd") is not None for span in exclusive_spans)
                    else None
                ),
                "status": agent.get("status"),
            }
        )

    def grouped(field: str, fallback: str = "unknown") -> list[dict[str, Any]]:
        bucket: dict[str, int] = defaultdict(int)
        for span in measured_spans:
            value = span.get(field)
            if field == "layer" and not value and span.get("owner_agent_span_id"):
                value = by_id[span["owner_agent_span_id"]].get("layer")
            key = str(value or fallback)
            bucket[key] += _usage_total(span)
        return [
            {field: key, "tokens": value, "share_pct": round(value * 100 / total, 2) if total else 0.0}
            for key, value in sorted(bucket.items(), key=lambda item: item[1], reverse=True)
        ]

    return {
        "trace_id": trace["trace_id"],
        "workflow_name": trace.get("workflow_name", "workflow"),
        "total_tokens": total,
        "total_cost_usd": total_cost,
        "cost_coverage_pct": round(priced_tokens * 100 / total, 2) if total else 100.0,
        "attributed_tokens": sum(row["exclusive_tokens"] for row in agent_rows),
        "attribution_coverage_pct": (
            round(sum(row["exclusive_tokens"] for row in agent_rows) * 100 / total, 2) if total else 100.0
        ),
        "wall_time_ms": max(
            (float(span.get("duration_ms") or 0.0) for span in spans if span["kind"] == "workflow"),
            default=0.0,
        ),
        "agents": agent_rows,
        "nonterminal_span_count": sum(span.get("status") == "running" for span in spans),
        "abnormal_agent_count": sum(row["status"] not in {"ok", "running"} for row in agent_rows),
        "models": grouped("model"),
        "providers": grouped("provider"),
        "layers": grouped("layer", "unassigned"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    cost = f"${report['total_cost_usd']:.6f}" if report["total_cost_usd"] is not None else "cost N/A"
    lines = [
        f"# {report['workflow_name']}",
        "",
        f"Trace `{report['trace_id']}` - **{report['total_tokens']:,} tokens** - **{cost}** - "
        f"**{report['wall_time_ms'] / 1000:.2f}s**",
        "",
        f"Attribution coverage: **{report['attribution_coverage_pct']:.2f}%** - "
        f"Cost coverage: **{report['cost_coverage_pct']:.2f}%**",
        "",
        "## Agent attribution",
        "",
        "| Agent | Layer | Exclusive | Share | Subtree | Subtree share | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["agents"]:
        label = f"{'+-- ' * row['depth']}{row['agent_name']}"
        row_cost = f"${row['cost_usd']:.6f}" if row["cost_usd"] is not None else "N/A"
        lines.append(
            f"| {label} | {row['layer']} | {row['exclusive_tokens']:,} | "
            f"{row['exclusive_share_pct']:.2f}% | {row['subtree_tokens']:,} | "
            f"{row['subtree_share_pct']:.2f}% | {row_cost} |"
        )
    lines.extend(["", "## Model attribution", "", "| Model | Tokens | Share |", "|---|---:|---:|"])
    for row in report["models"]:
        lines.append(f"| {row['model']} | {row['tokens']:,} | {row['share_pct']:.2f}% |")
    lines.extend(["", "## Layer attribution", "", "| Layer | Tokens | Share |", "|---|---:|---:|"])
    for row in report["layers"]:
        lines.append(f"| {row['layer']} | {row['tokens']:,} | {row['share_pct']:.2f}% |")
    lines.extend(
        [
            "",
            "> Exclusive values partition measured LLM usage exactly once. Subtree values are diagnostic and overlap by design.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_footer(report: dict[str, Any], *, scope: str = "root") -> str:
    """Render a compact, portable footer that never invents missing telemetry."""
    if scope not in {"root", "agent"}:
        raise ValueError("footer scope must be 'root' or 'agent'")
    if scope == "agent":
        raise ValueError("agent footer requires a separately built agent-scoped report")
    if report.get("nonterminal_span_count", 0):
        raise ValueError("root footer cannot be emitted while included spans are still running")
    cost = f"${report['total_cost_usd']:.6f}" if report["total_cost_usd"] is not None else "N/A"
    state = "partial" if report.get("abnormal_agent_count", 0) else "complete"
    lines = [
        "---",
        "LLM usage",
        f"Scope: {scope} | state {state}",
        f"Trace: {report['trace_id']} | {report['total_tokens']:,} tokens | "
        f"{report['wall_time_ms'] / 1000:.2f}s | cost {cost}",
        f"Coverage: attribution {report['attribution_coverage_pct']:.2f}% | "
        f"cost {report['cost_coverage_pct']:.2f}%",
        "Agents: exclusive tokens / trace share / subtree tokens",
    ]
    for row in report["agents"]:
        prefix = "+-- " * row["depth"]
        lines.append(
            f"- {prefix}{row['agent_name']} [{row['layer']}, status={row['status']}]: "
            f"{row['exclusive_tokens']:,} / {row['exclusive_share_pct']:.2f}% / {row['subtree_tokens']:,}"
        )
    lines.append(
        "Models: "
        + ", ".join(f"{row['model']} {row['tokens']:,} ({row['share_pct']:.2f}%)" for row in report["models"])
    )
    if report["attribution_coverage_pct"] < 100:
        missing = report["total_tokens"] - report["attributed_tokens"]
        lines.append(f"Warning: {missing:,} measured tokens are not attributed to an agent.")
    lines.append("Accounting: exclusive shares partition measured usage; subtree values overlap by design.")
    return "\n".join(lines) + "\n"


class FooterEmitter:
    """Process-local idempotency guard for user-visible root footer emission.

    Distributed runtimes should persist the emitted trace IDs in their own
    atomic store; this guard covers a single process.
    """

    def __init__(self) -> None:
        self._emitted_trace_ids: set[str] = set()
        self._lock = Lock()

    def emit(self, report: dict[str, Any]) -> str:
        trace_id = str(report["trace_id"])
        with self._lock:
            if trace_id in self._emitted_trace_ids:
                raise RuntimeError(f"root footer already emitted for trace {trace_id}")
            footer = render_footer(report, scope="root")
            self._emitted_trace_ids.add(trace_id)
            return footer
