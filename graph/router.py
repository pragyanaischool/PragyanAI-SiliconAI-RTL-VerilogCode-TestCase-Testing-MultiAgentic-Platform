"""
PragyanAI SiliconAI
Agentic RTL Verification LangGraph Workflow

IMPORTANT ARCHITECTURE RULE
----------------------------

Routing logic belongs ONLY in:

    graph/router.py

This file is responsible for:

    1. Creating agent instances.
    2. Defining LangGraph nodes.
    3. Connecting nodes.
    4. Calling router functions for conditional edges.
    5. Compiling the graph.

It should NOT contain verification routing decisions.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from langgraph.graph import END as LANGGRAPH_END
from langgraph.graph import START, StateGraph

from graph.state import (
    VerificationState,
    add_agent_log,
    add_agent_trace,
    mark_running,
)

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


# ============================================================================
# Agent imports
# ============================================================================

# Compatibility imports are intentional.
# Different versions of the project may use Agent or non-Agent class names.

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
    from agents.simulator_agent import Simulator

    SimulatorAgent = Simulator


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


# ============================================================================
# Agent construction
# ============================================================================

def _create_agent(
    cls: Any,
) -> Any:
    """
    Safely instantiate an agent.

    Agents in different project revisions may accept different constructor
    signatures, so try the normal constructor first and then fall back to
    an object-level construction where possible.
    """

    try:
        return cls()
    except TypeError:
        try:
            return cls
        except Exception:
            raise


def _build_agents() -> Dict[str, Any]:
    """Create all verification agents."""

    return {
        "rtl_analysis": _create_agent(
            RTLAnalyzerAgent
        ),

        "planning": _create_agent(
            VerificationPlannerAgent
        ),

        "test_generation": _create_agent(
            TestGeneratorAgent
        ),

        "testbench_generation": _create_agent(
            TestbenchGeneratorAgent
        ),

        "simulation": _create_agent(
            SimulatorAgent
        ),

        "failure_analysis": _create_agent(
            FailureAnalyzerAgent
        ),

        "coverage": _create_agent(
            CoverageAgent
        ),

        "red_team": _create_agent(
            RedTeamAgent
        ),

        "mutation": _create_agent(
            MutationAgent
        ),

        "formal": _create_agent(
            FormalAgent
        ),

        "bug_localization": _create_agent(
            BugLocalizationAgent
        ),

        "rtl_repair": _create_agent(
            RTLRepairAgent
        ),

        "judge": _create_agent(
            VerificationJudgeAgent
        ),
    }


# ============================================================================
# Agent execution
# ============================================================================

def _run_agent(
    state: VerificationState,
    agent: Any,
    agent_name: str,
) -> Dict[str, Any]:
    """
    Execute an agent and normalize its output.

    Agents may return:
        - dict
        - VerificationState
        - None

    LangGraph nodes should return a state update dictionary.
    """

    if state is None:
        state = {}

    # Record trace before execution.
    try:
        add_agent_trace(
            state,
            agent_name,
            "start",
        )

        add_agent_log(
            state,
            f"{agent_name}: started",
        )
    except Exception:
        pass

    try:
        # Preferred interface.
        if hasattr(agent, "run"):
            result = agent.run(state)

        # Compatibility with invoke-style agents.
        elif hasattr(agent, "invoke"):
            result = agent.invoke(state)

        # Compatibility with callable agents.
        elif callable(agent):
            result = agent(state)

        else:
            raise TypeError(
                f"Agent '{agent_name}' does not expose "
                "run(), invoke(), or __call__()."
            )

    except Exception as exc:
        message = (
            f"{agent_name} failed: "
            f"{type(exc).__name__}: {exc}"
        )

        try:
            add_agent_trace(
                state,
                agent_name,
                "error",
                message,
            )

            add_agent_log(
                state,
                message,
            )
        except Exception:
            pass

        return {
            "status": "error",
            "errors": [
                *state.get("errors", []),
                message,
            ],
            "error": message,
        }

    # ------------------------------------------------------------------------
    # Normalize agent output.
    # ------------------------------------------------------------------------

    if result is None:
        result = {}

    if not isinstance(result, dict):
        try:
            result = dict(result)
        except Exception:
            result = {
                "agent_output": result,
            }

    update: Dict[str, Any] = dict(result)

    # Keep workflow status alive unless an agent explicitly changed it.
    if "status" not in update:
        update["status"] = "running"

    try:
        add_agent_trace(
            state,
            agent_name,
            "complete",
        )

        add_agent_log(
            state,
            f"{agent_name}: completed",
        )
    except Exception:
        pass

    return update


# ============================================================================
# Node functions
# ============================================================================

def _rtl_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["rtl_analysis"],
        "rtl_analysis",
    )


def _planning_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["planning"],
        "planning",
    )


def _test_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["test_generation"],
        "test_generation",
    )


def _testbench_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["testbench_generation"],
        "testbench_generation",
    )


def _simulation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["simulation"],
        "simulation",
    )


def _failure_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["failure_analysis"],
        "failure_analysis",
    )


def _coverage_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["coverage"],
        "coverage",
    )


def _red_team_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["red_team"],
        "red_team",
    )


def _mutation_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["mutation"],
        "mutation",
    )


def _formal_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["formal"],
        "formal",
    )


def _bug_localization_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["bug_localization"],
        "bug_localization",
    )


def _rtl_repair_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["rtl_repair"],
        "rtl_repair",
    )


def _judge_node(
    state: VerificationState,
) -> Dict[str, Any]:
    return _run_agent(
        state,
        AGENTS["judge"],
        "judge",
    )


# ============================================================================
# Conditional-edge adapters
# ============================================================================

def _simulation_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_simulation(state)
    )


def _failure_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_failure(state)
    )


def _repair_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_repair(state)
    )


def _bug_localization_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_bug_localization(state)
    )


def _coverage_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_coverage(state)
    )


def _red_team_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_red_team(state)
    )


def _mutation_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_mutation(state)
    )


def _formal_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_formal(state)
    )


def _judge_route(
    state: VerificationState,
) -> str:
    return _router_to_langgraph(
        route_after_judge(state)
    )


def _router_to_langgraph(
    destination: str,
) -> str:
    """
    Convert router.py's END marker to LangGraph's END sentinel.

    All other node names pass through unchanged.
    """

    if destination == ROUTER_END:
        return LANGGRAPH_END

    return destination


# ============================================================================
# Graph construction
# ============================================================================

def build_workflow(
    agents: Optional[Dict[str, Any]] = None,
):
    """
    Build and compile the complete verification workflow.
    """

    global AGENTS

    if agents is None:
        agents = _build_agents()

    AGENTS = agents

    graph = StateGraph(VerificationState)

    # ------------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------------

    graph.add_node(
        "rtl_analysis",
        _rtl_analysis_node,
    )

    graph.add_node(
        "planning",
        _planning_node,
    )

    graph.add_node(
        "test_generation",
        _test_generation_node,
    )

    graph.add_node(
        "testbench_generation",
        _testbench_generation_node,
    )

    graph.add_node(
        "simulation",
        _simulation_node,
    )

    graph.add_node(
        "failure_analysis",
        _failure_analysis_node,
    )

    graph.add_node(
        "coverage",
        _coverage_node,
    )

    graph.add_node(
        "red_team",
        _red_team_node,
    )

    graph.add_node(
        "mutation",
        _mutation_node,
    )

    graph.add_node(
        "formal",
        _formal_node,
    )

    graph.add_node(
        "bug_localization",
        _bug_localization_node,
    )

    graph.add_node(
        "rtl_repair",
        _rtl_repair_node,
    )

    graph.add_node(
        "judge",
        _judge_node,
    )

    # ------------------------------------------------------------------------
    # Initial linear pipeline
    #
    # START
    #   ↓
    # RTL Analysis
    #   ↓
    # Planning
    #   ↓
    # Test Generation
    #   ↓
    # Testbench Generation
    #   ↓
    # Simulation
    # ------------------------------------------------------------------------

    graph.add_edge(
        START,
        "rtl_analysis",
    )

    graph.add_edge(
        "rtl_analysis",
        "planning",
    )

    graph.add_edge(
        "planning",
        "test_generation",
    )

    graph.add_edge(
        "test_generation",
        "testbench_generation",
    )

    graph.add_edge(
        "testbench_generation",
        "simulation",
    )

    # ------------------------------------------------------------------------
    # Simulation routing
    #
    # This routing decision is implemented ONLY in router.py.
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "simulation",
        _simulation_route,
        {
            "coverage": "coverage",
            "failure_analysis": "failure_analysis",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Failure analysis routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "failure_analysis",
        _failure_route,
        {
            "rtl_repair": "rtl_repair",
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # RTL repair routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "rtl_repair",
        _repair_route,
        {
            "bug_localization": "bug_localization",
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Bug localization
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "bug_localization",
        _bug_localization_route,
        {
            "test_generation": "test_generation",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Coverage routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "coverage",
        _coverage_route,
        {
            "test_generation": "test_generation",
            "red_team": "red_team",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Red-team routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "red_team",
        _red_team_route,
        {
            "mutation": "mutation",
            "formal": "formal",
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Mutation routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "mutation",
        _mutation_route,
        {
            "formal": "formal",
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Formal routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "formal",
        _formal_route,
        {
            "judge": "judge",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # ------------------------------------------------------------------------
    # Judge routing
    # ------------------------------------------------------------------------

    graph.add_conditional_edges(
        "judge",
        _judge_route,
        {
            "rtl_repair": "rtl_repair",
            "test_generation": "test_generation",
            "bug_localization": "bug_localization",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    return graph.compile()


# ============================================================================
# Build default workflow
# ============================================================================

AGENTS: Dict[str, Any] = {}

WORKFLOW_ERROR: Optional[Exception] = None


try:
    workflow = build_workflow()

except Exception as exc:
    WORKFLOW_ERROR = exc
    workflow = None


# ============================================================================
# Compatibility aliases
# ============================================================================

graph = workflow
app = workflow

verification_workflow = workflow
verification_graph = workflow


def create_workflow():
    """Compatibility factory."""

    return build_workflow()


def create_graph():
    """Compatibility factory."""

    return build_workflow()


def build_graph():
    """Compatibility factory."""

    return build_workflow()


# IMPORTANT:
# graph/__init__.py from earlier versions may import this exact name.

def build_verification_workflow():
    """Backward-compatible verification workflow factory."""

    return build_workflow()


def create_verification_workflow():
    """Backward-compatible verification workflow factory."""

    return build_workflow()


# ============================================================================
# Workflow execution helper
# ============================================================================

def run_workflow(
    state: VerificationState,
    **kwargs: Any,
) -> Any:
    """
    Execute the compiled workflow.

    This helper is intentionally compatible with both:
        workflow.invoke(...)
        workflow.stream(...)
    """

    if workflow is None:
        raise RuntimeError(
            "Verification workflow could not be loaded."
        ) from WORKFLOW_ERROR

    return workflow.invoke(
        state,
        **kwargs,
    )


# ============================================================================
# Public exports
# ============================================================================

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

    "build_verification_workflow",
    "create_verification_workflow",

    "run_workflow",

    "AGENTS",
    "WORKFLOW_ERROR",
]

