import pytest
from fastapi.testclient import TestClient

from dqagent.api import create_app
from dqagent.settings import Settings
from dqagent.store import Store


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
