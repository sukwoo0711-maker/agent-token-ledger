from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from .models import Usage


@dataclass(slots=True)
class OllamaResult:
    content: str
    thinking: str
    model: str
    usage: Usage
    total_duration_ns: int
    raw: dict[str, Any]


def generate(
    model: str,
    prompt: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    num_predict: int = 96,
    timeout: float = 180.0,
) -> OllamaResult:
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": num_predict}}
    ).encode()
    request = Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return OllamaResult(
        content=payload.get("response", ""),
        thinking=payload.get("thinking", ""),
        model=payload.get("model", model),
        usage=Usage(
            input_tokens=int(payload.get("prompt_eval_count", 0)),
            output_tokens=int(payload.get("eval_count", 0)),
        ),
        total_duration_ns=int(payload.get("total_duration", 0)),
        raw=payload,
    )
