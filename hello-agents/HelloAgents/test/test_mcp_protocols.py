import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from protocols.mcp.client import MCPClient
from protocols.mcp.server import MCPServer, MCPServerBuilder, create_example_server
from protocols.mcp.utils import (
    create_context,
    create_error_response,
    create_success_response,
    parse_context,
)


class MCPUtilsTest(unittest.TestCase):
    def test_create_context_uses_protocol_defaults(self):
        context = create_context()

        self.assertEqual(context["messages"], [])
        self.assertEqual(context["tools"], [])
        self.assertEqual(context["resources"], [])
        self.assertEqual(context["metadata"], {})

    def test_create_context_keeps_supplied_values(self):
        context = create_context(
            messages=[{"role": "user", "content": "hello"}],
            tools=[{"name": "calculator"}],
            resources=[{"uri": "resource://status"}],
            metadata={"trace_id": "unit-test"},
        )

        self.assertEqual(context["messages"][0]["role"], "user")
        self.assertEqual(context["tools"][0]["name"], "calculator")
        self.assertEqual(context["resources"][0]["uri"], "resource://status")
        self.assertEqual(context["metadata"]["trace_id"], "unit-test")

    def test_parse_context_accepts_dict_and_fills_missing_fields(self):
        parsed = parse_context({"messages": [{"role": "assistant"}]})

        self.assertEqual(parsed["messages"], [{"role": "assistant"}])
        self.assertEqual(parsed["tools"], [])
        self.assertEqual(parsed["resources"], [])
        self.assertEqual(parsed["metadata"], {})

    def test_parse_context_accepts_json_string(self):
        parsed = parse_context(json.dumps({"tools": [{"name": "search"}]}))

        self.assertEqual(parsed["messages"], [])
        self.assertEqual(parsed["tools"], [{"name": "search"}])
        self.assertEqual(parsed["resources"], [])
        self.assertEqual(parsed["metadata"], {})

    def test_parse_context_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            parse_context("{not-json")

        with self.assertRaises(ValueError):
            parse_context(["not", "a", "context"])

    def test_response_helpers_build_expected_shapes(self):
        success = create_success_response({"result": 42}, metadata={"source": "unit"})
        error = create_error_response(
            "Tool not found",
            error_code="TOOL_NOT_FOUND",
            details={"tool": "missing"},
        )

        self.assertTrue(success["success"])
        self.assertEqual(success["data"], {"result": 42})
        self.assertEqual(success["metadata"], {"source": "unit"})
        self.assertEqual(error["error"]["message"], "Tool not found")
        self.assertEqual(error["error"]["code"], "TOOL_NOT_FOUND")
        self.assertEqual(error["error"]["details"], {"tool": "missing"})


class MCPServerWrapperTest(unittest.TestCase):
    def test_server_info_and_tool_registration_are_exposed_through_memory_client(self):
        server = MCPServer("unit-server", description="Unit test MCP server")

        def greet(name: str) -> str:
            """Return a greeting."""
            return f"Hello, {name}!"

        server.add_tool(greet, name="greet", description="Generate a greeting")

        self.assertEqual(
            server.get_info(),
            {
                "name": "unit-server",
                "description": "Unit test MCP server",
                "protocol": "MCP",
            },
        )

        async def run_client_checks():
            async with MCPClient(server.mcp) as client:
                tools = await client.list_tools()
                result = await client.call_tool("greet", {"name": "MCP"})
                return tools, result

        tools, result = asyncio.run(run_client_checks())

        self.assertEqual([tool["name"] for tool in tools], ["greet"])
        self.assertEqual(tools[0]["description"], "Generate a greeting")
        self.assertEqual(result, "Hello, MCP!")

    def test_builder_supports_chained_tool_resource_and_prompt_registration(self):
        def add(a: int, b: int) -> int:
            return a + b

        def status() -> str:
            return "ready"

        def summarize(topic: str) -> str:
            return f"Summarize {topic}"

        builder = MCPServerBuilder("builder-server", "Builder test server")
        built = (
            builder
            .with_tool(add, name="add", description="Add two integers")
            .with_resource(status, uri="resource://status")
            .with_prompt(summarize, name="summarize", description="Summarize a topic")
            .build()
        )

        self.assertIsInstance(built, MCPServer)
        self.assertEqual(built.get_info()["name"], "builder-server")
        self.assertEqual(built.get_info()["description"], "Builder test server")

        async def run_client_checks():
            async with MCPClient(built.mcp) as client:
                tools = await client.list_tools()
                result = await client.call_tool("add", {"a": 2, "b": 5})
                return tools, result

        tools, result = asyncio.run(run_client_checks())

        self.assertIn("add", [tool["name"] for tool in tools])
        self.assertIn("7", str(result))

    def test_create_example_server_registers_documented_tools(self):
        server = create_example_server()

        self.assertIsInstance(server, MCPServer)
        self.assertEqual(server.get_info()["name"], "example-server")

        async def run_client_checks():
            async with MCPClient(server.mcp) as client:
                tools = await client.list_tools()
                calc_result = await client.call_tool("calculator", {"expression": "10 * 5"})
                greet_result = await client.call_tool("greet", {"name": "Alice"})
                return tools, calc_result, greet_result

        tools, calc_result, greet_result = asyncio.run(run_client_checks())

        self.assertEqual({tool["name"] for tool in tools}, {"calculator", "greet"})
        self.assertEqual(calc_result, "Result: 50")
        self.assertIn("Hello, Alice!", greet_result)


class MCPClientTransportTest(unittest.TestCase):
    def test_memory_transport_keeps_fastmcp_instance(self):
        server = FastMCP("memory-transport")
        client = MCPClient(server)

        self.assertIs(client.server_source, server)

    def test_http_and_sse_sources_create_expected_transport_types(self):
        http_client = MCPClient("http://localhost:8000/mcp")
        sse_client = MCPClient("http://localhost:8000/sse", transport_type="sse")

        self.assertEqual(type(http_client.server_source).__name__, "StreamableHttpTransport")
        self.assertEqual(type(sse_client.server_source).__name__, "SSETransport")

    def test_python_script_and_command_sources_create_stdio_transports(self):
        with tempfile.NamedTemporaryFile(suffix=".py") as script:
            script_path = script.name
            script_client = MCPClient(script_path, server_args=["--debug"], env={"DEBUG": "1"})
            command_client = MCPClient(["python", script_path, "--stdio"], server_args=["--verbose"])

        self.assertEqual(type(script_client.server_source).__name__, "PythonStdioTransport")
        self.assertEqual(type(command_client.server_source).__name__, "PythonStdioTransport")

    def test_config_sources_create_configured_transports(self):
        with tempfile.NamedTemporaryFile(suffix=".py") as script:
            stdio_config = {"transport": "stdio", "command": "python", "args": [script.name]}
            http_config = {"transport": "http", "url": "http://localhost:8000/mcp"}
            sse_config = {"transport": "sse", "url": "http://localhost:8000/sse"}

            self.assertEqual(type(MCPClient(stdio_config).server_source).__name__, "PythonStdioTransport")

        self.assertEqual(type(MCPClient(http_config).server_source).__name__, "StreamableHttpTransport")
        self.assertEqual(type(MCPClient(sse_config).server_source).__name__, "SSETransport")

        with self.assertRaises(ValueError):
            MCPClient({"transport": "websocket", "url": "ws://localhost:8000"})

    def test_client_methods_require_async_context_manager(self):
        client = MCPClient(FastMCP("not-connected"))

        async def call_without_connection():
            await client.list_tools()

        with self.assertRaises(RuntimeError):
            asyncio.run(call_without_connection())

        self.assertEqual(client.get_transport_info(), {"status": "not_connected"})


class MCPClientMemoryIntegrationTest(unittest.TestCase):
    def test_memory_client_can_list_ping_and_call_tools(self):
        server = FastMCP("memory-integration")

        @server.tool()
        def add(a: int, b: int) -> dict:
            return {"sum": a + b}

        async def run_client_checks():
            async with MCPClient(server) as client:
                tools = await client.list_tools()
                result = await client.call_tool("add", {"a": 3, "b": 4})
                ping_ok = await client.ping()
                transport_info = client.get_transport_info()
                return tools, result, ping_ok, transport_info

        tools, result, ping_ok, transport_info = asyncio.run(run_client_checks())

        self.assertEqual([tool["name"] for tool in tools], ["add"])
        self.assertIn('"sum":7', result.replace(" ", ""))
        self.assertTrue(ping_ok)
        self.assertEqual(transport_info["status"], "connected")

    def test_fastmcp_list_return_shapes_are_documented_for_future_client_compatibility(self):
        server = FastMCP("resource-prompt-shape")

        @server.resource("resource://status")
        def status() -> str:
            return "ready"

        @server.prompt()
        def explain(topic: str) -> str:
            return f"Explain {topic}"

        async def inspect_raw_fastmcp_shapes():
            async with MCPClient(server) as client:
                raw_resources = await client.client.list_resources()
                raw_prompts = await client.client.list_prompts()
                return raw_resources, raw_prompts

        raw_resources, raw_prompts = asyncio.run(inspect_raw_fastmcp_shapes())

        self.assertIsInstance(raw_resources, list)
        self.assertIsInstance(raw_prompts, list)
        self.assertEqual(str(raw_resources[0].uri), "resource://status")
        self.assertEqual(raw_prompts[0].name, "explain")


if __name__ == "__main__":
    unittest.main()
