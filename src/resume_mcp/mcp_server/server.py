import os
from typing import Literal, Dict, Any, List
import json

from fastmcp import FastMCP
from typing import Dict
from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import BearerAuthProvider
from resume_mcp.overleaf_api.core import OverleafClient, OverleafConnectionError
from .utils import load_public_key
from .config import Config

# --- Bearer Authentication Initialization ---
try:
    auth_provider = BearerAuthProvider(
        public_key=load_public_key(), audience=Config.AUDIENCE
    )
except Exception as e:
    print(f"Failed to initialize auth provider: {e}")
    auth_provider = None


# --- MCP Server Initialization ---
mcp = FastMCP(
    name="Overleaf Project Manager",
    instructions="This server provides tools to list Overleaf projects, and read or write files within a specific Overleaf project. Please provide a project_name for all file operations.",
    dependencies=["pyoverleaf", "python-dotenv", "uvicorn"],
    auth=auth_provider,
    stateless_http=True,
)


# --- Main MCP Functionality --- #
@mcp.tool
async def analyse_cv_against_job(
    job_description: str,
    ctx: Context,
) -> Dict[str, Any]:
    """
    Reads all CV sections from Overleaf, compares to the job description via LLM,
    and returns a strengths & gaps analysis.
    """
    # Step 1: Fetch resume sections -> Dict
    project_name = Config.CV_PROJECT_NAME
    resume_sections = await get_full_resume(project_name, ctx=ctx)

    # Step 2: Use the LLM prompt to get strengths/gaps as JSON (string) -> Gaps
    analysis_json_str = await assess_profile_similarity.render(
        resume_sections=resume_sections, job_description=job_description
    )

    # Step 3: Parse JSON (fail gracefully if LLM messes up)
    try:
        analysis = json.loads(analysis_json_str)
    except Exception as e:
        await ctx.error(
            f"Failed to parse LLM JSON: {e}\nRaw output: {analysis_json_str}"
        )
        raise ToolError("LLM did not return valid JSON for strengths/gaps.")

    # Step 4: Return strengths/gaps (already as dict)
    return analysis


@mcp.prompt
def assess_profile_similarity(resume_sections: dict, job_description: str) -> str:
    """
    Given a CV section dictionary and a job description,
    return a JSON object with two keys:
      - strengths: list of strengths relevant to the job
      - gaps: list of missing skills or experiences.
    Output MUST be valid JSON.
    """
    # The function just formats the message for the LLM.
    # You can customize the instruction as much as you want.
    return (
        "Compare the following candidate resume (split by sections) to the provided job description. "
        "Identify:\n"
        "- strengths: relevant skills, experiences, or qualifications\n"
        "- gaps: missing or weak areas\n"
        'Return a JSON object: {"strengths": [...], "gaps": [...]} ONLY.\n\n'
        f"RESUME: {resume_sections}\n\n"
        f"JOB DESCRIPTION: {job_description}"
    )


@mcp.tool
async def get_full_resume(project_name: str, ctx: Context) -> Dict[str, str]:
    """
    Reads every CV section file (.tex) from the configured Overleaf project and returns their contents
    as a dictionary keyed by the section name.
    Example: {"heading": "...", "education": "...", ...}
    """
    section_map = Config.CV_SECTIONS_PATHS
    client = _get_client(project_name)
    resume_data = {}

    for section, path in section_map.items():
        try:
            content = client.read(path)
            resume_data[section] = content
            # You can log with await ctx.debug(f"Read section '{section}'") if desired
        except Exception as e:
            await ctx.error(f"Failed to read section '{section}': {e}")
            raise ToolError(f"Could not read {section}: {e}")

    return resume_data


# --- Atomic MCP Functionality --- #
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


# --- Main Execution Block ---
def main():
    """Main function to run the MCP server."""
    mcp.run(transport="http", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
