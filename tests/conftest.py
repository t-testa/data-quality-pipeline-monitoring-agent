import os

import httpx
import pytest
from fastapi.testclient import TestClient

from dqagent.api import create_app
from dqagent.settings import Settings
from dqagent.store import Store


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    # Never inherit deployment paths or credentials in tests (including Docker ENV).
    for key in list(os.environ):
        if key.startswith("DQ_"):
            monkeypatch.delenv(key)
    # A developer may have configured a real key locally. No regression test
    # is permitted to reach the paid provider through a real HTTP transport.
    original = httpx.HTTPTransport.handle_request

    def no_paid_provider(self, request):
        if request.url.host == "api.openai.com":
            pytest.fail("Real OpenAI network access is forbidden in the offline test suite")
        return original(self, request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_paid_provider)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path, api_token="r" * 40, diagnostic_token="d" * 40)


@pytest.fixture
def store(settings):
    return Store(settings.data_dir)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def headers():
    return {"Authorization": "Bearer " + "r" * 40}
