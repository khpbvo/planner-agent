import asyncio
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
import json

# Add src to path
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools import create_todoist_tool, create_gmail_tool, create_nlp_tool
from tools.todoist_tool import TodoistOperation, TodoistResponse
from tools.gmail_tool import GmailOperation, GmailResponse
from tools.nlp_tool import NLPOperation, NLPResponse
from agents.tool_context import ToolContext


@pytest.mark.asyncio
async def test_stub_todoist_tool_schema():
    tool = create_todoist_tool(api_key=None)
    ctx = ToolContext(context=None, tool_name="todoist", tool_call_id="1")
    payload = json.dumps({"operation_input": TodoistOperation(operation="list").model_dump(mode="json")})
    result = await tool.on_invoke_tool(ctx, payload)
    assert isinstance(result, TodoistResponse)
    assert result.status == "error"
    with pytest.raises(ValidationError):
        TodoistOperation(operation="list", extra_field=1)


@pytest.mark.asyncio
async def test_stub_gmail_tool_schema():
    cfg = SimpleNamespace()  # missing google_client_id
    tool = create_gmail_tool(cfg)
    ctx = ToolContext(context=None, tool_name="gmail", tool_call_id="1")
    payload = json.dumps({"operation_input": GmailOperation(operation="list").model_dump(mode="json")})
    result = await tool.on_invoke_tool(ctx, payload)
    assert isinstance(result, GmailResponse)
    assert result.status == "error"
    assert result.authenticated is False
    with pytest.raises(ValidationError):
        GmailOperation(operation="list", extra="x")


@pytest.mark.asyncio
async def test_nlp_tool_schema_and_output():
    tool = create_nlp_tool()
    text = "Schedule meeting tomorrow"
    ctx = ToolContext(context=None, tool_name="nlp", tool_call_id="1")
    payload = json.dumps({"operation_input": NLPOperation(text=text).model_dump(mode="json")})
    result = await tool.on_invoke_tool(ctx, payload)
    assert isinstance(result, NLPResponse)
    assert result.raw_text == text
    assert result.intent == "schedule_event"
    with pytest.raises(ValidationError):
        NLPOperation(text=text, foo="bar")
