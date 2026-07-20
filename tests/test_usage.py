import pytest

from agent_token_ledger import Price, TraceRecorder, Usage


def test_cache_and_reasoning_are_subsets_not_extra_tokens():
    usage = Usage(
        input_tokens=100,
        output_tokens=40,
        cache_read_input_tokens=60,
        reasoning_output_tokens=10,
    )
    assert usage.total_tokens == 140


def test_invalid_subsets_rejected():
    with pytest.raises(ValueError):
        Usage(input_tokens=10, cache_read_input_tokens=11)
    with pytest.raises(ValueError):
        Usage(output_tokens=10, reasoning_output_tokens=11)


def test_price_uses_discounted_cache_subset():
    price = Price(2.0, 10.0, cache_read_per_million_usd=0.2)
    usage = Usage(input_tokens=100, output_tokens=20, cache_read_input_tokens=40)
    assert price.cost(usage) == pytest.approx((60 * 2.0 + 40 * 0.2 + 20 * 10.0) / 1_000_000)


def test_usage_can_only_be_recorded_on_canonical_llm_span():
    recorder = TraceRecorder("dedupe")
    with recorder.span("agent", kind="agent", agent_name="a") as agent:
        with pytest.raises(ValueError):
            recorder.record_usage(agent, Usage(input_tokens=1))
