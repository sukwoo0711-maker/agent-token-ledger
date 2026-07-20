"""Small deterministic local ablation for generator vs retrieval effects."""
from __future__ import annotations

import json
import random
import time
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434"
OUT = Path(__file__).parents[1] / "artifacts" / "rebutter-ablation.json"

EVIDENCE = [
    ("F1", "A trace footer is emitted exactly once by the root after every descendant has reached a terminal state. Child agents never emit user-visible footers."),
    ("F2", "Exclusive tokens are charged to one span. Subtree totals include descendants, so exclusive and subtree values must never be summed together."),
    ("F3", "Unknown local-model monetary cost must remain N/A. Zero is a measured free cost and must not represent missing price metadata."),
    ("F4", "A failed child keeps its measured partial token usage and terminal status. Failure does not erase usage."),
    ("D1", "For concise logs, suppress repeated status lines and print the footer as soon as each worker finishes."),
    ("D2", "For dashboards, missing numeric values are often rendered as zero to keep charts continuous."),
    ("D3", "A parent summary may combine any convenient totals when exact billing is unavailable."),
    ("D4", "Thread-local state is always equivalent to async context propagation."),
]

CASES = [
    {
        "id": "external_footer",
        "kind": "evidence",
        "query": "Review this orchestration proposal: every child prints an LLM footer immediately when it completes; root prints one too.",
        "gold": "F1",
        "terms": ["root", "once", "descendant"],
    },
    {
        "id": "external_unknown_cost",
        "kind": "evidence",
        "query": "Review: if a local model has no price metadata, store cost_usd=0 so aggregation remains numeric.",
        "gold": "F3",
        "terms": ["n/a", "unknown", "zero"],
    },
    {
        "id": "self_contained_double_count",
        "kind": "code",
        "query": "Find the accounting defect. child.exclusive=40; root.exclusive=10; root.subtree=50; billable=root.exclusive+root.subtree.",
        "gold": None,
        "terms": ["double", "subtree", "exclusive"],
    },
    {
        "id": "clean_hard_negative",
        "kind": "clean",
        "query": "Find only a reproducible defect. child.exclusive=40; root.exclusive=10; root.subtree=50; billable=root.subtree.",
        "gold": None,
        "terms": [],
    },
]

SYSTEM = """You are a skeptical code rebutter. Return JSON only: {\"verdict\":\"defect\"|\"clean\",\"reason\":\"...\",\"evidence_ids\":[\"...\"]}. Do not invent rules. A defect verdict must identify a concrete violated invariant and observable failure."""


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r)


def embed(texts: list[str]) -> list[list[float]]:
    return post("/api/embed", {"model": "bge-m3", "input": texts})["embeddings"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** .5
    nb = sum(y*y for y in b) ** .5
    return dot / (na*nb or 1)


def retrieve(query: str, corpus_vecs: list[list[float]], k: int = 2) -> list[tuple[str, str]]:
    qv = embed([query])[0]
    ranked = sorted(zip(EVIDENCE, corpus_vecs), key=lambda x: cosine(qv, x[1]), reverse=True)
    return [doc for doc, _ in ranked[:k]]


def generate(model: str, prompt: str) -> tuple[dict, dict]:
    started = time.perf_counter()
    raw = post("/api/generate", {
        "model": model, "system": SYSTEM, "prompt": prompt, "stream": False,
        "format": "json", "think": False,
        "options": {"temperature": 0, "seed": 20260721, "num_ctx": 4096, "num_predict": 180},
    })
    elapsed = time.perf_counter() - started
    try:
        parsed = json.loads(raw["response"])
    except Exception:
        parsed = {"verdict": "parse_error", "reason": raw.get("response", ""), "evidence_ids": []}
    return parsed, {"seconds": elapsed, "prompt_tokens": raw.get("prompt_eval_count"), "output_tokens": raw.get("eval_count")}


def main() -> None:
    corpus_vecs = embed([text for _, text in EVIDENCE])
    conditions = [
        ("qwen25_plain", "qwen2.5-coder:7b", "plain"),
        ("qwen25_bge", "qwen2.5-coder:7b", "bge"),
        ("qwen25_distractor", "qwen2.5-coder:7b", "distractor"),
        ("qwen35_plain", "qwen3.5:9b", "plain"),
    ]
    jobs = [(c, case) for case in CASES for c in conditions]
    random.Random(20260721).shuffle(jobs)
    rows = []
    for (name, model, mode), case in jobs:
        docs: list[tuple[str, str]] = []
        if mode == "bge":
            docs = retrieve(case["query"], corpus_vecs)
        elif mode == "distractor":
            docs = [EVIDENCE[-1], EVIDENCE[-2]]
        context = "\n".join(f"[{i}] {t}" for i, t in docs)
        prompt = case["query"] + ("\nAuthoritative evidence:\n" + context if context else "")
        answer, perf = generate(model, prompt)
        verdict = str(answer.get("verdict", "")).lower()
        expected = "clean" if case["kind"] == "clean" else "defect"
        reason = str(answer.get("reason", "")).lower()
        ids = answer.get("evidence_ids") if isinstance(answer.get("evidence_ids"), list) else []
        retrieval_hit = case["gold"] in [i for i, _ in docs] if case["gold"] else None
        if expected == "clean":
            correct = verdict == "clean"
        elif case["gold"]:
            correct = verdict == "defect" and (case["gold"] in ids or all(t in reason for t in case["terms"][:2]))
        else:
            correct = verdict == "defect" and all(t in reason for t in ["subtree", "exclusive"])
        rows.append({"condition": name, "model": model, "mode": mode, "case": case["id"], "kind": case["kind"],
                     "expected": expected, "answer": answer, "correct": correct, "retrieved": [i for i, _ in docs],
                     "retrieval_hit": retrieval_hit, **perf})
        print(f"{name:20} {case['id']:28} correct={correct} retrieved={[i for i, _ in docs]} {perf['seconds']:.1f}s", flush=True)
    summary = {}
    for name, _, _ in conditions:
        subset = [r for r in rows if r["condition"] == name]
        summary[name] = {
            "correct": sum(r["correct"] for r in subset), "total": len(subset),
            "clean_false_positive": sum(r["expected"] == "clean" and r["answer"].get("verdict") != "clean" for r in subset),
            "median_seconds": sorted(r["seconds"] for r in subset)[len(subset)//2],
            "tokens": sum((r["prompt_tokens"] or 0) + (r["output_tokens"] or 0) for r in subset),
        }
    payload = {"design": "4 fixtures x 4 conditions, randomized, temperature=0", "summary": summary, "rows": rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
