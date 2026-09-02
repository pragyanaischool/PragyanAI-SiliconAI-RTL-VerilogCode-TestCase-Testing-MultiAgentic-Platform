"""
PragyanAI SiliconAI
Agentic RTL Verification Workflow

File:
    graph/workflow.py

Architecture:
    - graph/state.py   -> shared workflow state
    - graph/router.py  -> ALL routing / decision logic
    - graph/workflow.py -> graph construction + node execution ONLY

IMPORTANT:
    Do not put verification routing decisions in this file.

The workflow connects:

    START
      |
      v
    RTL Analysis
      |
      v
    Verification Planning
      |
      v
    Test Generation
      |
      v
    Testbench Generation
      |
      v
    Simulation
      |
      +--------------------+
      |                    |
      | PASS               | FAIL
      v                    v
    Coverage         Failure Analysis
      |                    |
      |                    +----------+
      |                               |
      |                         RTL problem?
      |                               |
      |                         RTL Repair
      |                               |
      |                         Bug Localization
      |                               |
      +-------------------------------+
      |
      v
    Red Team
      |
      v
    Mutation (optional)
      |
      v
    Formal (optional)
      |
      v
    Judge
      |
      +----------------+
      |                |
     PASS             FAIL
      |                |
     END         Test Generation /
                RTL Repair
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import END as LANGGRAPH_END
from langgraph.graph import START, StateGraph

from graph.state import VerificationState

from graph.router import (
    END as ROUTER_END,
    route_after_simulation,
    route_after_failure,
    route_after_repair,
    route_after_bug_localization,
    route_after_coverage,
    route_after_red_team,
    route_after_mutation,
    route_after_formal,
    route_after_judge,
)


# =============================================================================
# Agent imports
# =============================================================================

# The project has gone through a few naming revisions. These imports support
# both Agent-suffixed and legacy class names.

try:
    from agents.rtl_analyzer import RTLAnalyzerAgent
except ImportError:
    from agents.rtl_analyzer import RTLAnalyzer

    RTLAnalyzerAgent = RTLAnalyzer


try:
    from agents.verification_planner import VerificationPlannerAgent
except ImportError:
    from agents.verification_planner import VerificationPlanner

    VerificationPlannerAgent = VerificationPlanner


try:
    from agents.test_generator import TestGeneratorAgent
except ImportError:
    from agents.test_generator import TestGenerator

    TestGeneratorAgent = TestGenerator


try:
    from agents.testbench_generator import TestbenchGeneratorAgent
except ImportError:
    from agents.testbench_generator import TestbenchGenerator

    TestbenchGeneratorAgent = TestbenchGenerator


try:
    from agents.simulator_agent import SimulatorAgent
except ImportError:
    try:
        from agents.simulator_agent import Simulator
        SimulatorAgent = Simulator
    except ImportError:
        from agents.simulator_agent import SimulatorAgent as SimulatorAgent


try:
    from agents.failure_analyzer import FailureAnalyzerAgent
except ImportError:
    from agents.failure_analyzer import FailureAnalyzer

    FailureAnalyzerAgent = FailureAnalyzer


try:
    from agents.coverage_agent import CoverageAgent
except ImportError:
    from agents.coverage_agent import Coverage

    CoverageAgent = Coverage


try:
    from agents.red_team_agent import RedTeamAgent
except ImportError:
    from agents.red_team_agent import RedTeam

    RedTeamAgent = RedTeam


try:
    from agents.mutation_agent import MutationAgent
except ImportError:
    from agents.mutation_agent import Mutation

    MutationAgent = Mutation


try:
    from agents.formal_agent import FormalAgent
except ImportError:
    from agents.formal_agent import Formal

    FormalAgent = Formal


try:
    from agents.bug_localization_agent import BugLocalizationAgent
except ImportError:
    from agents.bug_localization_agent import BugLocalization

    BugLocalizationAgent = BugLocalization


try:
    from agents.rtl_repair_agent import RTLRepairAgent
except ImportError:
    from agents.rtl_repair_agent import RTLRepair

    RTLRepairAgent = RTLRepair


try:
    from agents.verification_judge import VerificationJudgeAgent
except ImportError:
    from agents.verification_judge import VerificationJudge

    VerificationJudgeAgent = VerificationJudge


# =============================================================================
# Globals
# =============================================================================

AGENTS: Dict[str, Any] = {}

WORKFLOW_ERROR: Optional[Exception] = None


# =============================================================================
# Agent creation
# =============================================================================

def _instantiate_agent(agent_class: Any) -> Any:
    """
    Instantiate an agent.

    Normal project agents use:

        Agent()

    A small compatibility fallback is included for legacy implementations.
    """

    if agent_class is None:
        raise ValueError("Agent class is None.")

    # Normal constructor.
    try:
        return agent_class()
    except TypeError as first_error:

        # Some older implementations may expose a class-like singleton.
        if hasattr(agent_class, "run"):
            return agent_class

        raise first_error


def create_agents() -> Dict[str, Any]:
    """
    Create all verification agents.

    Returns
    -------
    dict
        Mapping between workflow node names and agent instances.
    """

    return {
        "rtl_analysis": _instantiate_agent(
            RTLAnalyzerAgent
        ),

        "planning": _instantiate_agent(
            VerificationPlannerAgent
        ),

        "test_generation": _instantiate_agent(
            TestGeneratorAgent
        ),

        "testbench_generation": _instantiate_agent(
            TestbenchGeneratorAgent
        ),

        "simulation": _instantiate_agent(
            SimulatorAgent
        ),

        "failure_analysis": _instantiate_agent(
            FailureAnalyzerAgent
        ),

        "coverage": _instantiate_agent(
            CoverageAgent
        ),

        "red_team": _instantiate_agent(
            RedTeamAgent
        ),

        "mutation": _instantiate_agent(
            MutationAgent
        ),

        "formal": _instantiate_agent(
            FormalAgent
        ),

        "bug_localization": _instantiate_agent(
            BugLocalizationAgent
        ),

        "rtl_repair": _instantiate_agent(
            RTLRepairAgent
        ),

        "judge": _instantiate_agent(
            VerificationJudgeAgent
        ),
    }


# =============================================================================
# Agent execution adapter
# =============================================================================

def _execute_agent(
    agent: Any,
    state: VerificationState,
    agent_name: str,
) -> Dict[str, Any]:
    """
    Execute one agent and normalize its output.

    Supported agent interfaces:

        agent.run(state)
        agent.invoke(state)
        agent(state)

    The workflow itself does not interpret the agent result.
    Routing remains exclusively in graph/router.py.
    """

    if state is None:
        state = {}

    try:

        # -------------------------------------------------------------
        # Preferred interface
        # -------------------------------------------------------------

        if hasattr(agent, "run"):
            result = agent.run(state)

        # -------------------------------------------------------------
        # LangChain-style interface
        # -------------------------------------------------------------

        elif hasattr(agent, "invoke"):
            result = agent.invoke(state)

        # -------------------------------------------------------------
        # Callable fallback
        # -------------------------------------------------------------

        elif callable(agent):
            result = agent(state)

        else:
            raise TypeError(
                f"Agent '{agent_name}' does not provide "
                "run(), invoke(), or callable interface."
            )

        # -------------------------------------------------------------
        # Normalize result
        # -------------------------------------------------------------

        if result is None:
            return {}

        if isinstance(result, dict):
            return result

        try:
            return dict(result)
        except Exception:
            return {
                "agent_output": result,
            }

    except Exception as exc:

        error_message = (
            f"{agent_name} failed: "
            f"{type(exc).__name__}: {exc}"
        )

        # Do not raise here.
        #
        # Returning an error state allows the Streamlit application
        # to display the failure cleanly rather than crashing.
        return {
            "status": "error",
            "error": error_message,
            "errors": [
                *state.get("errors", []),
                error_message,
            ],
        }


# =============================================================================
# Individual LangGraph nodes
# =============================================================================

def rtl_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run RTL analysis agent."""

    return _execute_agent(
        AGENTS["rtl_analysis"],
        state,
        "rtl_analysis",
    )


def planning_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run verification planning agent."""

    return _execute_agent(
        AGENTS["planning"],
        state,
        "planning",
    )


def test_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run test generation agent."""

    return _execute_agent(
        AGENTS["test_generation"],
        state,
        "test_generation",
    )


def testbench_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run testbench generation agent."""

    return _execute_agent(
        AGENTS["testbench_generation"],
        state,
        "testbench_generation",
    )


def simulation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run RTL simulation."""

    return _execute_agent(
        AGENTS["simulation"],
        state,
        "simulation",
    )


def failure_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Analyze simulation failure."""

    return _execute_agent(
        AGENTS["failure_analysis"],
        state,
        "failure_analysis",
    )


def coverage_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Analyze functional / verification coverage."""

    return _execute_agent(
        AGENTS["coverage"],
        state,
        "coverage",
    )


def red_team_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run adversarial / corner-case verification."""

    return _execute_agent(
        AGENTS["red_team"],
        state,
        "red_team",
    )


def mutation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run mutation testing."""

    return _execute_agent(
        AGENTS["mutation"],
        state,
        "mutation",
    )


def formal_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """
    Run optional formal verification.

    Formal availability is handled by the formal agent itself.
    No SymbiYosys requirement is introduced here.
    """

    return _execute_agent(
        AGENTS["formal"],
        state,
        "formal",
    )


def bug_localization_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Locate likely RTL bug."""

    return _execute_agent(
        AGENTS["bug_localization"],
        state,
        "bug_localization",
    )


def rtl_repair_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Generate/apply RTL repair."""

    return _execute_agent(
        AGENTS["rtl_repair"],
        state,
        "rtl_repair",
    )


def judge_node(
    state: VerificationState,
) -> Dict[str, Any]:
    """Run final verification judge."""

    return _execute_agent(
        AGENTS["judge"],
        state,
        "judge",
    )


# =============================================================================
# Router adapters
# =============================================================================

def _convert_router_result(
    result: str,
) -> str:
    """
    Convert router.py's internal END marker to LangGraph END.

    router.py returns:

        "end"

    LangGraph expects:

        END

    All other node names are returned unchanged.
    """

    if result == ROUTER_END:
        return LANGGRAPH_END

    return result


def simulation_router(
    state: VerificationState,
) -> str:
    """Delegate simulation routing to graph.router."""

    return _convert_router_result(
        route_after_simulation(state)
    )


def failure_router(
    state: VerificationState,
) -> str:
    """Delegate failure routing to graph.router."""

    return _convert_router_result(
        route_after_failure(state)
    )


def repair_router(
    state: VerificationState,
) -> str:
    """Delegate RTL repair routing to graph.router."""

    return _convert_router_result(
        route_after_repair(state)
    )


def bug_localization_router(
    state: VerificationState,
) -> str:
    """Delegate bug localization routing to graph.router."""

    return _convert_router_result(
        route_after_bug_localization(state)
    )


def coverage_router(
    state: VerificationState,
) -> str:
    """Delegate coverage routing to graph.router."""

    return _convert_router_result(
        route_after_coverage(state)
    )


def red_team_router(
    state: VerificationState,
) -> str:
    """Delegate red-team routing to graph.router."""

    return _convert_router_result(
        route_after_red_team(state)
    )


def mutation_router(
    state: VerificationState,
) -> str:
    """Delegate mutation routing to graph.router."""

    return _convert_router_result(
        route_after_mutation(state)
    )


def formal_router(
    state: VerificationState,
) -> str:
    """Delegate formal routing to graph.router."""

    return _convert_router_result(
        route_after_formal(state)
    )


def judge_router(
    state: VerificationState,
) -> str:
    """Delegate final judge routing to graph.router."""

    return _convert_router_result(
        route_after_judge(state)
    )


# =============================================================================
# Graph builder
# =============================================================================

def build_workflow(
    agents: Optional[Dict[str, Any]] = None,
):
    """
    Build and compile the PragyanAI SiliconAI verification graph.

    Parameters
    ----------
    agents:
        Optional agent dictionary.

        Primarily useful for testing and dependency injection.

    Returns
    -------
    CompiledStateGraph
        Compiled LangGraph workflow.
    """

    global AGENTS

    # -------------------------------------------------------------------------
    # Agents
    # -------------------------------------------------------------------------

    if agents is None:
        AGENTS = create_agents()
    else:
        AGENTS = agents

    # -------------------------------------------------------------------------
    # State graph
    # -------------------------------------------------------------------------

    builder = StateGraph(
        VerificationState
    )

    # -------------------------------------------------------------------------
    # Nodes
    # -------------------------------------------------------------------------

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

    # =========================================================================
    # Main pipeline
    # =========================================================================

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

    # =========================================================================
    # Simulation -> Coverage / Failure Analysis
    #
    # ALL DECISION LOGIC IS IN graph/router.py
    # =========================================================================

    builder.add_conditional_edges(
        "simulation",
        simulation_router,
        {
            "coverage": "coverage",
            "failure_analysis": "failure_analysis",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Failure Analysis -> RTL Repair / Test Generation / END
    # =========================================================================

    builder.add_conditional_edges(
        "failure_analysis",
        failure_router,
        {
            "rtl_repair": "rtl_repair",
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # RTL Repair -> Bug Localization / Test Generation / END
    # =========================================================================

    builder.add_conditional_edges(
        "rtl_repair",
        repair_router,
        {
            "bug_localization": "bug_localization",
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Bug Localization -> Test Generation
    # =========================================================================

    builder.add_conditional_edges(
        "bug_localization",
        bug_localization_router,
        {
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Coverage -> Test Generation / Red Team / END
    # =========================================================================

    builder.add_conditional_edges(
        "coverage",
        coverage_router,
        {
            "test_generation": "test_generation",
            "red_team": "red_team",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Red Team -> Mutation / Formal / Judge / END
    # =========================================================================

    builder.add_conditional_edges(
        "red_team",
        red_team_router,
        {
            "mutation": "mutation",
            "formal": "formal",
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Mutation -> Formal / Judge / END
    # =========================================================================

    builder.add_conditional_edges(
        "mutation",
        mutation_router,
        {
            "formal": "formal",
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Formal -> Judge / END
    # =========================================================================

    builder.add_conditional_edges(
        "formal",
        formal_router,
        {
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # Judge -> END / Test Generation / RTL Repair / Bug Localization
    # =========================================================================

    builder.add_conditional_edges(
        "judge",
        judge_router,
        {
            LANGGRAPH_END: LANGGRAPH_END,
            "test_generation": "test_generation",
            "rtl_repair": "rtl_repair",
            "bug_localization": "bug_localization",
        },
    )

    # =========================================================================
    # Compile
    # =========================================================================

    return builder.compile()


# =============================================================================
# Default compiled workflow
# =============================================================================

try:
    workflow = build_workflow()

except Exception as exc:
    WORKFLOW_ERROR = exc
    workflow = None


# =============================================================================
# Compatibility aliases
# =============================================================================

# Existing main_app.py may use any of these names.

graph = workflow

app = workflow

verification_workflow = workflow

verification_graph = workflow


# =============================================================================
# Factory functions
# =============================================================================

def create_workflow():
    """Create a fresh compiled workflow."""

    return build_workflow()


def create_graph():
    """Create a fresh compiled graph."""

    return build_workflow()


def build_graph():
    """Compatibility alias for build_workflow."""

    return build_workflow()


def build_verification_workflow():
    """
    Compatibility alias.

    Older graph/__init__.py versions may import this name.
    """

    return build_workflow()


def create_verification_workflow():
    """
    Compatibility alias.

    Older application code may import this name.
    """

    return build_workflow()


# =============================================================================
# Workflow execution
# =============================================================================

def run_workflow(
    state: VerificationState,
    **kwargs: Any,
) -> Any:
    """
    Execute the compiled workflow synchronously.

    Parameters
    ----------
    state:
        Initial VerificationState.

    kwargs:
        Optional LangGraph invoke configuration.

    Returns
    -------
    dict
        Final workflow state.
    """

    if workflow is None:

        if WORKFLOW_ERROR is not None:
            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is not available."
        )

    return workflow.invoke(
        state,
        **kwargs,
    )


def stream_workflow(
    state: VerificationState,
    **kwargs: Any,
):
    """
    Stream workflow updates.

    This is useful for Streamlit UI and agent trace display.
    """

    if workflow is None:

        if WORKFLOW_ERROR is not None:
            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is not available."
        )

    return workflow.stream(
        state,
        **kwargs,
    )


# =============================================================================
# Diagnostic helpers
# =============================================================================

def workflow_is_available() -> bool:
    """Return True when workflow compiled successfully."""

    return workflow is not None


def get_workflow_error() -> Optional[Exception]:
    """Return workflow construction error, if any."""

    return WORKFLOW_ERROR


def get_agent_names():
    """Return configured agent names."""

    return list(AGENTS.keys())


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    # Compiled workflow
    "workflow",
    "graph",
    "app",
    "verification_workflow",
    "verification_graph",

    # Agent management
    "AGENTS",
    "create_agents",

    # Node functions
    "rtl_analysis_node",
    "planning_node",
    "test_generation_node",
    "testbench_generation_node",
    "simulation_node",
    "failure_analysis_node",
    "coverage_node",
    "red_team_node",
    "mutation_node",
    "formal_node",
    "bug_localization_node",
    "rtl_repair_node",
    "judge_node",

    # Router adapters
    "simulation_router",
    "failure_router",
    "repair_router",
    "bug_localization_router",
    "coverage_router",
    "red_team_router",
    "mutation_router",
    "formal_router",
    "judge_router",

    # Builders
    "build_workflow",
    "create_workflow",
    "create_graph",
    "build_graph",
    "build_verification_workflow",
    "create_verification_workflow",

    # Execution
    "run_workflow",
    "stream_workflow",

    # Diagnostics
    "workflow_is_available",
    "get_workflow_error",
    "get_agent_names",

    # Errors
    "WORKFLOW_ERROR",
]


