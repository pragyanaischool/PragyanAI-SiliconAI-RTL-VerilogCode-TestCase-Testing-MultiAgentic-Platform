"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

LangGraph routing logic.
"""

from __future__ import annotations

from typing import Any, Dict


def _normalize_status(
    value: Any,
) -> str:

    if value is None:
        return "UNKNOWN"

    return str(value).strip().upper()


# ---------------------------------------------------------------------
# Simulation Router
# ---------------------------------------------------------------------

def route_after_simulation(
    state: Dict[str, Any],
) -> str:
    """
    Route workflow after deterministic simulation.

    Possible destinations:

    - coverage
    - failure_analysis
    - repair
    - end
    """

    if state.get("simulation_passed") is True:

        return "coverage"

    iteration = int(
        state.get(
            "iteration",
            0,
        )
    )

    max_iterations = int(
        state.get(
            "max_iterations",
            3,
        )
    )

    if iteration >= max_iterations:

        return "failure_analysis"

    return "failure_analysis"


# ---------------------------------------------------------------------
# Failure Analysis Router
# ---------------------------------------------------------------------

def route_after_failure_analysis(
    state: Dict[str, Any],
) -> str:
    """
    Decide what to do after failure analysis.
    """

    analysis = state.get(
        "failure_analysis",
        {},
    )

    if not isinstance(
        analysis,
        dict,
    ):
        return "repair"

    classification = _normalize_status(
        analysis.get(
            "classification",
            "",
        )
    )

    # Testbench-related problems should regenerate
    # the testbench instead of repairing RTL.

    if classification in {
        "TESTBENCH_BUG",
        "INCORRECT_EXPECTED_VALUE",
    }:

        return "test_generation"

    if classification in {
        "SPEC_AMBIGUITY",
        "ENVIRONMENT_SETUP",
    }:

        return "test_generation"

    # RTL-related failure

    if classification in {
        "RTL_BUG",
        "TIMING_ISSUE",
        "RESET_ISSUE",
        "PROTOCOL_ISSUE",
        "WIDTH_SIGN_ISSUE",
        "STATE_TRANSITION_ISSUE",
        "UNKNOWN",
        "",
    }:

        return "repair"

    return "repair"


# ---------------------------------------------------------------------
# Coverage Router
# ---------------------------------------------------------------------

def route_after_coverage(
    state: Dict[str, Any],
) -> str:
    """
    Decide whether verification is closed.

    Possible destinations:

    - red_team
    - mutation
    - test_generation
    - judge
    """

    coverage = state.get(
        "coverage",
        {},
    )

    if not isinstance(
        coverage,
        dict,
    ):
        return "test_generation"

    overall = float(
        coverage.get(
            "overall",
            0,
        )
    )

    gaps = coverage.get(
        "gaps",
        [],
    )

    # Continue targeted testing if meaningful gaps remain.

    if gaps and overall < 95.0:

        return "test_generation"

    # Move toward adversarial verification.

    return "red_team"


# ---------------------------------------------------------------------
# Judge Router
# ---------------------------------------------------------------------

def route_after_judge(
    state: Dict[str, Any],
) -> str:
    """
    Final routing decision.
    """

    judge = state.get(
        "judge_result",
        {},
    )

    if isinstance(
        judge,
        dict,
    ):

        verdict = _normalize_status(
            judge.get(
                "verdict",
                "",
            )
        )

        if verdict in {
            "PASS",
            "PASSED",
            "VERIFIED",
            "SIGNOFF",
        }:

            return "end"

    score = float(
        state.get(
            "verification_score",
            0,
        )
    )

    failed_tests = [
        test
        for test in state.get(
            "tests",
            [],
        )
        if _normalize_status(
            test.get("status")
        ) == "FAILED"
    ]

    if score >= 90 and not failed_tests:

        return "end"

    return "test_generation"
