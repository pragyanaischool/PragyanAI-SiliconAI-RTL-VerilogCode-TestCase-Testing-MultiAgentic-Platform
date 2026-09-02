"""
PragyanAI SiliconAI
Verification Data Models

Shared TypedDict structures used by the agentic verification system.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypedDict,
)


# ============================================================
# RTL ANALYSIS
# ============================================================

class RTLAnalysis(TypedDict, total=False):
    module_name: str
    language: str

    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    parameters: List[Dict[str, Any]]

    clocks: List[str]
    resets: List[str]

    registers: List[str]
    wires: List[str]

    state_elements: List[str]
    state_machine: bool
    states: List[str]

    combinational_logic: List[str]
    sequential_logic: List[str]

    interfaces: List[str]
    protocols: List[str]

    arithmetic_operations: List[str]
    memory_elements: List[str]

    critical_paths: List[str]
    corner_cases: List[str]

    potential_risks: List[str]
    assumptions: List[str]

    verification_points: List[str]

    complexity: str
    summary: str


# ============================================================
# VERIFICATION PLAN
# ============================================================

class VerificationPlan(TypedDict, total=False):
    objective: str

    requirements: List[Dict[str, Any]]

    functional_areas: List[str]

    directed_tests: List[str]
    random_tests: List[str]
    corner_tests: List[str]
    negative_tests: List[str]

    reset_strategy: List[str]
    clock_strategy: List[str]

    assertion_targets: List[str]

    coverage_targets: Dict[str, float]

    mutation_strategy: List[str]
    formal_strategy: List[str]

    red_team_strategy: List[str]

    priority_tests: List[str]

    expected_test_count: int

    completion_criteria: List[str]

    risks: List[str]


# ============================================================
# TEST SCENARIO
# ============================================================

class TestScenario(TypedDict, total=False):
    test_id: str

    name: str

    description: str

    category: str

    priority: str

    objective: str

    preconditions: List[str]

    inputs: Dict[str, Any]

    sequence: List[Dict[str, Any]]

    expected_behavior: str

    expected_outputs: Dict[str, Any]

    corner_case: bool

    negative_test: bool

    reset_required: bool

    coverage_target: str

    requirement_ids: List[str]

    rationale: str


# ============================================================
# FAILURE ANALYSIS
# ============================================================

class FailureAnalysis(TypedDict, total=False):
    test_id: str

    classification: str

    root_cause: str

    confidence: float

    severity: str

    failure_type: str

    evidence: List[str]

    failing_signal: str

    failing_cycle: str

    expected: str

    actual: str

    suspected_module: str

    suspected_lines: List[int]

    likely_source: str

    recommended_action: str

    regenerate_testbench: bool

    repair_rtl: bool

    spec_ambiguity: bool

    environment_issue: bool


# ============================================================
# COVERAGE GAP
# ============================================================

class CoverageGap(TypedDict, total=False):
    gap_id: str

    metric: str

    description: str

    classification: str

    severity: str

    percentage: float

    target: float

    affected_module: str

    affected_signal: str

    recommendation: str

    recommended_test: str

    requirement_id: str

    closure_priority: str


# ============================================================
# COVERAGE RESULT
# ============================================================

class CoverageResult(TypedDict, total=False):
    line: float
    branch: float
    toggle: float
    fsm: float
    functional: float
    assertion: float
    mutation: float

    overall: float

    target: float

    closure_status: str

    available_metrics: List[str]

    gaps: List[CoverageGap]

    recommended_tests: List[TestScenario]

    summary: str


# ============================================================
# RED TEAM SCENARIO
# ============================================================

class RedTeamScenario(TypedDict, total=False):
    scenario_id: str

    name: str

    description: str

    attack_type: str

    category: str

    priority: str

    inputs: Dict[str, Any]

    sequence: List[Dict[str, Any]]

    expected_failure: str

    target_signal: str

    target_state: str

    rationale: str

    requirement_id: str


# ============================================================
# MUTATION
# ============================================================

class MutationCandidate(TypedDict, total=False):
    mutation_id: str

    mutation_type: str

    description: str

    original_code: str

    mutated_code: str

    target_line: int

    target_signal: str

    rationale: str

    status: str


class MutationResult(TypedDict, total=False):
    mutation_id: str

    mutation_type: str

    status: str

    killed: bool

    survived: bool

    compile_failed: bool

    error: str

    test_id: str

    evidence: str

    duration_seconds: float


# ============================================================
# FORMAL VERIFICATION
# ============================================================

class FormalProperty(TypedDict, total=False):
    property_id: str

    name: str

    description: str

    assertion: str

    assumptions: List[str]

    expected_result: str

    priority: str


class FormalResult(TypedDict, total=False):
    status: str

    verdict: str

    properties: List[FormalProperty]

    passed_properties: int

    failed_properties: int

    unknown_properties: int

    counterexample: str

    counterexample_cycle: str

    failing_signal: str

    log: str

    error: str

    duration_seconds: float

    engine: str

    depth: int


# ============================================================
# BUG LOCALIZATION
# ============================================================

class BugLocation(TypedDict, total=False):
    bug_id: str

    module: str

    file: str

    line: int

    line_range: str

    signal: str

    always_block: str

    suspected_expression: str

    confidence: float

    evidence: List[str]

    root_cause: str

    impact: str

    recommendation: str


# ============================================================
# RTL REPAIR
# ============================================================

class RepairProposal(TypedDict, total=False):
    repair_id: str

    required: bool

    reason: str

    root_cause: str

    target_module: str

    target_lines: List[int]

    original_fragment: str

    proposed_fragment: str

    repaired_rtl: str

    changes: List[str]

    risk: str

    confidence: float

    verification_required: bool

    verified: bool


# ============================================================
# VERIFICATION JUDGE
# ============================================================

class JudgeResult(TypedDict, total=False):
    verdict: str

    score: float

    confidence: float

    signoff: bool

    test_score: float

    coverage_score: float

    mutation_score: float

    assertion_score: float

    formal_score: float

    traceability_score: float

    blocking_failures: List[str]

    warnings: List[str]

    passed_criteria: List[str]

    failed_criteria: List[str]

    missing_evidence: List[str]

    rationale: str

    recommendation: str


# ============================================================
# TEST EXECUTION RECORD
# ============================================================

class TestExecution(TypedDict, total=False):
    test_id: str

    description: str

    status: str

    inputs: str

    expected: str

    actual: str

    error_message: str

    rtl_version: str

    iteration: int

    agent: str

    duration_seconds: float

    test_code_file: str

    simulation_log: str

    waveform_file: str


# ============================================================
# AGENT TRACE
# ============================================================

class AgentTraceEntry(TypedDict, total=False):
    agent: str

    status: str

    timestamp: str

    duration_seconds: float

    message: str

    input_summary: str

    output_summary: str

    iteration: int

    error: str


# ============================================================
# TRACEABILITY
# ============================================================

class Requirement(TypedDict, total=False):
    requirement_id: str

    description: str

    source: str

    priority: str

    verification_status: str


class TraceabilityLink(TypedDict, total=False):
    requirement_id: str

    artifact_type: str

    artifact_id: str

    status: str

    evidence: str


# ============================================================
# RUN SUMMARY
# ============================================================

class RunSummary(TypedDict, total=False):
    run_id: str

    status: str

    specification: str

    rtl_version: str

    total_tests: int

    passed_tests: int

    failed_tests: int

    pass_rate: float

    coverage: CoverageResult

    mutation_score: float

    verification_score: float

    signoff: bool

    iterations: int

    duration_seconds: float
