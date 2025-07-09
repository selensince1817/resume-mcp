import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Configuration class for the application.
    """

    # --- Authentication ---
    AUDIENCE = "resume-mcp-server"
    PUBLIC_KEY_PATH = "public_key.pem"
    PRIVATE_KEY_PATH = "private_key.pem"

    # --- Overleaf ---
    CV_PROJECT_NAME = "cv-xelatex"
    CV_MAIN_TEX_PATH = "main.tex"
    CV_SECTIONS_PATHS = {
        "heading": "sections/heading.tex",
        "education": "sections/education.tex",
        "experience": "sections/experience.tex",
        "additional_experience": "sections/additional_experience.tex",
        "skills": "sections/skills.tex",
    }

    # --- LLM ---
    LLM_MAX_TOKENS = 8192

    # --- Overleaf Client ---
    OVERLEAF_SESSION_COOKIE = os.environ.get("OVERLEAF_SESSION_COOKIE")
