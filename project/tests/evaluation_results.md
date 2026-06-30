# Agent Evaluation Results

**Mock Mode**: `True`
**Overall Accuracy**: `100%` (`10/10` passed)

## Results Breakdown

| Category | Score | Percentage |
| :--- | :---: | :---: |
| Security | `4/4` | `100%` |
| Bug Detection | `4/4` | `100%` |
| Optimization | `2/2` | `100%` |

## Test Case Details

| Test Case Name | Category | Expected Keyword | Status |
| :--- | :--- | :--- | :---: |
| `security_sql_injection` | Security | `injection` | ✅ PASS |
| `security_hardcoded_secrets` | Security | `secret` | ✅ PASS |
| `security_unsafe_eval` | Security | `eval` | ✅ PASS |
| `security_weak_password` | Security | `weak` | ✅ PASS |
| `bug_division_by_zero` | Bug | `zero` | ✅ PASS |
| `bug_none_dereference` | Bug | `none` | ✅ PASS |
| `bug_off_by_one` | Bug | `index` | ✅ PASS |
| `bug_unhandled_exception` | Bug | `exception` | ✅ PASS |
| `optimization_inefficient_loop` | Optimization | `inefficient` | ✅ PASS |
| `optimization_redundant_recursion` | Optimization | `recursive` | ✅ PASS |
