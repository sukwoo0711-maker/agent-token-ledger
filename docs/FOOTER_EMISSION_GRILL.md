# Footer emission auto-grill

Decision: emit one user-visible footer at the terminal root-response boundary, not at each agent-completion boundary.

| Pressure case | Incorrect behavior | Required behavior |
|---|---|---|
| Ten parallel subagents finish at different times | Ten footers plus a root footer | Record ten completion events; emit one consolidated root footer |
| A subagent streams five chunks | Five partial footers | No footer until the applicable terminal response |
| One of ten agents fails after spending tokens | Drop the failed agent or block forever | Include partial measured usage with `status=error`; root state is partial |
| One agent times out or is cancelled | Pretend it used zero tokens | Include measured partial usage and terminal status |
| One agent is still running | Emit a misleading complete total | Reject root footer emission or mark a deliberately closed partial snapshot |
| A background agent outlives the reply | Append a second footer later | Declare it detached/excluded; keep the root snapshot immutable |
| User opens a subagent thread directly | Suppress all visibility or confuse it with root | Allow one `Scope: agent` footer for that independent response |
| Parent receives child response text | Child footer appears inside parent plus root footer | Strip child presentation; aggregate child telemetry only |
| Agent retries the same model call | One footer per retry | One root footer; retries appear as spans/status metadata |
| Footer is composed by an LLM | Footer-generation tokens are missing from its own total | Close trace, then use a deterministic non-LLM renderer |
| Renderer is called twice | Two identical root footers | Atomic trace-ID idempotency guard rejects the second emission |
| Root report is relabeled `Scope: agent` | Agent footer claims root totals | Require a genuinely agent-scoped snapshot and denominator |
| Root synthesis completes after workers | Snapshot before final synthesis | Include final synthesis, then close and render |
| No trustworthy telemetry exists | Model guesses a polished breakdown | Emit only the unavailable sentence |

## Invariants

1. `user_visible_root_footer_count <= 1` for a root request.
2. A complete root footer requires `nonterminal_included_agent_count == 0`.
3. Root exclusive usage equals the sum of canonical measured LLM calls, subject to disclosed attribution coverage.
4. Agent-scoped footer text is presentation and is never an input to root aggregation.
5. A rendered root footer is an immutable snapshot identified by its trace ID.
6. Footer rendering itself performs no model call.
7. Exactly-once delivery is enforced outside the pure renderer with an atomic trace-ID marker.

## Local-model grill outcome

`spec-analyst` and `code-assistant` were each prompted to attack the emission rule. Both summarized the implementation instead of producing counterexamples. Their output did not satisfy the requested finding format and was rejected as evidence. The idempotency and fake-agent-scope defects above were found through deterministic boundary analysis and converted into regression tests.
