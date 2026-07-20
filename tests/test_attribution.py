from agent_token_ledger import TraceRecorder, Usage, build_report


def test_exclusive_agent_shares_partition_total_without_double_counting():
    recorder = TraceRecorder("nested")
    with recorder.span("root", kind="workflow"):
        with recorder.span("orchestrator", kind="agent", agent_name="orchestrator", layer="root"):
            with recorder.span("root llm", kind="llm", provider="test", model="small") as root_llm:
                recorder.record_usage(root_llm, Usage(input_tokens=10, output_tokens=5))
            with recorder.span("researcher", kind="agent", agent_name="researcher", layer="research"):
                with recorder.span("child llm", kind="llm", provider="test", model="large") as child_llm:
                    recorder.record_usage(child_llm, Usage(input_tokens=70, output_tokens=15))

    report = build_report(recorder.to_dict())
    rows = {row["agent_name"]: row for row in report["agents"]}
    assert report["total_tokens"] == 100
    assert rows["orchestrator"]["exclusive_tokens"] == 15
    assert rows["researcher"]["exclusive_tokens"] == 85
    assert rows["orchestrator"]["subtree_tokens"] == 100
    assert rows["researcher"]["subtree_tokens"] == 85
    assert sum(row["exclusive_share_pct"] for row in rows.values()) == 100.0
    assert report["attribution_coverage_pct"] == 100.0
    assert report["cost_coverage_pct"] == 0.0
    assert report["total_cost_usd"] is None


def test_unowned_usage_is_visible_but_does_not_get_misattributed():
    recorder = TraceRecorder("unowned")
    with recorder.span("root", kind="workflow"):
        with recorder.span("direct", kind="llm", provider="test", model="m") as span:
            recorder.record_usage(span, Usage(input_tokens=3, output_tokens=2))
    report = build_report(recorder.to_dict())
    assert report["total_tokens"] == 5
    assert report["agents"] == []
    assert report["attribution_coverage_pct"] == 0.0


def test_llm_inherits_layer_from_owner_for_reporting():
    recorder = TraceRecorder("layer")
    with recorder.span("root", kind="workflow"):
        with recorder.span("critic", kind="agent", agent_name="critic", layer="verification"):
            with recorder.span("call", kind="llm", provider="test", model="m") as llm:
                recorder.record_usage(llm, Usage(input_tokens=9, output_tokens=1))
    report = build_report(recorder.to_dict())
    assert report["layers"] == [{"layer": "verification", "tokens": 10, "share_pct": 100.0}]
