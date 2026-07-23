"""Environment and session configuration.

Credentials are always the developer's own — resolved from the standard AWS
credential chain (``AWS_PROFILE`` / ``AWS_*`` env vars). There are no service
accounts here: the toolkit acts as the human running it.

The toolkit is read-only: it never mutates AWS, so there is no write guard.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError as AwsClientError

# This module is the single seam onto the AWS SDK: it is the only file that
# imports boto3/botocore. Session creation lives here, and the AWS client-error
# type is re-exported as ``AwsClientError`` so callers catch it without importing
# botocore themselves. When migrating to a company Glue library (the B→A path),
# this is the one file to adapt.
__all__ = [
    "AwsClientError",
    "DEFAULT_REGION",
    "Session",
    "resolve_session",
]

# Fallback region when neither the profile nor AWS_REGION/AWS_DEFAULT_REGION
# (both read natively by boto3) set one. The company runs in sa-east-1.
DEFAULT_REGION = "sa-east-1"


@dataclass(frozen=True)
class Session:
    """A resolved boto3 session plus the caller's account identity."""

    boto: boto3.Session
    account_id: str
    profile: str | None
    region: str | None

    def client(self, service: str) -> Any:
        # boto3-stubs types client() with per-service Literal overloads; a runtime
        # str has no matching overload, so we ignore it and return Any (the whole
        # codebase already treats AWS responses as Any).
        return self.boto.client(service)  # type: ignore[call-overload]


def resolve_session(profile: str | None = None, region: str | None = None) -> Session:
    """Build a session from the developer's own AWS credentials.

    ``profile`` defaults to the ambient ``AWS_PROFILE``. The account ID is
    resolved via STS so callers have an authoritative identity to report.
    """

    # TODO(empresa) item 1 — modelo de auth: named profiles por conta (decidido).
    # O parâmetro `profile` já cobre o `data_profile` (leitura da conta de dados).
    # Só troque para STS AssumeRole aqui se o time de infra migrar para "um profile
    # base + assume-role por conta"; nesse caso injete role_arn e use sts.assume_role.
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
