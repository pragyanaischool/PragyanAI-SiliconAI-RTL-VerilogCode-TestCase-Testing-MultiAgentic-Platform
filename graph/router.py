"""
PragyanAI SiliconAI
Agentic RTL Verification Router

IMPORTANT
---------
This file is the SINGLE SOURCE OF TRUTH for workflow routing.

DO NOT import graph.router from this file.

graph/workflow.py:
    - creates LangGraph
    - registers nodes
    - connects conditional edges
    - delegates decisions to this file

graph/state.py:
    - defines shared VerificationState

This file:
    - decides where the workflow goes next
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# =============================================================================
# ROUTER CONSTANTS
# =============================================================================

END = "end"

RTL_ANALYSIS = "rtl_analysis"
PLANNING = "planning"

TEST_GENERATION = "test_generation"
TESTBENCH_GENERATION = "testbench_generation"
SIMULATION = "simulation"

FAILURE_ANALYSIS = "failure_analysis"
BUG_LOCALIZATION = "bug_localization"
RTL_REPAIR = "rtl_repair"

COVERAGE = "coverage"
RED_TEAM = "red_team"

MUTATION = "mutation"
FORMAL = "formal"
JUDGE = "judge"


# =============================================================================
# SAFE HELPERS
# =============================================================================

def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(
    value: Any,
    default: bool = False,
) -> bool:

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        value = value.strip().lower()

        if value in {
            "true",
            "1",
            "yes",
            "y",
            "on",
            "pass",
            "passed",
        }:
            return True

        if value in {
            "false",
            "0",
            "no",
            "n",
            "off",
            "fail",
            "failed",
        }:
            return False

    return bool(value)


# =============================================================================
# ITERATION
# =============================================================================

def get_iteration(
    state: Optional[Dict[str, Any]],
) -> int:

    if not state:
        return 0

    return max(
        0,
        _safe_int(
            state.get("iteration", 0),
            0,
        ),
    )


def get_max_iterations(
    state: Optional[Dict[str, Any]],
) -> int:

    if not state:
        return 3

    value = _safe_int(
        state.get(
            "max_iterations",
            3,
        ),
        3,
    )

    return max(
        1,
        min(10, value),
    )


def iteration_limit_reached(
    state: Optional[Dict[str, Any]],
) -> bool:

    return (
        get_iteration(state)
        >= get_max_iterations(state)
    )


# =============================================================================
# VERDICT
# =============================================================================

def normalize_verdict(
    value: Any,
) -> str:

    if value is None:
        return "UNKNOWN"

    text = str(value).strip().upper()

    if text in {
        "PASS",
        "PASSED",
        "SUCCESS",
        "VERIFIED",
        "VERIFICATION PASSED",
    }:
        return "PASS"

    if text in {
        "FAIL",
        "FAILED",
        "ERROR",
        "REJECT",
        "REJECTED",
        "VERIFICATION FAILED",
    }:
        return "FAIL"

    if text in {
        "NEED_MORE",
        "NEED MORE",
        "RETRY",
        "RETRY_REQUIRED",
        "CONTINUE",
        "INCOMPLETE",
    }:
        return "NEED_MORE"

    return "UNKNOWN"


def get_judge_verdict(
    state: Dict[str, Any],
) -> str:

    # -------------------------------------------------------------------------
    # Direct state fields
    # -------------------------------------------------------------------------

    for key in (
        "final_verdict",
        "verdict",
    ):

        value = state.get(key)

        if value:

            result = normalize_verdict(
                value
            )

            if result != "UNKNOWN":
                return result

    # -------------------------------------------------------------------------
    # judge_result
    # -------------------------------------------------------------------------

    for container_key in (
        "judge_result",
        "judge",
    ):

        result = state.get(
            container_key
        )

        if not isinstance(
            result,
            dict,
        ):
            continue

        for key in (
            "verdict",
            "final_verdict",
            "status",
            "result",
        ):

            verdict = normalize_verdict(
                result.get(key)
            )

            if verdict != "UNKNOWN":
                return verdict

    return "UNKNOWN"


# =============================================================================
# SIMULATION
# =============================================================================

def simulation_passed(
    state: Dict[str, Any],
) -> bool:

    # Primary field.
    if "simulation_passed" in state:

        return _safe_bool(
            state.get(
                "simulation_passed"
            ),
            False,
        )

    # Compatibility.
    if "test_passed" in state:

        return _safe_bool(
            state.get(
                "test_passed"
            ),
            False,
        )

    # Simulation result dictionary.
    result = state.get(
        "simulation_result"
    )

    if isinstance(
        result,
        dict,
    ):

        if "passed" in result:

            return _safe_bool(
                result.get("passed"),
                False,
            )

        if "success" in result:

            return _safe_bool(
                result.get("success"),
                False,
            )

    return False


# =============================================================================
# COVERAGE
# =============================================================================

def get_coverage_score(
    state: Dict[str, Any],
) -> float:

    # Direct fields.
    for key in (
        "coverage_percent",
        "coverage_score",
    ):

        value = state.get(key)

        if value is not None:

            return max(
                0.0,
                min(
                    100.0,
                    _safe_float(
                        value,
                        0.0,
                    ),
                ),
            )

    # Coverage dictionary.
    coverage = state.get(
        "coverage"
    )

    if isinstance(
        coverage,
        dict,
    ):

        for key in (
            "coverage_percent",
            "coverage_percentage",
            "percentage",
            "score",
        ):

            if key in coverage:

                return max(
                    0.0,
                    min(
                        100.0,
                        _safe_float(
                            coverage.get(key),
                            0.0,
                        ),
                    ),
                )

    return 0.0


def has_coverage_gaps(
    state: Dict[str, Any],
) -> bool:

    gaps = state.get(
        "coverage_gaps"
    )

    if gaps is None:
        return False

    if isinstance(
        gaps,
        (
            list,
            tuple,
            set,
            dict,
        ),
    ):
        return len(gaps) > 0

    return bool(gaps)


# =============================================================================
# FEATURE FLAGS
# =============================================================================

def mutation_enabled(
    state: Dict[str, Any],
) -> bool:

    if "run_mutation" in state:

        return _safe_bool(
            state.get(
                "run_mutation"
            ),
            False,
        )

    return _safe_bool(
        state.get(
            "enable_mutation"
        ),
        False,
    )


def formal_enabled(
    state: Dict[str, Any],
) -> bool:

    if "run_formal" in state:

        return _safe_bool(
            state.get(
                "run_formal"
            ),
            False,
        )

    return _safe_bool(
        state.get(
            "enable_formal"
        ),
        False,
    )


# =============================================================================
# FAILURE CLASSIFICATION
# =============================================================================

def get_failure_text(
    state: Dict[str, Any],
) -> str:

    parts = []

    for key in (
        "failure_type",
        "root_cause",
    ):

        value = state.get(key)

        if value:
            parts.append(
                str(value)
            )

    for key in (
        "failure_analysis",
        "failure",
    ):

        value = state.get(key)

        if isinstance(
            value,
            dict,
        ):

            parts.extend(
                str(v)
                for v in value.values()
            )

        elif value:

            parts.append(
                str(value)
            )

    return " ".join(
        parts
    ).lower()


def is_rtl_failure(
    state: Dict[str, Any],
) -> bool:

    text = get_failure_text(
        state
    )

    # -------------------------------------------------------------------------
    # Strong RTL indicators
    # -------------------------------------------------------------------------

    rtl_keywords = (
        "rtl",
        "design bug",
        "design error",
        "functional bug",
        "functional error",
        "wrong output",
        "incorrect output",
        "wrong behavior",
        "incorrect behavior",
        "register",
        "counter",
        "fsm",
        "state machine",
        "always_ff",
        "always_comb",
        "always block",
        "nonblocking",
        "blocking assignment",
        "reset logic",
        "clock logic",
        "overflow",
        "underflow",
        "protocol violation",
    )

    # -------------------------------------------------------------------------
    # Strong verification-environment indicators
    # -------------------------------------------------------------------------

    testbench_keywords = (
        "testbench",
        "test bench",
        "stimulus",
        "checker",
        "expected value",
        "verification environment",
        "test case",
    )

    if any(
        keyword in text
        for keyword in rtl_keywords
    ):
        return True

    if any(
        keyword in text
        for keyword in testbench_keywords
    ):
        return False

    # Conservative default:
    # do NOT modify RTL when the failure has not been classified.
    return False


# =============================================================================
# REPAIR CLASSIFICATION
# =============================================================================

def repair_changed_rtl(
    state: Dict[str, Any],
) -> bool:

    repaired = state.get(
        "repaired_rtl",
        "",
    )

    current = state.get(
        "rtl_code",
        "",
    )

    if not isinstance(
        repaired,
        str,
    ):
        repaired = ""

    if not isinstance(
        current,
        str,
    ):
        current = ""

    if not repaired.strip():
        return False

    if repaired.strip() != current.strip():
        return True

    return _safe_bool(
        state.get(
            "repair_applied"
        ),
        False,
    )


# =============================================================================
# ROUTE AFTER SIMULATION
# =============================================================================

def route_after_simulation(
    state: Dict[str, Any],
) -> str:
    """
    Simulation:

        PASS -> Coverage

        FAIL -> Failure Analysis
    """

    if not isinstance(
        state,
        dict,
    ):
        return FAILURE_ANALYSIS

    if simulation_passed(
        state
    ):
        return COVERAGE

    return FAILURE_ANALYSIS


# =============================================================================
# ROUTE AFTER FAILURE ANALYSIS
# =============================================================================

def route_after_failure(
    state: Dict[str, Any],
) -> str:
    """
    Failure Analysis:

        RTL failure -> RTL Repair

        Other failure -> Test Generation

        Iteration exhausted -> END
    """

    if not isinstance(
        state,
        dict,
    ):
        return END

    if iteration_limit_reached(
        state
    ):
        return END

    if is_rtl_failure(
        state
    ):
        return RTL_REPAIR

    return TEST_GENERATION


# =============================================================================
# ROUTE AFTER REPAIR
# =============================================================================

def route_after_repair(
    state: Dict[str, Any],
) -> str:
    """
    RTL Repair:

        Actual RTL change -> Bug Localization

        No RTL change -> Test Generation

        Budget exhausted -> END
    """

    if not isinstance(
        state,
        dict,
    ):
        return END

    if iteration_limit_reached(
        state
    ):
        return END

    if repair_changed_rtl(
        state
    ):
        return BUG_LOCALIZATION

    return TEST_GENERATION


# =============================================================================
# ROUTE AFTER BUG LOCALIZATION
# =============================================================================

def route_after_bug_localization(
    state: Dict[str, Any],
) -> str:

    if not isinstance(
        state,
        dict,
    ):
        return END

    if iteration_limit_reached(
        state
    ):
        return END

    return TEST_GENERATION


# =============================================================================
# ROUTE AFTER COVERAGE
# =============================================================================

def route_after_coverage(
    state: Dict[str, Any],
) -> str:
    """
    Coverage:

        below target / gaps -> Test Generation

        target achieved -> Red Team

        budget exhausted -> END
    """

    if not isinstance(
        state,
        dict,
    ):
        return END

    if iteration_limit_reached(
        state
    ):
        return END

    score = get_coverage_score(
        state
    )

    target = _safe_float(
        state.get(
            "coverage_target",
            95.0,
        ),
        95.0,
    )

    if (
        has_coverage_gaps(state)
        or score < target
    ):
        return TEST_GENERATION

    return RED_TEAM


# =============================================================================
# ROUTE AFTER RED TEAM
# =============================================================================

def route_after_red_team(
    state: Dict[str, Any],
) -> str:
    """
    Red Team:

        Mutation enabled -> Mutation

        Formal enabled -> Formal

        Otherwise -> Judge
    """

    if not isinstance(
        state,
        dict,
    ):
        return JUDGE

    if mutation_enabled(
        state
    ):
        return MUTATION

    if formal_enabled(
        state
    ):
        return FORMAL

    return JUDGE


# =============================================================================
# ROUTE AFTER MUTATION
# =============================================================================

def route_after_mutation(
    state: Dict[str, Any],
) -> str:
    """
    Mutation:

        Formal enabled -> Formal

        Otherwise -> Judge
    """

    if not isinstance(
        state,
        dict,
    ):
        return JUDGE

    if formal_enabled(
        state
    ):
        return FORMAL

    return JUDGE


# =============================================================================
# ROUTE AFTER FORMAL
# =============================================================================

def route_after_formal(
    state: Dict[str, Any],
) -> str:
    """
    Formal -> Judge
    """

    return JUDGE


# =============================================================================
# ROUTE AFTER JUDGE
# =============================================================================

def route_after_judge(
    state: Dict[str, Any],
) -> str:
    """
    Judge:

        PASS
          -> END

        FAIL + RTL issue
          -> RTL Repair

        FAIL + verification issue
          -> Test Generation

        NEED_MORE
          -> Test Generation

        Unknown
          -> Test Generation if budget remains
    """

    if not isinstance(
        state,
        dict,
    ):
        return END

    verdict = get_judge_verdict(
        state
    )

    # -------------------------------------------------------------------------
    # PASS
    # -------------------------------------------------------------------------

    if verdict == "PASS":
        return END

    # -------------------------------------------------------------------------
    # Iteration guard
    # -------------------------------------------------------------------------

    if iteration_limit_reached(
        state
    ):
        return END

    # -------------------------------------------------------------------------
    # FAIL
    # -------------------------------------------------------------------------

    if verdict == "FAIL":

        if is_rtl_failure(
            state
        ):
            return RTL_REPAIR

        return TEST_GENERATION

    # -------------------------------------------------------------------------
    # NEED MORE
    # -------------------------------------------------------------------------

    if verdict == "NEED_MORE":
        return TEST_GENERATION

    # -------------------------------------------------------------------------
    # UNKNOWN
    # -------------------------------------------------------------------------

    return TEST_GENERATION


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def should_continue(
    state: Optional[Dict[str, Any]],
) -> bool:

    if not state:
        return False

    if iteration_limit_reached(
        state
    ):
        return False

    status = str(
        state.get(
            "status",
            "",
        )
    ).lower()

    if status in {
        "error",
        "stopped",
    }:
        return False

    return True


def get_final_verdict(
    state: Optional[Dict[str, Any]],
) -> str:

    if not state:
        return "UNKNOWN"

    return get_judge_verdict(
        state
    )


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

route_simulation = route_after_simulation
route_failure = route_after_failure
route_repair = route_after_repair
route_bug_localization = route_after_bug_localization
route_coverage = route_after_coverage
route_red_team = route_after_red_team
route_mutation = route_after_mutation
route_formal = route_after_formal
route_judge = route_after_judge


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [

    # Constants
    "END",

    "RTL_ANALYSIS",
    "PLANNING",

    "TEST_GENERATION",
    "TESTBENCH_GENERATION",
    "SIMULATION",

    "FAILURE_ANALYSIS",
    "BUG_LOCALIZATION",
    "RTL_REPAIR",

    "COVERAGE",
    "RED_TEAM",

    "MUTATION",
    "FORMAL",
    "JUDGE",

    # Helpers
    "get_iteration",
    "get_max_iterations",
    "iteration_limit_reached",

    "normalize_verdict",
    "get_judge_verdict",

    "simulation_passed",

    "get_coverage_score",
    "has_coverage_gaps",

    "mutation_enabled",
    "formal_enabled",

    "get_failure_text",
    "is_rtl_failure",

    "repair_changed_rtl",

    # Routes
    "route_after_simulation",
    "route_after_failure",
    "route_after_repair",
    "route_after_bug_localization",
    "route_after_coverage",
    "route_after_red_team",
    "route_after_mutation",
    "route_after_formal",
    "route_after_judge",

    # Compatibility
    "route_simulation",
    "route_failure",
    "route_repair",
    "route_bug_localization",
    "route_coverage",
    "route_red_team",
    "route_mutation",
    "route_formal",
    "route_judge",

    # Generic
    "should_continue",
    "get_final_verdict",
]
