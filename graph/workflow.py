"""
PragyanAI SiliconAI
===================

Agentic RTL Verification LangGraph Workflow.

Pipeline
--------

    01 RTL Analysis
        ↓
    02 Planning
        ↓
    03 Test Generation
        ↓
    04 Testbench Generation
        ↓
    05 Simulation
        ├── PASS → 07 Coverage
        └── FAIL → 06 Failure Analysis
                         ↓
                    RTL Repair / Test Generation
                         ↓
    07 Coverage
        ↓
    08 Red Team
        ↓
    09 Mutation
        ↓
    10 Formal
        ↓
    11 Judge

Additional iterative stages:

    Failure Analysis
        ↓
    RTL Repair
        ↓
    Bug Localization
        ↓
    Test Generation
        ↓
    Simulation
        ↓
    ...

IMPORTANT
---------
Routing decisions belong ONLY to graph/router.py.

This file is responsible for:

    - agent construction
    - LangGraph node construction
    - graph connectivity
    - execution logging
    - artifact dumping
    - calling router functions
    - compiling the graph
    - running the compiled workflow

This file does NOT decide:

    - whether simulation passed
    - whether coverage is sufficient
    - whether RTL should be repaired
    - whether mutation should run
    - whether formal should run
    - whether verification passed

Those decisions belong to graph/router.py.

OBSERVABILITY
-------------
Every verification run receives one ActivityLogger.

Artifacts are stored under:

    runtime/runs/<run_id>/

Example:

    runtime/runs/20260904_090000_a81f42/
        run_manifest.json
        agent_activity.jsonl
        workflow.log

        01_rtl_analysis/
            input_rtl.v
            rtl_analysis.json

        02_planning/
            verification_plan.json
            verification_plan.md

        03_test_generation/
            tests.json
            test_001.txt
            test_002.txt

        04_testbench_generation/
            testbench.v

        05_simulation/
            design.v
            testbench.v
            compile.log
            simulation.log
            simulation_result.json

        06_failure_analysis/
            failure_analysis.json

        07_coverage/
            coverage.json
            coverage.md

        08_red_team/
            red_team.json

        09_mutation/
            mutations.json
            mutation_001.v

        10_formal/
            formal.json

        11_judge/
            judge.json
            final_report.md

SymbiYosys is NOT required.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterator, Optional

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

# Central run/activity logging.
from logging.run_manager import create_verification_run
from logging.activity_logger import ActivityLogger


# =============================================================================
# MODULE LOGGER
# =============================================================================

LOGGER = logging.getLogger("PragyanAI.workflow")


# =============================================================================
# AGENT IMPORTS
# =============================================================================
#
# IMPORTANT:
# Do not use legacy fallbacks such as:
#
#     from agents.rtl_analyzer import RTLAnalyzer
#
# The repository uses the explicit *Agent class names.
#
# agents/__init__.py is now lazy-loaded, so these imports do not cause
# unrelated agents to be eagerly imported.
# =============================================================================

from agents.rtl_analyzer import RTLAnalyzerAgent
from agents.verification_planner import VerificationPlannerAgent
from agents.test_generator import TestGeneratorAgent
from agents.testbench_generator import TestbenchGeneratorAgent
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzerAgent
from agents.coverage_agent import CoverageAgent
from agents.red_team_agent import RedTeamAgent
from agents.mutation_agent import MutationAgent
from agents.formal_agent import FormalAgent
from agents.bug_localization_agent import BugLocalizationAgent
from agents.rtl_repair_agent import RTLRepairAgent
from agents.verification_judge import VerificationJudgeAgent


# =============================================================================
# GLOBAL STATE
# =============================================================================

AGENTS: Dict[str, Any] = {}

WORKFLOW_ERROR: Optional[Exception] = None

# ---------------------------------------------------------------------------
# One logger per active verification run.
#
# The logger is initialized by run_workflow()/stream_workflow(), not by
# individual agents.
# ---------------------------------------------------------------------------

_RUN_LOGGERS: Dict[str, ActivityLogger] = {}


# =============================================================================
# WORKFLOW STEP METADATA
# =============================================================================

AGENT_DISPLAY_NAMES = {
    "rtl_analysis": "RTL Analysis",
    "planning": "Planning",
    "test_generation": "Test Generation",
    "testbench_generation": "Testbench",
    "simulation": "Simulation",
    "failure_analysis": "Failure Analysis",
    "coverage": "Coverage",
    "red_team": "Red Team",
    "mutation": "Mutation",
    "formal": "Formal",
    "bug_localization": "Bug Localization",
    "rtl_repair": "RTL Repair",
    "judge": "Judge",
}


AGENT_STEPS = {
    "rtl_analysis": 1,
    "planning": 2,
    "test_generation": 3,
    "testbench_generation": 4,
    "simulation": 5,
    "failure_analysis": 6,
    "coverage": 7,
    "red_team": 8,
    "mutation": 9,
    "formal": 10,
    "judge": 11,

    # Iterative support stages.
    "bug_localization": 6,
    "rtl_repair": 6,
}


# =============================================================================
# AGENT CREATION
# =============================================================================

def _instantiate_agent(
    agent_class: Any,
) -> Any:
    """
    Instantiate an agent.

    Supports normal classes and callable agent implementations.
    """

    if agent_class is None:
        raise ImportError(
            "Required agent class is unavailable."
        )

    try:
        return agent_class()

    except TypeError:
        # Compatibility with implementations exposing run() directly.
        if hasattr(agent_class, "run"):
            return agent_class

        raise


def create_agents() -> Dict[str, Any]:
    """
    Create all verification agents.

    Returns
    -------
    Dict[str, Any]
        Agent registry.
    """

    LOGGER.info(
        "Creating PragyanAI SiliconAI verification agents."
    )

    agents = {
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

    LOGGER.info(
        "Created %d verification agents.",
        len(agents),
    )

    return agents


# =============================================================================
# RUN LOGGER HELPERS
# =============================================================================

def _get_activity_logger(
    state: VerificationState,
) -> Optional[ActivityLogger]:
    """
    Retrieve the ActivityLogger associated with the current run.

    The logger is initialized exactly once by run_workflow() or
    stream_workflow().
    """

    if not state:
        return None

    run_id = state.get("run_id")

    if not run_id:
        return None

    return _RUN_LOGGERS.get(
        str(run_id)
    )


def _register_run_logger(
    state: VerificationState,
    metadata: Optional[Dict[str, Any]] = None,
) -> tuple[
    VerificationState,
    ActivityLogger,
]:
    """
    Create or reuse the logger for one verification run.

    IMPORTANT:
    This function is intended to be called once at workflow execution start.
    """

    if state is None:
        state = {}

    run_id = state.get("run_id")

    # -------------------------------------------------------------------------
    # Existing run
    # -------------------------------------------------------------------------

    if run_id:

        run_id = str(run_id)

        existing = _RUN_LOGGERS.get(
            run_id
        )

        if existing is not None:

            state["run_id"] = run_id
            state["run_dir"] = str(
                existing.run_dir
            )

            return state, existing

        # Existing run ID but no in-memory logger.
        # Recreate the logger against the existing run directory.
        run_dir = state.get("run_dir")

        if run_dir:

            logger = ActivityLogger(
                run_dir=run_dir,
                run_id=run_id,
            )

            _RUN_LOGGERS[run_id] = logger

            state["run_id"] = run_id
            state["run_dir"] = str(
                logger.run_dir
            )

            logger.log_activity(
                agent="SYSTEM",
                activity="RUN_LOGGER_REATTACHED",
                status="SUCCESS",
                message=(
                    "Activity logger reattached to existing "
                    "verification run."
                ),
            )

            return state, logger

    # -------------------------------------------------------------------------
    # New run
    # -------------------------------------------------------------------------

    run_metadata = {
        "project": "PragyanAI SiliconAI",
        "workflow": "agentic_rtl_verification",
        "workflow_version": "1.0",
    }

    if metadata:
        run_metadata.update(
            metadata
        )

    run_id, run_dir, activity_logger = (
        create_verification_run(
            metadata=run_metadata
        )
    )

    _RUN_LOGGERS[run_id] = activity_logger

    state["run_id"] = run_id
    state["run_dir"] = str(
        run_dir
    )

    # Save initial user inputs, but never secrets.
    activity_logger.write_manifest(
        {
            "metadata": run_metadata,
            "status": "running",
            "prompt_present": bool(
                state.get("prompt")
                or state.get("user_prompt")
                or state.get("specification")
                or state.get("spec")
            ),
            "rtl_present": bool(
                state.get("rtl_code")
                or state.get("current_rtl")
                or state.get("original_rtl")
            ),
        }
    )

    # Dump original RTL immediately.
    initial_rtl = (
        state.get("original_rtl")
        or state.get("rtl_code")
        or state.get("current_rtl")
        or ""
    )

    if initial_rtl:

        activity_logger.write_code(
            agent="00_input",
            filename="original_rtl.v",
            code=str(initial_rtl),
            step=0,
        )

    activity_logger.log_activity(
        agent="SYSTEM",
        activity="VERIFICATION_RUN_STARTED",
        status="STARTED",
        message=(
            "Agentic RTL verification workflow started."
        ),
        metadata={
            "run_id": run_id,
        },
    )

    return state, activity_logger


def _remove_run_logger(
    run_id: Optional[str],
) -> None:
    """
    Remove logger from in-memory registry.

    The files remain on disk.
    """

    if not run_id:
        return

    _RUN_LOGGERS.pop(
        str(run_id),
        None,
    )


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================

def _merged_state(
    state: VerificationState,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a temporary merged view for artifact extraction.

    Does not mutate the LangGraph state.
    """

    merged = dict(
        state or {}
    )

    if result:
        merged.update(
            result
        )

    return merged


def _dump_agent_artifacts(
    state: VerificationState,
    result: Dict[str, Any],
    agent_name: str,
    activity_logger: Optional[ActivityLogger],
) -> None:
    """
    Dump important artifacts generated by an agent.

    This function is intentionally defensive.

    Artifact logging must NEVER cause verification to fail.
    """

    if activity_logger is None:
        return

    merged = _merged_state(
        state,
        result,
    )

    step = AGENT_STEPS.get(
        agent_name
    )

    display_name = AGENT_DISPLAY_NAMES.get(
        agent_name,
        agent_name,
    )

    try:

        # =====================================================================
        # 01 RTL ANALYSIS
        # =====================================================================

        if agent_name == "rtl_analysis":

            rtl = (
                merged.get("current_rtl")
                or merged.get("rtl_code")
                or merged.get("original_rtl")
                or ""
            )

            if rtl:

                activity_logger.write_code(
                    agent=display_name,
                    filename="input_rtl.v",
                    code=str(rtl),
                    step=step,
                )

            activity_logger.write_json(
                agent=display_name,
                filename="rtl_analysis.json",
                data=merged.get(
                    "rtl_analysis",
                    result,
                ),
                step=step,
            )

        # =====================================================================
        # 02 PLANNING
        # =====================================================================

        elif agent_name == "planning":

            plan = (
                merged.get("verification_plan")
                or merged.get("plan")
                or result
            )

            activity_logger.write_json(
                agent=display_name,
                filename="verification_plan.json",
                data=plan,
                step=step,
            )

            activity_logger.write_text(
                agent=display_name,
                filename="verification_plan.md",
                content=str(plan),
                step=step,
            )

        # =====================================================================
        # 03 TEST GENERATION
        # =====================================================================

        elif agent_name == "test_generation":

            tests = (
                merged.get("generated_tests")
                or merged.get("tests")
                or merged.get("test_cases")
                or []
            )

            activity_logger.write_json(
                agent=display_name,
                filename="tests.json",
                data=tests,
                step=step,
            )

            if isinstance(
                tests,
                (list, tuple),
            ):

                for index, test in enumerate(
                    tests,
                    start=1,
                ):

                    if isinstance(
                        test,
                        dict,
                    ):

                        test_content = (
                            test.get("code")
                            or test.get("test")
                            or test.get("content")
                            or str(test)
                        )

                    else:

                        test_content = str(
                            test
                        )

                    activity_logger.write_text(
                        agent=display_name,
                        filename=(
                            f"test_{index:03d}.txt"
                        ),
                        content=test_content,
                        step=step,
                    )

        # =====================================================================
        # 04 TESTBENCH
        # =====================================================================

        elif agent_name == "testbench_generation":

            testbench = (
                merged.get("testbench_code")
                or merged.get("testbench")
                or merged.get("test_code")
                or ""
            )

            if testbench:

                activity_logger.write_code(
                    agent=display_name,
                    filename="testbench.v",
                    code=str(testbench),
                    step=step,
                )

            activity_logger.write_text(
                agent=display_name,
                filename="testbench_raw.txt",
                content=str(testbench),
                step=step,
            )

        # =====================================================================
        # 05 SIMULATION
        # =====================================================================

        elif agent_name == "simulation":

            rtl = (
                merged.get("current_rtl")
                or merged.get("rtl_code")
                or ""
            )

            testbench = (
                merged.get("testbench_code")
                or merged.get("testbench")
                or merged.get("test_code")
                or ""
            )

            if rtl:

                activity_logger.write_code(
                    agent=display_name,
                    filename="design.v",
                    code=str(rtl),
                    step=step,
                )

            if testbench:

                activity_logger.write_code(
                    agent=display_name,
                    filename="testbench.v",
                    code=str(testbench),
                    step=step,
                )

            activity_logger.write_text(
                agent=display_name,
                filename="compile.log",
                content=(
                    merged.get("compile_output")
                    or merged.get("compile_error")
                    or ""
                ),
                step=step,
            )

            activity_logger.write_text(
                agent=display_name,
                filename="simulation.log",
                content=(
                    merged.get("simulation_output")
                    or merged.get("run_output")
                    or merged.get("simulation_error")
                    or ""
                ),
                step=step,
            )

            activity_logger.write_json(
                agent=display_name,
                filename="simulation_result.json",
                data={
                    "compile_passed": merged.get(
                        "compile_passed"
                    ),
                    "simulation_passed": merged.get(
                        "simulation_passed"
                    ),
                    "test_passed": merged.get(
                        "test_passed"
                    ),
                    "simulation_result": merged.get(
                        "simulation_result"
                    ),
                    "simulator_result": merged.get(
                        "simulator_result"
                    ),
                },
                step=step,
            )

        # =====================================================================
        # 06 FAILURE ANALYSIS
        # =====================================================================

        elif agent_name == "failure_analysis":

            activity_logger.write_json(
                agent=display_name,
                filename="failure_analysis.json",
                data=(
                    merged.get("failure_analysis")
                    or merged.get("failure")
                    or result
                ),
                step=step,
            )

        # =====================================================================
        # BUG LOCALIZATION
        # =====================================================================

        elif agent_name == "bug_localization":

            activity_logger.write_json(
                agent=display_name,
                filename="bug_localization.json",
                data=(
                    merged.get("bug_location")
                    or merged.get("bug_locations")
                    or merged.get("localization_result")
                    or result
                ),
                step=step,
            )

        # =====================================================================
        # RTL REPAIR
        # =====================================================================

        elif agent_name == "rtl_repair":

            repair = (
                merged.get("repair_result")
                or merged.get("repair_proposal")
                or merged.get("rtl_repair")
                or {}
            )

            activity_logger.write_json(
                agent=display_name,
                filename="repair_result.json",
                data=repair,
                step=step,
            )

            repaired_rtl = (
                merged.get("repaired_rtl")
                or ""
            )

            if repaired_rtl:

                activity_logger.write_code(
                    agent=display_name,
                    filename="repaired_rtl.v",
                    code=str(repaired_rtl),
                    step=step,
                )

        # =====================================================================
        # 07 COVERAGE
        # =====================================================================

        elif agent_name == "coverage":

            coverage = (
                merged.get("coverage")
                or merged.get("coverage_report")
                or {}
            )

            activity_logger.write_json(
                agent=display_name,
                filename="coverage.json",
                data=coverage,
                step=step,
            )

            activity_logger.write_text(
                agent=display_name,
                filename="coverage.md",
                content=str(
                    merged.get(
                        "coverage_report",
                        coverage,
                    )
                ),
                step=step,
            )

        # =====================================================================
        # 08 RED TEAM
        # =====================================================================

        elif agent_name == "red_team":

            activity_logger.write_json(
                agent=display_name,
                filename="red_team.json",
                data=(
                    merged.get("red_team_results")
                    or merged.get("red_team_scenarios")
                    or result
                ),
                step=step,
            )

        # =====================================================================
        # 09 MUTATION
        # =====================================================================

        elif agent_name == "mutation":

            mutations = (
                merged.get("mutation_results")
                or merged.get("mutations")
                or []
            )

            activity_logger.write_json(
                agent=display_name,
                filename="mutations.json",
                data=mutations,
                step=step,
            )

            if isinstance(
                mutations,
                (list, tuple),
            ):

                for index, mutation in enumerate(
                    mutations,
                    start=1,
                ):

                    if not isinstance(
                        mutation,
                        dict,
                    ):
                        continue

                    mutated_rtl = (
                        mutation.get("mutated_rtl")
                        or mutation.get("rtl")
                        or ""
                    )

                    if mutated_rtl:

                        activity_logger.write_code(
                            agent=display_name,
                            filename=(
                                f"mutation_{index:03d}.v"
                            ),
                            code=str(
                                mutated_rtl
                            ),
                            step=step,
                        )

            activity_logger.write_text(
                agent=display_name,
                filename="mutation_report.md",
                content=str(
                    merged.get(
                        "mutation_report",
                        mutations,
                    )
                ),
                step=step,
            )

        # =====================================================================
        # 10 FORMAL
        # =====================================================================

        elif agent_name == "formal":

            activity_logger.write_json(
                agent=display_name,
                filename="formal.json",
                data=(
                    merged.get("formal_result")
                    or merged.get("formal_results")
                    or result
                ),
                step=step,
            )

        # =====================================================================
        # 11 JUDGE
        # =====================================================================

        elif agent_name == "judge":

            judge_result = (
                merged.get("judge_result")
                or merged.get("judge")
                or result
            )

            activity_logger.write_json(
                agent=display_name,
                filename="judge.json",
                data=judge_result,
                step=step,
            )

            activity_logger.write_text(
                agent=display_name,
                filename="final_report.md",
                content=str(
                    judge_result
                ),
                step=step,
            )

        # =====================================================================
        # GENERIC FALLBACK
        # =====================================================================

        else:

            activity_logger.write_json(
                agent=display_name,
                filename="agent_output.json",
                data=result,
                step=step,
            )

    except Exception as exc:

        # Artifact failure must NEVER crash verification.
        LOGGER.exception(
            "Artifact dump failed for agent %s: %s",
            agent_name,
            exc,
        )

        try:

            activity_logger.log_activity(
                agent=display_name,
                activity="ARTIFACT_DUMP_FAILED",
                status="ERROR",
                message=str(exc),
                step=step,
            )

        except Exception:
            pass


# =============================================================================
# AGENT EXECUTION
# =============================================================================

def _execute_agent(
    agent: Any,
    state: VerificationState,
    agent_name: str,
) -> Dict[str, Any]:
    """
    Execute one agent and provide complete observability.

    Every execution records:

        STARTED
        ↓
        SUCCESS / ERROR
        ↓
        artifact dump
    """

    if state is None:
        state = {}

    display_name = AGENT_DISPLAY_NAMES.get(
        agent_name,
        agent_name,
    )

    step = AGENT_STEPS.get(
        agent_name
    )

    iteration = state.get(
        "iteration",
        0,
    )

    activity_logger = _get_activity_logger(
        state
    )

    started_at = time.perf_counter()

    # -------------------------------------------------------------------------
    # START LOG
    # -------------------------------------------------------------------------

    if activity_logger:

        activity_logger.agent_started(
            agent=display_name,
            activity=(
                f"{agent_name.upper()}_STARTED"
            ),
            step=step,
            iteration=iteration,
            message=(
                f"Starting {display_name} agent."
            ),
        )

    LOGGER.info(
        "[STEP %s] Starting agent: %s | iteration=%s",
        step,
        display_name,
        iteration,
    )

    try:

        # =====================================================================
        # EXECUTE
        # =====================================================================

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

        # =====================================================================
        # NORMALIZE RESULT
        # =====================================================================

        if result is None:

            normalized_result: Dict[str, Any] = {}

        elif isinstance(
            result,
            dict,
        ):

            normalized_result = result

        else:

            try:

                normalized_result = dict(
                    result
                )

            except Exception:

                normalized_result = {
                    "agent_output": result
                }

        duration_ms = (
            time.perf_counter()
            - started_at
        ) * 1000.0

        # =====================================================================
        # SUCCESS LOG
        # =====================================================================

        if activity_logger:

            activity_logger.agent_completed(
                agent=display_name,
                activity=(
                    f"{agent_name.upper()}_COMPLETED"
                ),
                step=step,
                iteration=iteration,
                duration_ms=duration_ms,
                message=(
                    f"{display_name} completed successfully."
                ),
                metadata={
                    "result_keys": list(
                        normalized_result.keys()
                    ),
                },
            )

        LOGGER.info(
            "[STEP %s] Completed agent: %s | %.2f ms",
            step,
            display_name,
            duration_ms,
        )

        # =====================================================================
        # ARTIFACTS
        # =====================================================================

        _dump_agent_artifacts(
            state=state,
            result=normalized_result,
            agent_name=agent_name,
            activity_logger=activity_logger,
        )

        return normalized_result

    except Exception as exc:

        duration_ms = (
            time.perf_counter()
            - started_at
        ) * 1000.0

        message = (
            f"{display_name} failed: "
            f"{type(exc).__name__}: {exc}"
        )

        LOGGER.exception(
            "[STEP %s] %s",
            step,
            message,
        )

        # ---------------------------------------------------------------------
        # ERROR LOG
        # ---------------------------------------------------------------------

        if activity_logger:

            activity_logger.agent_failed(
                agent=display_name,
                error=exc,
                step=step,
                iteration=iteration,
            )

            activity_logger.log_activity(
                agent=display_name,
                activity=(
                    f"{agent_name.upper()}_FAILED"
                ),
                status="ERROR",
                message=message,
                step=step,
                iteration=iteration,
                duration_ms=duration_ms,
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
# NODES
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
# ROUTER LOGGING
# =============================================================================

def _log_route(
    state: VerificationState,
    source: str,
    destination: str,
) -> None:
    """
    Log every LangGraph routing decision.

    Router.py remains responsible for deciding the destination.
    This function only records the decision.
    """

    activity_logger = _get_activity_logger(
        state
    )

    if activity_logger is None:
        return

    activity_logger.log_activity(
        agent="ROUTER",
        activity="ROUTE_DECISION",
        status="INFO",
        message=(
            f"{source} -> {destination}"
        ),
        iteration=state.get(
            "iteration",
            0,
        ),
        metadata={
            "source": source,
            "destination": destination,
        },
    )


def _route(
    state: VerificationState,
    source: str,
    destination: str,
) -> str:
    """
    Log and return a router destination.
    """

    _log_route(
        state,
        source,
        destination,
    )

    return destination


# =============================================================================
# ROUTER ADAPTERS
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

    destination = _langgraph_destination(
        route_after_simulation(
            state
        )
    )

    return _route(
        state,
        "simulation",
        destination,
    )


def failure_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_failure(
            state
        )
    )

    return _route(
        state,
        "failure_analysis",
        destination,
    )


def repair_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_repair(
            state
        )
    )

    return _route(
        state,
        "rtl_repair",
        destination,
    )


def bug_localization_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_bug_localization(
            state
        )
    )

    return _route(
        state,
        "bug_localization",
        destination,
    )


def coverage_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_coverage(
            state
        )
    )

    return _route(
        state,
        "coverage",
        destination,
    )


def red_team_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_red_team(
            state
        )
    )

    return _route(
        state,
        "red_team",
        destination,
    )


def mutation_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_mutation(
            state
        )
    )

    return _route(
        state,
        "mutation",
        destination,
    )


def formal_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_formal(
            state
        )
    )

    return _route(
        state,
        "formal",
        destination,
    )


def judge_router(
    state: VerificationState,
) -> str:

    destination = _langgraph_destination(
        route_after_judge(
            state
        )
    )

    return _route(
        state,
        "judge",
        destination,
    )


# =============================================================================
# BUILD WORKFLOW
# =============================================================================

def build_workflow(
    agents: Optional[
        Dict[str, Any]
    ] = None,
):
    """
    Build and compile the LangGraph verification workflow.

    Parameters
    ----------
    agents:
        Optional agent registry used primarily for testing.

    Returns
    -------
    CompiledStateGraph
    """

    global AGENTS

    LOGGER.info(
        "Building PragyanAI SiliconAI LangGraph workflow."
    )

    if agents is None:

        AGENTS = create_agents()

    else:

        AGENTS = agents

    builder = StateGraph(
        VerificationState
    )

    # =========================================================================
    # NODES
    # =========================================================================

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
    # INITIAL PIPELINE
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
    # SIMULATION
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
    # FAILURE ANALYSIS
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
    # RTL REPAIR
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
    # BUG LOCALIZATION
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
    # COVERAGE
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
    # RED TEAM
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
    # MUTATION
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
    # FORMAL
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
    # JUDGE
    # =========================================================================

    builder.add_conditional_edges(
        "judge",
        judge_router,
        {
            "rtl_repair": "rtl_repair",
            "test_generation": "test_generation",
            "bug_localization": "bug_localization",
            LANGGRAPH_END: LANGGRAPH_END,
        },
    )

    # =========================================================================
    # COMPILE
    # =========================================================================

    compiled = builder.compile()

    LOGGER.info(
        "LangGraph verification workflow compiled successfully."
    )

    return compiled


# =============================================================================
# DEFAULT WORKFLOW
# =============================================================================

try:

    workflow = build_workflow()

except Exception as exc:

    WORKFLOW_ERROR = exc
    workflow = None

    LOGGER.exception(
        "Failed to build default verification workflow."
    )


# =============================================================================
# COMPATIBILITY ALIASES
# =============================================================================

graph = workflow

app = workflow

verification_workflow = workflow

verification_graph = workflow


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_workflow():
    """
    Create a new compiled verification workflow.
    """

    return build_workflow()


def create_graph():
    """
    Create a new compiled graph.
    """

    return build_workflow()


def build_graph():
    """
    Compatibility alias.
    """

    return build_workflow()


def build_verification_workflow():
    """
    Create verification workflow.
    """

    return build_workflow()


def create_verification_workflow():
    """
    Create verification workflow.
    """

    return build_workflow()


# =============================================================================
# FINAL RUN ARTIFACTS
# =============================================================================

def _write_final_artifacts(
    state: VerificationState,
    activity_logger: ActivityLogger,
) -> None:
    """
    Write final run-level artifacts.
    """

    try:

        # ---------------------------------------------------------------------
        # Final RTL
        # ---------------------------------------------------------------------

        final_rtl = (
            state.get("repaired_rtl")
            or state.get("current_rtl")
            or state.get("rtl_code")
            or state.get("original_rtl")
            or ""
        )

        if final_rtl:

            activity_logger.write_code(
                agent="11_judge",
                filename="final_rtl.v",
                code=str(final_rtl),
                step=11,
            )

        # ---------------------------------------------------------------------
        # Final verification summary
        # ---------------------------------------------------------------------

        activity_logger.write_json(
            agent="11_judge",
            filename="verification_summary.json",
            data={
                "run_id": state.get(
                    "run_id"
                ),
                "status": state.get(
                    "status"
                ),
                "final_verdict": state.get(
                    "final_verdict"
                ),
                "verdict": state.get(
                    "verdict"
                ),
                "verification_score": state.get(
                    "verification_score"
                ),
                "coverage_score": state.get(
                    "coverage_score"
                ),
                "coverage_percent": state.get(
                    "coverage_percent"
                ),
                "mutation_score": state.get(
                    "mutation_score"
                ),
                "simulation_passed": state.get(
                    "simulation_passed"
                ),
                "compile_passed": state.get(
                    "compile_passed"
                ),
                "formal_passed": state.get(
                    "formal_passed"
                ),
                "iteration": state.get(
                    "iteration"
                ),
                "max_iterations": state.get(
                    "max_iterations"
                ),
            },
            step=11,
        )

        # ---------------------------------------------------------------------
        # Final warnings/errors
        # ---------------------------------------------------------------------

        activity_logger.write_json(
            agent="SYSTEM",
            filename="final_errors.json",
            data={
                "errors": state.get(
                    "errors",
                    [],
                ),
                "warnings": state.get(
                    "warnings",
                    [],
                ),
            },
        )

    except Exception as exc:

        LOGGER.exception(
            "Failed writing final verification artifacts: %s",
            exc,
        )


def _finalize_run(
    state: VerificationState,
    activity_logger: Optional[ActivityLogger],
    status: str = "COMPLETED",
) -> None:
    """
    Finalize the verification run and persist summary artifacts.
    """

    if activity_logger is None:
        return

    try:

        _write_final_artifacts(
            state,
            activity_logger,
        )

        verdict = (
            state.get("final_verdict")
            or state.get("verdict")
        )

        activity_logger.finalize(
            status=status,
            verdict=verdict,
            message=(
                "Agentic RTL verification workflow finished."
            ),
        )

    except Exception as exc:

        LOGGER.exception(
            "Failed finalizing verification run: %s",
            exc,
        )


# =============================================================================
# EXECUTION
# =============================================================================

def run_workflow(
    state: VerificationState,
    **kwargs: Any,
):
    """
    Execute the complete verification workflow.

    A single ActivityLogger is created for this verification run and shared
    by every LangGraph node.

    Parameters
    ----------
    state:
        Initial VerificationState.

    Returns
    -------
    VerificationState
        Final workflow state.
    """

    if workflow is None:

        if WORKFLOW_ERROR is not None:

            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is unavailable."
        )

    # -------------------------------------------------------------------------
    # INITIALIZE ONE LOGGER PER RUN
    # -------------------------------------------------------------------------

    state, activity_logger = _register_run_logger(
        state,
        metadata={
            "execution_mode": "invoke",
        },
    )

    run_id = state.get(
        "run_id"
    )

    try:

        LOGGER.info(
            "Starting verification run: %s",
            run_id,
        )

        result = workflow.invoke(
            state,
            **kwargs,
        )

        # ---------------------------------------------------------------------
        # Final result
        # ---------------------------------------------------------------------

        final_state = (
            result
            if isinstance(
                result,
                dict,
            )
            else state
        )

        _finalize_run(
            state=final_state,
            activity_logger=activity_logger,
            status="COMPLETED",
        )

        LOGGER.info(
            "Verification run completed: %s | verdict=%s",
            run_id,
            final_state.get(
                "final_verdict",
                final_state.get(
                    "verdict"
                ),
            ),
        )

        return final_state

    except Exception as exc:

        LOGGER.exception(
            "Verification run failed: %s",
            run_id,
        )

        activity_logger.agent_failed(
            agent="SYSTEM",
            error=exc,
            activity="VERIFICATION_RUN_FAILED",
        )

        activity_logger.finalize(
            status="FAILED",
            verdict="FAIL",
            message=str(exc),
        )

        raise

    finally:

        # Keep files on disk but release in-memory logger.
        _remove_run_logger(
            run_id
        )


# =============================================================================
# STREAMING EXECUTION
# =============================================================================

def stream_workflow(
    state: VerificationState,
    **kwargs: Any,
) -> Iterator[Any]:
    """
    Stream workflow execution while maintaining one ActivityLogger.

    The logger remains alive until the stream is completely consumed.
    """

    if workflow is None:

        if WORKFLOW_ERROR is not None:

            raise RuntimeError(
                "Verification workflow could not be loaded."
            ) from WORKFLOW_ERROR

        raise RuntimeError(
            "Verification workflow is unavailable."
        )

    # -------------------------------------------------------------------------
    # INITIALIZE LOGGER ONCE
    # -------------------------------------------------------------------------

    state, activity_logger = _register_run_logger(
        state,
        metadata={
            "execution_mode": "stream",
        },
    )

    run_id = state.get(
        "run_id"
    )

    last_state: VerificationState = state

    try:

        LOGGER.info(
            "Starting streamed verification run: %s",
            run_id,
        )

        for event in workflow.stream(
            state,
            **kwargs,
        ):

            # LangGraph normally yields dictionaries.
            if isinstance(
                event,
                dict,
            ):

                # Capture the latest state-like event for final reporting.
                last_state = {
                    **last_state,
                    **event,
                }

            yield event

        _finalize_run(
            state=last_state,
            activity_logger=activity_logger,
            status="COMPLETED",
        )

        LOGGER.info(
            "Streamed verification run completed: %s",
            run_id,
        )

    except Exception as exc:

        LOGGER.exception(
            "Streamed verification run failed: %s",
            run_id,
        )

        activity_logger.agent_failed(
            agent="SYSTEM",
            error=exc,
            activity="VERIFICATION_STREAM_FAILED",
        )

        activity_logger.finalize(
            status="FAILED",
            verdict="FAIL",
            message=str(exc),
        )

        raise

    finally:

        _remove_run_logger(
            run_id
        )


# =============================================================================
# DIAGNOSTICS
# =============================================================================

def workflow_is_available() -> bool:
    """
    Return True when the LangGraph workflow compiled successfully.
    """

    return workflow is not None


def get_workflow_error():
    """
    Return the workflow initialization error, if any.
    """

    return WORKFLOW_ERROR


def get_agent_names():
    """
    Return currently registered agent names.
    """

    return list(
        AGENTS.keys()
    )


def get_active_run_ids() -> list[str]:
    """
    Return verification runs that currently have an in-memory logger.
    """

    return list(
        _RUN_LOGGERS.keys()
    )


def get_run_logger(
    run_id: str,
) -> Optional[ActivityLogger]:
    """
    Return the active logger for a run.

    Intended primarily for Streamlit UI/status displays.
    """

    return _RUN_LOGGERS.get(
        str(run_id)
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [

    # Workflow
    "workflow",
    "graph",
    "app",
    "verification_workflow",
    "verification_graph",

    # Global state
    "AGENTS",
    "WORKFLOW_ERROR",

    # Agents
    "create_agents",

    # Nodes
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

    # Routers
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
    "get_active_run_ids",
    "get_run_logger",
]
