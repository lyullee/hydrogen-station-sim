import io
import json
from urllib.error import HTTPError

import pytest

from h2station import api


def test_switching_provider_is_not_blocked_by_other_provider_failure(monkeypatch):
    calls = []
    def request(req, **kwargs):
        provider = json.loads(req.data)['provider']
        calls.append(provider)
        if provider == 'service_hub':
            raise HTTPError(req.full_url, 503, 'Missing key', {}, None)
        return io.BytesIO(b'{"answer":"ok","model":"test"}')
    monkeypatch.setattr(api, 'urlopen', request)
    monkeypatch.setattr(api, '_saga_assistant_failure_until', {})
    with pytest.raises(HTTPError):
        api._invoke_isolated_twin_assistant('sensor', {'provider':'service_hub'})
    result = api._invoke_isolated_twin_assistant('sensor', {'provider':'groq'})
    assert result['answer'] == 'ok'
    assert calls == ['service_hub','groq']
