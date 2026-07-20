from concurrent.futures import ThreadPoolExecutor

from agent_token_ledger import TraceRecorder, Usage, build_report


def test_explicit_parallel_branches_keep_distinct_owners():
    recorder = TraceRecorder("parallel")

    def worker(name: str, tokens: int) -> None:
        with recorder.span(name, kind="agent", agent_name=name):
            with recorder.span(f"{name}-llm", kind="llm", provider="test", model="m") as llm:
                recorder.record_usage(llm, Usage(input_tokens=tokens))

    with recorder.span("root", kind="workflow"):
        # ContextVars intentionally isolate stacks per thread. Parent context
        # propagation should be handled by an executor wrapper in production.
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda item: worker(*item), [("a", 10), ("b", 20)]))

    report = build_report(recorder.to_dict())
    assert {row["agent_name"]: row["exclusive_tokens"] for row in report["agents"]} == {"a": 10, "b": 20}


def test_bound_thread_context_preserves_parent_agent_subtree():
    recorder = TraceRecorder("parallel-parent")

    def child() -> None:
        with recorder.span("child", kind="agent", agent_name="child"):
            with recorder.span("child-llm", kind="llm", provider="test", model="m") as llm:
                recorder.record_usage(llm, Usage(input_tokens=20))

    with recorder.span("root", kind="workflow"):
        with recorder.span("parent", kind="agent", agent_name="parent"):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(recorder.bind_context(child)).result()

    report = build_report(recorder.to_dict())
    rows = {row["agent_name"]: row for row in report["agents"]}
    assert rows["child"]["parent_agent_span_id"] == rows["parent"]["span_id"]
    assert rows["parent"]["subtree_tokens"] == 20
