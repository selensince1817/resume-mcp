import os
from typing import Literal, Dict, Any, List
import json
import re


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


@mcp.tool
def create_tailored_section(
    cv_section: Literal["education", "experience", "additional_experience", "skills"],
    company_role_slug: str,
    new_content: str,
) -> Dict[str, Any]:
    """
    This function is to be used when the final change is consolidated and you are ready to create a tailored section.
    Creates a NEW .tex file for a CV section tailored to a specific company and role.
    This is a NON-DESTRUCTIVE action; it does not overwrite the original file.

    Args:
        cv_section: The base section, e.g., "experience". Literal["education", "experience", "additional_experience", "skills".
        company_role_slug: A clean string for the filename derived from the job company name and some id, e.g., "amazon_data_scientist".
        new_content: The full XeLaTeX content for the new file.
    """
    # Define the directory where tailored sections will be stored.
    target_dir = os.path.dirname(Config.CV_SECTIONS_PATHS[cv_section])

    # Construct the new filename
    file_name = f"{cv_section}-{company_role_slug}.tex"
    full_path = os.path.join(target_dir, file_name)

    project_name = Config.CV_PROJECT_NAME
    logger.info(f"Creating new tailored file at: {full_path}")

    try:
        client = _get_client(project_name)

        # Ensure the target directory exists in the Overleaf project
        client.mkdir(target_dir, parents=True, exist_ok=True)

        # Write the new file
        client.write(full_path, new_content)

        logger.success(f"Successfully created file: {file_name}")
        return {
            "status": "success",
            "file_path": full_path,
            "project_name": project_name,
        }
    except Exception as e:
        logger.exception(f"Failed to create tailored file '{full_path}'")
        raise ToolError(
            f"Failed to write to file '{full_path}' in project '{project_name}': {e}"
        )


@mcp.tool
def update_main_tex_with_new_sections(
    new_section_filenames: list[str],
) -> Dict[str, Any]:
    """
    Updates main.tex to point to the new tailored section files.
    This is the final 'compile' step after creating tailored sections.

    Args:
        new_section_filenames: A list of the new filenames that were created,
                               e.g., ["experience-amazon_data_scientist.tex"].
    """
    project_name = Config.CV_PROJECT_NAME
    main_tex_path = "main.tex"
    logger.info(
        f"Updating '{main_tex_path}' with new sections: {new_section_filenames}"
    )

    try:
        client = _get_client(project_name)

        # 1. Read the current main.tex content
        original_content = client.read(main_tex_path)
        modified_content = original_content

        # 2. Loop through each new filename and perform a replacement
        for filename in new_section_filenames:
            # Extract the base section name (e.g., "experience" from "experience-amazon_...-.tex")
            base_section = filename.split("-")[0]
            if base_section not in Config.CV_SECTIONS_PATHS:
                logger.warning(
                    f"Could not find base section for '{filename}', skipping."
                )
                continue

            # This regex finds the original \input, handling "./" prefix and whitespace
            # e.g., \input{./sections/experience.tex}
            pattern_to_find = re.compile(
                r"\\input\{(\./)?sections/" + base_section + r"\.tex\}"
            )

            # This is the new path inside the 'tailored' subdirectory we defined before
            path_to_new_file = f"sections/tailored/{filename}"
            replacement_string = f"\\input{{{path_to_new_file}}}"

            # Perform the substitution
            modified_content = pattern_to_find.sub(replacement_string, modified_content)

        # 3. Write the updated content back to main.tex
        if modified_content != original_content:
            client.write(main_tex_path, modified_content)
            logger.success(f"Successfully updated '{main_tex_path}'.")
            return {"status": "success", "message": f"{main_tex_path} updated."}
        else:
            logger.warning(
                "No changes were made to main.tex; new sections may not have matched."
            )
            return {
                "status": "no_changes",
                "message": "No matching sections found to update.",
            }

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
