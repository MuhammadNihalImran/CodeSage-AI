import os
import json
import re
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

class OptimizationAgent:
    """Sub-agent responsible for detecting code inefficiencies and suggesting optimizations."""

    def __init__(self) -> None:
        """Initialize the OptimizationAgent with the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def suggest_optimizations(self, code: str, language: str) -> dict:
        """Sends the code to Gemini to suggest performance and style optimizations.

        Args:
            code (str): The code snippet to analyze.
            language (str): The programming language of the code.

        Returns:
            dict: The optimizations found, structured as JSON.
        """
        # 1. Check for simulated quota error
        if os.environ.get("SIMULATE_QUOTA_ERROR", "").lower() == "true":
            logger.info("OptimizationAgent: Simulating quota error.")
            return {
                "error": True,
                "error_type": "quota_exceeded",
                "message": "Daily AI quota reached. Please try again later or enable mock mode for testing."
            }

        # 2. Check for mock responses
        if os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true":
            logger.info("OptimizationAgent: Returning mock response.")
            return {
                "optimizations": [
                    {
                        "suggestion": "Refactor recursive calls to an iterative loop.",
                        "reason": "Python does not support tail-call optimization. Iterative approaches prevent stack overflows and save overhead memory."
                    }
                ]
            }

        system_prompt = (
            "You are an expert developer specializing in code performance, optimization, and software best practices. "
            "Analyze the code and suggest improvements regarding performance (time/space complexity), readability, "
            "clean code principles, and idiomatic patterns. "
            "Do NOT report security vulnerabilities or functional bugs. "
            "You must return a JSON object with a single key 'optimizations' containing a list of dictionaries. "
            "Each dictionary must have exactly two keys: 'suggestion' (string) and 'reason' (string)."
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
                return {"optimizations": []}

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            parsed_json = json.loads(cleaned_text.strip())
            return parsed_json
        except Exception as e:
            logger.exception(f"Error in OptimizationAgent: {e}")
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
