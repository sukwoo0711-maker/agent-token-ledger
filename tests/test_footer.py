from agent_token_ledger import TraceRecorder, Usage, build_report, render_footer


def test_footer_is_portable_and_discloses_unknown_cost():
    recorder = TraceRecorder("footer")
    with recorder.span("root", kind="workflow"):
        with recorder.span("orchestrator", kind="agent", agent_name="orchestrator", layer="planning"):
            with recorder.span("call", kind="llm", provider="local", model="small") as llm:
                recorder.record_usage(llm, Usage(input_tokens=8, output_tokens=2))
    footer = render_footer(build_report(recorder.to_dict()))
    assert "cost N/A" in footer
    assert "attribution 100.00%" in footer
    assert "orchestrator [planning]: 10 / 100.00% / 10" in footer
    assert "exclusive shares partition measured usage" in footer


def test_footer_warns_about_unattributed_usage():
    recorder = TraceRecorder("gap")
    with recorder.span("root", kind="workflow"):
        with recorder.span("call", kind="llm", provider="local", model="small") as llm:
            recorder.record_usage(llm, Usage(input_tokens=5))
    footer = render_footer(build_report(recorder.to_dict()))
    assert "Warning: 5 measured tokens are not attributed" in footer
