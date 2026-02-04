import asyncio
import os
from contextlib import AsyncExitStack
from pathlib import Path
import shlex
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

load_dotenv()  # load environment variables from .env

# Claude model constant
ANTHROPIC_MODEL = "claude-sonnet-4-5"


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self._anthropic: Anthropic | None = None

    @property
    def anthropic(self) -> Anthropic:
        """Lazy-initialize Anthropic client when needed"""
        if self._anthropic is None:
            self._anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._anthropic


    # CONNECT TO SERVER
    async def connect_to_server(self, server_target: str, server_args: list[str] | None = None):
        """
        Connect to an MCP server over stdio.

        server_target può essere:
        - path a .py (server python)
        - path a .js (server node)
        - path a .csproj (server .NET)
        - un comando generico (es: "dotnet"), con args separati
        - un comando completo in una stringa (es: "dotnet run --project ...")
        """

        server_args = server_args or []

        # Caso 1: se mi passi una singola stringa tipo "dotnet run --project ..."
        # e non è un file esistente, la splitto come linea di comando.
        if server_args == [] and not Path(server_target).exists():
            parts = shlex.split(server_target)
            if len(parts) > 1:
                server_target, server_args = parts[0], parts[1:]

        # Caso 2: path a file esistente
        path = Path(server_target).expanduser().resolve()
        if path.exists():
            suffix = path.suffix.lower()

            if suffix == ".py":
                server_params = StdioServerParameters(
                    command="uv",
                    args=["--directory", str(path.parent), "run", path.name],
                    env=None,
                )

            elif suffix == ".js":
                server_params = StdioServerParameters(
                    command="node",
                    args=[str(path)],
                    env=None,
                )

            elif suffix == ".csproj":
                # Avvio server MCP .NET dal progetto
                server_params = StdioServerParameters(
                    command="dotnet",
                    args=["run", "--project", str(path)],
                    env=None,
                )

            else:
                # Se è un eseguibile (es: binario publishato), lo lancio direttamente
                server_params = StdioServerParameters(
                    command=str(path),
                    args=server_args,
                    env=None,
                )
        else:
            # Caso 3: comando generico (dotnet, python, node, ecc.)
            server_params = StdioServerParameters(
                command=server_target,
                args=server_args,
                env=None,
            )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        response = await self.session.list_tools()
        print("\nConnected to server with tools:", [tool.name for tool in response.tools])


    # CHAT LOOP
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")


    # CLEANUP
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


    #PROCESS QUERY
    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools (MCP)."""
        messages = [{"role": "user", "content": query}]

        tools_resp = await self.session.list_tools()
        available_tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema
        } for t in tools_resp.tools]

        final_text = []

        while True:
            # 1) Claude response (SYNC client). Se usi AsyncAnthropic, qui va: await self.anthropic.messages.create(...)
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=messages,
                tools=available_tools
            )

            assistant_blocks = []
            tool_use_block = None

            for block in response.content:
                assistant_blocks.append(block)
                if getattr(block, "type", None) == "text":
                    final_text.append(block.text)
                elif getattr(block, "type", None) == "tool_use":
                    tool_use_block = block
                    break  # gestiamo 1 tool per iterazione (più semplice e stabile)

            # 2) Se non c'è tool_use, abbiamo finito
            if tool_use_block is None:
                messages.append({"role": "assistant", "content": assistant_blocks})
                return "\n".join(final_text)

            # 3) Chiama tool MCP
            tool_name = tool_use_block.name
            tool_args = tool_use_block.input

            result = await self.session.call_tool(tool_name, tool_args)

            # MCP result -> stringa (robusto)
            if hasattr(result, "content"):
                tool_text = "\n".join(
                    c.text if hasattr(c, "text") else str(c)
                    for c in result.content
                )
            else:
                tool_text = str(result)

            # 4) Aggiorna conversazione: assistant -> tool_result
            messages.append({"role": "assistant", "content": assistant_blocks})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": tool_text
                }]
            })

# MAIN
async def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python client.py <path_to_server.py|.js|.csproj>")
        print("  python client.py <command> [args...]")
        sys.exit(1)

    client = MCPClient()
    server_target = sys.argv[1]
    server_args = sys.argv[2:]

    try:
        await client.connect_to_server(server_target, server_args=server_args)

        # Check if we have a valid API key to continue
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\nNo ANTHROPIC_API_KEY found. To query these tools with Claude, set your API key:")
            print("  export ANTHROPIC_API_KEY=your-api-key-here")
            return

        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())