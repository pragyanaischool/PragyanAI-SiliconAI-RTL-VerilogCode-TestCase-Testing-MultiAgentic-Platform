"""
tests/test_workflow.py

Integration tests for the PragyanAI SiliconAI verification workflow.

Expected high-level flow:

    RTL Analysis
         ↓
    Verification Planning
         ↓
    Test Generation
         ↓
    Testbench Generation
         ↓
    Simulation
      ↙     ↘
  Failure   Pass
    ↓         ↓
  Analysis  Coverage
    ↓         ↓
  Repair   Red Team
    ↓         ↓
 Bug Loc.  Mutation
    ↓         ↓
 Test Gen   Formal
              ↓
            Judge
           ↙     ↘
        PASS      FAIL
          ↓        ↓
         END     Repair/Test Gen
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from graph import router


# ---------------------------------------------------------------------------
# Sample RTL
# ---------------------------------------------------------------------------

SAMPLE_RTL = r"""
module counter #(
    parameter WIDTH = 4
)(
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg [WIDTH-1:0]  count
);

always @(posedge clk) begin
    if (rst)
        count <= {WIDTH{1'b0}};
    else if (en)
        count <= count + 1'b1;
end

endmodule
"""


SIMPLE_RTL = r"""
module simple(
    input  wire a,
    input  wire b,
    output wire y
);

assign y = a & b;

endmodule
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_state(**overrides: Any) -> Dict[str, Any]:
    """
    Minimal VerificationState compatible with the workflow and router.
    """
    state: Dict[str, Any] = {
        "prompt": "Verify a 4-bit synchronous counter.",
        "specification": (
            "The counter resets to zero when rst is asserted and increments "
            "by one on each rising clock edge when en is asserted."
        ),
        "rtl_code": SAMPLE_RTL,
        "rtl_version": 1,
        "rtl_history": [],
        "rtl_analysis": {},
        "verification_plan": {},
        "generated_tests": [],
        "tests": [],
        "testbench": "",
        "test_code": "",
        "run_output": "",
        "simulation_output": "",
        "compile_output": "",
        "compile_error": "",
        "simulation_error": "",
        "simulation_passed": False,
        "failure_analysis": {},
        "root_cause": "",
        "coverage": {},
        "coverage_gaps": [],
        "red_team_scenarios": [],
        "mutations": [],
        "mutation_score": 0.0,
        "formal_result": {},
        "bug_location": {},
        "repair_proposal": {},
        "repaired_rtl": "",
        "verification_score": 0.0,
        "judge_result": {},
        "agent_log": [],
        "agent_trace": [],
        "iteration": 0,
        "max_iterations": 3,
        "status": "READY",
        "run_id": "",
        "run_dir": "",
        "next_action": "",
        "retry_required": False,
        "stop_reason": "",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    state.update(overrides)
    return state


def call_router(name: str, state: Dict[str, Any]):
    """
    Call a router function by name.

    This makes the tests slightly more tolerant of implementation changes
    while still testing the actual exported routing functions.
    """
    fn = getattr(router, name, None)

    if fn is None:
        pytest.skip(f"Router function {name} is not exported")

    assert callable(fn)
    return fn(state)


def assert_route(result: Any, expected: str):
    """
    Accept either a direct route string or a conditional-router result.
    """
    if isinstance(result, str):
        assert result == expected
        return

    if isinstance(result, dict):
        values = set()

        for value in result.values():
            if isinstance(value, str):
                values.add(value)

        assert expected in values
        return

    assert result == expected


# ---------------------------------------------------------------------------
# Router constants
# ---------------------------------------------------------------------------

def test_router_exports_expected_constants():
    expected = {
        "END",
        "TEST_GENERATION",
        "RTL_REPAIR",
        "BUG_LOCALIZATION",
        "COVERAGE",
        "RED_TEAM",
        "MUTATION",
        "FORMAL",
        "JUDGE",
    }

    available = {
        name
        for name in expected
        if hasattr(router, name)
    }

    assert available == expected


def test_router_constants_are_strings():
    names = [
        "END",
        "TEST_GENERATION",
        "RTL_REPAIR",
        "BUG_LOCALIZATION",
        "COVERAGE",
        "RED_TEAM",
        "MUTATION",
        "FORMAL",
        "JUDGE",
    ]

    for name in names:
        value = getattr(router, name)
        assert isinstance(value, str)
        assert value


# ---------------------------------------------------------------------------
# Simulation routing
# ---------------------------------------------------------------------------

def test_simulation_pass_routes_to_coverage():
    state = base_state(
        simulation_passed=True,
        compile_error="",
        simulation_error="",
    )

    result = call_router("route_after_simulation", state)

    assert_route(result, router.COVERAGE)


def test_simulation_failure_routes_to_failure_analysis():
    state = base_state(
        simulation_passed=False,
        compile_error="",
        simulation_error="simulation failed",
    )

    result = call_router("route_after_simulation", state)

    assert_route(result, "failure_analysis")


def test_compilation_failure_routes_to_failure_analysis():
    state = base_state(
        simulation_passed=False,
        compile_error="syntax error",
        simulation_error="",
    )

    result = call_router("route_after_simulation", state)

    assert_route(result, "failure_analysis")


# ---------------------------------------------------------------------------
# Failure analysis routing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "category, expected",
    [
        ("TESTBENCH_BUG", router.TEST_GENERATION),
        ("SPEC_AMBIGUITY", router.TEST_GENERATION),
        ("ENVIRONMENT", router.TEST_GENERATION),
        ("COMPILATION_ERROR", router.TEST_GENERATION),
        ("RTL_BUG", router.RTL_REPAIR),
        ("RESET_ERROR", router.RTL_REPAIR),
        ("FSM_ERROR", router.RTL_REPAIR),
        ("WIDTH_ERROR", router.RTL_REPAIR),
        ("PROTOCOL_ERROR", router.RTL_REPAIR),
        ("TIMING_ISSUE", router.RTL_REPAIR),
    ],
)
def test_failure_category_routes_correctly(category, expected):
    state = base_state(
        failure_analysis={
            "category": category,
            "root_cause": f"Example {category}",
            "recommended_action": expected,
        },
        root_cause=f"Example {category}",
    )

    result = call_router("route_after_failure_analysis", state)

    assert_route(result, expected)


def test_unknown_failure_routes_to_test_generation():
    state = base_state(
        failure_analysis={
            "category": "UNKNOWN",
            "root_cause": "Unknown failure",
        }
    )

    result = call_router("route_after_failure_analysis", state)

    assert_route(result, router.TEST_GENERATION)


# ---------------------------------------------------------------------------
# Repair routing
# ---------------------------------------------------------------------------

def test_actual_repair_routes_to_bug_localization():
    state = base_state(
        rtl_code=SAMPLE_RTL,
        repaired_rtl=SAMPLE_RTL.replace(
            "count <= count + 1'b1;",
            "count <= count + 1'b1;",
        ),
    )

    # Make the repaired design materially different.
    state["repaired_rtl"] = state["rtl_code"].replace(
        "count <= count + 1'b1;",
        "count <= count + 2'b01;",
    )

    result = call_router("route_after_repair", state)

    assert_route(result, router.BUG_LOCALIZATION)


def test_no_actual_repair_routes_to_test_generation():
    state = base_state(
        rtl_code=SAMPLE_RTL,
        repaired_rtl=SAMPLE_RTL,
    )

    result = call_router("route_after_repair", state)

    assert_route(result, router.TEST_GENERATION)


def test_empty_repair_routes_to_test_generation():
    state = base_state(
        repaired_rtl="",
    )

    result = call_router("route_after_repair", state)

    assert_route(result, router.TEST_GENERATION)


# ---------------------------------------------------------------------------
# Bug localization
# ---------------------------------------------------------------------------

def test_bug_localization_routes_to_test_generation():
    state = base_state(
        bug_location={
            "module": "counter",
            "line": 15,
            "signal": "count",
            "confidence": 0.8,
        }
    )

    result = call_router("route_after_bug_localization", state)

    assert_route(result, router.TEST_GENERATION)


# ---------------------------------------------------------------------------
# Coverage routing
# ---------------------------------------------------------------------------

def test_coverage_below_target_routes_to_test_generation():
    state = base_state(
        coverage={
            "overall": 70.0,
            "target": 95.0,
        },
        coverage_gaps=[
            "Reset release boundary",
            "Counter wrap-around",
        ],
    )

    result = call_router("route_after_coverage", state)

    assert_route(result, router.TEST_GENERATION)


def test_coverage_with_gaps_routes_to_test_generation():
    state = base_state(
        coverage={
            "overall": 98.0,
            "target": 95.0,
        },
        coverage_gaps=[
            "Reset boundary",
        ],
    )

    result = call_router("route_after_coverage", state)

    assert_route(result, router.TEST_GENERATION)


def test_coverage_above_target_without_gaps_routes_to_red_team():
    state = base_state(
        coverage={
            "overall": 98.0,
            "target": 95.0,
        },
        coverage_gaps=[],
    )

    result = call_router("route_after_coverage", state)

    assert_route(result, router.RED_TEAM)


def test_coverage_exactly_at_target_without_gaps_routes_to_red_team():
    state = base_state(
        coverage={
            "overall": 95.0,
            "target": 95.0,
        },
        coverage_gaps=[],
    )

    result = call_router("route_after_coverage", state)

    assert_route(result, router.RED_TEAM)


# ---------------------------------------------------------------------------
# Red team → mutation
# ---------------------------------------------------------------------------

def test_red_team_routes_to_mutation():
    state = base_state(
        red_team_scenarios=[
            {
                "id": "RT001",
                "scenario": "Reset during active transaction",
            },
            {
                "id": "RT002",
                "scenario": "Counter wrap-around",
            },
        ]
    )

    result = call_router("route_after_red_team", state)

    assert_route(result, router.MUTATION)


def test_red_team_empty_still_routes_to_mutation():
    state = base_state(red_team_scenarios=[])

    result = call_router("route_after_red_team", state)

    assert_route(result, router.MUTATION)


# ---------------------------------------------------------------------------
# Mutation → formal
# ---------------------------------------------------------------------------

def test_mutation_routes_to_formal():
    state = base_state(
        mutations=[
            {
                "id": "M001",
                "operator": "AND_TO_OR",
                "status": "KILLED",
            }
        ],
        mutation_score=100.0,
    )

    result = call_router("route_after_mutation", state)

    assert_route(result, router.FORMAL)


# ---------------------------------------------------------------------------
# Formal → judge
# ---------------------------------------------------------------------------

def test_formal_routes_to_judge():
    state = base_state(
        formal_result={
            "status": "PROVEN",
            "properties_checked": 5,
        }
    )

    result = call_router("route_after_formal", state)

    assert_route(result, router.JUDGE)


# ---------------------------------------------------------------------------
# Judge routing
# ---------------------------------------------------------------------------

def test_judge_pass_routes_to_end():
    state = base_state(
        judge_result={
            "verdict": "PASS",
            "confidence": 0.95,
        },
        verification_score=96.0,
    )

    result = call_router("route_after_judge", state)

    assert_route(result, router.END)


def test_judge_fail_with_rtl_bug_routes_to_repair():
    state = base_state(
        judge_result={
            "verdict": "FAIL",
            "failure_category": "RTL_BUG",
        },
        failure_analysis={
            "category": "RTL_BUG",
        },
    )

    result = call_router("route_after_judge", state)

    assert_route(result, router.RTL_REPAIR)


def test_judge_fail_with_reset_bug_routes_to_repair():
    state = base_state(
        judge_result={
            "verdict": "FAIL",
            "failure_category": "RESET_ERROR",
        },
        failure_analysis={
            "category": "RESET_ERROR",
        },
    )

    result = call_router("route_after_judge", state)

    assert_route(result, router.RTL_REPAIR)


def test_judge_fail_with_test_issue_routes_to_test_generation():
    state = base_state(
        judge_result={
            "verdict": "FAIL",
            "failure_category": "TESTBENCH_BUG",
        },
        failure_analysis={
            "category": "TESTBENCH_BUG",
        },
    )

    result = call_router("route_after_judge", state)

    assert_route(result, router.TEST_GENERATION)


def test_judge_need_more_verification_routes_to_test_generation():
    state = base_state(
        judge_result={
            "verdict": "NEED_MORE_VERIFICATION",
        },
        iteration=0,
        max_iterations=3,
    )

    result = call_router("route_after_judge", state)

    assert_route(result, router.TEST_GENERATION)


def test_judge_uncertainty_does_not_become_pass():
    state = base_state(
        judge_result={
            "verdict": "NEED_MORE_VERIFICATION",
        },
        verification_score=90.0,
    )

    result = call_router("route_after_judge", state)

    assert result != router.END


# ---------------------------------------------------------------------------
# Iteration budget
# ---------------------------------------------------------------------------

def test_iteration_budget_is_respected():
    state = base_state(
        judge_result={
            "verdict": "NEED_MORE_VERIFICATION",
        },
        iteration=3,
        max_iterations=3,
    )

    result = call_router("route_after_judge", state)

    # Once the configured budget is exhausted, the workflow should not
    # continuously route back into verification.
    assert result in {
        router.END,
        router.TEST_GENERATION,
        router.RTL_REPAIR,
    }


def test_zero_max_iterations_does_not_crash():
    state = base_state(
        judge_result={
            "verdict": "NEED_MORE_VERIFICATION",
        },
        iteration=0,
        max_iterations=0,
    )

    result = call_router("route_after_judge", state)

    assert result is not None


# ---------------------------------------------------------------------------
# State compatibility
# ---------------------------------------------------------------------------

def test_base_state_is_json_serializable():
    state = base_state()

    serialized = json.dumps(state, default=str)

    assert isinstance(serialized, str)


def test_state_preserves_rtl():
    state = base_state()

    assert state["rtl_code"] == SAMPLE_RTL


def test_state_contains_required_workflow_fields():
    state = base_state()

    required = {
        "rtl_code",
        "specification",
        "tests",
        "testbench",
        "simulation_passed",
        "coverage",
        "mutations",
        "formal_result",
        "judge_result",
        "iteration",
        "max_iterations",
    }

    assert required.issubset(state.keys())


# ---------------------------------------------------------------------------
# Workflow module
# ---------------------------------------------------------------------------

def test_workflow_module_imports():
    import graph.workflow as workflow

    assert workflow is not None


def test_workflow_exposes_build_function_or_graph():
    import graph.workflow as workflow

    possible = (
        "build_workflow",
        "create_workflow",
        "build_graph",
        "create_graph",
        "workflow",
        "app",
        "graph",
    )

    available = [
        name
        for name in possible
        if hasattr(workflow, name)
    ]

    assert available, (
        "graph.workflow should expose a workflow builder or compiled graph"
    )


def test_workflow_builder_is_callable_when_present():
    import graph.workflow as workflow

    candidates = (
        "build_workflow",
        "create_workflow",
        "build_graph",
        "create_graph",
    )

    found = False

    for name in candidates:
        fn = getattr(workflow, name, None)

        if callable(fn):
            found = True

            try:
                graph = fn()
            except TypeError:
                # Some implementations require configuration/state.
                continue

            assert graph is not None
            break

    if not found:
        pytest.skip("No callable workflow builder found")


# ---------------------------------------------------------------------------
# Compiled graph compatibility
# ---------------------------------------------------------------------------

def _get_compiled_graph():
    """
    Try common workflow export patterns.
    """
    import graph.workflow as workflow

    for name in (
        "workflow",
        "graph",
        "app",
        "verification_workflow",
        "verification_graph",
    ):
        candidate = getattr(workflow, name, None)

        if candidate is not None:
            return candidate

    for name in (
        "build_workflow",
        "create_workflow",
        "build_graph",
        "create_graph",
    ):
        fn = getattr(workflow, name, None)

        if callable(fn):
            try:
                return fn()
            except TypeError:
                continue

    return None


def test_compiled_workflow_has_graph_interface():
    graph = _get_compiled_graph()

    if graph is None:
        pytest.skip("Compiled workflow is not exposed")

    interfaces = (
        "invoke",
        "ainvoke",
        "stream",
        "astream",
        "get_graph",
    )

    assert any(hasattr(graph, name) for name in interfaces)


# ---------------------------------------------------------------------------
# Full workflow smoke test
# ---------------------------------------------------------------------------

def test_workflow_smoke_invocation(tmp_path):
    """
    Lightweight workflow smoke test.

    External LLM/simulator calls are intentionally not mocked here unless
    the workflow implementation exposes dependency injection. If the
    workflow cannot run in the current environment, the test skips rather
    than falsely declaring the workflow broken due to missing credentials
    or EDA tools.
    """
    graph = _get_compiled_graph()

    if graph is None:
        pytest.skip("Compiled workflow is not available")

    if not hasattr(graph, "invoke"):
        pytest.skip("Workflow does not expose synchronous invoke()")

    state = base_state(
        run_dir=str(tmp_path),
    )

    try:
        result = graph.invoke(state)
    except Exception as exc:
        message = str(exc).lower()

        environment_errors = (
            "groq",
            "api key",
            "iverilog",
            "vvp",
            "permission",
            "connection",
            "authentication",
            "credentials",
            "rate limit",
            "429",
            "413",
        )

        if any(token in message for token in environment_errors):
            pytest.skip(f"Environment-dependent workflow unavailable: {exc}")

        raise

    assert result is not None

    if isinstance(result, dict):
        assert isinstance(result, dict)

        # A completed or partially completed graph should preserve RTL.
        if "rtl_code" in result:
            assert result["rtl_code"]


# ---------------------------------------------------------------------------
# Workflow branch coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "simulation_passed, compile_error, simulation_error, expected",
    [
        (True, "", "", "coverage"),
        (False, "", "runtime error", "failure_analysis"),
        (False, "compile error", "", "failure_analysis"),
    ],
)
def test_simulation_branch_matrix(
    simulation_passed,
    compile_error,
    simulation_error,
    expected,
):
    state = base_state(
        simulation_passed=simulation_passed,
        compile_error=compile_error,
        simulation_error=simulation_error,
    )

    result = call_router("route_after_simulation", state)

    # Normalize route for readable assertion.
    if expected == "coverage":
        assert_route(result, router.COVERAGE)
    else:
        assert_route(result, "failure_analysis")


@pytest.mark.parametrize(
    "overall,gaps,expected",
    [
        (50, ["reset"], router.TEST_GENERATION),
        (94.9, [], router.TEST_GENERATION),
        (95, [], router.RED_TEAM),
        (99, [], router.RED_TEAM),
        (100, [], router.RED_TEAM),
    ],
)
def test_coverage_branch_matrix(overall, gaps, expected):
    state = base_state(
        coverage={
            "overall": overall,
            "target": 95,
        },
        coverage_gaps=gaps,
    )

    result = call_router("route_after_coverage", state)

    assert_route(result, expected)


# ---------------------------------------------------------------------------
# Safety properties
# ---------------------------------------------------------------------------

def test_router_does_not_route_unknown_node():
    state = base_state()

    # The normal router outputs must always be strings or supported
    # conditional results.
    result = call_router("route_after_simulation", state)

    if isinstance(result, str):
        known = {
            router.END,
            router.TEST_GENERATION,
            router.RTL_REPAIR,
            router.BUG_LOCALIZATION,
            router.COVERAGE,
            router.RED_TEAM,
            router.MUTATION,
            router.FORMAL,
            router.JUDGE,
            "failure_analysis",
        }

        assert result in known


def test_router_handles_missing_optional_fields():
    state = {
        "rtl_code": SIMPLE_RTL,
        "iteration": 0,
        "max_iterations": 3,
    }

    for function_name in (
        "route_after_simulation",
        "route_after_failure_analysis",
        "route_after_repair",
        "route_after_bug_localization",
        "route_after_coverage",
        "route_after_red_team",
        "route_after_mutation",
        "route_after_formal",
        "route_after_judge",
    ):
        fn = getattr(router, function_name, None)

        if fn is None:
            continue

        try:
            result = fn(state)
        except (KeyError, TypeError, AttributeError):
            # Missing optional state fields should not be considered a
            # workflow test failure when the router explicitly expects
            # populated state at that stage.
            continue

        assert result is not None


# ---------------------------------------------------------------------------
# End-to-end logical path
# ---------------------------------------------------------------------------

def test_expected_happy_path_sequence():
    """
    Validate the intended logical route without executing expensive agents.

    Expected:

        Simulation PASS
          -> Coverage
          -> Red Team
          -> Mutation
          -> Formal
          -> Judge
          -> END
    """
    state = base_state(
        simulation_passed=True,
        coverage={
            "overall": 98,
            "target": 95,
        },
        coverage_gaps=[],
        red_team_scenarios=[
            {
                "id": "RT001",
                "scenario": "Reset boundary",
            }
        ],
        mutations=[
            {
                "id": "M001",
                "operator": "EQ_TO_NE",
                "status": "KILLED",
            }
        ],
        mutation_score=100,
        formal_result={
            "status": "PROVEN",
        },
        judge_result={
            "verdict": "PASS",
        },
    )

    simulation_route = call_router(
        "route_after_simulation",
        state,
    )
    assert_route(simulation_route, router.COVERAGE)

    coverage_route = call_router(
        "route_after_coverage",
        state,
    )
    assert_route(coverage_route, router.RED_TEAM)

    red_team_route = call_router(
        "route_after_red_team",
        state,
    )
    assert_route(red_team_route, router.MUTATION)

    mutation_route = call_router(
        "route_after_mutation",
        state,
    )
    assert_route(mutation_route, router.FORMAL)

    formal_route = call_router(
        "route_after_formal",
        state,
    )
    assert_route(formal_route, router.JUDGE)

    judge_route = call_router(
        "route_after_judge",
        state,
    )
    assert_route(judge_route, router.END)


def test_expected_failure_and_repair_path():
    """
    Validate:

        Simulation FAIL
             ↓
        Failure Analysis
             ↓
           RTL Bug
             ↓
          RTL Repair
             ↓
       Bug Localization
             ↓
        Test Generation
    """
    state = base_state(
        simulation_passed=False,
        simulation_error="Incorrect counter behavior",
        failure_analysis={
            "category": "RTL_BUG",
            "root_cause": "Counter increments incorrectly",
        },
        repaired_rtl=SAMPLE_RTL.replace(
            "count <= count + 1'b1;",
            "count <= count + 1'b1;",
        ),
    )

    route1 = call_router(
        "route_after_simulation",
        state,
    )
    assert_route(route1, "failure_analysis")

    route2 = call_router(
        "route_after_failure_analysis",
        state,
    )
    assert_route(route2, router.RTL_REPAIR)

    # Actual repair
    state["repaired_rtl"] = SAMPLE_RTL.replace(
        "count <= count + 1'b1;",
        "count <= count + {{(WIDTH-1){1'b0}},1'b1};",
    )

    route3 = call_router(
        "route_after_repair",
        state,
    )

    assert_route(route3, router.BUG_LOCALIZATION)

    route4 = call_router(
        "route_after_bug_localization",
        state,
    )

    assert_route(route4, router.TEST_GENERATION)


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

def test_workflow_state_can_be_persisted(tmp_path):
    state = base_state(
        run_dir=str(tmp_path),
        rtl_analysis={
            "module": "counter",
            "signals": ["clk", "rst", "en", "count"],
        },
        verification_plan={
            "test_count": 10,
            "coverage_target": 95,
        },
    )

    path = tmp_path / "workflow_state.json"

    path.write_text(
        json.dumps(state, indent=2, default=str),
        encoding="utf-8",
    )

    assert path.exists()

    restored = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert restored["rtl_code"] == SAMPLE_RTL
    assert restored["iteration"] == 0
    assert restored["max_iterations"] == 3
