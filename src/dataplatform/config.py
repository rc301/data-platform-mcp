"""Environment and session configuration.

Credentials are always the developer's own — resolved from the standard AWS
credential chain (``AWS_PROFILE`` / ``AWS_*`` env vars). There are no service
accounts here: the toolkit acts as the human running it.

Writes are only ever allowed against *sandbox* accounts. The set of sandbox
account IDs is read from ``DATAPLATFORM_SANDBOX_ACCOUNTS`` (comma separated) and
enforced by :func:`ensure_sandbox` before any mutating operation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import boto3

SANDBOX_ENV_VAR = "DATAPLATFORM_SANDBOX_ACCOUNTS"

# Fallback region when neither the profile nor AWS_REGION/AWS_DEFAULT_REGION
# (both read natively by boto3) set one. The company runs in sa-east-1.
DEFAULT_REGION = "sa-east-1"


class SandboxViolation(RuntimeError):
    """Raised when a write is attempted against a non-sandbox account."""


@dataclass(frozen=True)
class Session:
    """A resolved boto3 session plus the caller's account identity."""

    boto: boto3.Session
    account_id: str
    profile: str | None
    region: str | None

    def client(self, service: str):
        return self.boto.client(service)


def sandbox_account_ids() -> frozenset[str]:
    raw = os.environ.get(SANDBOX_ENV_VAR, "")
    return frozenset(a.strip() for a in raw.split(",") if a.strip())


def resolve_session(profile: str | None = None, region: str | None = None) -> Session:
    """Build a session from the developer's own AWS credentials.

    ``profile`` defaults to the ambient ``AWS_PROFILE``. The account ID is
    resolved via STS so every downstream guard has an authoritative identity.
    """

    # TODO(empresa) item 1 — modelo de auth: named profiles por conta (decidido).
    # O parâmetro `profile` já cobre sandbox_profile / data_profile. Só troque
    # para STS AssumeRole aqui se o time de infra migrar para "um profile base +
    # assume-role por conta"; nesse caso injete role_arn e use sts.assume_role.
    boto = boto3.Session(profile_name=profile, region_name=region)
    # item 2 — region: precedência arg > profile > AWS_REGION/AWS_DEFAULT_REGION
    # (lidos nativamente pelo boto3) > DEFAULT_REGION. Sem isto, um profile sem
    # região deixa os clients Glue/Logs sem endpoint. TODO(empresa): a conta de
    # dados pode estar em outra região — exponha `region` nas tools de tabela.
    if boto.region_name is None:
        boto = boto3.Session(profile_name=profile, region_name=DEFAULT_REGION)
    account_id = boto.client("sts").get_caller_identity()["Account"]
    return Session(
        boto=boto,
        account_id=account_id,
        profile=profile or os.environ.get("AWS_PROFILE"),
        region=boto.region_name,
    )


def ensure_sandbox(session: Session) -> None:
    """Guard: raise unless ``session`` points at a configured sandbox account.

    Call this at the top of every mutating operation. It fails closed — if no
    sandbox accounts are configured, all writes are refused.
    """

    # TODO(empresa) item 10 — auditoria: este é o único gargalo por onde toda
    # escrita passa. Se o time quiser trilha de "quem replicou/rodou o quê",
    # emita aqui um log estruturado (account_id, profile, operação) antes de liberar.
    allowed = sandbox_account_ids()
    if not allowed:
        raise SandboxViolation(
            f"No sandbox accounts configured. Set {SANDBOX_ENV_VAR} to the "
            "comma-separated account IDs where writes are permitted."
        )
    if session.account_id not in allowed:
        raise SandboxViolation(
            f"Account {session.account_id} is not a sandbox account. "
            f"Writes are only allowed in: {', '.join(sorted(allowed))}."
        )
