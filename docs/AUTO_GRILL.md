# Auto-grill decision log

| Challenge | Failure if ignored | Resolution | Verification |
|---|---|---|---|
| Are parent and child tokens double-counted? | Percentages exceed 100% | Exclusive ownership plus separate subtree totals | Nested attribution unit test |
| Are cached and reasoning tokens added twice? | Inflated usage | Treat them as subsets | Usage invariant tests |
| Is local-model cost falsely reported as zero? | Misleading economics | Unknown cost is `N/A`, with explicit cost coverage | Demo report shows measured tokens without invented price |
| Can concurrent agents corrupt the current owner? | Usage assigned to the wrong agent | Context-local stacks | Parallel branch unit test |
| Does a new thread lose parentage? | Child appears as a root agent | Explicit `bind_context` helper | Bound worker subtree test |
| Can the same call be measured at agent and LLM layers? | 2x token inflation | Usage accepted only on canonical LLM spans | Duplicate instrumentation rejection test |
| Can a reasoning model return only a thinking field? | Empty review/output despite token spend | Ollama adapter retains both content and thinking | Auto-grill model-switch run |
| Does a changing OTel schema corrupt stored data? | Historical traces become unreadable | Stable canonical schema plus exporter mapping | OTel exporter unit test |
| Are token counts estimates? | Dashboard looks exact but is not | Prefer provider-reported counts and label estimates | Ollama integration run |
| Can percentages look complete while usage is unowned? | Silent attribution gap | Keep unowned usage in total and expose attribution coverage | Unowned usage unit test |

## Remaining limitations

- Cross-process and message-queue context propagation is not yet implemented.
- OTLP network export is deliberately not bundled; `to_otel_like` provides a dependency-free mapping envelope.

## Local reviewer reliability

Four local reviewers were tried: `qwen3.5:9b`, `qwen2.5-coder:7b`, `spec-analyst`, and `code-assistant`. Despite an adversarial-only prompt, they mostly summarized the code. One review also incorrectly recommended replacing `ContextVar` with thread-local state, which would regress asyncio isolation. Local model review is therefore recorded as weak evidence, not a release gate. Counterexample tests and explicit invariants remain authoritative.
