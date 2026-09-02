"""
PragyanAI SiliconAI
RTL Verification Agentic Workflow

LangGraph orchestration for:

RTL Analysis
    ↓
Verification Planning
    ↓
Test Generation
    ↓
Testbench Generation
    ↓
Simulation
    ↓
Failure Analysis / Coverage
    ↓
RTL Repair / Bug Localization
    ↓
Red Team
    ↓
Mutation
    ↓
Formal Verification
    ↓
Verification Judge

This module intentionally keeps graph construction simple and explicit
to maximize compatibility across LangGraph versions.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END as LANGGRAPH_END
from langgraph.graph import START, StateGraph

from graph.state import VerificationState
from graph.router import (
    route_after_coverage,
    route_after_failure,
    route_after_formal,
    route_after_judge,
    route_after_mutation,
    route_after_repair,
    route_after_simulation,
)

from agents.rtl_analyzer import RTLAnalyzer
from agents.verification_planner import VerificationPlanner
from agents.test_generator import TestGenerator
from agents.testbench_generator import TestbenchGenerator
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzer
from agents.coverage_agent import CoverageAgent
from agents.red_team_agent import RedTeamAgent
from agents.mutation_agent import MutationAgent
from agents.formal_agent import FormalAgent
from agents.bug_localization_agent import BugLocalizationAgent
from agents.rtl_repair_agent import RTLRepairAgent
from agents.verification_judge import VerificationJudge


# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def _safe_state(state: Any) -> Dict[str, Any]:
    """
    Convert LangGraph state into a normal dictionary.

    This makes the workflow tolerant of TypedDict-like state objects
    and regular dictionaries.
    """
    if state is None:
        return {}

    if isinstance(state, dict):
        return dict(state)

    try:
        return dict(state)
    except Exception:
        return {}


def _run_agent(agent: Any, state: Any) -> Dict[str, Any]:
    """
    Execute an agent using the common .run(state) interface.

    A small compatibility layer is used so the workflow can fail
    gracefully instead of crashing during graph execution.
    """
    current_state = _safe_state(state)

    try:
        result = agent.run(current_state)

        if result is None:
            return current_state

        if isinstance(result, dict):
            return result

        try:
            return dict(result)
        except Exception:
            current_state["errors"] = list(
                current_state.get("errors", [])
            ) + [
                f"{agent.__class__.__name__} returned unsupported result type"
            ]
            return current_state

    except Exception as exc:
        errors = list(current_state.get("errors", []))

        errors.append(
            f"{agent.__class__.__name__}: {type(exc).__name__}: {exc}"
        )

        current_state["errors"] = errors
        current_state["status"] = "ERROR"

        return current_state


# ---------------------------------------------------------------------
# Agent instances
# ---------------------------------------------------------------------

rtl_analyzer = RTLAnalyzer()
verification_planner = VerificationPlanner()
test_generator = TestGenerator()
testbench_generator = TestbenchGenerator()
simulator_agent = SimulatorAgent()
failure_analyzer = FailureAnalyzer()
coverage_agent = CoverageAgent()
red_team_agent = RedTeamAgent()
mutation_agent = MutationAgent()
formal_agent = FormalAgent()
bug_localization_agent = BugLocalizationAgent()
rtl_repair_agent = RTLRepairAgent()
verification_judge = VerificationJudge()


# ---------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------

def rtl_analysis_node(state: VerificationState) -> Dict[str, Any]:
    """Analyze RTL structure and potential risk areas."""
    return _run_agent(rtl_analyzer, state)


def planning_node(state: VerificationState) -> Dict[str, Any]:
    """Create verification strategy and coverage plan."""
    return _run_agent(verification_planner, state)


def test_generation_node(state: VerificationState) -> Dict[str, Any]:
    """Generate functional and corner-case tests."""
    return _run_agent(test_generator, state)


def testbench_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Generate executable Verilog/SystemVerilog testbench."""
    return _run_agent(testbench_generator, state)


def simulation_node(state: VerificationState) -> Dict[str, Any]:
    """Compile and execute RTL/testbench using Icarus."""
    return _run_agent(simulator_agent, state)


def failure_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Analyze simulation failures."""
    return _run_agent(failure_analyzer, state)


def coverage_node(state: VerificationState) -> Dict[str, Any]:
    """Analyze coverage and verification gaps."""
    return _run_agent(coverage_agent, state)


def red_team_node(state: VerificationState) -> Dict[str, Any]:
    """Generate adversarial verification scenarios."""
    return _run_agent(red_team_agent, state)


def mutation_node(state: VerificationState) -> Dict[str, Any]:
    """Run mutation testing against the RTL."""
    return _run_agent(mutation_agent, state)


def formal_node(state: VerificationState) -> Dict[str, Any]:
    """Run formal verification where available."""
    return _run_agent(formal_agent, state)


def bug_localization_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Localize likely RTL bug locations."""
    return _run_agent(bug_localization_agent, state)


def rtl_repair_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Propose and validate conservative RTL repair."""
    return _run_agent(rtl_repair_agent, state)


def judge_node(state: VerificationState) -> Dict[str, Any]:
    """Independently judge final verification status."""
    return _run_agent(verification_judge, state)


# ---------------------------------------------------------------------
# Safe router wrappers
# ---------------------------------------------------------------------

def _safe_route(
    router,
    state: VerificationState,
    default: str,
) -> str:
    """
    Execute a router safely.

    If a router throws an exception, route to a conservative
    verification path rather than breaking graph execution.
    """
    try:
        value = router(_safe_state(state))

        if value is None:
            return default

        return str(value)

    except Exception as exc:
        # Preserve routing failure in state where possible.
        # LangGraph conditional routing itself cannot mutate state,
        # therefore the safe fallback is simply returned.
        _ = exc
        return default


def simulation_router(state: VerificationState) -> str:
    """
    Simulation result router.

    PASS  -> coverage
    FAIL  -> failure analysis
    """
    return _safe_route(
        route_after_simulation,
        state,
        "failure_analysis",
    )


def failure_router(state: VerificationState) -> str:
    """
    Failure analysis router.

    Typical destinations:
        test_generation
        rtl_repair
        end
    """
    return _safe_route(
        route_after_failure,
        state,
        "test_generation",
    )


def repair_router(state: VerificationState) -> str:
    """
    Repair router.

    If actual RTL changed:
        bug_localization

    Otherwise:
        test_generation
    """
    return _safe_route(
        route_after_repair,
        state,
        "test_generation",
    )


def coverage_router(state: VerificationState) -> str:
    """
    Coverage router.

    Insufficient coverage:
        test_generation

    Sufficient:
        red_team

    Optional terminal path:
        end
    """
    return _safe_route(
        route_after_coverage,
        state,
        "test_generation",
    )


def mutation_router(state: VerificationState) -> str:
    """
    Mutation router.

    Normally:
        formal

    If mutation/formal is disabled:
        formal/end depending on router implementation.
    """
    return _safe_route(
        route_after_mutation,
        state,
        "formal",
    )


def formal_router(state: VerificationState) -> str:
    """
    Formal verification router.

    Normally:
        judge

    If formal is unavailable:
        judge
    """
    return _safe_route(
        route_after_formal,
        state,
        "judge",
    )


def judge_router(state: VerificationState) -> str:
    """
    Final verification judge router.

    PASS:
        END

    FAIL:
        RTL repair or test generation

    NEED_MORE_VERIFICATION:
        test generation
    """
    return _safe_route(
        route_after_judge,
        state,
        "test_generation",
    )


# ---------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------

def build_workflow():
    """
    Build and compile the PragyanAI SiliconAI verification graph.

    Important:
    Graph construction itself does not require a Groq API key.
    Agents are instantiated once, while model calls happen only
    when individual nodes execute.
    """

    builder = StateGraph(VerificationState)

    # -------------------------------------------------------------
    # Nodes
    # -------------------------------------------------------------

    builder.add_node(
        "rtl_analysis",
        rtl_analysis_node,
    )

    builder.add_node(
        "planning",
        planning_node,
    )

    builder.add_node(
        "test_generation",
        test_generation_node,
    )

    builder.add_node(
        "testbench_generation",
        testbench_generation_node,
    )

    builder.add_node(
        "simulation",
        simulation_node,
    )

    builder.add_node(
        "failure_analysis",
        failure_analysis_node,
    )

    builder.add_node(
        "coverage",
        coverage_node,
    )

    builder.add_node(
        "red_team",
        red_team_node,
    )

    builder.add_node(
        "mutation",
        mutation_node,
    )

    builder.add_node(
        "formal",
        formal_node,
    )

    builder.add_node(
        "bug_localization",
        bug_localization_node,
    )

    builder.add_node(
        "rtl_repair",
        rtl_repair_node,
    )

    builder.add_node(
        "judge",
        judge_node,
    )

    # -------------------------------------------------------------
    # Initial linear flow
    # -------------------------------------------------------------

    builder.add_edge(
        START,
        "rtl_analysis",
    )

    builder.add_edge(
        "rtl_analysis",
        "planning",
    )

    builder.add_edge(
        "planning",
        "test_generation",
    )

    builder.add_edge(
        "test_generation",
        "testbench_generation",
    )

    builder.add_edge(
        "testbench_generation",
        "simulation",
    )

    # -------------------------------------------------------------
    # Simulation routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "simulation",
        simulation_router,
        {
            "coverage": "coverage",
            "failure_analysis": "failure_analysis",
            "test_generation": "test_generation",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # Failure analysis routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "failure_analysis",
        failure_router,
        {
            "test_generation": "test_generation",
            "rtl_repair": "rtl_repair",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # RTL repair routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "rtl_repair",
        repair_router,
        {
            "bug_localization": "bug_localization",
            "test_generation": "test_generation",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # Bug localization
    # -------------------------------------------------------------

    builder.add_edge(
        "bug_localization",
        "test_generation",
    )

    # -------------------------------------------------------------
    # Coverage routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "coverage",
        coverage_router,
        {
            "test_generation": "test_generation",
            "red_team": "red_team",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # Red team
    # -------------------------------------------------------------

    builder.add_edge(
        "red_team",
        "mutation",
    )

    # -------------------------------------------------------------
    # Mutation routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "mutation",
        mutation_router,
        {
            "formal": "formal",
            "judge": "judge",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # Formal routing
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "formal",
        formal_router,
        {
            "judge": "judge",
            "end": LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------
    # Final judge
    # -------------------------------------------------------------

    builder.add_conditional_edges(
        "judge",
        judge_router,
        {
            "end": LANGGRAPH_END,
            "test_generation": "test_generation",
            "rtl_repair": "rtl_repair",
            "bug_localization": "bug_localization",
        },
    )

    # -------------------------------------------------------------
    # Compile
    # -------------------------------------------------------------

    return builder.compile()


# ---------------------------------------------------------------------
# Public workflow object
# ---------------------------------------------------------------------

workflow = None
WORKFLOW_ERROR = None

try:
    workflow = build_workflow()
except Exception as exc:
    import traceback

    WORKFLOW_ERROR = traceback.format_exc()
    workflow = None


# Compatibility aliases
graph = workflow
app = workflow
verification_workflow = workflow
verification_graph = workflow


# ---------------------------------------------------------------------
# Factory aliases
# ---------------------------------------------------------------------

def create_workflow():
    """Create a new compiled verification workflow."""
    return build_workflow()


def build_graph():
    """Compatibility alias for build_workflow()."""
    return build_workflow()


def create_graph():
    """Compatibility alias for build_workflow()."""
    return build_workflow()


# ---------------------------------------------------------------------
# Execution helper
# ---------------------------------------------------------------------

def run_workflow(
    state: VerificationState,
    *,
    stream: bool = False,
):
    """
    Execute the verification workflow.

    Parameters
    ----------
    state:
        Initial VerificationState.

    stream:
        If True, return LangGraph stream output.
        If False, invoke the graph and return final state.
    """

    if workflow is None:
        raise RuntimeError(
            "Verification workflow could not be built.\n\n"
            + (WORKFLOW_ERROR or "Unknown workflow construction error")
        )

    if stream:
        return workflow.stream(
            state,
            stream_mode="updates",
        )

    return workflow.invoke(state)


__all__ = [
    "workflow",
    "graph",
    "app",
    "verification_workflow",
    "verification_graph",
    "build_workflow",
    "create_workflow",
    "build_graph",
    "create_graph",
    "run_workflow",
    "WORKFLOW_ERROR",
]

