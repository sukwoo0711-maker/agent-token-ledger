# Local rebutter ablation

Run date: 2026-07-21

This screening separates generator choice from retrieval choice. It does not
claim that an embedding model increases a generator's intrinsic language or
reasoning ability.

## Conditions

All generators used the same rebutter contract, 4K context, temperature 0,
fixed seed, JSON output contract, and randomized job order.

| Condition | Generator | Evidence |
|---|---|---|
| qwen25_plain | qwen2.5-coder:7b | none |
| qwen25_bge | qwen2.5-coder:7b | BGE-M3 dense top-2 |
| qwen25_distractor | qwen2.5-coder:7b | fixed irrelevant top-2 |
| qwen35_plain | qwen3.5:9b | none |

The four screening fixtures cover two external-policy defects, one
self-contained accounting defect, and one clean hard negative.

## Corrected result

| Condition | Correct | Clean false positives | Median generation seconds | Total tokens |
|---|---:|---:|---:|---:|
| qwen25_plain | 0/4 | 1 | 1.49 | 645 |
| qwen25_bge | 3/4 | 1 | 1.60 | 905 |
| qwen25_distractor | 0/4 | 1 | 0.99 | 725 |
| qwen35_plain | 2/4 | 0 | 22.34 | 695 |

BGE-M3 retrieved the authoritative rule for both external-policy cases in its
top two. Qwen2.5 then used those rules correctly. It also retrieved the
double-counting rule for the self-contained defect. However, the same retrieval
path injected a suspicious accounting rule into the clean case and caused a
false positive. The larger 9B model was much slower on this execution host but
was the only condition to reject the clean bait.

## Auto-grill

The first run was invalid for model comparison. A brittle keyword scorer marked
semantically correct answers wrong, and Qwen3.5 thinking output conflicted with
the JSON parser. The corrected run disabled thinking uniformly for structured
output and scored evidence cases using the cited ground-truth rule ID.

The corrected run still has important limits:

- Four fixtures are a screening set, not statistical proof.
- The evidence corpus is synthetic and small.
- Ollama exposes BGE-M3 dense embeddings here, not its complete sparse and
  multi-vector feature set.
- Top-2 retrieval has no lexical, symbol-graph, or cross-encoder reranking.
- Retrieval time and cold model-load time are not represented by the displayed
  generation median.
- The reported latency belongs only to the execution host. Hardware,
  quantization, runtime version, model residency, and thermal state were not
  controlled well enough to generalize it to another machine.

## Decision

The screening does not justify a universal default model. It supports testing a
smaller default with conditional retrieval against alternatives on a larger
holdout. Retrieval may be useful when a question depends on specifications,
historical defects, policies, or other external evidence, but irrelevant
retrieval can increase false positives. Candidate generation, reranking, and
selective escalation must therefore be evaluated as parts of the system rather
than assumed to help. Every accepted engineering finding should have an
executable reproduction or regression test where practical.

Before replacing the default, repeat this as a blinded holdout with at least 30
fixtures, including clean negatives, and report retrieval recall separately from
finding precision and recall.
