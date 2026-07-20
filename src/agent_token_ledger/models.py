from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    reasoning_output_tokens: int = 0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.cache_read_input_tokens + self.cache_write_input_tokens > self.input_tokens:
            raise ValueError("cache input token subsets cannot exceed input_tokens")
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning_output_tokens cannot exceed output_tokens")

    @property
    def total_tokens(self) -> int:
        # Cache and reasoning counts are subsets, not extra billable tokens.
        return self.input_tokens + self.output_tokens

    def __add__(self, other: Usage) -> Usage:
        return Usage(**{key: getattr(self, key) + getattr(other, key) for key in asdict(self)})

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Price:
    input_per_million_usd: float
    output_per_million_usd: float
    cache_read_per_million_usd: float | None = None

    def cost(self, usage: Usage) -> float:
        cache_rate = self.cache_read_per_million_usd
        cached = usage.cache_read_input_tokens if cache_rate is not None else 0
        uncached = usage.input_tokens - cached
        total = uncached * self.input_per_million_usd
        total += cached * (cache_rate if cache_rate is not None else self.input_per_million_usd)
        total += usage.output_tokens * self.output_per_million_usd
        return total / 1_000_000


@dataclass(slots=True)
class Span:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    kind: str
    started_at: str
    ended_at: str | None = None
    duration_ms: float | None = None
    status: str = "running"
    agent_name: str | None = None
    owner_agent_span_id: str | None = None
    layer: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: Usage = field(default_factory=Usage)
    cost_usd: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["usage"]["total_tokens"] = self.usage.total_tokens
        return result
