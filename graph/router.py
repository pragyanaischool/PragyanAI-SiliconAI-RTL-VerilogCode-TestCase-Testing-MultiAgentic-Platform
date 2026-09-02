"""
PragyanAI SiliconAI
Verification Workflow Routing

All LangGraph conditional routing decisions are centralized here.

Important design principle:
routers return simple string route names only.

They do not execute agents.
They do not mutate state.
They do not call the LLM.
"""

from __future__ import annotations

from typing import Any, Dict


# =====================================================================
# ROUTE CONSTANTS
# =====================================================================

END = "end"

TEST_GENERATION = "test_generation"
TESTBENCH_GENERATION = "testbench_generation"
SIMULATION = "simulation"

FAILURE_ANALYSIS = "failure_analysis"

RTL_REPAIR = "rtl_repair"
BUG_LOCALIZATION = "bug_localization"

COVERAGE = "coverage"
RED_TEAM = "red_team"

MUTATION = "mutation"
FORMAL = "formal"

JUDGE = "judge"


# =====================================================================
# HELPERS
# =====================================================================

def _state(state: Any) -> Dict[str, Any]:
    """Safely convert LangGraph state to a dictionary."""

    if state is None:
        return {}

    if isinstance(state, dict):
        return dict(state)

    try:
        return dict(state)
    except Exception:
        return {}


def _string(value: Any) -> str:
    """Normalize a value to lowercase string."""

    if value is None:
        return ""

    return str(value).strip().lower()


def _bool(value: Any) -> bool:
    """Safely normalize boolean-like values."""

    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = _string(value)

    return text in {
        "true",
        "1",
        "yes",
        "y",
        "pass",
        "passed",
        "success",
        "successful",
    }


def _iteration(state: Any) -> int:
    """Return current iteration."""

    data = _state(state)

    try:
        return int(data.get("iteration", 0))
    except Exception:
        return 0


def _max_iterations(state: Any) -> int:
    """Return maximum iterations."""

    data = _state(state)

    try:
        return max(1, int(data.get("max_iterations", 3)))
    except Exception:
        return 3


def _budget_exhausted(state: Any) -> bool:
    """Return True when iteration budget has been reached."""

    return _iteration(state) >= _max_iterations(state)


def _get_nested(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """Read nested dictionaries safely."""

    current: Any = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


# =====================================================================
# SIMULATION ROUTER
# =====================================================================

def route_after_simulation(
    state: Dict[str, Any],
) -> str:
    """
    Decide what happens after simulation.

    PASS:
        coverage

    FAIL:
        failure_analysis

    Compilation errors are treated as failures.
    """

    data = _state(state)

    simulation_passed = data.get("simulation_passed")

    if _bool(simulation_passed):
        return COVERAGE

    # Explicit compile/simulation errors are failures.
    compile_error = _string(data.get("compile_error"))
    simulation_error = _string(data.get("simulation_error"))

    if compile_error or simulation_error:
        return FAILURE_ANALYSIS

    # Inspect simulator result when boolean flag is unavailable.
    simulation_output = _string(
        data.get("simulation_output")
        or data.get("run_output")
    )

    if "test_result: pass" in simulation_output:
        return COVERAGE

    if "test_result=pass" in simulation_output:
        return COVERAGE

    if "passed" in simulation_output and "failed" not in simulation_output:
        return COVERAGE

    return FAILURE_ANALYSIS


# =====================================================================
# FAILURE ROUTER
# =====================================================================

def route_after_failure(
    state: Dict[str, Any],
) -> str:
    """
    Decide what to do after failure analysis.

    Testbench/spec/environment/compile problems:
        test_generation

    RTL-related problems:
        rtl_repair

    Unknown:
        test_generation

    If iteration budget is exhausted:
        end
    """

    data = _state(state)

    if _budget_exhausted(data):
        return END

    analysis = data.get("failure_analysis", {})

    if not isinstance(analysis, dict):
        analysis = {}

    category = _string(
        analysis.get("category")
        or analysis.get("failure_category")
        or data.get("root_cause")
    )

    action = _string(
        analysis.get("recommended_action")
        or analysis.get("action")
        or analysis.get("next_action")
    )

    # Explicit RTL repair request.
    if action in {
        "rtl_repair",
        "repair_rtl",
        "repair",
        "fix_rtl",
    }:
        return RTL_REPAIR

    # RTL-related failure categories.
    rtl_categories = {
        "rtl_bug",
        "reset_error",
        "fsm_error",
        "width_error",
        "protocol_error",
        "timing_issue",
        "rtl_failure",
        "design_bug",
        "logic_bug",
    }

    if category in rtl_categories:
        return RTL_REPAIR

    # Testbench/spec/environment failures should regenerate tests.
    test_categories = {
        "testbench_bug",
        "spec_ambiguity",
        "environment",
        "compilation_error",
        "compile_error",
        "unknown",
        "test_failure",
    }

    if category in test_categories:
        return TEST_GENERATION

    # Conservative default.
    return TEST_GENERATION


# =====================================================================
# REPAIR ROUTER
# =====================================================================

def route_after_repair(
    state: Dict[str, Any],
) -> str:
    """
    Decide what happens after RTL repair.

    Actual repaired RTL:
        bug_localization

    No actual RTL change:
        test_generation

    Budget exhausted:
        end
    """

    data = _state(state)

    if _budget_exhausted(data):
        return END

    original_rtl = str(data.get("rtl_code", "") or "")
    repaired_rtl = str(data.get("repaired_rtl", "") or "")

    proposal = data.get("repair_proposal", {})

    if not isinstance(proposal, dict):
        proposal = {}

    applied = _bool(
        proposal.get("applied")
        or proposal.get("repair_applied")
    )

    rtl_changed = (
        bool(repaired_rtl.strip())
        and repaired_rtl.strip() != original_rtl.strip()
    )

    if applied and rtl_changed:
        return BUG_LOCALIZATION

    if rtl_changed:
        return BUG_LOCALIZATION

    return TEST_GENERATION


# =====================================================================
# COVERAGE ROUTER
# =====================================================================

def route_after_coverage(
    state: Dict[str, Any],
) -> str:
    """
    Decide what happens after coverage analysis.

    Coverage below target:
        test_generation

    Coverage sufficient:
        red_team

    Budget exhausted:
        end

    Proxy coverage is deliberately accepted for development flow,
    but the final judge can still prevent production signoff.
    """

    data = _state(state)

    coverage = data.get("coverage", {})

    if not isinstance(coverage, dict):
        coverage = {}

    # -------------------------------------------------------------
    # Explicit gaps
    # -------------------------------------------------------------

    gaps = data.get("coverage_gaps", [])

    if isinstance(gaps, list) and len(gaps) > 0:
        if not _budget_exhausted(data):
            return TEST_GENERATION

    # -------------------------------------------------------------
    # Coverage score
    # -------------------------------------------------------------

    overall = coverage.get("overall")

    if overall is None:
        overall = coverage.get("overall_coverage")

    if overall is None:
        overall = coverage.get("score")

    try:
        overall_value = float(overall)
    except Exception:
        overall_value = 0.0

    # -------------------------------------------------------------
    # Target
    # -------------------------------------------------------------

    target = coverage.get("target", 95)

    try:
        target_value = float(target)
    except Exception:
        target_value = 95.0

    # -------------------------------------------------------------
    # Insufficient coverage
    # -------------------------------------------------------------

    if overall_value < target_value:
        if not _budget_exhausted(data):
            return TEST_GENERATION

        return END

    # -------------------------------------------------------------
    # Coverage target achieved
    # -------------------------------------------------------------

    return RED_TEAM


# =====================================================================
# RED TEAM ROUTER
# =====================================================================

def route_after_red_team(
    state: Dict[str, Any],
) -> str:
    """
    Red-team stage normally proceeds to mutation testing.
    """

    data = _state(state)

    if _budget_exhausted(data):
        return END

    return MUTATION


# =====================================================================
# MUTATION ROUTER
# =====================================================================

def route_after_mutation(
    state: Dict[str, Any],
) -> str:
    """
    Decide what happens after mutation testing.

    Formal verification enabled:
        formal

    Formal verification disabled:
        judge
    """

    data = _state(state)

    run_formal = data.get("run_formal", True)

    if _bool(run_formal):
        return FORMAL

    return JUDGE


# =====================================================================
# FORMAL ROUTER
# =====================================================================

def route_after_formal(
    state: Dict[str, Any],
) -> str:
    """
    Formal verification always feeds the independent judge.

    Even if formal tools are unavailable, the judge evaluates the
    formal_result status.
    """

    _ = _state(state)

    return JUDGE


# =====================================================================
# JUDGE ROUTER
# =====================================================================

def route_after_judge(
    state: Dict[str, Any],
) -> str:
    """
    Route based on independent verification judge.

    PASS:
        END

    FAIL:
        RTL_REPAIR for RTL-related failure
        otherwise TEST_GENERATION

    NEED_MORE_VERIFICATION:
        TEST_GENERATION

    Budget exhausted:
        END

    Never convert uncertainty into PASS.
    """

    data = _state(state)

    judge = data.get("judge_result", {})

    if not isinstance(judge, dict):
        judge = {}

    verdict = _string(
        judge.get("verdict")
        or judge.get("status")
        or judge.get("result")
    )

    # -------------------------------------------------------------
    # PASS
    # -------------------------------------------------------------

    if verdict in {
        "pass",
        "passed",
        "verified",
        "signoff",
        "signoff_ready",
    }:
        return END

    # -------------------------------------------------------------
    # Budget protection
    # -------------------------------------------------------------

    if _budget_exhausted(data):
        return END

    # -------------------------------------------------------------
    # FAIL
    # -------------------------------------------------------------

    if verdict in {
        "fail",
        "failed",
        "failure",
        "not_verified",
    }:

        failure_analysis = data.get(
            "failure_analysis",
            {},
        )

        if not isinstance(failure_analysis, dict):
            failure_analysis = {}

        category = _string(
            failure_analysis.get("category")
            or failure_analysis.get("failure_category")
            or judge.get("failure_category")
            or judge.get("root_cause")
        )

        rtl_categories = {
            "rtl_bug",
            "reset_error",
            "fsm_error",
            "width_error",
            "protocol_error",
            "timing_issue",
            "rtl_failure",
            "design_bug",
            "logic_bug",
        }

        if category in rtl_categories:
            return RTL_REPAIR

        return TEST_GENERATION

    # -------------------------------------------------------------
    # NEED MORE VERIFICATION
    # -------------------------------------------------------------

    if verdict in {
        "need_more_verification",
        "need_more",
        "uncertain",
        "inconclusive",
        "not_proven",
        "unknown",
        "",
    }:
        return TEST_GENERATION

    # -------------------------------------------------------------
    # Conservative default
    # -------------------------------------------------------------

    return TEST_GENERATION


# =====================================================================
# GENERIC HELPERS
# =====================================================================

def should_continue(
    state: Dict[str, Any],
) -> bool:
    """
    Return True when verification may continue.
    """

    return not _budget_exhausted(state)


def get_final_verdict(
    state: Dict[str, Any],
) -> str:
    """
    Return normalized final verdict.
    """

    data = _state(state)

    judge = data.get("judge_result", {})

    if not isinstance(judge, dict):
        judge = {}

    verdict = _string(
        judge.get("verdict")
        or judge.get("status")
        or data.get("status")
    )

    if verdict in {
        "pass",
        "passed",
        "verified",
        "signoff",
        "signoff_ready",
    }:
        return "PASS"

    if verdict in {
        "fail",
        "failed",
        "failure",
        "not_verified",
    }:
        return "FAIL"

    return "NEED_MORE_VERIFICATION"


# =====================================================================
# PUBLIC API
# =====================================================================

__all__ = [
    # Constants
    "END",
    "TEST_GENERATION",
    "TESTBENCH_GENERATION",
    "SIMULATION",
    "FAILURE_ANALYSIS",
    "RTL_REPAIR",
    "BUG_LOCALIZATION",
    "COVERAGE",
    "RED_TEAM",
    "MUTATION",
    "FORMAL",
    "JUDGE",

    # Routers
    "route_after_simulation",
    "route_after_failure",
    "route_after_repair",
    "route_after_coverage",
    "route_after_red_team",
    "route_after_mutation",
    "route_after_formal",
    "route_after_judge",

    # Helpers
    "should_continue",
    "get_final_verdict",
]

