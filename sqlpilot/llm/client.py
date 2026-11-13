"""LLMClient: the single entry point for all LLM calls (doc §12.3 / §13.5).

- OpenAI-compatible; base_url / model / key from .env.
- temperature=0; JSON output; token counting; bounded retries.
- DeepSeek quirk: JSON mode requires the word "json" in the prompt.
- FakeLLM: deterministic stub for unit tests / offline demos.
"""
from __future__ import annotations

import json
import time
from typing import Any

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from sqlpilot.config import get_settings


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings=None):
        s = settings or get_settings()
        if not s.llm_api_key:
            raise LLMUnavailable("LLM_API_KEY 未配置；请在 .env 中设置或使用 DEMO_OFFLINE_MODE")
        self.s = s
        self._client = OpenAI(
            base_url=s.llm_base_url,
            api_key=s.llm_api_key,
            timeout=s.llm_timeout_s,
        )
        # Usage accumulators (read by the loop after each call)
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.llm_calls = 0

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """Call the model, expect a JSON object, return the parsed dict."""
        # DeepSeek requires the literal word "json" somewhere in the prompt
        # when response_format is JSON_object. Be defensive without side-effects.
        if "json" not in (system + user).lower():
            system = system + "\n请以 JSON 格式输出。"

        last_err: Exception | None = None
        for attempt in range(self.s.llm_max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.s.llm_model,
                    temperature=self.s.llm_temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                )
                self.llm_calls += 1
                if resp.usage:
                    self.prompt_tokens += resp.usage.prompt_tokens or 0
                    self.completion_tokens += resp.usage.completion_tokens or 0
                content = (resp.choices[0].message.content or "").strip()
                return json.loads(content)
            except json.JSONDecodeError as e:
                # One format-repair attempt per doc §2.6.
                last_err = e
                if attempt >= 1:
                    break
                system = system + "\n只输出合法 JSON，无 markdown 代码块，无前后解释。"
            except (APITimeoutError, RateLimitError, APIError) as e:
                last_err = e
                if attempt < self.s.llm_max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break
        raise LLMUnavailable(f"LLM 调用失败: {type(last_err).__name__}: {last_err}")


class FakeLLM:
    """Deterministic stub. Feeds a queue of dicts back as JSON responses."""

    def __init__(self, responses: list[dict[str, Any]]):
        self._responses = responses
        self._i = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.llm_calls = 0

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        self.llm_calls += 1
        r = self._responses[self._i % len(self._responses)]
        self._i += 1
        return r


if __name__ == "__main__":
    # Smoke test: python -m sqlpilot.llm.client
    c = LLMClient()
    print("-- real call --")
    out = c.chat_json(
        "你是助手，只输出 JSON 对象。",
        '返回 {"ok": true, "msg": "hello"}',
    )
    print("result:", out)
    print("calls:", c.llm_calls,
          "prompt_tokens:", c.prompt_tokens,
          "completion_tokens:", c.completion_tokens)