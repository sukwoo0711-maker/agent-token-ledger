# Portable LLM Footer rule

The block below is intentionally provider-neutral. It can be pasted into a system prompt, `AGENTS.md`, personal rule file, or agent framework policy.

## Drop-in rule

```md
## LLM Footer

For every completed user request, append a compact `LLM usage` footer when runtime telemetry is available.

The footer must describe the entire root execution trace for that one user request, including nested agents and model calls. Report:

1. Root trace identifier, total measured tokens, end-to-end wall time, and total cost.
2. Attribution coverage and cost coverage as percentages.
3. For each agent: hierarchy, logical layer or role, model when known, exclusive tokens, percentage of root-trace tokens, subtree tokens, status, and retries when available.
4. Model and provider totals with percentages.
5. Input, output, cache-read, cache-write, and reasoning token breakdowns when the provider exposes them.

Accounting rules:

- Use provider-reported usage whenever available. Label tokenizer-derived values as estimates.
- Assign every measured model call to at most one canonical LLM span and one owning agent.
- Use exclusive agent usage for percentages. Exclusive usage must partition measured trace usage exactly once.
- Report subtree usage separately. Subtree values include descendants and may overlap, so never sum subtree percentages.
- Treat cache and reasoning token counts as subsets of input or output tokens unless the provider explicitly defines otherwise.
- Never infer missing token counts, prices, agent identities, parentage, or model names. Render unavailable values as `N/A` and disclose incomplete coverage.
- Do not report unknown local-model cost as zero.
- Preserve the parent trace and owner agent across async tasks, worker threads, processes, queues, gateways, and remote agent calls when the runtime supports context propagation.
- Exclude prompts, private outputs, credentials, and sensitive tool arguments from the footer. Include only operational metadata unless content capture is explicitly authorized.

Control rules when enforcement is available:

- Apply a hard budget to the root run and optional soft budgets to roles or workflow steps.
- Preserve a protected reserve for verification, recovery, and final synthesis.
- Stop or escalate on budget, retry, tool-call, or loop limits. Enforcement must not depend on the agent voluntarily stopping itself.
- Track repeated payloads or context passed between agents so duplicated input-token spend is visible.
- Evaluate cost per successful task and recovery rate, not token reduction alone.

If runtime telemetry is unavailable, emit only:

`LLM usage: unavailable - this runtime did not expose trustworthy per-call telemetry.`

Never fabricate a detailed footer from conversational context or model self-report.
```

## Recommended compact shape

```text
---
LLM usage
Trace: <trace-id> | <total> tokens | <wall-time> | cost <amount-or-N/A>
Coverage: attribution <pct> | cost <pct>
Agents: exclusive tokens / trace share / subtree tokens
- orchestrator [planning]: 147 / 20.68% / 711
- +-- researcher [analysis]: 136 / 19.13% / 136
Models: local-small 409 (57.52%), local-deep 302 (42.48%)
Accounting: exclusive shares partition measured usage; subtree values overlap by design.
```

The concrete renderer is available as `agent_token_ledger.render_footer`.
