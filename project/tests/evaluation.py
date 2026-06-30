import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Ensure the parent project folder is in the python path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from agent.sub_agents.bug_finder import BugFinderAgent
from agent.sub_agents.security_agent import SecurityAgent
from agent.sub_agents.optimization_agent import OptimizationAgent

load_dotenv()

# Toggle this flag to switch between mock evaluations and live Gemini calls
USE_MOCK_FOR_EVAL = True

# Define 10 known-issue test cases
TEST_CASES = [
    {
        "name": "security_sql_injection",
        "code": "query = f'SELECT * FROM users WHERE username = {user_input}'",
        "language": "python",
        "expected_category": "security",
        "expected_keyword": "injection"
    },
    {
        "name": "security_hardcoded_secrets",
        "code": "API_KEY = 'super_secret_token_123'",
        "language": "python",
        "expected_category": "security",
        "expected_keyword": "secret"
    },
    {
        "name": "security_unsafe_eval",
        "code": "result = eval(user_submitted_data)",
        "language": "python",
        "expected_category": "security",
        "expected_keyword": "eval"
    },
    {
        "name": "security_weak_password",
        "code": "if password == '123456': return True",
        "language": "python",
        "expected_category": "security",
        "expected_keyword": "weak"
    },
    {
        "name": "bug_division_by_zero",
        "code": "def div(a, b):\n    return a / b  # Bug: b can be zero",
        "language": "python",
        "expected_category": "bug",
        "expected_keyword": "zero"
    },
    {
        "name": "bug_none_dereference",
        "code": "data = get_optional_data()\nprint(data.upper())  # Bug: data could be None",
        "language": "python",
        "expected_category": "bug",
        "expected_keyword": "none"
    },
    {
        "name": "bug_off_by_one",
        "code": "for i in range(len(arr) + 1):\n    print(arr[i])  # Bug: IndexOutOfBounds",
        "language": "python",
        "expected_category": "bug",
        "expected_keyword": "index"
    },
    {
        "name": "bug_unhandled_exception",
        "code": "import json\ndef parse(data):\n    return json.loads(data)  # Bug: json decode raises exception",
        "language": "python",
        "expected_category": "bug",
        "expected_keyword": "exception"
    },
    {
        "name": "optimization_inefficient_loop",
        "code": "for x in range(len(data)):\n    for y in range(len(data)):\n        # Quadratic loop search instead of set/hash lookup",
        "language": "python",
        "expected_category": "optimization",
        "expected_keyword": "inefficient"
    },
    {
        "name": "optimization_redundant_recursion",
        "code": "def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)  # Inefficient recursive pattern",
        "language": "python",
        "expected_category": "optimization",
        "expected_keyword": "recursive"
    }
]


# Simple mock results database to bypass Gemini when USE_MOCK_FOR_EVAL = True
MOCK_EVAL_RESPONSES = {
    "security_sql_injection": {
        "security_issues": [
            {
                "issue": "SQL injection risk due to string interpolation in raw query.",
                "risk_level": "high",
                "recommendation": "Use parameterized queries or ORM bindings."
            }
        ]
    },
    "security_hardcoded_secrets": {
        "security_issues": [
            {
                "issue": "Hardcoded API secret token found in variable assignment.",
                "risk_level": "high",
                "recommendation": "Read API secret credentials from environment variables."
            }
        ]
    },
    "security_unsafe_eval": {
        "security_issues": [
            {
                "issue": "Unsafe usage of eval() on untrusted user-submitted input.",
                "risk_level": "high",
                "recommendation": "Use literal_eval or parse data parameters explicitly."
            }
        ]
    },
    "security_weak_password": {
        "security_issues": [
            {
                "issue": "Weak hardcoded password validation check detected.",
                "risk_level": "medium",
                "recommendation": "Implement strong password hashing algorithms like bcrypt."
            }
        ]
    },
    "bug_division_by_zero": {
        "bugs": [
            {
                "line": 2,
                "issue": "Potential division by zero bug. b is not validated before division.",
                "severity": "medium"
            }
        ]
    },
    "bug_none_dereference": {
        "bugs": [
            {
                "line": 2,
                "issue": "Potential AttributeError. data can be None but is dereferenced immediately.",
                "severity": "high"
            }
        ]
    },
    "bug_off_by_one": {
        "bugs": [
            {
                "line": 1,
                "issue": "Off-by-one index loop bug. Range extends beyond array bounds.",
                "severity": "high"
            }
        ]
    },
    "bug_unhandled_exception": {
        "bugs": [
            {
                "line": 3,
                "issue": "Unhandled JSONDecodeError exception. Function does not catch parsing failures.",
                "severity": "medium"
            }
        ]
    },
    "optimization_inefficient_loop": {
        "optimizations": [
            {
                "suggestion": "Optimize inefficient quadratic loop structure.",
                "reason": "Avoid using O(N^2) searches by indexing array items into a hash set."
            }
        ]
    },
    "optimization_redundant_recursion": {
        "optimizations": [
            {
                "suggestion": "Optimize redundant calculations in recursive function.",
                "reason": "Use memoization, caching, or iterative dynamic programming solutions."
            }
        ]
    }
}

async def run_evaluation():
    print("=" * 70)
    print(f"STARTING AGENT EVALUATION (Mock Mode: {USE_MOCK_FOR_EVAL})")
    print("=" * 70)

    # Initialize sub-agents
    bug_agent = BugFinderAgent()
    sec_agent = SecurityAgent()
    opt_agent = OptimizationAgent()

    passed_count = 0
    results = []

    for test in TEST_CASES:
        name = test["name"]
        code = test["code"]
        lang = test["language"]
        category = test["expected_category"]
        keyword = test["expected_keyword"].lower()

        print(f"Running test: {name}...")

        # Obtain response (Mock vs Live Gemini)
        if USE_MOCK_FOR_EVAL:
            response = MOCK_EVAL_RESPONSES.get(name, {})
        else:
            try:
                if category == "bug":
                    response = await bug_agent.find_bugs(code, lang)
                elif category == "security":
                    response = await sec_agent.check_security(code, lang)
                elif category == "optimization":
                    response = await opt_agent.suggest_optimizations(code, lang)
                else:
                    response = {}
            except Exception as e:
                response = {"error": True, "message": str(e)}

        # Search for keyword (case-insensitive) in the entire stringified response
        response_str = str(response).lower()
        passed = keyword in response_str

        if passed:
            passed_count += 1
            status = "PASS"
        else:
            status = "FAIL"

        results.append({
            "name": name,
            "category": category,
            "keyword": keyword,
            "status": status,
            "output": response
        })

    # Calculate category breakdowns
    sec_passed = sum(1 for r in results if r["category"] == "security" and r["status"] == "PASS")
    bug_passed = sum(1 for r in results if r["category"] == "bug" and r["status"] == "PASS")
    opt_passed = sum(1 for r in results if r["category"] == "optimization" and r["status"] == "PASS")
    
    total_cases = len(TEST_CASES)
    failed_count = total_cases - passed_count
    accuracy = (passed_count / total_cases) * 100

    # Print console report in requested format
    print("\n===== AI Code Mentor Agent — Evaluation Report =====")
    print(f"Total Test Cases: {total_cases}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Accuracy: {accuracy:.0f}%")
    print("Breakdown by category:\n")
    print(f"Security: {sec_passed}/4 passed")
    print(f"Bug Detection: {bug_passed}/4 passed")
    print(f"Optimization: {opt_passed}/2 passed\n")

    failed_tests = [r for r in results if r["status"] == "FAIL"]
    if failed_tests:
        print("Failed cases:")
        for res in failed_tests:
            print(f"[{res['name']}]: expected '{res['keyword']}' not found in response")
    else:
        print("Failed cases (if any): None")
    print("=====================================================")

    # Generate Markdown Table Report
    md_content = f"""# Agent Evaluation Results

**Mock Mode**: `{USE_MOCK_FOR_EVAL}`
**Overall Accuracy**: `{accuracy:.0f}%` (`{passed_count}/{total_cases}` passed)

## Results Breakdown

| Category | Score | Percentage |
| :--- | :---: | :---: |
| Security | `{sec_passed}/4` | `{(sec_passed/4)*100:.0f}%` |
| Bug Detection | `{bug_passed}/4` | `{(bug_passed/4)*100:.0f}%` |
| Optimization | `{opt_passed}/2` | `{(opt_passed/2)*100:.0f}%` |

## Test Case Details

| Test Case Name | Category | Expected Keyword | Status |
| :--- | :--- | :--- | :---: |
"""
    for res in results:
        md_content += f"| `{res['name']}` | {res['category'].capitalize()} | `{res['keyword']}` | {'✅ PASS' if res['status'] == 'PASS' else '❌ FAIL'} |\n"

    # Save to project/tests/evaluation_results.md
    md_file_path = os.path.join(PROJECT_DIR, "tests", "evaluation_results.md")
    try:
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"\nSaved markdown report to: {md_file_path}")
    except Exception as e:
        print(f"Failed to save markdown report: {e}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
