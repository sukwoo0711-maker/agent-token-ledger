# Design decisions

## Canonical schema first

OpenTelemetry GenAI conventions are still marked development. The recorder therefore owns a small stable schema and maps it at export time. This avoids coupling stored traces to a changing semantic convention.

## Exclusive versus subtree usage

Every measured LLM span has one `owner_agent_span_id`. Exclusive agent totals partition measured usage exactly once. Subtree totals recursively include descendants and intentionally overlap, so they are diagnostic only.

This distinction prevents the classic error where a parent agent reports both its own tokens and all child tokens while child agents report those tokens again.

Usage can only be attached to a canonical `llm` span. Recording the same provider call again on an agent or tool span is rejected, preventing double instrumentation.

Wall-clock overlap is not token duplication. Two concurrent provider calls each consume their reported tokens and both belong in the trace total.

## Provider-reported counts win

Use provider usage fields whenever available. Ollama exposes `prompt_eval_count` and `eval_count`; the demo records those values directly. Offline tokenization should be labeled as estimated because templates and hidden provider transformations can differ.

## Cache and reasoning subsets

Cache-read and cache-write input tokens are subsets of input tokens. Reasoning output tokens are a subset of output tokens. They must not be added again to total tokens.

## Cost is optional

Local models have no reliable per-token API price. Their cost remains unknown rather than pretending it is zero. Hosted-model cost can be calculated only from an explicit, versioned price table supplied by the caller.

## Privacy

Prompts and responses are not stored by default. The Ollama demo stores only a short preview to prove model execution; production deployments should disable or redact content attributes.

## Concurrency

`ContextVar` is used because it isolates asyncio tasks. New OS threads do not inherit context automatically; call `recorder.bind_context(worker)` when submitting a child operation to a thread pool.
