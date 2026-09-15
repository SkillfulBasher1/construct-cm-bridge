"""Smoke test the real in-memory FastMCP transport and tool registry."""

import json

import pytest
from fastmcp import Client

from construct_cm_bridge.server import mcp


@pytest.mark.asyncio
async def test_mcp_registry_and_tool_call():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}
        assert len(tool_names) == 31
        assert {
            "index_project_instruction",
            "search_project_memory",
            "track_design_changes",
            "verify_calculation_safety",
        }.issubset(tool_names)

        result = await client.call_tool(
            "verify_calculation_safety",
            {
                "item_name": "MCP transport smoke test",
                "design_val": 10.0,
                "allowable_val": 20.0,
                "req_sf": 1.25,
            },
        )
        assert not result.is_error
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "SUCCESS"
        assert "PASS" in payload["judgement"]
