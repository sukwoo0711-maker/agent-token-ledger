# Local validation

Validated on 2026-07-20 on Windows with Ollama and Python 3.12.

## Real model-switching trace

One root query used four agent roles and three installed local models:

| Agent | Layer | Model | Exclusive tokens | Trace share | Subtree tokens |
|---|---|---|---:|---:|---:|
| orchestrator | planning | hermes3:3b | 147 | 20.68% | 711 |
| researcher | analysis | qwen3.5:9b | 136 | 19.13% | 136 |
| verifier | verification | qwen2.5-coder:7b | 166 | 23.35% | 166 |
| synthesizer | synthesis | hermes3:3b | 262 | 36.85% | 262 |

Observed invariants:

- Total provider-reported usage: 711 tokens.
- Exclusive agent usage: 147 + 136 + 166 + 262 = 711.
- Attribution coverage: 100%.
- Orchestrator subtree: 711 tokens, or 100% of the trace.
- Model shares: hermes3:3b 57.52%, qwen2.5-coder:7b 23.35%, qwen3.5:9b 19.13%.
- Cost is `N/A`, not zero, because no price table was supplied for local inference.
- End-to-end wall time: 60.80 seconds.

The exact raw trace is intentionally gitignored because it contains response previews. Reproduce it with `examples/ollama_multi_agent.py`.

## Automated verification

```text
10 passed in 0.04s
wheel: agent_token_ledger-0.1.0-py3-none-any.whl
sdist: agent_token_ledger-0.1.0.tar.gz
```

Tests cover nested exclusive/subtree accounting, cache and reasoning subset invariants, partial attribution, layer inheritance, duplicate instrumentation rejection, OpenTelemetry mapping, independent parallel branches, and bound thread context propagation.

## Auto-grill result

Four local reviewer models were exercised across two prompt revisions. They consistently summarized the implementation instead of producing strong counterexamples. One produced an incorrect recommendation to replace `ContextVar` with thread-local state. The review was therefore treated as weak evidence.

Manual adversarial analysis plus executable counterexamples found and fixed:

1. Unknown local-model cost was rendered as zero. It now renders as `N/A` with cost coverage.
2. New worker threads lost parent trace context. `bind_context` now propagates it explicitly.
3. Usage could be attached at multiple span layers. Only canonical LLM spans now accept token usage.
4. Reasoning-only Ollama output could appear empty. Both `content` and `thinking` are preserved.
5. Unicode tree markers failed on a CP949 console. Reports now use portable ASCII markers.

Remaining limitations are tracked in [AUTO_GRILL.md](AUTO_GRILL.md).
