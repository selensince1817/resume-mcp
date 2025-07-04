import os
import pytest
import uuid

# Load .env automatically if python-dotenv is installed (optional)
try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    pass

from mcp.overleaf_api.core import OverleafClient

# --- Test Configuration ---
PROJECT = os.environ.get("OVERLEAF_TEST_PROJECT")
MAIN_TEX = "main.tex"
SECTIONS_DIR = "sections"
# A representative content file to validate the core editing workflow
CONTENT_FILE_TO_TEST = f"{SECTIONS_DIR}/experience.tex"
# A temporary file for write/delete tests, ensuring no side effects
TEMP_FILE = f"{SECTIONS_DIR}/_pytest_temp_{uuid.uuid4().hex[:6]}.txt"


# Skip all tests if the project is not configured
pytestmark = pytest.mark.skipif(
    not PROJECT, reason="OVERLEAF_TEST_PROJECT environment variable not set"
)


@pytest.fixture(scope="module")
def client():
    """Provides a single, authenticated client for the entire test session."""
    return OverleafClient(PROJECT)


def test_client_can_read_project_structure(client):
    """Verifies the client can connect and list the expected file structure."""
    root_files = client.listdir("")
    assert MAIN_TEX in root_files
    assert SECTIONS_DIR in root_files

    section_files = client.listdir(SECTIONS_DIR)
    assert "experience.tex" in section_files
    assert "education.tex" in section_files


def test_full_file_lifecycle(client):
    """
    Tests the fundamental create, write, read, and delete cycle.
    This test guarantees the client's basic file operations work.
    """
    try:
        # Verify the file doesn't exist initially
        assert not client.exists(TEMP_FILE)

        # Create the file by writing to it
        test_content = "This is a temporary file for testing."
        client.write(TEMP_FILE, test_content)
        client.refresh()
        assert client.exists(TEMP_FILE)

        # Read the content back and verify it's correct
        read_content = client.read(TEMP_FILE)
        assert read_content == test_content

    finally:
        # The 'finally' block ensures cleanup happens even if asserts fail
        if client.exists(TEMP_FILE):
            client.remove(TEMP_FILE)
            client.refresh()
        assert not client.exists(TEMP_FILE)


def test_lossless_edit_of_content_section(client):
    """
    Ensures the core workflow of editing a real content section is lossless,
    and restores the original content to prevent side effects.
    """
    original_content = None
    try:
        # Read the original content and confirm it's a valid target
        original_content = client.read(CONTENT_FILE_TO_TEST)
        assert "\\pounds" in original_content

        # Perform a simulated edit
        edited_content = original_content + "\n% --- Test edit ---"

        # Write the change and read it back
        client.write(CONTENT_FILE_TO_TEST, edited_content)
        client.refresh()
        final_content = client.read(CONTENT_FILE_TO_TEST)

        # Assert that the API cycle was perfect
        assert final_content == edited_content

    finally:
        # Crucially, restore the file to its original state after the test
        if original_content is not None:
            client.write(CONTENT_FILE_TO_TEST, original_content)
