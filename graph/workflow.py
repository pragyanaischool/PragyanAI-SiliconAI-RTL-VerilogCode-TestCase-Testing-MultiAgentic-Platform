"""
PragyanAI SiliconAI
Agentic RTL Verification LangGraph Workflow

IMPORTANT
---------

Routing logic belongs ONLY to:

    graph/router.py

This file is responsible for:

    - agent construction
    - LangGraph node construction
    - graph connectivity
    - calling router functions
    - compiling the graph

It does NOT decide:
    - whether simulation passed
    - whether coverage is sufficient
    - whether RTL should be repaired
    - whether mutation should run
    - whether formal should run
    - whether verification passed
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import (
    END as LANGGRAPH_END,
    START,
    StateGraph,
)

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
        SimulatorAgent = None


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
# Global agent registry
# =============================================================================

AGENTS: Dict[str, Any] = {}

WORKFLOW_ERROR: Optional[Exception] = None


# =============================================================================
# Agent creation
# =============================================================================

def _instantiate_agent(
    agent_class: Any,
) -> Any:

    if agent_class is None:
        raise ImportError(
            "Required agent class is unavailable."
        )

    try:
        return agent_class()
    except TypeError:

        if hasattr(
            agent_class,
            "run",
        ):
            return agent_class

        raise


def create_agents() -> Dict[str, Any]:

    return {

        "rtl_analysis":
            _instantiate_agent(
                RTLAnalyzerAgent
            ),

        "planning":
            _instantiate_agent(
                VerificationPlannerAgent
            ),

        "test_generation":
            _instantiate_agent(
                TestGeneratorAgent
            ),

        "testbench_generation":
            _instantiate_agent(
                TestbenchGeneratorAgent
            ),

        "simulation":
            _instantiate_agent(
                SimulatorAgent
            ),

        "failure_analysis":
            _instantiate_agent(
                FailureAnalyzerAgent
            ),

        "coverage":
            _instantiate_agent(
                CoverageAgent
            ),

        "red_team":
            _instantiate_agent(
                RedTeamAgent
            ),

        "mutation":
            _instantiate_agent(
                MutationAgent
            ),

        "formal":
            _instantiate_agent(
                FormalAgent
            ),

        "bug_localization":
            _instantiate_agent(
                BugLocalizationAgent
            ),

        "rtl_repair":
            _instantiate_agent(
                RTLRepairAgent
            ),

        "judge":
            _instantiate_agent(
                VerificationJudgeAgent
            ),
    }


# =============================================================================
# Agent execution
# =============================================================================

def _execute_agent(
    agent: Any,
    state: VerificationState,
    agent_name: str,
) -> Dict[str, Any]:

    if state is None:
        state = {}

    try:

        if hasattr(
            agent,
            "run",
        ):

            result = agent.run(
                state
            )

        elif hasattr(
            agent,
            "invoke",
        ):

            result = agent.invoke(
                state
            )

        elif callable(agent):

            result = agent(
                state
            )

        else:

            raise TypeError(
                f"Agent '{agent_name}' does not "
                "support run(), invoke(), or callable."
            )

        if result is None:
            return {}

        if isinstance(
            result,
            dict,
        ):
            return result

        try:
            return dict(result)
        except Exception:

            return {
                "agent_output": result
            }

    except Exception as exc:

        message = (
            f"{agent_name} failed: "
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "status": "error",
            "error": message,
            "errors": [
                *state.get(
                    "errors",
                    [],
                ),
                message,
            ],
        }


# =============================================================================
# Nodes
# =============================================================================

def rtl_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["rtl_analysis"],
        state,
        "rtl_analysis",
    )


def planning_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["planning"],
        state,
        "planning",
    )


def test_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["test_generation"],
        state,
        "test_generation",
    )


def testbench_generation_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["testbench_generation"],
        state,
        "testbench_generation",
    )


def simulation_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["simulation"],
        state,
        "simulation",
    )


def failure_analysis_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["failure_analysis"],
        state,
        "failure_analysis",
    )


def coverage_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["coverage"],
        state,
        "coverage",
    )


def red_team_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["red_team"],
        state,
        "red_team",
    )


def mutation_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["mutation"],
        state,
        "mutation",
    )


def formal_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["formal"],
        state,
        "formal",
    )


def bug_localization_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["bug_localization"],
        state,
        "bug_localization",
    )


def rtl_repair_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["rtl_repair"],
        state,
        "rtl_repair",
    )


def judge_node(
    state: VerificationState,
) -> Dict[str, Any]:

    return _execute_agent(
        AGENTS["judge"],
        state,
        "judge",
    )


# =============================================================================
# Router adapters
# =============================================================================

def _langgraph_destination(
    destination: str,
) -> str:

    if destination == ROUTER_END:
        return LANGGRAPH_END

    return destination


def simulation_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_simulation(
            state
        )
    )


def failure_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_failure(
            state
        )
    )


def repair_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_repair(
            state
        )
    )


def bug_localization_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_bug_localization(
            state
        )
    )


def coverage_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_coverage(
            state
        )
    )


def red_team_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_red_team(
            state
        )
    )


def mutation_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_mutation(
            state
        )
    )


def formal_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_formal(
            state
        )
    )


def judge_router(
    state: VerificationState,
) -> str:

    return _langgraph_destination(
        route_after_judge(
            state
        )
    )


# =============================================================================
# Build workflow
# =============================================================================

def build_workflow(
    agents: Optional[
        Dict[str, Any]
    ] = None,
):

    global AGENTS

    if agents is None:
        AGENTS = create_agents()
    else:
        AGENTS = agents

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

    # -------------------------------------------------------------------------
    # Initial pipeline
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "simulation",
        simulation_router,
        {
            "coverage":
                "coverage",

            "failure_analysis":
                "failure_analysis",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Failure analysis
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "failure_analysis",
        failure_router,
        {
            "rtl_repair":
                "rtl_repair",

            "test_generation":
                "test_generation",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Repair
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "rtl_repair",
        repair_router,
        {
            "bug_localization":
                "bug_localization",

            "test_generation":
                "test_generation",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Bug localization
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "bug_localization",
        bug_localization_router,
        {
            "test_generation":
                "test_generation",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Coverage
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "coverage",
        coverage_router,
        {
            "test_generation":
                "test_generation",

            "red_team":
                "red_team",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Red team
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "red_team",
        red_team_router,
        {
            "mutation":
                "mutation",

            "formal":
                "formal",

            "judge":
                "judge",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Mutation
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "mutation",
        mutation_router,
        {
            "formal":
                "formal",

            "judge":
                "judge",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Formal
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "formal",
        formal_router,
        {
            "judge":
                "judge",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Judge
    # -------------------------------------------------------------------------

    builder.add_conditional_edges(
        "judge",
        judge_router,
        {
            "rtl_repair":
                "rtl_repair",

            "test_generation":
                "test_generation",

            "bug_localization":
                "bug_localization",

            LANGGRAPH_END:
                LANGGRAPH_END,
        },
    )

    # -------------------------------------------------------------------------
    # Compile
    # -------------------------------------------------------------------------

    return builder.compile()


# =============================================================================
# Default workflow
# =============================================================================

try:

    workflow = build_workflow()

except Exception as exc:

    WORKFLOW_ERROR = exc
    workflow = None


# =============================================================================
# Compatibility aliases
# =============================================================================

graph = workflow
app = workflow

verification_workflow = workflow
verification_graph = workflow


# =============================================================================
# Factory functions
# =============================================================================

def create_workflow():
    return build_workflow()


def create_graph():
    return build_workflow()


def build_graph():
    return build_workflow()


def build_verification_workflow():
    return build_workflow()


def create_verification_workflow():
    return build_workflow()


# =============================================================================
# Execution
# =============================================================================

def run_workflow(
    state: VerificationState,
    **kwargs: Any,
):

    if workflow is None:

        if WORKFLOW_ERROR is not None:

            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is unavailable."
        )

    return workflow.invoke(
        state,
        **kwargs,
    )


def stream_workflow(
    state: VerificationState,
    **kwargs: Any,
):

    if workflow is None:

        if WORKFLOW_ERROR is not None:

            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is unavailable."
        )

    return workflow.stream(
        state,
        **kwargs,
    )


# =============================================================================
# Diagnostics
# =============================================================================

def workflow_is_available() -> bool:
    return workflow is not None


def get_workflow_error():
    return WORKFLOW_ERROR


def get_agent_names():
    return list(
        AGENTS.keys()
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [

    "workflow",
    "graph",
    "app",

    "verification_workflow",
    "verification_graph",

    "AGENTS",
    "WORKFLOW_ERROR",

    "create_agents",

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

    "simulation_router",
    "failure_router",
    "repair_router",
    "bug_localization_router",
    "coverage_router",
    "red_team_router",
    "mutation_router",
    "formal_router",
    "judge_router",

    "build_workflow",
    "create_workflow",
    "create_graph",
    "build_graph",

    "build_verification_workflow",
    "create_verification_workflow",

    "run_workflow",
    "stream_workflow",

    "workflow_is_available",
    "get_workflow_error",
    "get_agent_names",
]

