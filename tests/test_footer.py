import pytest

from agent_token_ledger import FooterEmitter, TraceRecorder, Usage, build_report, render_footer


def test_footer_is_portable_and_discloses_unknown_cost():
    recorder = TraceRecorder("footer")
    with recorder.span("root", kind="workflow"):
        with recorder.span("orchestrator", kind="agent", agent_name="orchestrator", layer="planning"):
            with recorder.span("call", kind="llm", provider="local", model="small") as llm:
                recorder.record_usage(llm, Usage(input_tokens=8, output_tokens=2))
    footer = render_footer(build_report(recorder.to_dict()))
    assert "cost N/A" in footer
    assert "Scope: root | state complete" in footer
    assert "attribution 100.00%" in footer
    assert "orchestrator [planning, status=ok]: 10 / 100.00% / 10" in footer
    assert "exclusive shares partition measured usage" in footer


def test_footer_warns_about_unattributed_usage():
    recorder = TraceRecorder("gap")
    with recorder.span("root", kind="workflow"):
        with recorder.span("call", kind="llm", provider="local", model="small") as llm:
            recorder.record_usage(llm, Usage(input_tokens=5))
    footer = render_footer(build_report(recorder.to_dict()))
    assert "Warning: 5 measured tokens are not attributed" in footer


def test_ten_subagents_produce_one_consolidated_root_footer():
    recorder = TraceRecorder("fanout")
    with recorder.span("root", kind="workflow"):
        with recorder.span("orchestrator", kind="agent", agent_name="orchestrator"):
            for index in range(10):
                with recorder.span(f"worker-{index}", kind="agent", agent_name=f"worker-{index}"):
                    with recorder.span("call", kind="llm", provider="test", model="m") as llm:
                        recorder.record_usage(llm, Usage(input_tokens=1))
    report = build_report(recorder.to_dict())
    emitter = FooterEmitter()
    footer = emitter.emit(report)
    assert footer.count("LLM usage") == 1
    assert footer.count("worker-") == 10
    assert "orchestrator" in footer
    with pytest.raises(RuntimeError, match="already emitted"):
        emitter.emit(report)


def test_root_footer_rejected_while_an_included_agent_is_running():
    recorder = TraceRecorder("running")
    trace = recorder.to_dict()
    trace["spans"] = [
        {
            "span_id": "agent",
            "trace_id": trace["trace_id"],
            "parent_span_id": None,
            "name": "worker",
            "kind": "agent",
            "status": "running",
            "agent_name": "worker",
            "owner_agent_span_id": "agent",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
    ]
    with pytest.raises(ValueError, match="still running"):
        render_footer(build_report(trace))


def test_failed_agent_partial_usage_is_kept_in_root_footer():
    recorder = TraceRecorder("failure")
    with pytest.raises(RuntimeError):
        with recorder.span("root", kind="workflow"):
            with recorder.span("worker", kind="agent", agent_name="worker", layer="analysis"):
                with recorder.span("call", kind="llm", provider="test", model="m") as llm:
                    recorder.record_usage(llm, Usage(input_tokens=4, output_tokens=1))
                raise RuntimeError("boom")
    footer = render_footer(build_report(recorder.to_dict()))
    assert "Scope: root | state partial" in footer
    assert "worker [analysis, status=error]: 5 / 100.00% / 5" in footer


def test_agent_scope_requires_a_real_scoped_report_and_invalid_scope_is_rejected():
    recorder = TraceRecorder("agent-scope")
    with recorder.span("worker", kind="agent", agent_name="worker"):
        with recorder.span("call", kind="llm", provider="test", model="m") as llm:
            recorder.record_usage(llm, Usage(input_tokens=1))
    report = build_report(recorder.to_dict())
    with pytest.raises(ValueError, match="agent-scoped report"):
        render_footer(report, scope="agent")
    with pytest.raises(ValueError, match="scope"):
        render_footer(report, scope="child")
