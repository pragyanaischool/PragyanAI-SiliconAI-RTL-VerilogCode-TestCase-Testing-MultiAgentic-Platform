"""
PragyanAI SiliconAI
Agentic RTL Verification
Shared LangGraph State
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_ITERATIONS = 3
MIN_ITERATIONS = 1
MAX_ITERATIONS = 10

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


# =============================================================================
# Verification State
# =============================================================================

class VerificationState(TypedDict, total=False):

    # -------------------------------------------------------------------------
    # Input
    # -------------------------------------------------------------------------

    prompt: str
    user_prompt: str

    specification: str
    spec: str

    # -------------------------------------------------------------------------
    # RTL
    # -------------------------------------------------------------------------

    rtl_code: str
    original_rtl: str
    current_rtl: str

    rtl_version: int
    rtl_history: List[Dict[str, Any]]
    rtl_analysis: Dict[str, Any]

    # -------------------------------------------------------------------------
    # Planning
    # -------------------------------------------------------------------------

    verification_plan: Dict[str, Any]
    plan: Dict[str, Any]

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    generated_tests: List[Any]
    tests: List[Any]
    test_cases: List[Any]

    # -------------------------------------------------------------------------
    # Testbench
    # -------------------------------------------------------------------------

    testbench: str
    test_code: str
    testbench_code: str

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    run_output: str
    simulation_output: str
    compile_output: str

    compile_error: str
    simulation_error: str

    simulation_passed: bool
    compile_passed: bool
    test_passed: bool

    simulation_result: Dict[str, Any]
    simulator_result: Dict[str, Any]

    # -------------------------------------------------------------------------
    # Failure analysis
    # -------------------------------------------------------------------------

    failure_analysis: Dict[str, Any]
    failure: Dict[str, Any]

    root_cause: str
    failure_type: str

    # -------------------------------------------------------------------------
    # Coverage
    # -------------------------------------------------------------------------

    coverage: Dict[str, Any]
    coverage_report: Dict[str, Any]

    coverage_gaps: List[Any]

    coverage_score: float
    coverage_percent: float
    coverage_target: float

    # -------------------------------------------------------------------------
    # Red team
    # -------------------------------------------------------------------------

    red_team_scenarios: List[Any]
    red_team_results: List[Any]

    # -------------------------------------------------------------------------
    # Mutation
    # -------------------------------------------------------------------------

    mutations: List[Any]
    mutation_results: List[Any]
    mutation_report: Dict[str, Any]

    mutation_score: float
    mutation_target: float

    # -------------------------------------------------------------------------
    # Formal
    # -------------------------------------------------------------------------

    formal_result: Dict[str, Any]
    formal_results: Dict[str, Any]
    formal_passed: bool

    # -------------------------------------------------------------------------
    # Bug localization
    # -------------------------------------------------------------------------

    bug_location: Dict[str, Any]
    bug_locations: List[Any]
    localization_result: Dict[str, Any]

    # -------------------------------------------------------------------------
    # RTL repair
    # -------------------------------------------------------------------------

    repair_proposal: Dict[str, Any]
    repair_result: Dict[str, Any]
    rtl_repair: Dict[str, Any]

    repaired_rtl: str
    repair_applied: bool

    # -------------------------------------------------------------------------
    # Judge
    # -------------------------------------------------------------------------

    verification_score: float

    judge_result: Dict[str, Any]
    judge: Dict[str, Any]

    final_verdict: str
    verdict: str

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------

    agent_log: List[Any]
    agent_trace: List[Any]

    logs: List[Any]
    trace: List[Any]

    messages: List[Any]
    warnings: List[str]
    errors: List[str]

    error: str

    # -------------------------------------------------------------------------
    # Workflow
    # -------------------------------------------------------------------------

    iteration: int
    max_iterations: int

    status: str
    run_id: str
    run_dir: str

    next_action: str
    retry_required: bool
    stop_reason: str

    # -------------------------------------------------------------------------
    # Feature flags
    # -------------------------------------------------------------------------

    run_mutation: bool
    run_formal: bool

    enable_mutation: bool
    enable_formal: bool


# =============================================================================
# Safe conversion helpers
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
# State creation
# =============================================================================

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

    max_iterations = _safe_int(
        max_iterations,
        DEFAULT_MAX_ITERATIONS,
    )

    max_iterations = max(
        MIN_ITERATIONS,
        min(MAX_ITERATIONS, max_iterations),
    )

    state: VerificationState = {

        # Input
        "prompt": prompt or "",
        "user_prompt": prompt or "",

        "specification": specification or "",
        "spec": specification or "",

        # RTL
        "rtl_code": rtl_code or "",
        "original_rtl": rtl_code or "",
        "current_rtl": rtl_code or "",

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
        "compile_passed": False,
        "test_passed": False,

        "simulation_result": {},
        "simulator_result": {},

        # Failure
        "failure_analysis": {},
        "failure": {},

        "root_cause": "",
        "failure_type": "",

        # Coverage
        "coverage": {},
        "coverage_report": {},

        "coverage_gaps": [],

        "coverage_score": 0.0,
        "coverage_percent": 0.0,
        "coverage_target": 95.0,

        # Red team
        "red_team_scenarios": [],
        "red_team_results": [],

        # Mutation
        "mutations": [],
        "mutation_results": [],
        "mutation_report": {},

        "mutation_score": 0.0,
        "mutation_target": 90.0,

        # Formal
        "formal_result": {},
        "formal_results": {},
        "formal_passed": False,

        # Bug localization
        "bug_location": {},
        "bug_locations": [],
        "localization_result": {},

        # Repair
        "repair_proposal": {},
        "repair_result": {},
        "rtl_repair": {},

        "repaired_rtl": "",
        "repair_applied": False,

        # Judge
        "verification_score": 0.0,

        "judge_result": {},
        "judge": {},

        "final_verdict": VERDICT_UNKNOWN,
        "verdict": VERDICT_UNKNOWN,

        # Logging
        "agent_log": [],
        "agent_trace": [],

        "logs": [],
        "trace": [],

        "messages": [],
        "warnings": [],
        "errors": [],
        "error": "",

        # Workflow
        "iteration": 0,
        "max_iterations": max_iterations,

        "status": STATUS_INITIALIZED,

        "run_id": run_id or "",
        "run_dir": run_dir or "",

        "next_action": "",
        "retry_required": False,
        "stop_reason": "",

        # Feature flags
        "run_mutation": _safe_bool(
            run_mutation
        ),

        "run_formal": _safe_bool(
            run_formal
        ),

        "enable_mutation": _safe_bool(
            run_mutation
        ),

        "enable_formal": _safe_bool(
            run_formal
        ),
    }

    for key, value in kwargs.items():
        state[key] = value  # type: ignore

    return state


# =============================================================================
# Basic helpers
# =============================================================================

def state_to_dict(
    state: Optional[Dict[str, Any]],
) -> Dict[str, Any]:

    if state is None:
        return {}

    try:
        return dict(state)
    except Exception:
        return {}


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

    return (
        get_iteration(state)
        >= get_max_iterations(state)
    )


def increment_iteration(
    state: VerificationState,
) -> VerificationState:

    current = get_iteration(state)
    maximum = get_max_iterations(state)

    state["iteration"] = min(
        current + 1,
        maximum,
    )

    return state


# =============================================================================
# Message helpers
# =============================================================================

def add_error(
    state: VerificationState,
    message: Any,
) -> VerificationState:

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


# =============================================================================
# Trace helpers
# =============================================================================

def add_agent_trace(
    state: VerificationState,
    agent: str,
    event: str = "",
    details: Any = None,
) -> VerificationState:

    trace = state.get("agent_trace", [])

    if not isinstance(trace, list):
        trace = []

    entry = {
        "agent": str(agent or ""),
        "event": str(event or ""),
    }

    if details is not None:
        entry["details"] = details

    trace.append(entry)

    state["agent_trace"] = trace
    state["trace"] = trace

    return state


def add_agent_log(
    state: VerificationState,
    message: Any,
) -> VerificationState:

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


# =============================================================================
# RTL helpers
# =============================================================================

def get_rtl_code(
    state: Optional[Dict[str, Any]],
) -> str:

    if not state:
        return ""

    for key in (
        "repaired_rtl",
        "rtl_code",
        "current_rtl",
        "original_rtl",
    ):

        value = state.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return ""


def update_rtl(
    state: VerificationState,
    rtl_code: str,
    reason: str = "",
) -> VerificationState:

    old_rtl = get_rtl_code(state)
    new_rtl = rtl_code or ""

    history = state.get("rtl_history", [])

    if not isinstance(history, list):
        history = []

    if old_rtl and old_rtl != new_rtl:

        history.append(
            {
                "version": state.get(
                    "rtl_version",
                    1,
                ),
                "rtl_code": old_rtl,
                "reason": reason or "rtl_update",
            }
        )

    version = _safe_int(
        state.get("rtl_version", 0),
        0,
    )

    state["rtl_code"] = new_rtl
    state["current_rtl"] = new_rtl
    state["rtl_version"] = max(
        1,
        version + 1,
    )
    state["rtl_history"] = history

    return state


# =============================================================================
# Test helpers
# =============================================================================

def get_tests(
    state: Optional[Dict[str, Any]],
) -> List[Any]:

    if not state:
        return []

    for key in (
        "generated_tests",
        "tests",
        "test_cases",
    ):

        value = state.get(key)

        if isinstance(value, list) and value:
            return value

    return []


def get_testbench(
    state: Optional[Dict[str, Any]],
) -> str:

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


# =============================================================================
# Simulation helpers
# =============================================================================

def simulation_succeeded(
    state: Optional[Dict[str, Any]],
) -> bool:

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

    result = state.get(
        "simulation_result"
    )

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


# =============================================================================
# Coverage
# =============================================================================

def get_coverage_score(
    state: Optional[Dict[str, Any]],
) -> float:

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


def coverage_is_sufficient(
    state: Optional[Dict[str, Any]],
    target: float = 95.0,
) -> bool:

    return (
        get_coverage_score(state)
        >= float(target)
    )


# =============================================================================
# Mutation
# =============================================================================

def get_mutation_score(
    state: Optional[Dict[str, Any]],
) -> float:

    if not state:
        return 0.0

    return max(
        0.0,
        min(
            100.0,
            _safe_float(
                state.get(
                    "mutation_score",
                    0.0,
                ),
                0.0,
            ),
        ),
    )


# =============================================================================
# Verdict
# =============================================================================

def normalize_verdict(
    value: Any,
) -> str:

    if value is None:
        return VERDICT_UNKNOWN

    value = str(value).strip().upper()

    if value in {
        "PASS",
        "PASSED",
        "SUCCESS",
        "VERIFIED",
    }:
        return VERDICT_PASS

    if value in {
        "FAIL",
        "FAILED",
        "ERROR",
        "REJECTED",
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

    if not state:
        return VERDICT_UNKNOWN

    for key in (
        "final_verdict",
        "verdict",
    ):

        value = state.get(key)

        if value:

            result = normalize_verdict(
                value
            )

            if result != VERDICT_UNKNOWN:
                return result

    judge = state.get(
        "judge_result"
    )

    if isinstance(judge, dict):

        for key in (
            "verdict",
            "final_verdict",
            "status",
            "result",
        ):

            result = normalize_verdict(
                judge.get(key)
            )

            if result != VERDICT_UNKNOWN:
                return result

    return VERDICT_UNKNOWN


# =============================================================================
# Feature flags
# =============================================================================

def mutation_enabled(
    state: Optional[Dict[str, Any]],
) -> bool:

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


# =============================================================================
# Status
# =============================================================================

def set_status(
    state: VerificationState,
    status: str,
) -> VerificationState:

    state["status"] = str(status)
    return state


def mark_running(
    state: VerificationState,
) -> VerificationState:

    state["status"] = STATUS_RUNNING
    return state


def mark_completed(
    state: VerificationState,
    verdict: Optional[str] = None,
) -> VerificationState:

    state["status"] = STATUS_COMPLETED

    if verdict:

        normalized = normalize_verdict(
            verdict
        )

        state["final_verdict"] = normalized
        state["verdict"] = normalized

        if normalized == VERDICT_PASS:
            state["status"] = STATUS_PASSED

        elif normalized == VERDICT_FAIL:
            state["status"] = STATUS_FAILED

    return state


# =============================================================================
# Validation
# =============================================================================

def validate_state(
    state: Optional[Dict[str, Any]],
) -> List[str]:

    problems: List[str] = []

    if state is None:
        return ["State is None."]

    if not get_rtl_code(state).strip():
        problems.append(
            "RTL code is empty."
        )

    if get_max_iterations(state) < 1:
        problems.append(
            "max_iterations must be at least 1."
        )

    return problems


# =============================================================================
# JSON-safe conversion
# =============================================================================

def clean_state_for_json(
    state: Optional[Dict[str, Any]],
) -> Dict[str, Any]:

    if not state:
        return {}

    def clean(value: Any) -> Any:

        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(value, dict):
            return {
                str(key): clean(val)
                for key, val in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                clean(item)
                for item in value
            ]

        try:
            return str(value)
        except Exception:
            return repr(value)

    return clean(dict(state))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "VerificationState",

    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",

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

    "create_initial_state",
    "state_to_dict",

    "get_iteration",
    "get_max_iterations",
    "iteration_limit_reached",
    "increment_iteration",

    "add_error",
    "add_warning",
    "add_message",

    "add_agent_trace",
    "add_agent_log",

    "get_rtl_code",
    "update_rtl",

    "get_tests",
    "get_testbench",

    "simulation_succeeded",

    "get_coverage_score",
    "coverage_is_sufficient",

    "get_mutation_score",

    "normalize_verdict",
    "get_verdict",

    "mutation_enabled",
    "formal_enabled",

    "set_status",
    "mark_running",
    "mark_completed",

    "validate_state",
    "clean_state_for_json",
]

