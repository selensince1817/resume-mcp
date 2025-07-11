import os
from dotenv import load_dotenv

load_dotenv()


class PromptLibrary:
    """
    Prompt Library class for the application.
    """

    @staticmethod
    def assess_profile_similarity(resume_sections: dict, job_description: str) -> str:
        return f"""
            Compare the following candidate resume (split by sections) to the provided job description.
            Identify:
            - strengths: relevant skills, experiences, or qualifications
            - gaps: missing or weak areas
            Return a JSON object: {{"strengths": [...], "gaps": [...]}} ONLY.

            RESUME: {resume_sections}

            JOB DESCRIPTION: {job_description}
            """
