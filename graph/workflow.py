"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

LangGraph verification workflow.

High-level flow:

Specification
      ↓
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
Red Team
      ↓
Mutation
      ↓
Verification Judge
      ↓
Sign-off / Loop
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from langgraph.graph import END, StateGraph

from .state import VerificationState
from .router import (
    route_after_simulation,
    route_after_failure_analysis,
    route_after_coverage,
    route_after_judge,
)


# ---------------------------------------------------------------------
# Generic node wrapper
# ---------------------------------------------------------------------

def _default_node(
    name: str,
) -> Callable:

    def node(
        state: VerificationState,
    ) -> Dict[str, Any]:

        trace = list(
            state.get(
                "agent_trace",
                [],
            )
        )

        trace.append(
            {
                "agent": name,
                "status": "COMPLETED",
                "message": (
                    f"{name} executed using default node."
                ),
            }
        )

        return {
            "agent_trace": trace,
        }

    return node


# ---------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------

def build_verification_workflow(
    rtl_analyzer: Optional[Callable] = None,
    verification_planner: Optional[Callable] = None,
    test_generator: Optional[Callable] = None,
    testbench_generator: Optional[Callable] = None,
    simulator: Optional[Callable] = None,
    failure_analyzer: Optional[Callable] = None,
    coverage_agent: Optional[Callable] = None,
    red_team_agent: Optional[Callable] = None,
    mutation_agent: Optional[Callable] = None,
    formal_agent: Optional[Callable] = None,
    bug_localization_agent: Optional[Callable] = None,
    rtl_repair_agent: Optional[Callable] = None,
    verification_judge: Optional[Callable] = None,
):
    """
    Build the complete LangGraph verification workflow.

    Every argument is a callable that receives the current state
    and returns a state update dictionary.
    """

    # ---------------------------------------------------------------
    # Defaults
    # ---------------------------------------------------------------

    rtl_analyzer = (
        rtl_analyzer
        or _default_node("RTL Analyzer")
    )

    verification_planner = (
        verification_planner
        or _default_node("Verification Planner")
    )

    test_generator = (
        test_generator
        or _default_node("Test Generator")
    )

    testbench_generator = (
        testbench_generator
        or _default_node("Testbench Generator")
    )

    simulator = (
        simulator
        or _default_node("Simulation Agent")
    )

    failure_analyzer = (
        failure_analyzer
        or _default_node("Failure Analyzer")
    )

    coverage_agent = (
        coverage_agent
        or _default_node("Coverage Agent")
    )

    red_team_agent = (
        red_team_agent
        or _default_node("Red Team Agent")
    )

    mutation_agent = (
        mutation_agent
        or _default_node("Mutation Agent")
    )

    formal_agent = (
        formal_agent
        or _default_node("Formal Agent")
    )

    bug_localization_agent = (
        bug_localization_agent
        or _default_node("Bug Localization Agent")
    )

    rtl_repair_agent = (
        rtl_repair_agent
        or _default_node("RTL Repair Agent")
    )

    verification_judge = (
        verification_judge
        or _default_node("Verification Judge")
    )

    # ---------------------------------------------------------------
    # Graph
    # ---------------------------------------------------------------

    graph = StateGraph(
        VerificationState
    )

    # ---------------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------------

    graph.add_node(
        "rtl_analysis",
        rtl_analyzer,
    )

    graph.add_node(
        "verification_planning",
        verification_planner,
    )

    graph.add_node(
        "test_generation",
        test_generator,
    )

    graph.add_node(
        "testbench_generation",
        testbench_generator,
    )

    graph.add_node(
        "simulation",
        simulator,
    )

    graph.add_node(
        "failure_analysis",
        failure_analyzer,
    )

    graph.add_node(
        "coverage",
        coverage_agent,
    )

    graph.add_node(
        "red_team",
        red_team_agent,
    )

    graph.add_node(
        "mutation",
        mutation_agent,
    )

    graph.add_node(
        "formal",
        formal_agent,
    )

    graph.add_node(
        "bug_localization",
        bug_localization_agent,
    )

    graph.add_node(
        "rtl_repair",
        rtl_repair_agent,
    )

    graph.add_node(
        "verification_judge",
        verification_judge,
    )

    # ---------------------------------------------------------------
    # Entry
    # ---------------------------------------------------------------

    graph.set_entry_point(
        "rtl_analysis"
    )

    # ---------------------------------------------------------------
    # Main forward flow
    # ---------------------------------------------------------------

    graph.add_edge(
        "rtl_analysis",
        "verification_planning",
    )

    graph.add_edge(
        "verification_planning",
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

    # ---------------------------------------------------------------
    # Simulation router
    # ---------------------------------------------------------------

    graph.add_conditional_edges(
        "simulation",
        route_after_simulation,
        {
            "coverage": "coverage",
            "failure_analysis": "failure_analysis",
            "repair": "rtl_repair",
            "end": END,
        },
    )

    # ---------------------------------------------------------------
    # Failure analysis router
    # ---------------------------------------------------------------

    graph.add_conditional_edges(
        "failure_analysis",
        route_after_failure_analysis,
        {
            "test_generation": "test_generation",
            "repair": "rtl_repair",
        },
    )

    # ---------------------------------------------------------------
    # Repair
    # ---------------------------------------------------------------

    graph.add_edge(
        "rtl_repair",
        "bug_localization",
    )

    graph.add_edge(
        "bug_localization",
        "test_generation",
    )

    # ---------------------------------------------------------------
    # Coverage
    # ---------------------------------------------------------------

    graph.add_conditional_edges(
        "coverage",
        route_after_coverage,
        {
            "test_generation": "test_generation",
            "red_team": "red_team",
            "mutation": "mutation",
            "judge": "verification_judge",
        },
    )

    # ---------------------------------------------------------------
    # Red Team
    # ---------------------------------------------------------------

    graph.add_edge(
        "red_team",
        "test_generation",
    )

    # ---------------------------------------------------------------
    # Mutation
    # ---------------------------------------------------------------

    graph.add_edge(
        "mutation",
        "formal",
    )

    # ---------------------------------------------------------------
    # Formal
    # ---------------------------------------------------------------

    graph.add_edge(
        "formal",
        "verification_judge",
    )

    # ---------------------------------------------------------------
    # Judge
    # ---------------------------------------------------------------

    graph.add_conditional_edges(
        "verification_judge",
        route_after_judge,
        {
            "end": END,
            "test_generation": "test_generation",
        },
    )

    # ---------------------------------------------------------------
    # Compile
    # ---------------------------------------------------------------

    return graph.compile()


# ---------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------

def run_verification_workflow(
    initial_state: VerificationState,
    **agents: Callable,
) -> Dict[str, Any]:
    """
    Build and execute the verification graph.
    """

    workflow = build_verification_workflow(
        **agents
    )

    result = workflow.invoke(
        initial_state
    )

    return result
