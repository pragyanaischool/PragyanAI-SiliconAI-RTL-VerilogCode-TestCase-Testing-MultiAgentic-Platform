"""
PragyanAI SiliconAI
Agentic RTL Verification Router

IMPORTANT
---------
ALL workflow routing decisions live in this file.

graph/workflow.py only connects LangGraph nodes to these functions.

DO NOT import graph.router from graph.router.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# =============================================================================
# Router constants
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
# Helpers
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
            "on",
            "pass",
            "passed",
        }:
            return True

        if value in {
            "false",
            "0",
            "no",
            "off",
            "fail",
            "failed",
        }:
            return False

    return bool(value)


def _iteration(
    state: Dict[str, Any],
) -> int:

    return max(
        0,
        _safe_int(
            state.get("iteration", 0),
            0,
        ),
    )


def _max_iterations(
    state: Dict[str, Any],
) -> int:

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
    state: Dict[str, Any],
) -> bool:

    return (
        _iteration(state)
        >= _max_iterations(state)
    )


def _normalize_verdict(
    value: Any,
) -> str:

    if value is None:
        return "UNKNOWN"

    value = str(value).strip().upper()

    if value in {
        "PASS",
        "PASSED",
        "SUCCESS",
        "VERIFIED",
        "VERIFICATION PASSED",
    }:
        return "PASS"

    if value in {
        "FAIL",
        "FAILED",
        "ERROR",
        "REJECTED",
        "VERIFICATION FAILED",
    }:
        return "FAIL"

    if value in {
        "NEED_MORE",
        "NEED MORE",
        "RETRY",
        "RETRY_REQUIRED",
        "CONTINUE",
        "INCOMPLETE",
    }:
        return "NEED_MORE"

    return "UNKNOWN"


def _get_judge_verdict(
    state: Dict[str, Any],
) -> str:

    for key in (
        "final_verdict",
        "verdict",
    ):

        value = state.get(key)

        if value:

            verdict = _normalize_verdict(
                value
            )

            if verdict != "UNKNOWN":
                return verdict

    for container_key in (
        "judge_result",
        "judge",
    ):

        result = state.get(
            container_key
        )

        if not isinstance(result, dict):
            continue

        for key in (
            "verdict",
            "final_verdict",
            "status",
            "result",
        ):

            verdict = _normalize_verdict(
                result.get(key)
            )

            if verdict != "UNKNOWN":
                return verdict

    return "UNKNOWN"


def _coverage_score(
    state: Dict[str, Any],
) -> float:

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

    coverage = state.get("coverage")

    if isinstance(coverage, dict):

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


def _has_coverage_gaps(
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


def _mutation_enabled(
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


def _formal_enabled(
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


def _failure_text(
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

        if isinstance(value, dict):

            parts.extend(
                str(v)
                for v in value.values()
            )

        elif value:

            parts.append(
                str(value)
            )

    return " ".join(parts).lower()


def _rtl_failure(
    state: Dict[str, Any],
) -> bool:

    text = _failure_text(state)

    rtl_keywords = (
        "rtl",
        "design bug",
        "design error",
        "functional bug",
        "functional error",
        "wrong output",
        "incorrect output",
        "wrong behavior",
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

    testbench_keywords = (
        "testbench",
        "test bench",
        "stimulus",
        "checker",
        "expected value",
        "verification environment",
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

    return False


def _repair_changed_rtl(
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
# Simulation
# =============================================================================

def route_after_simulation(
    state: Dict[str, Any],
) -> str:
    """
    Simulation result:

        PASS -> Coverage

        FAIL -> Failure Analysis
    """

    if not isinstance(
        state,
        dict,
    ):
        return FAILURE_ANALYSIS

    passed = state.get(
        "simulation_passed"
    )

    if passed is None:
        passed = state.get(
            "test_passed"
        )

    if passed is None:

        result = state.get(
            "simulation_result"
        )

        if isinstance(
            result,
            dict,
        ):

            passed = result.get(
                "passed",
                result.get(
                    "success",
                    False,
                ),
            )

    if _safe_bool(
        passed,
        False,
    ):
        return COVERAGE

    return FAILURE_ANALYSIS


# =============================================================================
# Failure analysis
# =============================================================================

def route_after_failure(
    state: Dict[str, Any],
) -> str:
    """
    Failure:

        RTL problem -> RTL Repair

        Otherwise -> Test Generation

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

    if _rtl_failure(
        state
    ):
        return RTL_REPAIR

    return TEST_GENERATION


# =============================================================================
# Repair
# =============================================================================

def route_after_repair(
    state: Dict[str, Any],
) -> str:
    """
    Repair:

        Changed RTL -> Bug Localization

        No changed RTL -> Test Generation

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

    if _repair_changed_rtl(
        state
    ):
        return BUG_LOCALIZATION

    return TEST_GENERATION


# =============================================================================
# Bug localization
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
# Coverage
# =============================================================================

def route_after_coverage(
    state: Dict[str, Any],
) -> str:
    """
    Coverage:

        insufficient -> Test Generation

        sufficient -> Red Team

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

    score = _coverage_score(
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
        _has_coverage_gaps(state)
        or score < target
    ):
        return TEST_GENERATION

    return RED_TEAM


# =============================================================================
# Red team
# =============================================================================

def route_after_red_team(
    state: Dict[str, Any],
) -> str:
    """
    Red Team:

        mutation enabled -> Mutation

        formal enabled -> Formal

        otherwise -> Judge
    """

    if not isinstance(
        state,
        dict,
    ):
        return JUDGE

    if _mutation_enabled(
        state
    ):
        return MUTATION

    if _formal_enabled(
        state
    ):
        return FORMAL

    return JUDGE


# =============================================================================
# Mutation
# =============================================================================

def route_after_mutation(
    state: Dict[str, Any],
) -> str:

    if not isinstance(
        state,
        dict,
    ):
        return JUDGE

    if _formal_enabled(
        state
    ):
        return FORMAL

    return JUDGE


# =============================================================================
# Formal
# =============================================================================

def route_after_formal(
    state: Dict[str, Any],
) -> str:

    return JUDGE


# =============================================================================
# Judge
# =============================================================================

def route_after_judge(
    state: Dict[str, Any],
) -> str:
    """
    Judge:

        PASS -> END

        FAIL + RTL problem -> RTL Repair

        FAIL + verification problem -> Test Generation

        NEED_MORE -> Test Generation

        budget exhausted -> END
    """

    if not isinstance(
        state,
        dict,
    ):
        return END

    verdict = _get_judge_verdict(
        state
    )

    if verdict == "PASS":
        return END

    if iteration_limit_reached(
        state
    ):
        return END

    if verdict == "FAIL":

        if _rtl_failure(
            state
        ):
            return RTL_REPAIR

        return TEST_GENERATION

    if verdict == "NEED_MORE":
        return TEST_GENERATION

    return TEST_GENERATION


# =============================================================================
# Generic helpers
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

    return _get_judge_verdict(
        state
    )


# =============================================================================
# Compatibility aliases
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
# Public exports
# =============================================================================

__all__ = [
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

    "iteration_limit_reached",

    "route_after_simulation",
    "route_after_failure",
    "route_after_repair",
    "route_after_bug_localization",
    "route_after_coverage",
    "route_after_red_team",
    "route_after_mutation",
    "route_after_formal",
    "route_after_judge",

    "route_simulation",
    "route_failure",
    "route_repair",
    "route_bug_localization",
    "route_coverage",
    "route_red_team",
    "route_mutation",
    "route_formal",
    "route_judge",

    "should_continue",
    "get_final_verdict",
]

