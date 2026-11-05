"""
tests/test_smoke_test.py
The self-check that the release workflow runs inside the built app
(utils/smoke_test.py) also works from source, on every OS in CI.
"""

import pytest
from peewee import SqliteDatabase

from models.models import ALL_MODELS, User
from utils import smoke_test

test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_db():
    test_db.bind(ALL_MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(ALL_MODELS)
    yield
    test_db.drop_tables(ALL_MODELS)
    test_db.close()


def test_enabled_only_by_the_env_variable(monkeypatch):
    monkeypatch.delenv(smoke_test.ENV_VAR, raising=False)
    assert not smoke_test.enabled()
    monkeypatch.setenv(smoke_test.ENV_VAR, "1")
    assert smoke_test.enabled()


def test_pdf_report_check_passes():
    user = User.create(name="Smoke Test", currency="USD", language="en")
    smoke_test._check_pdf_report(user)          # raises if the PDF can't be built


def test_notification_module_check_passes():
    smoke_test._check_notification_module()     # raises if plyer's module for this OS is missing