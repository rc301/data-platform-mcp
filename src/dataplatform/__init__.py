"""data-platform toolkit: read-only inspection and diagnosis of AWS Glue jobs.

The MCP server (``dataplatform.mcp``) is a thin developer-only shell over the
public functions exposed here. All business logic lives in this package; the
server never adds behaviour of its own.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("data-platform-mcp")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
