import os
import json
import re
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

class LearnerProfilerAgent:
    """Sub-agent responsible for analyzing learner patterns, knowledge gaps, and progress."""

    def __init__(self) -> None:
        """Initialize the LearnerProfilerAgent with the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def estimate_skill_level(self, code: str, language: str) -> dict:
        """Sends the code to Gemini to profile the learner's skill level.

        Args:
            code (str): The code snippet to analyze.
            language (str): The programming language of the code.

        Returns:
            dict: The learner skill level and reasoning, structured as JSON.
        """
        # 1. Check for mock responses
        if os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true":
            logger.info("LearnerProfilerAgent: Returning mock response.")
            return {
                "skill_level": "beginner",
                "reasoning": "The code implements basic function calls but uses recursive structures without stopping criteria, indicative of beginner understanding of memory limits."
            }

        system_prompt = (
            "You are a computer science educator and mentor. "
            "Analyze the provided code and estimate the user's programming skill level (beginner, intermediate, or advanced) "
            "based on code complexity, naming conventions, use of constructs, structure, and design patterns. "
            "You must return a JSON object with exactly two keys: "
            "'skill_level' (must be exactly 'beginner', 'intermediate', or 'advanced') and 'reasoning' (string explaining the decision)."
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
                return {"skill_level": "beginner", "reasoning": "Failed to analyze code; default to beginner."}

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            parsed_json = json.loads(cleaned_text.strip())
            return parsed_json
        except Exception as e:
            logger.exception(f"Error in LearnerProfilerAgent: {e}")
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
        
