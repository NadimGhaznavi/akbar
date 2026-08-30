"""Bounded OpenAI-compatible function-calling loop backed by MCP."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, Self

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from constants.DAgent import DAgent


class AgentError(RuntimeError):
    """The model or tool loop returned an invalid or unsafe response."""


class ChatClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]: ...


class ToolGateway(Protocol):
    async def list_tools(self) -> list[dict[str, Any]]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class LlamaChatClient:
    def __init__(
        self,
        url: str = DAgent.CHAT_COMPLETIONS_URL,
        model: str = DAgent.MODEL_NAME,
        timeout_seconds: float = DAgent.CHAT_TIMEOUT_SECONDS,
    ) -> None:
        self.url = url
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self.client.post(
            self.url,
            json={
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "stream": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise AgentError("llama.cpp returned a non-object response")
        return payload


class MCPToolGateway:
    """Expose one stdio MCP server as OpenAI-compatible tools."""

    def __init__(self, command: str, args: list[str], cwd: Path) -> None:
        self.parameters = StdioServerParameters(
            command=command,
            args=args,
            cwd=cwd,
        )
        self._stdio_context: Any = None
        self._session_context: ClientSession | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> Self:
        self._stdio_context = stdio_client(self.parameters)
        read_stream, write_stream = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session_context is not None:
            await self._session_context.__aexit__(
                exception_type,
                exception,
                traceback,
            )
        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(
                exception_type,
                exception,
                traceback,
            )
        self._session = None

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise AgentError("MCP tool gateway is not connected")
        return self._session

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._require_session().list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._require_session().call_tool(name, arguments)
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json", exclude_none=True)
        return result


class AkbarAgent:
    def __init__(
        self,
        chat: ChatClient,
        tools: ToolGateway,
        max_tool_rounds: int = DAgent.MAX_TOOL_ROUNDS,
        max_tool_calls: int = DAgent.MAX_TOOL_CALLS,
    ) -> None:
        self.chat = chat
        self.tools = tools
        self.max_tool_rounds = max_tool_rounds
        self.max_tool_calls = max_tool_calls

    async def run(self, prompt: str) -> str:
        tool_definitions = await self.tools.list_tools()
        allowed_tools = {
            definition["function"]["name"] for definition in tool_definitions
        }
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt}
        ]
        total_calls = 0

        for _round in range(self.max_tool_rounds + 1):
            response = await self.chat.complete(messages, tool_definitions)
            message = self._assistant_message(response)
            messages.append(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise AgentError("model returned neither tool calls nor text")
                return content

            if _round == self.max_tool_rounds:
                raise AgentError("model exceeded the maximum tool-call rounds")
            total_calls += len(tool_calls)
            if total_calls > self.max_tool_calls:
                raise AgentError("model exceeded the maximum total tool calls")

            for tool_call in tool_calls:
                call_id, name, arguments = self._parse_tool_call(
                    tool_call,
                    allowed_tools,
                )
                result = await self.tools.call_tool(name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(result, separators=(",", ":")),
                    }
                )

        raise AgentError("model did not produce a final response")

    @staticmethod
    def _assistant_message(response: dict[str, Any]) -> dict[str, Any]:
        try:
            raw_message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise AgentError("model returned an invalid chat response") from error
        if not isinstance(raw_message, dict):
            raise AgentError("model returned an invalid assistant message")
        message = {
            "role": "assistant",
            "content": raw_message.get("content"),
        }
        if raw_message.get("tool_calls") is not None:
            message["tool_calls"] = raw_message["tool_calls"]
        return message

    @staticmethod
    def _parse_tool_call(
        tool_call: Any,
        allowed_tools: set[str],
    ) -> tuple[str, str, dict[str, Any]]:
        try:
            call_id = tool_call["id"]
            function = tool_call["function"]
            name = function["name"]
            raw_arguments = function["arguments"]
        except (KeyError, TypeError) as error:
            raise AgentError("model returned a malformed tool call") from error
        if not isinstance(call_id, str) or not call_id:
            raise AgentError("tool call ID must be a non-empty string")
        if name not in allowed_tools:
            raise AgentError(f"model requested unknown tool: {name}")
        if not isinstance(raw_arguments, str):
            raise AgentError("tool arguments must be JSON text")
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as error:
            raise AgentError("model returned invalid tool arguments") from error
        if not isinstance(arguments, dict):
            raise AgentError("tool arguments must be a JSON object")
        return call_id, name, arguments
