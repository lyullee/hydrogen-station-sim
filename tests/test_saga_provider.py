import asyncio
import json
from io import BytesIO

import h2station.api as api


def test_groq_selection_is_forwarded_to_saga_without_provider_fallback(monkeypatch):
    calls = []

    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data))
        return Response(b'{"answer":"ok"}')

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    result = asyncio.run(api._invoke_saga_selected("check sensor", "concise", "groq"))
    assert result == {"answer": "ok"}
    assert calls == [{"message": "check sensor", "mode": "chat", "answer_length": "concise", "provider": "groq"}]


def test_saga_sse_reader_forwards_deltas_and_returns_reviewed_answer(monkeypatch):
    lines = [
        b"event: status\n", b'data: {"text":"working"}\n', b"\n",
        b"event: draft_token\n", b'data: {"text":"first "}\n', b"\n",
        b"event: draft_token\n", b'data: {"text":"pass"}\n', b"\n",
        b"event: answer\n", b'data: {"answer":"reviewed","model":"groq"}\n', b"\n",
    ]
    captured = []

    class Response:
        def __enter__(self):
            return iter(lines)

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/api/chat/stream")
        assert json.loads(request.data)["provider"] == "groq"
        return Response()

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    result = api._invoke_saga_stream("prompt", "concise", "groq", captured.append)
    assert captured == ["first ", "pass"]
    assert result["answer"] == "reviewed"
