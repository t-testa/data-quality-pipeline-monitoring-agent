"""Stdio MCP proxy. It has no direct DB access and no network listener."""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

from dqagent.evidence import TOOLS, ToolInput


def make_server():
    token = os.environ.get("DQ_MCP_TOKEN", "")
    if len(token) < 32:
        raise ValueError("Set DQ_MCP_TOKEN to an authorized monitoring read token")
    base = os.environ.get("DQ_MCP_API_URL", "http://127.0.0.1:8765")
    url = httpx.URL(base)
    if url.scheme != "https" and not (url.scheme == "http" and url.host in {"127.0.0.1", "localhost"}):
        raise ValueError("Remote MCP API connections require HTTPS")
    server = FastMCP("data-quality-monitoring")

    def register(name, description):
        def call(
            pipeline: str | None = None, run_id: str | None = None, table: str | None = None, limit: int = 30
        ) -> dict:
            args = ToolInput(pipeline=pipeline, run_id=run_id, table=table, limit=limit)
            with httpx.Client(base_url=base, timeout=15, follow_redirects=False, trust_env=False) as client:
                with client.stream(
                    "POST",
                    f"/api/tools/{name}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=args.model_dump(),
                ) as response:
                    if response.status_code != 200:
                        raise ValueError("Monitoring API denied or could not complete the request")
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        payload.extend(chunk)
                        if len(payload) > 262144:
                            raise ValueError("Evidence exceeds response limit")
                    return json.loads(payload)

        server.add_tool(call, name=name, description=description)

    for name, description in TOOLS.items():
        register(name, description)
    return server


if __name__ == "__main__":
    make_server().run(transport="stdio")
