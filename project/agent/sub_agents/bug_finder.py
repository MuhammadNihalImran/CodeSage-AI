import os
import json
import re
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

class BugFinderAgent:
    """Sub-agent responsible for finding bugs and logic errors in user code."""

    def __init__(self) -> None:
        """Initialize the BugFinderAgent with the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def find_bugs(self, code: str, language: str) -> dict:
        """Sends the code to Gemini to find logic, syntax, and runtime bugs.

        Args:
            code (str): The code snippet to analyze.
            language (str): The programming language of the code.

        Returns:
            dict: The bugs found, structured as JSON.
        """
        # 1. Check for simulated quota error
        if os.environ.get("SIMULATE_QUOTA_ERROR", "").lower() == "true":
            logger.info("BugFinderAgent: Simulating quota error.")
            return {
                "error": True,
                "error_type": "quota_exceeded",
                "message": "Daily AI quota reached. Please try again later or enable mock mode for testing."
            }

        # 2. Check for mock responses
        if os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true":
            logger.info("BugFinderAgent: Returning mock response.")
            return {
                "bugs": [
                    {
                        "line": 3,
                        "issue": "Infinite recursion detected. The function calls itself without a base case.",
                        "severity": "high"
                    }
                ]
            }

        system_prompt = (
            "You are a senior code reviewer specializing in software reliability and bug detection. "
            "Analyze the code and identify only logic errors, syntax issues, runtime bugs, and functional errors. "
            "Do NOT report security issues, performance optimization tips, or general code style improvements. "
            "You must return a JSON object with a single key 'bugs' containing a list of dictionaries. "
            "Each dictionary must have exactly three keys: 'line' (integer or null), 'issue' (string), and 'severity' (string, e.g., 'low', 'medium', 'high')."
        )

        user_content = f"Language: {language}\n\nCode:\n```\n{code}\n```"

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                )
            )

            response_text = response.text
            if not response_text:
                return {"bugs": []}

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            parsed_json = json.loads(cleaned_text.strip())
            return parsed_json
        except Exception as e:
            logger.exception(f"Error in BugFinderAgent: {e}")
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                return {
                    "error": True,
                    "error_type": "quota_exceeded",
                    "message": "Daily AI quota reached. Please try again later or enable mock mode for testing."
                }
            return {
                "error": True,
                "error_type": "agent_failure",
                "message": "This agent encountered an issue and could not complete the analysis."
            }
