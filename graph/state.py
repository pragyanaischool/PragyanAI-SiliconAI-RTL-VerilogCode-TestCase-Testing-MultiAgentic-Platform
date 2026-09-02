"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

VerificationState

Shared LangGraph state for the complete RTL verification loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class VerificationState(TypedDict, total=False):

    # ================================================================
    # User / specification
    # ================================================================

    prompt: str
    specification: str

    # ================================================================
    # RTL
    # ================================================================

    rtl_code: str
    rtl_version: str
    rtl_history: List[Dict[str, Any]]

    # ================================================================
    # RTL analysis
    # ================================================================

    rtl_analysis: Dict[str, Any]

    # ================================================================
    # Verification planning
    # ================================================================

    verification_plan: Dict[str, Any]

    # ================================================================
    # Test generation
    # ================================================================

    generated_tests: List[Dict[str, Any]]
    tests: List[Dict[str, Any]]

    # ================================================================
    # Testbench
    # ================================================================

    testbench: str
    test_code: str

    # ================================================================
    # Simulation
    # ================================================================

    run_output: str
    simulation_output: str

    compile_output: str
    compile_error: str
    simulation_error: str

    simulation_passed: bool

    # ================================================================
    # Failure analysis
    # ================================================================

    failure_analysis: Dict[str, Any]
    root_cause: str

    # ================================================================
    # Coverage
    # ================================================================

    coverage: Dict[str, Any]
    coverage_gaps: List[Dict[str, Any]]

    # ================================================================
    # Red team
    # ================================================================

    red_team_scenarios: List[Dict[str, Any]]

    # ================================================================
    # Mutation testing
    # ================================================================

    mutations: List[Dict[str, Any]]
    mutation_score: float

    # ================================================================
    # Formal verification
    # ================================================================

    formal_result: Dict[str, Any]

    # ================================================================
    # Bug localization
    # ================================================================

    bug_location: Dict[str, Any]

    # ================================================================
    # RTL repair
    # ================================================================

    repair_proposal: Dict[str, Any]
    repaired_rtl: str

    # ================================================================
    # Verification judge
    # ================================================================

    verification_score: float
    judge_result: Dict[str, Any]

    # ================================================================
    # Agent trace
    # ================================================================

    agent_log: List[Dict[str, Any]]
    agent_trace: List[Dict[str, Any]]

    # ================================================================
    # Execution
    # ================================================================

    iteration: int
    max_iterations: int

    status: str

    # ================================================================
    # Run / evidence
    # ================================================================

    run_id: str
    run_dir: str

    # ================================================================
    # Control
    # ================================================================

    next_action: str
    retry_required: bool
    stop_reason: str

    # ================================================================
    # Generic messages
    # ================================================================

    messages: List[str]
    warnings: List[str]
    errors: List[str]
