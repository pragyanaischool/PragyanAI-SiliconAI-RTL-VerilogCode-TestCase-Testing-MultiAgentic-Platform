# graph/state.py
"""
PragyanAI SiliconAI
Agentic RTL Verification Workflow State

Central state definition shared by:
    - graph.workflow
    - graph.router
    - all verification agents
    - Streamlit UI
    - reporting / logging

Design goals:
    1. Stable LangGraph-compatible TypedDict state.
    2. Backward-compatible field aliases.
    3. Defensive helper functions.
    4. No dependency on SymbiYosys.
    5. Safe handling of missing/partial agent outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


# ============================================================================
# Verification State
# ============================================================================

class VerificationState(TypedDict, total=False):
    """
    Shared state for the complete RTL verification workflow.

    All fields are optional so that individual LangGraph nodes can return
    partial state updates without causing TypedDict/runtime issues.
    """

    # ------------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------------

    prompt: str
    specification: str

    # Original aliases / compatibility
    user_prompt: str
    spec: str

    # ------------------------------------------------------------------------
    # RTL
    # ------------------------------------------------------------------------

    rtl_code: str
    rtl_version: int
    rtl_history: List[Dict[str, Any]]
    rtl_analysis: Dict[str, Any]

    # Compatibility aliases
    original_rtl: str
    repaired_rtl: str
    current_rtl: str

    # ------------------------------------------------------------------------
    # Verification planning
    # ------------------------------------------------------------------------

    verification_plan: Dict[str, Any]

    # Compatibility
    plan: Dict[str, Any]

    # ------------------------------------------------------------------------
    # Test generation
    # ------------------------------------------------------------------------

    generated_tests: List[Any]
    tests: List[Any]

    # Compatibility
    test_cases: List[Any]

    # ------------------------------------------------------------------------
    # Testbench generation
    # ------------------------------------------------------------------------

    testbench: str
    test_code: str

    # Compatibility
    testbench_code: str

    # ------------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------------

    run_output: str
    simulation_output: str
    compile_output: str

    compile_error: str
    simulation_error: str

    simulation_passed: bool

    # Compatibility / additional simulator information
    simulation_result: Dict[str, Any]
    simulator_result: Dict[str, Any]
    compile_passed: bool
    test_passed: bool

    # ------------------------------------------------------------------------
    # Failure analysis
    # ------------------------------------------------------------------------

    failure_analysis: Dict[str, Any]
    root_cause: str

    # Compatibility
    failure: Dict[str, Any]
    failure_type: str

    # ------------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------------

    coverage: Dict[str, Any]
    coverage_gaps: List[Any]

    # Compatibility
    coverage_report: Dict[str, Any]
    coverage_score: float
    coverage_percent: float

    # ------------------------------------------------------------------------
    # Red-team verification
    # ------------------------------------------------------------------------

    red_team_scenarios: List[Any]

    # Compatibility
    red_team_results: List[Any]

    # ------------------------------------------------------------------------
    # Mutation testing
    # ------------------------------------------------------------------------

    mutations: List[Any]
    mutation_score: float

    # Compatibility
    mutation_results: List[Any]
    mutation_report: Dict[str, Any]

    # ------------------------------------------------------------------------
    # Formal verification
    # ------------------------------------------------------------------------

    formal_result: Dict[str, Any]

    # Compatibility
    formal_results: Dict[str, Any]
    formal_passed: bool

    # ------------------------------------------------------------------------
    # Bug localization
    # ------------------------------------------------------------------------

    bug_location: Dict[str, Any]

    # Compatibility
    bug_locations: List[Any]
    localization_result: Dict[str, Any]

    # ------------------------------------------------------------------------
    # RTL repair
    # ------------------------------------------------------------------------

    repair_proposal: Dict[str, Any]
    repaired_rtl: str

    # Compatibility
    repair_result: Dict[str, Any]
    rtl_repair: Dict[str, Any]
    repair_applied: bool

    # ------------------------------------------------------------------------
    # Verification judge
    # ------------------------------------------------------------------------

    verification_score: float
    judge_result: Dict[str, Any]

    # Compatibility
    judge: Dict[str, Any]
    final_verdict: str
    verdict: str

    # ------------------------------------------------------------------------
    # Agent observability
    # ------------------------------------------------------------------------

    agent_log: List[Any]
    agent_trace: List[Any]

    # Compatibility
    logs: List[Any]
    trace: List[Any]

    # ------------------------------------------------------------------------
    # Iteration / workflow control
    # ------------------------------------------------------------------------

    iteration: int
    max_iterations: int

    status: str
    run_id: str
    run_dir: str

    next_action: str
    retry_required: bool
    stop_reason: str

    # ------------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------------

    run_mutation: bool
    run_formal: bool

    # Compatibility
    enable_mutation: bool
    enable_formal: bool

    # ------------------------------------------------------------------------
    # Messages / diagnostics
    # ------------------------------------------------------------------------

    messages: List[Any]
    warnings: List[str]
    errors: List[str]

    # Compatibility
    error: str


# ============================================================================
# Constants
# ============================================================================

DEFAULT_MAX_ITERATIONS = 3
MIN_ITERATIONS = 1
MAX_ITERATIONS = 10

DEFAULT_STATUS = "initialized"

STATUS_INITIALIZED = "initialized"
STATUS_RUNNING = "running"
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"
STATUS_STOPPED = "stopped"

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NEED_MORE = "NEED_MORE"
VERDICT_UNKNOWN = "UNKNOWN"


# ============================================================================
# Internal utility helpers
# ============================================================================

def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int without raising."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float without raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    """Convert a value to bool safely."""
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.strip().lower()

        if value_lower in {
            "true",
            "1",
            "yes",
            "y",
            "on",
            "pass",
            "passed",
        }:
            return True

        if value_lower in {
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


def _ensure_list(value: Any) -> List[Any]:
    """Return a value as a list."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


def _ensure_dict(value: Any) -> Dict[str, Any]:
    """Return a value as a dictionary."""
    if isinstance(value, dict):
        return value

    return {}


# ============================================================================
# State creation
# ============================================================================

def create_initial_state(
    rtl_code: str = "",
    specification: str = "",
    prompt: str = "",
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    run_mutation: bool = False,
    run_formal: bool = False,
    run_id: str = "",
    run_dir: str = "",
    **kwargs: Any,
) -> VerificationState:
    """
    Create a clean initial verification state.

    Parameters
    ----------
    rtl_code:
        Initial RTL source.

    specification:
        Functional/design specification.

    prompt:
        User request / verification prompt.

    max_iterations:
        Maximum number of repair/test-generation iterations.

    run_mutation:
        Enable mutation testing.

    run_formal:
        Enable optional formal verification.

    run_id:
        Optional workflow run identifier.

    run_dir:
        Optional runtime directory.

    Returns
    -------
    VerificationState
        Initialized LangGraph state.
    """

    # Clamp iteration budget.
    max_iterations = _safe_int(
        max_iterations,
        DEFAULT_MAX_ITERATIONS,
    )

    max_iterations = max(
        MIN_ITERATIONS,
        min(MAX_ITERATIONS, max_iterations),
    )

    rtl_code = rtl_code or ""
    specification = specification or ""
    prompt = prompt or ""

    state: VerificationState = {
        # Input
        "prompt": prompt,
        "specification": specification,
        "user_prompt": prompt,
        "spec": specification,

        # RTL
        "rtl_code": rtl_code,
        "original_rtl": rtl_code,
        "current_rtl": rtl_code,
        "rtl_version": 1 if rtl_code else 0,
        "rtl_history": [],
        "rtl_analysis": {},

        # Planning
        "verification_plan": {},
        "plan": {},

        # Tests
        "generated_tests": [],
        "tests": [],
        "test_cases": [],

        # Testbench
        "testbench": "",
        "test_code": "",
        "testbench_code": "",

        # Simulation
        "run_output": "",
        "simulation_output": "",
        "compile_output": "",
        "compile_error": "",
        "simulation_error": "",
        "simulation_passed": False,
        "simulation_result": {},
        "simulator_result": {},
        "compile_passed": False,
        "test_passed": False,

        # Failure
        "failure_analysis": {},
        "root_cause": "",
        "failure": {},
        "failure_type": "",

        # Coverage
        "coverage": {},
        "coverage_gaps": [],
        "coverage_report": {},
        "coverage_score": 0.0,
        "coverage_percent": 0.0,

        # Red team
        "red_team_scenarios": [],
        "red_team_results": [],

        # Mutation
        "mutations": [],
        "mutation_score": 0.0,
        "mutation_results": [],
        "mutation_report": {},

        # Formal
        "formal_result": {},
        "formal_results": {},
        "formal_passed": False,

        # Debug
        "bug_location": {},
        "bug_locations": [],
        "localization_result": {},

        # Repair
        "repair_proposal": {},
        "repaired_rtl": "",
        "repair_result": {},
        "rtl_repair": {},
        "repair_applied": False,

        # Judge
        "verification_score": 0.0,
        "judge_result": {},
        "judge": {},
        "final_verdict": VERDICT_UNKNOWN,
        "verdict": VERDICT_UNKNOWN,

        # Observability
        "agent_log": [],
        "agent_trace": [],
        "logs": [],
        "trace": [],

        # Iteration
        "iteration": 0,
        "max_iterations": max_iterations,

        # Runtime
        "status": STATUS_INITIALIZED,
        "run_id": run_id or "",
        "run_dir": run_dir or "",

        # Routing
        "next_action": "",
        "retry_required": False,
        "stop_reason": "",

        # Feature flags
        "run_mutation": _safe_bool(run_mutation),
        "run_formal": _safe_bool(run_formal),
        "enable_mutation": _safe_bool(run_mutation),
        "enable_formal": _safe_bool(run_formal),

        # Messages
        "messages": [],
        "warnings": [],
        "errors": [],
        "error": "",
    }

    # Preserve explicitly supplied extra state fields.
    for key, value in kwargs.items():
        state[key] = value  # type: ignore[literal-required]

    return state


# ============================================================================
# State conversion
# ============================================================================

def state_to_dict(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert a LangGraph state into a normal dictionary.

    This intentionally creates a shallow copy so callers can safely inspect
    or serialize the state without modifying the original object.
    """

    if state is None:
        return {}

    if isinstance(state, dict):
        return dict(state)

    try:
        return dict(state)
    except Exception:
        return {}


# ============================================================================
# Iteration helpers
# ============================================================================

def get_iteration(state: Optional[Dict[str, Any]]) -> int:
    """Return current workflow iteration."""
    if not state:
        return 0

    return max(
        0,
        _safe_int(state.get("iteration", 0), 0),
    )


def get_max_iterations(
    state: Optional[Dict[str, Any]],
) -> int:
    """Return maximum workflow iterations."""
    if not state:
        return DEFAULT_MAX_ITERATIONS

    value = _safe_int(
        state.get(
            "max_iterations",
            DEFAULT_MAX_ITERATIONS,
        ),
        DEFAULT_MAX_ITERATIONS,
    )

    return max(
        MIN_ITERATIONS,
        min(MAX_ITERATIONS, value),
    )


def iteration_limit_reached(
    state: Optional[Dict[str, Any]],
) -> bool:
    """
    Return True when the workflow has reached its iteration budget.

    Example:
        iteration = 3
        max_iterations = 3

        -> True
    """

    return get_iteration(state) >= get_max_iterations(state)


def increment_iteration(
    state: VerificationState,
) -> VerificationState:
    """
    Increment the workflow iteration.

    Returns the same state object for convenient use in LangGraph nodes.
    """

    current = get_iteration(state)
    maximum = get_max_iterations(state)

    state["iteration"] = min(
        current + 1,
        maximum,
    )

    return state


# ============================================================================
# Error / warning helpers
# ============================================================================

def add_error(
    state: VerificationState,
    message: Any,
) -> VerificationState:
    """Add an error message to the workflow state."""

    if message is None:
        return state

    text = str(message).strip()

    if not text:
        return state

    errors = state.get("errors", [])

    if not isinstance(errors, list):
        errors = []

    errors.append(text)

    state["errors"] = errors
    state["error"] = text
    state["status"] = STATUS_ERROR

    return state


def add_warning(
    state: VerificationState,
    message: Any,
) -> VerificationState:
    """Add a warning message to the workflow state."""

    if message is None:
        return state

    text = str(message).strip()

    if not text:
        return state

    warnings = state.get("warnings", [])

    if not isinstance(warnings, list):
        warnings = []

    warnings.append(text)

    state["warnings"] = warnings

    return state


def add_message(
    state: VerificationState,
    message: Any,
) -> VerificationState:
    """Add a general workflow message."""

    if message is None:
        return state

    text = str(message).strip()

    if not text:
        return state

    messages = state.get("messages", [])

    if not isinstance(messages, list):
        messages = []

    messages.append(text)

    state["messages"] = messages

    return state


# ============================================================================
# Agent trace helpers
# ============================================================================

def add_agent_trace(
    state: VerificationState,
    agent: str,
    event: str = "",
    details: Any = None,
) -> VerificationState:
    """
    Append a structured agent trace entry.

    The function is intentionally lightweight and does not require a logging
    framework, making it safe for Streamlit Cloud.
    """

    trace = state.get("agent_trace", [])

    if not isinstance(trace, list):
        trace = []

    entry: Dict[str, Any] = {
        "agent": str(agent or ""),
        "event": str(event or ""),
    }

    if details is not None:
        entry["details"] = details

    trace.append(entry)

    state["agent_trace"] = trace

    # Keep compatibility alias synchronized.
    state["trace"] = trace

    return state


def add_agent_log(
    state: VerificationState,
    message: Any,
) -> VerificationState:
    """Append a simple agent log message."""

    if message is None:
        return state

    text = str(message).strip()

    if not text:
        return state

    logs = state.get("agent_log", [])

    if not isinstance(logs, list):
        logs = []

    logs.append(text)

    state["agent_log"] = logs
    state["logs"] = logs

    return state


# ============================================================================
# RTL helpers
# ============================================================================

def get_rtl_code(
    state: Optional[Dict[str, Any]],
) -> str:
    """
    Return the best available RTL source.

    Priority:
        repaired_rtl
        rtl_code
        current_rtl
        original_rtl
    """

    if not state:
        return ""

    repaired = state.get("repaired_rtl")

    if isinstance(repaired, str) and repaired.strip():
        return repaired

    rtl = state.get("rtl_code")

    if isinstance(rtl, str) and rtl.strip():
        return rtl

    current = state.get("current_rtl")

    if isinstance(current, str) and current.strip():
        return current

    original = state.get("original_rtl")

    if isinstance(original, str):
        return original

    return ""


def update_rtl(
    state: VerificationState,
    rtl_code: str,
    reason: str = "",
) -> VerificationState:
    """
    Update RTL while preserving a small version history.
    """

    new_rtl = rtl_code or ""

    old_rtl = get_rtl_code(state)

    history = state.get("rtl_history", [])

    if not isinstance(history, list):
        history = []

    if old_rtl and old_rtl != new_rtl:
        history.append(
            {
                "version": state.get("rtl_version", 1),
                "rtl_code": old_rtl,
                "reason": reason or "previous_version",
            }
        )

    current_version = _safe_int(
        state.get("rtl_version", 0),
        0,
    )

    state["rtl_code"] = new_rtl
    state["current_rtl"] = new_rtl
    state["rtl_version"] = max(
        1,
        current_version + 1,
    )
    state["rtl_history"] = history

    return state


# ============================================================================
# Test helpers
# ============================================================================

def get_tests(
    state: Optional[Dict[str, Any]],
) -> List[Any]:
    """Return generated tests using compatibility fallbacks."""

    if not state:
        return []

    tests = state.get("generated_tests")

    if tests:
        return _ensure_list(tests)

    tests = state.get("tests")

    if tests:
        return _ensure_list(tests)

    return _ensure_list(
        state.get("test_cases")
    )


# ============================================================================
# Testbench helpers
# ============================================================================

def get_testbench(
    state: Optional[Dict[str, Any]],
) -> str:
    """Return the best available testbench source."""

    if not state:
        return ""

    for key in (
        "testbench",
        "test_code",
        "testbench_code",
    ):
        value = state.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return ""


# ============================================================================
# Simulation helpers
# ============================================================================

def simulation_succeeded(
    state: Optional[Dict[str, Any]],
) -> bool:
    """
    Determine whether simulation passed.

    Explicit simulation_passed takes priority.
    """

    if not state:
        return False

    if "simulation_passed" in state:
        return _safe_bool(
            state.get("simulation_passed"),
            False,
        )

    if "test_passed" in state:
        return _safe_bool(
            state.get("test_passed"),
            False,
        )

    result = state.get("simulation_result")

    if isinstance(result, dict):
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


# ============================================================================
# Coverage helpers
# ============================================================================

def get_coverage_score(
    state: Optional[Dict[str, Any]],
) -> float:
    """Return normalized coverage score as a percentage."""

    if not state:
        return 0.0

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
                    _safe_float(value, 0.0),
                ),
            )

    coverage = state.get("coverage")

    if isinstance(coverage, dict):
        for key in (
            "coverage_percent",
            "coverage_percentage",
            "score",
            "total",
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


def coverage_is_sufficient(
    state: Optional[Dict[str, Any]],
    target: float = 95.0,
) -> bool:
    """Return True if coverage has reached the requested target."""

    return get_coverage_score(state) >= float(target)


# ============================================================================
# Mutation helpers
# ============================================================================

def get_mutation_score(
    state: Optional[Dict[str, Any]],
) -> float:
    """Return mutation score as percentage."""

    if not state:
        return 0.0

    return max(
        0.0,
        min(
            100.0,
            _safe_float(
                state.get("mutation_score", 0.0),
                0.0,
            ),
        ),
    )


# ============================================================================
# Verdict helpers
# ============================================================================

def normalize_verdict(
    verdict: Any,
) -> str:
    """
    Normalize judge/router verdicts.

    Supported canonical values:
        PASS
        FAIL
        NEED_MORE
        UNKNOWN
    """

    if verdict is None:
        return VERDICT_UNKNOWN

    value = str(verdict).strip().upper()

    if value in {
        "PASS",
        "PASSED",
        "SUCCESS",
        "VERIFIED",
        "VERIFICATION PASSED",
    }:
        return VERDICT_PASS

    if value in {
        "FAIL",
        "FAILED",
        "ERROR",
        "REJECT",
        "REJECTED",
        "VERIFICATION FAILED",
    }:
        return VERDICT_FAIL

    if value in {
        "NEED_MORE",
        "NEED MORE",
        "RETRY",
        "RETRY_REQUIRED",
        "CONTINUE",
        "INCOMPLETE",
    }:
        return VERDICT_NEED_MORE

    return VERDICT_UNKNOWN


def get_verdict(
    state: Optional[Dict[str, Any]],
) -> str:
    """Return the normalized final verification verdict."""

    if not state:
        return VERDICT_UNKNOWN

    for key in (
        "final_verdict",
        "verdict",
    ):
        value = state.get(key)

        if value:
            normalized = normalize_verdict(value)

            if normalized != VERDICT_UNKNOWN:
                return normalized

    judge_result = state.get("judge_result")

    if isinstance(judge_result, dict):
        for key in (
            "verdict",
            "final_verdict",
            "status",
            "result",
        ):
            if key in judge_result:
                normalized = normalize_verdict(
                    judge_result.get(key)
                )

                if normalized != VERDICT_UNKNOWN:
                    return normalized

    return VERDICT_UNKNOWN


# ============================================================================
# Feature helpers
# ============================================================================

def mutation_enabled(
    state: Optional[Dict[str, Any]],
) -> bool:
    """Return whether mutation testing is enabled."""

    if not state:
        return False

    if "run_mutation" in state:
        return _safe_bool(
            state.get("run_mutation"),
            False,
        )

    return _safe_bool(
        state.get("enable_mutation"),
        False,
    )


def formal_enabled(
    state: Optional[Dict[str, Any]],
) -> bool:
    """Return whether optional formal verification is enabled."""

    if not state:
        return False

    if "run_formal" in state:
        return _safe_bool(
            state.get("run_formal"),
            False,
        )

    return _safe_bool(
        state.get("enable_formal"),
        False,
    )


# ============================================================================
# Status helpers
# ============================================================================

def set_status(
    state: VerificationState,
    status: str,
) -> VerificationState:
    """Set workflow status safely."""

    state["status"] = str(
        status or STATUS_INITIALIZED
    )

    return state


def mark_running(
    state: VerificationState,
) -> VerificationState:
    """Mark workflow as running."""

    state["status"] = STATUS_RUNNING
    return state


def mark_completed(
    state: VerificationState,
    verdict: Optional[str] = None,
) -> VerificationState:
    """Mark workflow as completed."""

    state["status"] = STATUS_COMPLETED

    if verdict:
        normalized = normalize_verdict(verdict)

        state["final_verdict"] = normalized
        state["verdict"] = normalized

        if normalized == VERDICT_PASS:
            state["status"] = STATUS_PASSED

        elif normalized == VERDICT_FAIL:
            state["status"] = STATUS_FAILED

    return state


# ============================================================================
# Router convenience
# ============================================================================

def should_continue(
    state: Optional[Dict[str, Any]],
) -> bool:
    """
    Determine whether the workflow can continue.

    This is deliberately conservative:
        - errors stop the workflow
        - explicit stop status stops the workflow
        - iteration budget stops the workflow
        - otherwise continue
    """

    if not state:
        return False

    status = str(
        state.get("status", "")
    ).strip().lower()

    if status in {
        STATUS_ERROR,
        STATUS_STOPPED,
        STATUS_FAILED,
    }:
        return False

    if iteration_limit_reached(state):
        return False

    return True


# ============================================================================
# State validation
# ============================================================================

def validate_state(
    state: Optional[Dict[str, Any]],
) -> List[str]:
    """
    Validate essential workflow state.

    Returns a list of problems rather than raising exceptions.
    """

    problems: List[str] = []

    if state is None:
        problems.append("State is None.")
        return problems

    rtl = get_rtl_code(state)

    if not rtl.strip():
        problems.append("RTL code is empty.")

    if get_max_iterations(state) < 1:
        problems.append(
            "max_iterations must be at least 1."
        )

    if get_iteration(state) < 0:
        problems.append(
            "iteration cannot be negative."
        )

    return problems


# ============================================================================
# Serialization helper
# ============================================================================

def clean_state_for_json(
    state: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Produce a best-effort JSON-friendly state.

    Useful for Streamlit downloads and report generation.
    """

    if not state:
        return {}

    def clean(value: Any) -> Any:
        if value is None:
            return None

        if isinstance(
            value,
            (str, int, float, bool),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(k): clean(v)
                for k, v in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                clean(item)
                for item in value
            ]

        # Fallback for arbitrary objects.
        try:
            return str(value)
        except Exception:
            return repr(value)

    return clean(dict(state))


# ============================================================================
# Public exports
# ============================================================================

__all__ = [
    # State
    "VerificationState",

    # Constants
    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",
    "DEFAULT_STATUS",

    "STATUS_INITIALIZED",
    "STATUS_RUNNING",
    "STATUS_PASSED",
    "STATUS_FAILED",
    "STATUS_COMPLETED",
    "STATUS_ERROR",
    "STATUS_STOPPED",

    "VERDICT_PASS",
    "VERDICT_FAIL",
    "VERDICT_NEED_MORE",
    "VERDICT_UNKNOWN",

    # Creation / conversion
    "create_initial_state",
    "state_to_dict",
    "clean_state_for_json",

    # Iteration
    "get_iteration",
    "get_max_iterations",
    "iteration_limit_reached",
    "increment_iteration",

    # Messages
    "add_error",
    "add_warning",
    "add_message",

    # Observability
    "add_agent_trace",
    "add_agent_log",

    # RTL
    "get_rtl_code",
    "update_rtl",

    # Tests
    "get_tests",

    # Testbench
    "get_testbench",

    # Simulation
    "simulation_succeeded",

    # Coverage
    "get_coverage_score",
    "coverage_is_sufficient",

    # Mutation
    "get_mutation_score",

    # Verdict
    "normalize_verdict",
    "get_verdict",

    # Features
    "mutation_enabled",
    "formal_enabled",

    # Status
    "set_status",
    "mark_running",
    "mark_completed",

    # Routing
    "should_continue",

    # Validation
    "validate_state",
]


