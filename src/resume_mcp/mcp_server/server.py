from fastmcp import FastMCP
from resume_mcp.overleaf_api.core import OverleafClient
from typing import List, Dict, Any, Optional

# Initialize the MCP server
mcp = FastMCP("cv_mcp_server")


# --- Helper Function ---
# This helper handles client creation and errors gracefully, keeping the tools clean.
def _get_client(project_name: str) -> Optional[OverleafClient]:
    """Tries to create an OverleafClient, returning None on failure."""
    try:
        return OverleafClient(project_name)
    except Exception as e:
        print(f"Error initializing client for project '{project_name}': {e}")
        return None


# --- MCP Tools ---


@mcp.tool
def list_overleaf_projects() -> List[Dict[str, str]]:
    """
    Lists all accessible Overleaf projects, returning their names and IDs.
    """
    try:
        return OverleafClient.list_projects()
    except Exception as e:
        return [{"error": f"Failed to list projects: {e}"}]


@mcp.tool
def list_files(project_name: str, path: str = "") -> List[str]:
    """
    Lists all files and folders within a given path in a specific Overleaf project.
    Defaults to the root directory.
    """
    client = _get_client(project_name)
    if not client:
        return [f"Error: Could not connect to project '{project_name}'."]

    try:
        return client.listdir(path)
    except Exception as e:
        return [f"Error listing files in '{path}': {e}"]


@mcp.tool
def read_file(project_name: str, file_path: str) -> str:
    """
    Reads the content of a specific file from an Overleaf project.
    """
    client = _get_client(project_name)
    if not client:
        return f"Error: Could not connect to project '{project_name}'."

    try:
        return client.read(file_path)
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found in project '{project_name}'."
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool
def write_file(project_name: str, file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes (or overwrites) a file in an Overleaf project with the provided content.
    """
    client = _get_client(project_name)
    if not client:
        return {
            "status": "error",
            "message": f"Could not connect to project '{project_name}'.",
        }

    try:
        client.write(file_path, content)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        return {"status": "error", "message": f"Failed to write to file: {e}"}


# --- Main execution block ---

if __name__ == "__main__":
    print("Starting MCP Server for Overleaf...")
    # To run this server, you would typically use a command like `uvicorn`
    # or the method provided by the FastMCP library.
    # The mcp.run() might be for development.
    mcp.run()
