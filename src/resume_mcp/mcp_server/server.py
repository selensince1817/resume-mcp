import os
import sys
from typing import List, Dict, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import BearerAuthProvider
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from resume_mcp.overleaf_api.core import OverleafClient, OverleafConnectionError

# Authentication Setup
AUDIENCE = "resume-mcp-server"
PUBLIC_KEY_PATH = "public_key.pem"
PRIVATE_KEY_PATH = "private_key.pem"

try:
    # Load the keys from the files you generated in binary mode
    with open(PUBLIC_KEY_PATH, "rb") as f:
        public_key_bytes = f.read()
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_bytes = f.read()

    # Decode bytes into strings
    public_key = public_key_bytes.decode("utf-8")
    private_key = private_key_bytes.decode("utf-8")

    auth_provider = BearerAuthProvider(public_key=public_key, audience=AUDIENCE)

except FileNotFoundError:
    auth_provider = None


# --- MCP Server Initialization ---
mcp = FastMCP(
    name="Overleaf Project Manager",
    instructions="This server provides tools to list Overleaf projects, and read or write files within a specific Overleaf project. Please provide a project_name for all file operations.",
    dependencies=["pyoverleaf", "python-dotenv", "uvicorn"],
    auth=auth_provider,
    stateless_http=True,
)


# --- Helper Function ---
def _get_client(project_name: str) -> OverleafClient:
    """
    Initializes and returns an OverleafClient for the given project.
    Raises ToolError if the client cannot be created.
    """
    try:
        if not os.environ.get("OVERLEAF_SESSION_COOKIE"):
            raise OverleafConnectionError(
                "Configuration Error: The OVERLEAF_SESSION_COOKIE environment variable is not set on the server."
            )
        return OverleafClient(project_name)
    except OverleafConnectionError as e:
        raise ToolError(f"Failed to connect to Overleaf: {e}")
    except Exception as e:
        raise ToolError(
            f"An unexpected error occurred while connecting to project '{project_name}': {e}"
        )


# --- MCP Tools ---


@mcp.tool
def list_overleaf_projects() -> List[Dict[str, str]]:
    """
    Lists all accessible Overleaf projects, returning their names and IDs.
    """
    try:
        return OverleafClient.list_projects()
    except Exception as e:
        raise ToolError(f"Failed to list Overleaf projects: {e}")


@mcp.tool
def list_files(project_name: str, path: str = "") -> List[str]:
    """
    Lists all files and folders within a given path in a specific Overleaf project.
    Defaults to the root directory of the project.
    """
    try:
        client = _get_client(project_name)
        return [entity for entity in client.listdir(path)]
    except FileNotFoundError:
        raise ToolError(f"Path '{path}' not found in project '{project_name}'.")
    except Exception as e:
        raise ToolError(str(e))


@mcp.tool
def read_file(project_name: str, file_path: str) -> str:
    """
    Reads the content of a specific file from an Overleaf project.
    """
    try:
        client = _get_client(project_name)
        return client.read(file_path)
    except FileNotFoundError:
        raise ToolError(f"File '{file_path}' not found in project '{project_name}'.")
    except Exception as e:
        raise ToolError(str(e))


@mcp.tool
def write_file(project_name: str, file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes (or overwrites) a file in an Overleaf project with the provided content.
    """
    try:
        client = _get_client(project_name)
        client.write(file_path, content)
        return {
            "status": "success",
            "file_path": file_path,
            "project_name": project_name,
        }
    except Exception as e:
        raise ToolError(
            f"Failed to write to file '{file_path}' in project '{project_name}': {e}"
        )


@mcp.tool
def read_resume() -> str:
    """
    Reads the content of user's resume/CV from an Overleaf project called "CV-XeLate".
    """
    try:
        client = _get_client("CV-XeLate")
        return client.read("main.tex")
    except FileNotFoundError:
        raise ToolError(f"Oops")
    except Exception as e:
        raise ToolError(str(e))


# --- Custom Web Route ---
# As per the docs, custom routes can be added for things like health checks.
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """A simple health check endpoint that returns 'OK'."""
    return PlainTextResponse("OK")


# --- Main Execution Block ---
if __name__ == "__main__":

    mcp.run(
        transport="stdio",
        host="127.0.0.1",
        port=8000,
        log_level="debug",
    )
