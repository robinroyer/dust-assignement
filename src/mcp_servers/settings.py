import os


def _require(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise EnvironmentError(f"Required environment variable '{name}' is not set")
    return val


MCP_AUTH_TOKEN: str = _require("MCP_AUTH_TOKEN")
BOARD_PREFIX: str = os.environ.get("BOARD_PREFIX", "")
