import os
from typing import Literal, Dict, Any, List
import json


from loguru import logger
from fastmcp import FastMCP
from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import BearerAuthProvider
from resume_mcp.overleaf_api.core import OverleafClient, OverleafConnectionError
from .utils import load_public_key
from .config import Config
from .prompts import PromptLibrary

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
    # Step 1: Fetch resume sections
    project_name = Config.CV_PROJECT_NAME
    logger.info(f"Step 1: Fetching resume sections for '{project_name}'...")

    resume_sections = await get_full_resume(project_name, ctx=ctx)
    logger.success("Step 1: Successfully fetched resume sections.")
    logger.debug(f"Found {len(resume_sections)} sections.")

    # Step 2: Use the LLM prompt
    logger.info("Step 2: Sending prompt to LLM for analysis...")
    analysis_prompt = PromptLibrary.assess_profile_similarity(
        resume_sections, job_description
    )
    logger.info("Step 2: Prompt sent. Sending to LLM...")
    analysis_response = await ctx.sample(
        messages=analysis_prompt, max_tokens=Config.LLM_MAX_TOKENS
    )
    logger.info("Step 2: LLM response received.")
    analysis_response_json_str = analysis_response.text
    logger.success("Step 2: Received analysis from LLM.")

    # Step 3: Parse JSON
    logger.info("Step 3: Parsing LLM JSON response...")
    try:
        analysis_json = json.loads(analysis_response_json_str)
        logger.success("Step 3: Successfully parsed LLM JSON.")
    except Exception as e:
        # logger.exception automatically captures the error details
        logger.exception("Failed to parse LLM JSON. Raw output below.")
        logger.error(f"Raw output: {analysis_response_json_str}")
        raise ToolError("LLM did not return valid JSON for strengths/gaps.")

    # Step 4: Return strengths/gaps
    logger.success("Step 4: Analysis complete. Returning results.")
    return analysis_json


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
    # mcp.run()


if __name__ == "__main__":
    main()
