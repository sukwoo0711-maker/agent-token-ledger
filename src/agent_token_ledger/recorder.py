from __future__ import annotations

import contextvars
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, ParamSpec, TypeVar

from .models import Price, Span, Usage

P = ParamSpec("P")
R = TypeVar("R")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceRecorder:
    """Records a trace tree without double-counting nested agent usage."""

    def __init__(self, workflow_name: str, trace_id: str | None = None) -> None:
        self.workflow_name = workflow_name
        self.trace_id = trace_id or uuid.uuid4().hex
        self.spans: list[Span] = []
        self._span_stack: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
            f"atl_span_stack_{id(self)}", default=()
        )
        self._agent_stack: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
            f"atl_agent_stack_{id(self)}", default=()
        )

    @property
    def current_span_id(self) -> str | None:
        stack = self._span_stack.get()
        return stack[-1] if stack else None

    @property
    def current_agent_span_id(self) -> str | None:
        stack = self._agent_stack.get()
        return stack[-1] if stack else None

    @contextmanager
    def span(
        self,
        name: str,
        *,
        kind: str,
        agent_name: str | None = None,
        layer: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[Span]:
        if kind not in {"workflow", "agent", "llm", "tool"}:
            raise ValueError(f"unsupported span kind: {kind}")
        span = Span(
            span_id=uuid.uuid4().hex[:16],
            trace_id=self.trace_id,
            parent_span_id=self.current_span_id,
            name=name,
            kind=kind,
            started_at=_now(),
            agent_name=agent_name,
            owner_agent_span_id=self.current_agent_span_id,
            layer=layer,
            provider=provider,
            model=model,
            attributes=attributes or {},
        )
        if kind == "agent":
            span.owner_agent_span_id = span.span_id
        self.spans.append(span)
        span_token = self._span_stack.set((*self._span_stack.get(), span.span_id))
        agent_token = None
        if kind == "agent":
            agent_token = self._agent_stack.set((*self._agent_stack.get(), span.span_id))
        started = time.perf_counter()
        try:
            yield span
            span.status = "ok"
        except Exception as exc:
            span.status = "error"
            span.attributes["error.type"] = type(exc).__name__
            span.attributes["error.message"] = str(exc)
            raise
        finally:
            span.duration_ms = (time.perf_counter() - started) * 1000
            span.ended_at = _now()
            self._span_stack.reset(span_token)
            if agent_token is not None:
                self._agent_stack.reset(agent_token)

    def record_usage(self, span: Span, usage: Usage, price: Price | None = None) -> None:
        if span.kind != "llm":
            raise ValueError("token usage must be recorded on exactly one canonical llm span")
        span.usage = span.usage + usage
        if price is not None:
            span.cost_usd = (span.cost_usd or 0.0) + price.cost(usage)

    def bind_context(self, function: Callable[P, R]) -> Callable[P, R]:
        """Capture current parent/owner stacks for a worker thread.

        ContextVars isolate concurrent tasks correctly but new OS threads do not
        inherit context automatically. Bind at submission time when parentage
        must cross a thread-pool boundary.
        """
        span_stack = self._span_stack.get()
        agent_stack = self._agent_stack.get()

        def bound(*args: P.args, **kwargs: P.kwargs) -> R:
            span_token = self._span_stack.set(span_stack)
            agent_token = self._agent_stack.set(agent_stack)
            try:
                return function(*args, **kwargs)
            finally:
                self._span_stack.reset(span_token)
                self._agent_stack.reset(agent_token)

        return bound

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "trace_id": self.trace_id,
            "workflow_name": self.workflow_name,
            "spans": [span.to_dict() for span in self.spans],
        }

    def export_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target
