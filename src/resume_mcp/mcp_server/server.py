from fastmcp import FastMCP

mcp = FastMCP("cv_mcp_server")


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
