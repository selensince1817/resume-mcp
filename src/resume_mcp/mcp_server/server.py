import os
from typing import Literal, Dict, Any, List
import json
import re
import uuid

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
    name="RMCP",
    instructions="This server provides tools to read the CV and modify it (if user permits).",
    dependencies=["pyoverleaf", "python-dotenv", "uvicorn"],
    auth=auth_provider,
    stateless_http=True,
)


# --- Main MCP Functionality --- #
@mcp.tool
async def get_full_resume(ctx: Context) -> Dict[str, Any]:
    """
    Reads every CV section file (.tex) from the configured Overleaf project and returns their contents
    as a dictionary keyed by the section name. Sections may contain XeLatex code, which must be respected.
    Example: {"heading": "...", "education": "...", ...}
    """
    project_name = Config.CV_PROJECT_NAME
    section_map = Config.CV_SECTIONS_PATHS

    logger.info(f"Step 1: Fetching resume sections for '{project_name}'...")

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

    logger.success("Step 1: Successfully fetched resume sections.")
    logger.debug(f"Found {len(resume_data)} sections.")
    return resume_data


@mcp.tool
def read_cv_section(
    cv_section: Literal["education", "experience", "additional_experience", "skills"]
) -> str:
    """
    Reads a given CV section.
    Choose from ["education", "experience", "additional_experience", "skills"].
    Returns a string containing some XeLatex structure which must be respected.
    """
    file_path = Config.CV_SECTIONS_PATHS[cv_section]
    project_name = Config.CV_PROJECT_NAME
    try:
        client = _get_client()
        return client.read(file_path)
    except FileNotFoundError:
        raise ToolError(f"File '{file_path}' not found in project.")
    except Exception as e:
        raise ToolError(str(e))


import os
from typing import Dict, Any, Literal


# Assuming the following are defined elsewhere:
# - @mcp.tool decorator
# - Config object with CV_PROJECT_NAME and CV_SECTIONS_PATHS
# - _get_client(project_name) function
# - logger object
# - ToolError exception


@mcp.tool
def create_tailored_section(
    cv_section: Literal["education", "experience", "additional_experience", "skills"],
    company_role_slug: str,
    new_content: str,
) -> Dict[str, Any]:
    """
    Creates a NEW .tex file for a CV section tailored to a specific company and role.
    If a file with the same name already exists, it adds a unique ID to the filename.
    This is a NON-DESTRUCTIVE action.

    Args:
        cv_section: The base section, e.g., "experience".
        company_role_slug: A clean string for the filename, e.g., "amazon_data_scientist".
        new_content: The full XeLaTeX content for the new file.
    """
    project_name = Config.CV_PROJECT_NAME
    # Assuming CV_SECTIONS_PATHS gives a file path, os.path.dirname gets its directory
    target_dir = os.path.dirname(Config.CV_SECTIONS_PATHS[cv_section])

    try:
        client = _get_client(project_name)
        client.mkdir(target_dir, parents=True, exist_ok=True)  # Ensure directory exists

        # --- Start of Corrected Block ---

        base_filename = f"{cv_section}-{company_role_slug}"
        extension = ".tex"
        file_name = f"{base_filename}{extension}"
        full_path = os.path.join(target_dir, file_name)
        counter = 1

        # Use the client.exists() method to check for the file robustly.
        while client.exists(full_path):
            logger.warning(f"File '{file_name}' already exists. Generating a new name.")
            # If it exists, create a new filename and a new full_path to check in the next loop.
            file_name = f"{base_filename}_{counter}{extension}"
            full_path = os.path.join(target_dir, file_name)
            counter += 1

        # --- End of Corrected Block ---

        # 'full_path' now contains a path that is guaranteed to be unique.

        logger.info(f"Creating new tailored file at: {full_path}")
        client.write(full_path, new_content)

        logger.success(f"Successfully created file: {file_name}")
        return {
            "status": "success",
            "file_path": full_path,
            "filename": file_name,
            "project_name": project_name,
        }
    except Exception as e:
        logger.exception(f"Failed to create tailored file.")
        raise ToolError(f"Failed to write to file in project '{project_name}': {e}")


@mcp.tool
def update_main_tex_with_new_sections(
    new_section_filenames: list[str],
) -> Dict[str, Any]:
    """
    Updates main.tex by REPLACING the current \input command for a given section
    with the one for the new tailored section. Handles replacing already-tailored sections.

    Args:
        new_section_filenames: A list of the new filenames to use for replacement,
                               e.g., ["experience.tex"] or ["experience-google_product_manager.tex"].
    """
    project_name = Config.CV_PROJECT_NAME
    main_tex_path = Config.CV_MAIN_TEX_PATH

    logger.info(
        f"Updating '{main_tex_path}' by replacing sections with: {new_section_filenames}"
    )

    try:
        client = _get_client(project_name)
        original_content = client.read(main_tex_path)
        modified_content = original_content

        for filename in new_section_filenames:

            # Use the robust split() method to get the base section.
            base_section = filename.split(".tex")[0].split("-")[0]

            # Validate that the result is a section we actually know about.
            if base_section not in Config.CV_SECTIONS_PATHS:
                logger.warning(
                    f"Base section '{base_section}' (from '{filename}') is not a valid section. Skipping."
                )
                continue

            # This regex finds the \input for the base section, whether it's the
            # original or a previously tailored version.
            pattern_to_find = re.compile(
                r"\\input\s*\{\s*(\./)?sections/"
                + re.escape(base_section)
                + r"(-[a-zA-Z0-9_.-]*)?\.tex\s*\}",
                re.IGNORECASE,
            )

            path_to_new_file = f"sections/{filename}"
            replacement_string = f"\\\\input{{{path_to_new_file}}}"

            modified_content, num_subs = pattern_to_find.subn(
                replacement_string, modified_content
            )

            if num_subs == 0:
                error_msg = f"Update failed: Could not find any existing '\\input{{.../{base_section}...}}' line in '{main_tex_path}' to replace."
                logger.error(error_msg)
                raise ToolError(error_msg)

        # Only write and report success if a change was actually made.
        if modified_content != original_content:
            client.write(main_tex_path, modified_content)
            logger.success(
                f"Successfully updated '{main_tex_path}' by replacing sections."
            )
            return {"status": "success", "message": f"{main_tex_path} updated."}
        else:
            logger.warning(
                "No changes were made to main.tex because no valid filenames were processed."
            )
            return {"status": "no_changes", "message": "No changes made."}

    except Exception as e:
        logger.exception(f"Failed to update '{main_tex_path}'.")
        raise ToolError(f"Failed to update '{main_tex_path}': {e}")


# --- Atomic MCP Functionality --- #
@mcp.tool(enabled=False)
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


@mcp.tool(enabled=False)
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


@mcp.tool(enabled=False)
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
    # mcp.run(transport="http", host="127.0.0.1", port=8000, log_level="info")
    mcp.run()


if __name__ == "__main__":
    main()
