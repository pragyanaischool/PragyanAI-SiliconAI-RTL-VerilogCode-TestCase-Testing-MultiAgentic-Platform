"""
PragyanAI SiliconAI
Prompt Utilities

Loads version-controlled prompts from the prompts/ directory
and provides compact context helpers for LLM calls.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPTS_DIR = BASE_DIR / "prompts"


# ============================================================
# PROMPT FILES
# ============================================================

PROMPT_FILES = {
    "rtl_analysis": "rtl_analysis.txt",
    "verification_planning": "verification_planning.txt",
    "test_generation": "test_generation.txt",
    "testbench_generation": "testbench_generation.txt",
    "failure_analysis": "failure_analysis.txt",
    "red_team": "red_team.txt",
    "coverage_analysis": "coverage_analysis.txt",
    "mutation_testing": "mutation_testing.txt",
    "rtl_repair": "rtl_repair.txt",
}


# ============================================================
# LOAD PROMPT
# ============================================================

def load_prompt(name: str) -> str:
    """
    Load a prompt from the prompts/ directory.

    Parameters
    ----------
    name:
        Prompt key, e.g. "rtl_analysis".

    Returns
    -------
    str
        Prompt contents.
    """

    filename = PROMPT_FILES.get(name, name)

    path = PROMPTS_DIR / filename

    if not path.exists():
        return ""

    try:
        return path.read_text(
            encoding="utf-8"
        )
    except Exception:
        return ""


# ============================================================
# SAFE TEXT LIMITER
# ============================================================

def limit_text(
    text: Any,
    max_chars: int = 5000,
    keep: str = "tail",
) -> str:
    """
    Limit text sent to an LLM.

    This is important for:
    - simulation logs
    - compiler output
    - generated RTL history
    - agent traces
    - large testbenches

    Parameters
    ----------
    text:
        Any input that can be converted to text.

    max_chars:
        Maximum number of characters.

    keep:
        "head", "tail", or "both".
    """

    if text is None:
        return ""

    text = str(text)

    if len(text) <= max_chars:
        return text

    if max_chars < 100:
        return text[:max_chars]

    if keep == "head":
        return (
            text[:max_chars]
            + "\n...[TRUNCATED]..."
        )

    if keep == "both":
        half = max_chars // 2

        return (
            text[:half]
            + "\n...[TRUNCATED]...\n"
            + text[-half:]
        )

    # Default: tail.
    return (
        "...[TRUNCATED]...\n"
        + text[-max_chars:]
    )


# ============================================================
# COMPACT JSON
# ============================================================

def compact_json(
    data: Any,
    max_chars: int = 5000,
) -> str:
    """
    Convert Python data to compact JSON and limit its size.
    """

    try:
        text = json.dumps(
            data,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
    except Exception:
        text = str(data)

    return limit_text(
        text,
        max_chars=max_chars,
        keep="both",
    )


# ============================================================
# COMPACT LIST
# ============================================================

def compact_list(
    items: Optional[List[Any]],
    max_items: int = 10,
    item_chars: int = 500,
) -> List[str]:
    """
    Convert a list into a compact textual representation.
    """

    if not items:
        return []

    result = []

    for item in items[:max_items]:

        if isinstance(item, dict):
            text = compact_json(
                item,
                max_chars=item_chars,
            )
        else:
            text = str(item)

        result.append(
            limit_text(
                text,
                max_chars=item_chars,
            )
        )

    return result


# ============================================================
# COMPACT RTL
# ============================================================

def compact_rtl(
    rtl_code: str,
    max_chars: int = 30000,
) -> str:
    """
    Keep RTL within a reasonable LLM input size.

    RTL should generally be preserved from the beginning because
    module declarations and interfaces commonly occur there.
    """

    if not rtl_code:
        return ""

    return limit_text(
        rtl_code,
        max_chars=max_chars,
        keep="both",
    )


# ============================================================
# COMPACT SIMULATION LOG
# ============================================================

def compact_simulation_log(
    log: str,
    max_chars: int = 5000,
) -> str:
    """
    Compress simulation output before sending it to an LLM.
    """

    if not log:
        return ""

    lines = log.splitlines()

    important = []

    keywords = [
        "ERROR",
        "FAILED",
        "FAIL",
        "WARNING",
        "TEST_RESULT",
        "TEST_ERROR",
        "ASSERT",
        "FATAL",
        "MISMATCH",
        "EXPECTED",
        "ACTUAL",
    ]

    for line in lines:

        upper = line.upper()

        if any(
            keyword in upper
            for keyword in keywords
        ):
            important.append(line)

    if important:
        selected = "\n".join(important)

        return limit_text(
            selected,
            max_chars=max_chars,
            keep="both",
        )

    return limit_text(
        log,
        max_chars=max_chars,
        keep="tail",
    )


# ============================================================
# COMPACT FAILURE
# ============================================================

def compact_failure(
    failure: Optional[Dict[str, Any]],
    max_chars: int = 4000,
) -> str:
    """
    Create a compact failure-analysis context.
    """

    if not failure:
        return "No previous failure analysis available."

    important_fields = [
        "test_id",
        "classification",
        "root_cause",
        "confidence",
        "severity",
        "failure_type",
        "failing_signal",
        "failing_cycle",
        "expected",
        "actual",
        "suspected_module",
        "suspected_lines",
        "likely_source",
        "recommended_action",
        "repair_rtl",
        "regenerate_testbench",
    ]

    compact = {}

    for field in important_fields:

        if field in failure:
            compact[field] = failure[field]

    return compact_json(
        compact,
        max_chars=max_chars,
    )


# ============================================================
# COMPACT PLAN
# ============================================================

def compact_plan(
    plan: Optional[Dict[str, Any]],
    max_chars: int = 5000,
) -> str:
    """
    Reduce verification plan to fields useful for
    downstream test generation.
    """

    if not plan:
        return "No verification plan available."

    fields = [
        "objective",
        "requirements",
        "functional_areas",
        "directed_tests",
        "random_tests",
        "corner_tests",
        "negative_tests",
        "reset_strategy",
        "clock_strategy",
        "assertion_targets",
        "coverage_targets",
        "priority_tests",
        "completion_criteria",
    ]

    compact = {}

    for field in fields:

        if field in plan:
            value = plan[field]

            if isinstance(value, list):
                value = value[:10]

            compact[field] = value

    return compact_json(
        compact,
        max_chars=max_chars,
    )


# ============================================================
# COMPACT RTL ANALYSIS
# ============================================================

def compact_rtl_analysis(
    analysis: Optional[Dict[str, Any]],
    max_chars: int = 5000,
) -> str:
    """
    Reduce RTL analysis to verification-relevant information.
    """

    if not analysis:
        return "No RTL analysis available."

    fields = [
        "module_name",
        "language",
        "inputs",
        "outputs",
        "clocks",
        "resets",
        "registers",
        "state_elements",
        "state_machine",
        "states",
        "interfaces",
        "protocols",
        "memory_elements",
        "corner_cases",
        "potential_risks",
        "verification_points",
        "summary",
    ]

    compact = {}

    for field in fields:

        if field in analysis:
            value = analysis[field]

            if isinstance(value, list):
                value = value[:15]

            compact[field] = value

    return compact_json(
        compact,
        max_chars=max_chars,
    )


# ============================================================
# COMPACT TEST SCENARIOS
# ============================================================

def compact_test_scenarios(
    tests: Optional[List[Dict[str, Any]]],
    max_items: int = 10,
    max_chars: int = 6000,
) -> str:
    """
    Compact generated test scenarios before testbench generation.
    """

    if not tests:
        return "No test scenarios available."

    selected = []

    for test in tests[:max_items]:

        selected.append(
            {
                "test_id": test.get("test_id", ""),
                "name": test.get("name", ""),
                "description": test.get("description", ""),
                "category": test.get("category", ""),
                "priority": test.get("priority", ""),
                "inputs": test.get("inputs", {}),
                "sequence": test.get("sequence", [])[:10],
                "expected_behavior": test.get(
                    "expected_behavior",
                    "",
                ),
                "requirement_ids": test.get(
                    "requirement_ids",
                    [],
                ),
            }
        )

    return compact_json(
        selected,
        max_chars=max_chars,
    )


# ============================================================
# COMPACT RED TEAM SCENARIOS
# ============================================================

def compact_red_team(
    scenarios: Optional[List[Dict[str, Any]]],
    max_items: int = 8,
    max_chars: int = 5000,
) -> str:
    """
    Compact adversarial scenarios.
    """

    if not scenarios:
        return "No red-team scenarios available."

    selected = []

    for scenario in scenarios[:max_items]:

        selected.append(
            {
                "scenario_id": scenario.get(
                    "scenario_id",
                    "",
                ),
                "name": scenario.get(
                    "name",
                    "",
                ),
                "attack_type": scenario.get(
                    "attack_type",
                    "",
                ),
                "description": scenario.get(
                    "description",
                    "",
                ),
                "priority": scenario.get(
                    "priority",
                    "",
                ),
                "target_signal": scenario.get(
                    "target_signal",
                    "",
                ),
                "expected_failure": scenario.get(
                    "expected_failure",
                    "",
                ),
            }
        )

    return compact_json(
        selected,
        max_chars=max_chars,
    )


# ============================================================
# COMPACT COVERAGE
# ============================================================

def compact_coverage(
    coverage: Optional[Dict[str, Any]],
    max_chars: int = 5000,
) -> str:
    """
    Compact coverage information for agents.
    """

    if not coverage:
        return "No coverage data available."

    fields = [
        "line",
        "branch",
        "toggle",
        "fsm",
        "functional",
        "assertion",
        "mutation",
        "overall",
        "target",
        "closure_status",
        "gaps",
        "recommended_tests",
    ]

    compact = {}

    for field in fields:

        if field in coverage:

            value = coverage[field]

            if field == "gaps" and isinstance(value, list):
                value = value[:10]

            if field == "recommended_tests" and isinstance(
                value,
                list,
            ):
                value = value[:10]

            compact[field] = value

    return compact_json(
        compact,
        max_chars=max_chars,
    )


# ============================================================
# BUILD AGENT CONTEXT
# ============================================================

def build_agent_context(
    *,
    specification: str = "",
    rtl_code: str = "",
    rtl_analysis: Optional[Dict[str, Any]] = None,
    verification_plan: Optional[Dict[str, Any]] = None,
    tests: Optional[List[Dict[str, Any]]] = None,
    red_team_scenarios: Optional[List[Dict[str, Any]]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    failure_analysis: Optional[Dict[str, Any]] = None,
    simulation_output: str = "",
    max_rtl_chars: int = 30000,
) -> Dict[str, str]:
    """
    Build a compact context dictionary for downstream agents.

    The goal is to avoid repeatedly sending the entire state,
    logs, history, and generated artifacts to the LLM.
    """

    return {
        "specification": limit_text(
            specification,
            max_chars=8000,
            keep="both",
        ),

        "rtl_code": compact_rtl(
            rtl_code,
            max_chars=max_rtl_chars,
        ),

        "rtl_analysis": compact_rtl_analysis(
            rtl_analysis,
            max_chars=5000,
        ),

        "verification_plan": compact_plan(
            verification_plan,
            max_chars=5000,
        ),

        "tests": compact_test_scenarios(
            tests,
            max_items=10,
            max_chars=6000,
        ),

        "red_team": compact_red_team(
            red_team_scenarios,
            max_items=8,
            max_chars=5000,
        ),

        "coverage": compact_coverage(
            coverage,
            max_chars=5000,
        ),

        "failure_analysis": compact_failure(
            failure_analysis,
            max_chars=4000,
        ),

        "simulation_output": compact_simulation_log(
            simulation_output,
            max_chars=5000,
        ),
    }


# ============================================================
# PROMPT + CONTEXT
# ============================================================

def build_prompt(
    prompt_name: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Load a prompt and append compact context.

    Parameters
    ----------
    prompt_name:
        Name of prompt in PROMPT_FILES.

    context:
        Dictionary of context values.

    Returns
    -------
    str
        Final LLM prompt.
    """

    system_prompt = load_prompt(prompt_name)

    if not system_prompt:
        system_prompt = (
            "You are an expert semiconductor RTL verification "
            "engineer. Analyze the supplied information carefully "
            "and return only the requested output."
        )

    if not context:
        return system_prompt

    context_text = []

    for key, value in context.items():

        if value is None:
            continue

        if isinstance(value, (dict, list)):
            value = compact_json(
                value,
                max_chars=5000,
            )

        else:
            value = str(value)

        context_text.append(
            f"\n--- {key.upper()} ---\n"
            f"{value}"
        )

    return (
        system_prompt
        + "\n\n"
        + "\n".join(context_text)
    )


# ============================================================
# SAFE LLM ERROR CONTEXT
# ============================================================

def compact_llm_error(
    error: Exception,
    max_chars: int = 2000,
) -> str:
    """
    Produce a safe compact LLM error string.

    Prevents huge exception payloads from being propagated
    through LangGraph state.
    """

    return limit_text(
        str(error),
        max_chars=max_chars,
        keep="tail",
    )
