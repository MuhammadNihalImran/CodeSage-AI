import os
import logging
import asyncio
import time
from dotenv import load_dotenv

from agent.sub_agents.bug_finder import BugFinderAgent
from agent.sub_agents.security_agent import SecurityAgent
from agent.sub_agents.optimization_agent import OptimizationAgent
from agent.sub_agents.learner_profiler import LearnerProfilerAgent
from agent.synthesizer import SynthesizerAgent

from db.supabase_client import (
    get_user_profile,
    upsert_user_profile,
    save_code_review,
    get_recurring_mistakes,
    update_recurring_mistake
)

load_dotenv()

# Setup logging targeting logs/agent_activity.log
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(PROJECT_DIR, "logs", "agent_activity.log")
IS_VERCEL = "VERCEL" in os.environ

activity_logger = logging.getLogger("agent_activity")
if not activity_logger.handlers:
    activity_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    if IS_VERCEL:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        activity_logger.addHandler(sh)
    else:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(formatter)
        activity_logger.addHandler(fh)


class OrchestratorAgent:
    """Orchestrator Agent that manages concurrent sub-agent analyses and state updates."""

    def __init__(self) -> None:
        """Initialize all sub-agents and the synthesizer agent."""
        self.bug_finder = BugFinderAgent()
        self.security_agent = SecurityAgent()
        self.optimization_agent = OptimizationAgent()
        self.learner_profiler = LearnerProfilerAgent()
        self.synthesizer = SynthesizerAgent()

    async def run_full_pipeline(self, user_id: str, session_id: str, code: str, language: str) -> dict:
        """Runs the entire analysis and synthesis pipeline, storing state in Supabase.

        Args:
            user_id (str): The ID of the user.
            session_id (str): The active session ID.
            code (str): The code snippet to analyze.
            language (str): The programming language.

        Returns:
            dict: The combined analysis and tailored explanation.
        """
        # 1. Fetch existing user profile to establish prior skill level
        prior_profile = get_user_profile(user_id)
        prior_skill = prior_profile.get("skill_level") if prior_profile else None
        
        # 2. Run all 4 sub-agents concurrently
        async def run_agent_task(agent_name: str, task_coroutine) -> dict:
            start_time = time.time()
            try:
                result = await task_coroutine
                elapsed_ms = int((time.time() - start_time) * 1000)
                if isinstance(result, dict) and "error" in result:
                    activity_logger.info(f"Orchestrator -> {agent_name} -> failure ({elapsed_ms}ms)")
                else:
                    activity_logger.info(f"Orchestrator -> {agent_name} -> success ({elapsed_ms}ms)")
                return result
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                activity_logger.info(f"Orchestrator -> {agent_name} -> failure ({elapsed_ms}ms)")
                return {
                    "error": True,
                    "error_type": "agent_failure",
                    "message": f"This agent encountered an issue: {str(e)}"
                }

        tasks = [
            run_agent_task("Bug Finder", self.bug_finder.find_bugs(code, language)),
            run_agent_task("Security Agent", self.security_agent.check_security(code, language)),
            run_agent_task("Optimization Agent", self.optimization_agent.suggest_optimizations(code, language)),
            run_agent_task("Learner Profiler", self.learner_profiler.estimate_skill_level(code, language))
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        bug_res = results[0]
        sec_res = results[1]
        opt_res = results[2]
        prof_res = results[3]

        # Parse sub-agent outputs
        bugs = bug_res.get("bugs", []) if not bug_res.get("error") else []
        security_issues = sec_res.get("security_issues", []) if not sec_res.get("error") else []
        optimizations = opt_res.get("optimizations", []) if not opt_res.get("error") else []
        
        # Skill level decision: use prior baseline if profiler fails, otherwise use new estimation
        skill_level = prof_res.get("skill_level", prior_skill or "beginner") if not prof_res.get("error") else (prior_skill or "beginner")
        skill_reasoning = prof_res.get("reasoning", "Using existing profile baseline.") if not prof_res.get("error") else prof_res.get("message", "Using baseline due to analysis error.")

        # 3. Query recurring mistakes history
        recurring_mistakes = get_recurring_mistakes(user_id)

        # 4. Call SynthesizerAgent to summarize tailory
        synth_res = await self.synthesizer.synthesize(
            bug_results=bug_res,
            security_results=sec_res,
            optimization_results=opt_res,
            skill_level=skill_level,
            recurring_mistakes=recurring_mistakes
        )

        # 5. Save the code review row
        save_code_review(
            user_id=user_id,
            session_id=session_id,
            code=code,
            bugs=bugs,
            security_issues=security_issues,
            optimizations=optimizations,
            skill_level=skill_level
        )

        # 6. Identify bug types & update recurring mistakes
        found_types = set()
        for bug in bugs:
            issue_text = bug.get("issue", "")
            found_types.add(self._categorize_mistake(issue_text, is_security=False))
        for sec in security_issues:
            issue_text = sec.get("issue", "")
            found_types.add(self._categorize_mistake(issue_text, is_security=True))

        for mistake_type in found_types:
            update_recurring_mistake(user_id, mistake_type)

        # 7. Update user profile with latest skill level
        upsert_user_profile(user_id, skill_level, language)

        # 8. Return combined results
        return {
            "bugs": bugs,
            "security_issues": security_issues,
            "optimizations": optimizations,
            "skill_level": skill_level,
            "skill_reasoning": skill_reasoning,
            "final_explanation": synth_res.get("final_explanation", "Could not synthesize findings.") if not synth_res.get("error") else synth_res.get("message"),
            "flagged_recurring": synth_res.get("flagged_recurring", []),
            "skill_level_used": synth_res.get("skill_level_used", skill_level),
            "bugs_error": bug_res if bug_res.get("error") else None,
            "security_error": sec_res if sec_res.get("error") else None,
            "optimizations_error": opt_res if opt_res.get("error") else None,
            "profiler_error": prof_res if prof_res.get("error") else None,
            "synthesizer_error": synth_res if synth_res.get("error") else None
        }

    def _categorize_mistake(self, text: str, is_security: bool) -> str:
        """Helper to categorize raw issue descriptions into machine slugs."""
        t = text.lower()
        if "recursion" in t or "recursive" in t or "stack overflow" in t:
            return "infinite_recursion"
        if "secrets" in t or "password" in t or "key" in t or "token" in t:
            return "hardcoded_secrets"
        if "sql" in t or "injection" in t:
            return "sql_injection_risk"
        if "eval" in t or "exec" in t:
            return "unsafe_eval_exec"
        if "resource" in t or "leak" in t or "close" in t or "unclosed" in t:
            return "resource_leak"
        if "performance" in t or "complexity" in t or "slow" in t:
            return "inefficient_algorithm"
        return "general_security_risk" if is_security else "general_logic_error"
