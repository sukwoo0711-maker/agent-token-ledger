# LLM Footer rule gap analysis

The exact pre-existing personal rule file was not found locally. The baseline below therefore uses the requirement stated in the conversation: show which layer and agent used which model, how many tokens it consumed, and what percentage of one completed query it represented.

| Recent practitioner need | Existing baseline | Better in the baseline | Missing or risky | Added rule clause |
|---|---|---|---|---|
| One user request as the accounting boundary | Present as "one context/query" | Clear user-facing unit | No durable correlation key | Root trace identifier and end-to-end wall time |
| Per-agent token usage | Present | More actionable than account-level billing | Parent totals can double-count children | Exclusive ownership plus separate subtree totals |
| Per-layer usage | Present | Captures planning, analysis, verification, synthesis | Layer may be omitted by wrappers | Inherit owner-agent layer and report `unassigned` explicitly |
| Per-model usage and switching | Present | Makes routing behavior visible | Model self-report can be wrong | Use runtime/provider model metadata only |
| Percent of total | Present | Immediately shows dominant spend | Percentage denominator was unspecified | Root measured tokens are the denominator; exclusive shares partition once |
| Input and output tokens | Not explicit | None | Cannot identify context inflation versus verbose generation | Separate input/output, plus cache and reasoning subsets |
| Nested agent hierarchy | Implied | Recognizes orchestration | No parent ID or context propagation contract | Parent trace propagation across async, threads, processes, queues, and remote calls |
| Tool calls, retries, and loops | Missing | Footer stays simple | Silent retry loops are a common cost source | Record status/retries and enforce tool/retry/loop ceilings |
| Attribution completeness | Missing | None | A polished 100% chart can silently omit unowned calls | Attribution coverage and explicit unattributed warning |
| Price completeness | Missing | Avoids premature pricing dependency | Unknown local cost may appear as free | `N/A` plus cost coverage; never coerce unknown to zero |
| Budget enforcement | Missing | Observational scope is easy to adopt | Post-hoc dashboards cannot stop runaway spend | Root hard cap, role soft caps, verification reserve, gateway/runtime kill switch |
| Duplicate context spend | Missing | None | The same payload may be billed by several agents | Track repeated inter-agent payloads and cache opportunities |
| Outcome quality | Missing | Token ratio is easy to understand | Lowest-token run may be wrong or unverifiable | Cost per successful task and recovery rate |
| Privacy | Missing | None | Footer or trace may leak prompts and tool data | Operational metadata only by default; sensitive content opt-in |
| Missing telemetry | Missing | None | Models may invent convincing usage numbers | Emit a single unavailable line; never estimate from conversation |
| Footer emission boundary | Ambiguous | Simplicity | Ten subagents may produce eleven user-visible footers | Exactly one terminal root footer; subagents record telemetry only |
| Footer-generation overhead | Missing | None | LLM-generated footer creates circular, incomplete accounting | Deterministic renderer after trace closure |

## Critical conclusion

The original idea is stronger than common provider dashboards because it starts at the unit users actually care about: one completed task and its internal agent/model allocation. Its main weakness is that a visually precise footer can still be mathematically or operationally false unless it defines ownership, denominator, coverage, missing-data behavior, and enforcement boundaries.

The improved rule preserves the compact user-facing footer while adding those correctness contracts. Observability and enforcement remain separate: the footer explains what happened, while runtime or gateway controls decide whether an expensive run is allowed to continue.
