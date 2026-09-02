"""
PragyanAI SiliconAI
Verification Workflow State

Shared state used by all LangGraph verification agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class VerificationState(TypedDict, total=False):
    """
    Shared state passed between all verification agents.

    All fields are optional so individual agents can return partial
    state updates without requiring every field to exist.
    """

    # ================================================================
    # INPUT
    # ================================================================

    prompt: str
    specification: str

    # ================================================================
    # RTL
    # ================================================================

    rtl_code: str
    rtl_version: int
    rtl_history: List[Dict[str, Any]]

    rtl_analysis: Dict[str, Any]

    # ================================================================
    # VERIFICATION PLAN
    # ================================================================

    verification_plan: Dict[str, Any]

    # ================================================================
    # TEST GENERATION
    # ================================================================

    generated_tests: List[Dict[str, Any]]
    tests: List[Dict[str, Any]]

    # ================================================================
    # TESTBENCH
    # ================================================================

    testbench: str
    test_code: str

    # ================================================================
    # SIMULATION
    # ================================================================

    run_output: str
    simulation_output: str
    compile_output: str

    compile_error: str
    simulation_error: str

    simulation_passed: bool

    # ================================================================
    # FAILURE ANALYSIS
    # ================================================================

    failure_analysis: Dict[str, Any]
    root_cause: str

    # ================================================================
    # COVERAGE
    # ================================================================

    coverage: Dict[str, Any]
    coverage_gaps: List[Dict[str, Any]]

    # ================================================================
    # RED TEAM
    # ================================================================

    red_team_scenarios: List[Dict[str, Any]]

    # ================================================================
    # MUTATION
    # ================================================================

    mutations: List[Dict[str, Any]]
    mutation_score: float

    # ================================================================
    # FORMAL
    # ================================================================

    formal_result: Dict[str, Any]

    # ================================================================
    # DEBUG / REPAIR
    # ================================================================

    bug_location: Dict[str, Any]

    repair_proposal: Dict[str, Any]
    repaired_rtl: str

    # ================================================================
    # FINAL JUDGEMENT
    # ================================================================

    verification_score: float
    judge_result: Dict[str, Any]

    # ================================================================
    # AGENT OBSERVABILITY
    # ================================================================

    agent_log: List[Dict[str, Any]]
    agent_trace: List[Dict[str, Any]]

    # ================================================================
    # ITERATION CONTROL
    # ================================================================

    iteration: int
    max_iterations: int

    # ================================================================
    # WORKFLOW STATUS
    # ================================================================

    status: str
    run_id: str
    run_dir: str

    next_action: str
    retry_required: bool
    stop_reason: str

    # ================================================================
    # OPTIONAL FEATURE FLAGS
    # ================================================================

    run_mutation: bool
    run_formal: bool

    # ================================================================
    # MESSAGES
    # ================================================================

    messages: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]


def create_initial_state(
    *,
    specification: str = "",
    rtl_code: str = "",
    prompt: str = "",
    max_iterations: int = 3,
    run_mutation: bool = True,
    run_formal: bool = True,
    run_id: str = "",
    run_dir: str = "",
) -> VerificationState:
    """
    Create a clean initial VerificationState.

    This helper is useful for main_app.py and tests.
    """

    return VerificationState(
        prompt=prompt,
        specification=specification,
        rtl_code=rtl_code,

        rtl_version=1,
        rtl_history=[],
        rtl_analysis={},

        verification_plan={},

        generated_tests=[],
        tests=[],

        testbench="",
        test_code="",

        run_output="",
        simulation_output="",
        compile_output="",

        compile_error="",
        simulation_error="",

        simulation_passed=False,

        failure_analysis={},
        root_cause="",

        coverage={},
        coverage_gaps=[],

        red_team_scenarios=[],

        mutations=[],
        mutation_score=0.0,

        formal_result={},

        bug_location={},

        repair_proposal={},
        repaired_rtl="",

        verification_score=0.0,
        judge_result={},

        agent_log=[],
        agent_trace=[],

        iteration=0,
        max_iterations=max(1, int(max_iterations)),

        status="READY",
        run_id=run_id,
        run_dir=run_dir,

        next_action="rtl_analysis",
        retry_required=False,
        stop_reason="",

        run_mutation=bool(run_mutation),
        run_formal=bool(run_formal),

        messages=[],
        warnings=[],
        errors=[],
    )


def state_to_dict(
    state: VerificationState | Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Convert state into a normal dictionary.

    Useful for logging, JSON serialization and UI display.
    """

    if state is None:
        return {}

    if isinstance(state, dict):
        return dict(state)

    try:
        return dict(state)
    except Exception:
        return {}


def get_iteration(
    state: VerificationState | Dict[str, Any] | None,
) -> int:
    """Return current workflow iteration safely."""

    data = state_to_dict(state)

    try:
        return int(data.get("iteration", 0))
    except Exception:
        return 0


def get_max_iterations(
    state: VerificationState | Dict[str, Any] | None,
    default: int = 3,
) -> int:
    """Return configured maximum iterations safely."""

    data = state_to_dict(state)

    try:
        value = int(data.get("max_iterations", default))
    except Exception:
        value = default

    return max(1, value)


def iteration_limit_reached(
    state: VerificationState | Dict[str, Any] | None,
) -> bool:
    """Return True if workflow iteration budget has been reached."""

    return get_iteration(state) >= get_max_iterations(state)


def increment_iteration(
    state: VerificationState | Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return a state update that increments the iteration counter.
    """

    current = get_iteration(state)
    maximum = get_max_iterations(state)

    return {
        "iteration": min(current + 1, maximum)
    }


def add_error(
    state: VerificationState | Dict[str, Any],
    message: str,
) -> Dict[str, Any]:
    """Return a state update with an appended error."""

    data = state_to_dict(state)

    errors = list(data.get("errors", []))
    errors.append(str(message))

    return {
        "errors": errors,
        "status": "ERROR",
    }


def add_warning(
    state: VerificationState | Dict[str, Any],
    message: str,
) -> Dict[str, Any]:
    """Return a state update with an appended warning."""

    data = state_to_dict(state)

    warnings = list(data.get("warnings", []))
    warnings.append(str(message))

    return {
        "warnings": warnings,
    }


__all__ = [
    "VerificationState",
    "create_initial_state",
    "state_to_dict",
    "get_iteration",
    "get_max_iterations",
    "iteration_limit_reached",
    "increment_iteration",
    "add_error",
    "add_warning",
]

