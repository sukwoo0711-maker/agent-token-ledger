# Local LLM adoption: evidence, limits, and a practical decision framework

This note reports a local experiment intended to inform deployment decisions.
It does not establish that local models are generally better or worse than
hosted models, or that one model family is generally superior to another.

## What was measured

The experiment used 208 unique records from one local retrieval corpus. Each
record was converted into five Korean query templates, producing 1,040 test
cases. Every query included the record's exact name. A dense embedding model
retrieved candidates, after which one of two local instruction models selected
the best evidence ID from the same frozen top-three candidate set.

The generator conditions were a 7B coding-oriented model and a 9B general
instruction model. Temperature, seed, output format, candidate evidence, and
prompt contract were held constant. Runs were performed on one local host, so
latency is host-specific.

## Observed results

| Stage or condition | Point estimate | Entity-cluster 95% interval |
|---|---:|---:|
| Dense retrieval Recall@1 | 72.69% | 67.88–77.21% |
| Dense retrieval Recall@3 | 86.92% | 83.56–90.10% |
| Dense retrieval Recall@10 | 95.00% | 92.79–96.92% |
| 7B selector, end-to-end | 77.88% (810/1,040) | 74.04–81.63% |
| 9B selector, end-to-end | 76.15% (792/1,040) | 72.21–79.90% |

When the expected record was present in the top three, conditional selection
accuracy was 87.17% for the 7B condition and 84.85% for the 9B condition. The
complete selector runs took approximately 432 and 460 seconds respectively on
the test host.

Paired outcomes were 697 cases where both were correct, 113 where only the 7B
condition was correct, 95 where only the 9B condition was correct, and 135
where both were wrong. The confidence intervals overlap. This experiment
therefore does not demonstrate general superiority of the 7B model. It shows
only that switching to the tested 9B model did not produce a measured benefit
on this task and host.

## AUTO-GRILL: what these numbers do not prove

1. The 1,040 cases are correlated repeated measurements, not 1,040 independent
   facts. Confidence intervals must be clustered by the 208 source records.
2. Exact names appear in every query. This is a named-record retrieval and
   paraphrase test, not a general question-answering benchmark.
3. Questions and expected evidence were derived from the same corpus. This
   circular construction cannot verify whether the corpus itself is factually
   correct.
4. Selecting an evidence ID is not the same as producing a correct answer. The
   experiment did not score unsupported claims, missing conditions, citation
   entailment, or final-answer usefulness.
5. It did not cover aliases, typographical errors, pronouns, description-only
   questions, multi-hop reasoning, conflicting evidence, adversarial prompts,
   or unanswerable questions.
6. Model size is not an isolated variable. Training data, architecture,
   quantization, specialization, runtime, and prompt compatibility also differ.
7. The latency values are not portable. Hardware, quantization, context length,
   batch size, model residency, and runtime versions can materially change
   throughput.
8. Exact model revisions, quantization variants, GPU offload, cold-start time,
   peak RAM and VRAM, and energy use were not recorded completely enough for a
   controlled hardware-efficiency comparison.

## Neutral adoption guidance

A local LLM is a reasonable candidate when privacy, offline availability,
latency control, predictable marginal cost, or integration with local data is
important. It also introduces operational costs: hardware capacity, model and
runtime maintenance, evaluation, monitoring, security controls, and fallback
handling.

Choose a deployment only after measuring it against the actual workload. At a
minimum, separate and report:

- retrieval Recall@k and ranking quality;
- selector accuracy conditional on the correct candidate being available;
- abstention behavior for unanswerable or weak-evidence queries;
- final-answer factuality and unsupported-claim rate;
- citation support and omitted-condition rate;
- warm latency, cold-start latency, throughput, memory use, and energy use;
- worst-group results rather than only the overall average.

Compare models on paired, frozen test cases and randomized execution order.
Use independently authored holdout questions, cluster repeated paraphrases by
intent or entity, and preserve negative and adversarial examples. A larger
model should be adopted only when its measured quality improvement justifies
its additional latency, memory, energy, and maintenance cost.

For constrained systems, a small default model with retrieval and selective
escalation is one testable architecture, not a universal recommendation. Route
ambiguous, conflicting, or high-risk cases to a stronger verifier only after
the routing rule itself has been evaluated. Hosted, local, and hybrid designs
should be judged by the same workload-specific quality and operational metrics.

## Evidence disclosure

These measurements are exploratory evidence from one corpus and one host. Raw
corpus-specific material is intentionally excluded from this public repository.
The public figures therefore cannot be independently reproduced from this
repository alone. They should be treated as an example of evaluation discipline,
not as a portable model leaderboard or an independently reproducible benchmark.
