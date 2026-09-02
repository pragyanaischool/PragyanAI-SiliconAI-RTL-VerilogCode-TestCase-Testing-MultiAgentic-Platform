"""
PragyanAI SiliconAI
RTL Verification Multi-Agent Graph Package
"""

from .state import (
    VerificationState,
    create_initial_state,
    state_to_dict,
    get_iteration,
    get_max_iterations,
    iteration_limit_reached,
    increment_iteration,
    add_error,
    add_warning,
)

from .router import (
    END,
    TEST_GENERATION,
    TESTBENCH_GENERATION,
    SIMULATION,
    FAILURE_ANALYSIS,
    RTL_REPAIR,
    BUG_LOCALIZATION,
    COVERAGE,
    RED_TEAM,
    MUTATION,
    FORMAL,
    JUDGE,
    route_after_simulation,
    route_after_failure,
    route_after_repair,
    route_after_coverage,
    route_after_red_team,
    route_after_mutation,
    route_after_formal,
    route_after_judge,
    should_continue,
    get_final_verdict,
)

from .workflow import (
    workflow,
    graph,
    app,
    verification_workflow,
    verification_graph,
    build_workflow,
    create_workflow,
    build_graph,
    create_graph,
    run_workflow,
    WORKFLOW_ERROR,
)

# ------------------------------------------------------------
# Backward compatibility
# ------------------------------------------------------------

build_verification_workflow = build_workflow


__all__ = [
    # State
    "VerificationState",
    "create_initial_state",
    "state_to_dict",
    "get_iteration",
    "get_max_iterations",
    "iteration_limit_reached",
    "increment_iteration",
    "add_error",
    "add_warning",

    # Router constants
    "END",
    "TEST_GENERATION",
    "TESTBENCH_GENERATION",
    "SIMULATION",
    "FAILURE_ANALYSIS",
    "RTL_REPAIR",
    "BUG_LOCALIZATION",
    "COVERAGE",
    "RED_TEAM",
    "MUTATION",
    "FORMAL",
    "JUDGE",

    # Router functions
    "route_after_simulation",
    "route_after_failure",
    "route_after_repair",
    "route_after_coverage",
    "route_after_red_team",
    "route_after_mutation",
    "route_after_formal",
    "route_after_judge",
    "should_continue",
    "get_final_verdict",

    # Workflow
    "workflow",
    "graph",
    "app",
    "verification_workflow",
    "verification_graph",
    "build_workflow",
    "build_verification_workflow",
    "create_workflow",
    "build_graph",
    "create_graph",
    "run_workflow",
    "WORKFLOW_ERROR",
]

