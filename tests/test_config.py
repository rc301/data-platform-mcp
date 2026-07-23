import pytest

from dataplatform.config import SandboxViolation, Session, ensure_sandbox, sandbox_account_ids


class _FakeBoto:
    region_name = "us-east-1"


def _session(account_id: str) -> Session:
    return Session(boto=_FakeBoto(), account_id=account_id, profile="dev", region="us-east-1")


def test_sandbox_ids_parsed(monkeypatch):
    monkeypatch.setenv("DATAPLATFORM_SANDBOX_ACCOUNTS", "111, 222 ,333")
    assert sandbox_account_ids() == frozenset({"111", "222", "333"})


def test_ensure_sandbox_fails_closed_without_config(monkeypatch):
    monkeypatch.delenv("DATAPLATFORM_SANDBOX_ACCOUNTS", raising=False)
    with pytest.raises(SandboxViolation):
        ensure_sandbox(_session("111"))


def test_ensure_sandbox_rejects_non_sandbox(monkeypatch):
    monkeypatch.setenv("DATAPLATFORM_SANDBOX_ACCOUNTS", "111")
    with pytest.raises(SandboxViolation):
        ensure_sandbox(_session("999"))


def test_ensure_sandbox_allows_configured(monkeypatch):
    monkeypatch.setenv("DATAPLATFORM_SANDBOX_ACCOUNTS", "111")
    ensure_sandbox(_session("111"))  # does not raise
