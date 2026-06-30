import os
import json
import re
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

class SynthesizerAgent:
    """Synthesizer Agent that creates a tailored feedback response based on skill level and mistake history."""

    def __init__(self) -> None:
        """Initialize the SynthesizerAgent with the Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)

    async def synthesize(
        self,
        bug_results: dict,
        security_results: dict,
        optimization_results: dict,
        skill_level: str,
        recurring_mistakes: list
    ) -> dict:
        """Synthesizes the findings of other agents into a unified, skill-adapted mentor report.

        Args:
            bug_results (dict): Output from BugFinderAgent.
            security_results (dict): Output from SecurityAgent.
            optimization_results (dict): Output from OptimizationAgent.
            skill_level (str): The user's skill level (beginner, intermediate, or advanced).
            recurring_mistakes (list): List of recurring mistakes from database.

        Returns:
            dict: The synthesized final response.
        """
        # 1. Check for mock responses
        if os.environ.get("USE_MOCK_RESPONSES", "").lower() == "true":
            logger.info("SynthesizerAgent: Returning mock response.")
            flagged = []
            explanation = (
                "Hey there! It looks like you've written a recursive function that calls itself endlessly. "
                "Recursion is a neat concept, but it always needs a 'base case' to tell it when to stop. "
                "Without it, your program will run out of call stack memory and crash with a RecursionError."
            )
            
            # If recurring mistakes exist, flag them
            if len(recurring_mistakes) > 0:
                flagged = ["infinite_recursion"]
                explanation += (
                    "\n\n⚠️ Note: You've made this specific mistake (infinite_recursion) before. "
                    "Remember, checking base conditions before the recursive step is critical to prevent call stack issues!"
                )
            
            return {
                "final_explanation": explanation,
                "flagged_recurring": flagged,
                "skill_level_used": skill_level
            }

        system_prompt = (
            "You are a senior CS mentor. Synthesize the reports from the specialized sub-agents "
            "(bugs, security issues, optimization tips) and the learner's recurring mistakes history. "
            "Your output must be a JSON object with exactly three keys:\n"
            "1. 'final_explanation' (string): A human-readable synthesis. Modify your teaching style based on 'skill_level':\n"
            "   - 'beginner': Explain concepts in simple terms, be encouraging, and avoid overly academic jargon.\n"
            "   - 'intermediate': Explain the issues and fixes concisely.\n"
            "   - 'advanced': Just state the issues and fixes directly, no hand-holding.\n"
            "2. 'flagged_recurring' (list of strings): Any mistake types from the recurring history that are present in the current code.\n"
            "3. 'skill_level_used' (string): The skill level used for tailoring (e.g. 'beginner', 'intermediate', 'advanced').\n\n"
            "Important: If a current bug or security issue matches a recurring mistake in the history, explicitly call it out "
            "in 'final_explanation' (e.g., 'You've made this type of mistake N times before — let's make sure it sticks this time')."
        )

        user_content = {
            "bugs": bug_results.get("bugs", []),
            "security_issues": security_results.get("security_issues", []),
            "optimizations": optimization_results.get("optimizations", []),
            "skill_level": skill_level,
            "recurring_mistakes_history": recurring_mistakes
        }

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=json.dumps(user_content),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                )
            )

            response_text = response.text
            if not response_text:
                return {
                    "final_explanation": "Could not synthesize findings.",
                    "flagged_recurring": [],
                    "skill_level_used": skill_level
                }

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            parsed_json = json.loads(cleaned_text.strip())
            return parsed_json
        except Exception as e:
            logger.exception(f"Error in SynthesizerAgent: {e}")
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                return {
                    "error": True,
                    "error_type": "quota_exceeded",
                    "message": "Daily AI quota reached. Please try again later or enable mock mode for testing.",
                    "final_explanation": "Failed to synthesize analysis due to an internal error.",
                    "flagged_recurring": [],
                    "skill_level_used": skill_level
                }
            return {
                "error": True,
                "error_type": "agent_failure",
                "message": "This agent encountered an issue and could not complete the analysis.",
                "final_explanation": "Failed to synthesize analysis due to an internal error.",
                "flagged_recurring": [],
                "skill_level_used": skill_level
            }
