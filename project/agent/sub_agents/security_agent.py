import os
import json
import re
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

class SecurityAgent:
    """Sub-agent responsible for security audits and vulnerability checks."""

    def __init__(self) -> None:
        """Initialize the SecurityAgent with the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def check_security(self, code: str, language: str) -> dict:
        """Sends the code to Gemini to check for security vulnerabilities.

        Args:
            code (str): The code snippet to analyze.
            language (str): The programming language of the code.

        Returns:
            dict: The security issues found, structured as JSON.
        """
        # 1. Check for mock responses
        if os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true":
            logger.info("SecurityAgent: Returning mock response.")
            return {
                "security_issues": [
                    {
                        "issue": "Uncontrolled recursion leading to resource exhaustion (DoS risk).",
                        "risk_level": "medium",
                        "recommendation": "Ensure a strict recursion base case or refactor to an iterative loop."
                    }
                ]
            }

        system_prompt = (
            "You are a senior security engineer and code auditor. "
            "Analyze the code and identify only security vulnerabilities, such as hardcoded secrets, injection risks, "
            "unsafe eval/exec usage, insecure dependency patterns, or cryptographic flaws. "
            "Do NOT report functional bugs, logical errors, or style optimizations. "
            "You must return a JSON object with a single key 'security_issues' containing a list of dictionaries. "
            "Each dictionary must have exactly three keys: 'issue' (string), 'risk_level' (string, e.g., 'low', 'medium', 'high'), "
            "and 'recommendation' (string)."
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
                return {"security_issues": []}

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            parsed_json = json.loads(cleaned_text.strip())
            return parsed_json
        except Exception as e:
            logger.exception(f"Error in SecurityAgent: {e}")
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
