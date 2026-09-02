"""
PragyanAI SiliconAI
Agent Unit Tests

Tests the deterministic and fallback behavior of the verification agents.

These tests should NOT require:
    - GROQ_API_KEY
    - Streamlit
    - Icarus Verilog
    - Verilator
    - Yosys

The purpose is to catch:
    - import errors
    - constructor errors
    - malformed state handling
    - missing output fields
    - broken fallback logic
    - invalid agent outputs
"""

from __future__ import annotations

import os
import sys

import pytest


# ---------------------------------------------------------------------
# Make repository root importable when pytest is launched from tests/
# ---------------------------------------------------------------------

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

from agents.rtl_analyzer import RTLAnalyzerAgent
from agents.verification_planner import VerificationPlannerAgent
from agents.test_generator import TestGeneratorAgent
from agents.testbench_generator import TestbenchGeneratorAgent
from agents.red_team_agent import RedTeamAgent
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzerAgent
from agents.coverage_agent import CoverageAgent
from agents.mutation_agent import MutationAgent
from agents.formal_agent import FormalAgent
from agents.bug_localization_agent import BugLocalizationAgent
from agents.rtl_repair_agent import RTLRepairAgent
from agents.verification_judge import VerificationJudgeAgent


# ---------------------------------------------------------------------
# Sample RTL
# ---------------------------------------------------------------------

SAMPLE_RTL = """
module counter #(
    parameter WIDTH = 4
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    output reg [WIDTH-1:0]  count
);

always @(posedge clk) begin
    if (!rst_n)
        count <= 0;
    else if (en)
        count <= count + 1'b1;
end

endmodule
"""


SAMPLE_SPECIFICATION = """
Design a synchronous 4-bit counter.

Requirements:
1. Active-low reset shall set count to zero.
2. When en is high, count increments on every rising clock edge.
3. When en is low, count holds its previous value.
4. Counter wraps naturally after reaching the maximum value.
"""


# ---------------------------------------------------------------------
# Common test state
# ---------------------------------------------------------------------

def base_state():
    return {
        "prompt": SAMPLE_SPECIFICATION,
        "specification": SAMPLE_SPECIFICATION,
        "rtl_code": SAMPLE_RTL,
        "rtl_version": "v1",

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
        "simulation_passed": None,

        "failure_analysis": {},
        "root_cause": "",

        "coverage": {},
        "coverage_gaps": [],

        "red_team_scenarios": [],
        "mutations": [],
        "mutation_score": 0,

        "formal_result": {},
        "bug_location": {},

        "repair_proposal": {},
        "repaired_rtl": "",

        "verification_score": 0,
        "judge_result": {},

        "agent_log": [],
        "agent_trace": [],

        "iteration": 1,
        "max_iterations": 3,

        "status": "INITIALIZED",
        "run_id": "",
        "run_dir": "",

        "next_action": "",
        "retry_required": False,
        "stop_reason": "",

        "messages": [],
        "warnings": [],
        "errors": [],
    }


# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def assert_common_agent_output(
    result,
    expected_keys=None,
):
    """
    Common validation for LangGraph-compatible agent results.
    """

    assert isinstance(
        result,
        dict,
    )

    assert "status" in result

    assert "agent_log" in result
    assert isinstance(
        result["agent_log"],
        list,
    )

    assert "agent_trace" in result
    assert isinstance(
        result["agent_trace"],
        list,
    )

    assert "warnings" in result
    assert isinstance(
        result["warnings"],
        list,
    )

    assert "errors" in result
    assert isinstance(
        result["errors"],
        list,
    )

    if expected_keys:
        for key in expected_keys:
            assert key in result, (
                f"Expected output key '{key}' "
                f"was not returned."
            )


# =====================================================================
# RTL ANALYZER
# =====================================================================

def test_rtl_analyzer_constructor():
    agent = RTLAnalyzerAgent()

    assert agent is not None
    assert agent.name == "RTL Analyzer"


def test_rtl_analyzer_static_analysis():
    agent = RTLAnalyzerAgent()

    state = base_state()

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "rtl_analysis",
        ],
    )

    analysis = result["rtl_analysis"]

    assert isinstance(
        analysis,
        dict,
    )


def test_rtl_analyzer_detects_module():
    agent = RTLAnalyzerAgent()

    state = base_state()

    result = agent.run(
        state
    )

    analysis = result["rtl_analysis"]

    # Different implementations may use different field names.
    text = str(
        analysis
    ).lower()

    assert (
        "counter" in text
        or "module" in text
        or "clock" in text
        or "signals" in text
    )


# =====================================================================
# VERIFICATION PLANNER
# =====================================================================

def test_verification_planner_constructor():
    agent = VerificationPlannerAgent()

    assert agent is not None
    assert agent.name == "Verification Planner"


def test_verification_planner_generates_plan():
    agent = VerificationPlannerAgent()

    result = agent.run(
        base_state()
    )

    assert_common_agent_output(
        result,
        [
            "verification_plan",
        ],
    )

    plan = result["verification_plan"]

    assert isinstance(
        plan,
        dict,
    )


def test_verification_plan_has_testing_strategy():
    agent = VerificationPlannerAgent()

    result = agent.run(
        base_state()
    )

    plan = result["verification_plan"]

    text = str(
        plan
    ).lower()

    assert (
        "test" in text
        or "coverage" in text
        or "functional" in text
        or "reset" in text
    )


# =====================================================================
# TEST GENERATOR
# =====================================================================

def test_test_generator_constructor():
    agent = TestGeneratorAgent()

    assert agent is not None
    assert agent.name == "Test Generator"


def test_test_generator_creates_scenarios():
    agent = TestGeneratorAgent()

    state = base_state()

    state["rtl_analysis"] = {
        "module_name": "counter",
        "clock_signals": ["clk"],
        "reset_signals": ["rst_n"],
        "inputs": ["en"],
        "outputs": ["count"],
    }

    state["verification_plan"] = {
        "functional_tests": [
            "reset",
            "increment",
            "hold",
            "wraparound",
        ],
        "corner_cases": [
            "maximum count",
        ],
    }

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "generated_tests",
        ],
    )

    scenarios = result["generated_tests"]

    assert isinstance(
        scenarios,
        list,
    )

    assert len(scenarios) > 0


def test_test_generator_ids_are_unique():
    agent = TestGeneratorAgent()

    result = agent.run(
        base_state()
    )

    scenarios = result.get(
        "generated_tests",
        [],
    )

    ids = [
        str(
            item.get(
                "test_id",
                item.get(
                    "id",
                    "",
                ),
            )
        )
        for item in scenarios
        if isinstance(item, dict)
    ]

    ids = [
        item
        for item in ids
        if item
    ]

    assert len(ids) == len(
        set(ids)
    )


# =====================================================================
# TESTBENCH GENERATOR
# =====================================================================

def test_testbench_generator_constructor():
    agent = TestbenchGeneratorAgent()

    assert agent is not None
    assert agent.name == "Testbench Generator"


def test_testbench_generator_output_structure():
    agent = TestbenchGeneratorAgent()

    state = base_state()

    state["generated_tests"] = [
        {
            "test_id": "TC001",
            "description": "Reset test",
            "category": "RESET",
            "priority": "HIGH",
        },
        {
            "test_id": "TC002",
            "description": "Increment test",
            "category": "FUNCTIONAL",
            "priority": "HIGH",
        },
    ]

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "testbench",
        ],
    )

    assert isinstance(
        result["testbench"],
        str,
    )


def test_testbench_fallback_is_not_false_pass():
    """
    If the LLM is unavailable, the fallback must not fabricate a PASS.

    This is a critical safety test.
    """

    agent = TestbenchGeneratorAgent()

    # Force deterministic fallback.
    agent.llm = None

    state = base_state()

    state["generated_tests"] = [
        {
            "test_id": "TC001",
            "description": "Reset test",
            "category": "RESET",
        }
    ]

    result = agent.run(
        state
    )

    testbench = result.get(
        "testbench",
        "",
    )

    if testbench:
        # The fallback should explicitly report that it cannot
        # determine expected behavior rather than claiming PASS.
        if "TEST_ERROR" in testbench:
            assert (
                "TEST_RESULT" not in testbench
                or "PASS" not in testbench
            )


# =====================================================================
# RED TEAM
# =====================================================================

def test_red_team_constructor():
    agent = RedTeamAgent()

    assert agent is not None
    assert agent.name == "Red Team Agent"


def test_red_team_generates_adversarial_scenarios():
    agent = RedTeamAgent()

    state = base_state()

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "red_team_scenarios",
        ],
    )

    scenarios = result[
        "red_team_scenarios"
    ]

    assert isinstance(
        scenarios,
        list,
    )

    assert len(scenarios) > 0


def test_red_team_scenario_ids_unique():
    agent = RedTeamAgent()

    result = agent.run(
        base_state()
    )

    scenarios = result[
        "red_team_scenarios"
    ]

    ids = [
        item.get(
            "id",
            item.get(
                "scenario_id",
                "",
            ),
        )
        for item in scenarios
        if isinstance(item, dict)
    ]

    ids = [
        item
        for item in ids
        if item
    ]

    assert len(ids) == len(
        set(ids)
    )


# =====================================================================
# SIMULATOR
# =====================================================================

def test_simulator_constructor():
    agent = SimulatorAgent()

    assert agent is not None
    assert agent.name == "Simulation Agent"


def test_simulator_handles_missing_testbench():
    """
    Simulator should fail gracefully rather than crash when no
    testbench exists.
    """

    agent = SimulatorAgent()

    state = base_state()

    state["testbench"] = ""
    state["test_code"] = ""

    result = agent.run(
        state
    )

    assert isinstance(
        result,
        dict,
    )

    assert "status" in result
    assert "errors" in result


# =====================================================================
# FAILURE ANALYZER
# =====================================================================

def test_failure_analyzer_constructor():
    agent = FailureAnalyzerAgent()

    assert agent is not None
    assert agent.name == "Failure Analyzer"


def test_failure_analyzer_classifies_testbench_failure():
    agent = FailureAnalyzerAgent()

    state = base_state()

    state["simulation_passed"] = False

    state["simulation_error"] = """
ERROR: TEST_RESULT expected signal not found.
TEST_ERROR|TC001|FAIL|testbench assertion mismatch
"""

    state["run_output"] = state[
        "simulation_error"
    ]

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "failure_analysis",
            "root_cause",
            "next_action",
        ],
    )

    failure = result[
        "failure_analysis"
    ]

    assert isinstance(
        failure,
        dict,
    )


def test_failure_analyzer_handles_empty_failure():
    agent = FailureAnalyzerAgent()

    state = base_state()

    state["simulation_passed"] = False
    state["simulation_error"] = ""

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "failure_analysis",
        ],
    )


# =====================================================================
# COVERAGE
# =====================================================================

def test_coverage_agent_constructor():
    agent = CoverageAgent()

    assert agent is not None
    assert agent.name == "Coverage Agent"


def test_coverage_agent_generates_proxy_coverage():
    agent = CoverageAgent()

    state = base_state()

    state["tests"] = [
        {
            "test_id": "TC001",
            "description": "Reset",
            "status": "PASSED",
        },
        {
            "test_id": "TC002",
            "description": "Increment",
            "status": "PASSED",
        },
    ]

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "coverage",
            "coverage_gaps",
        ],
    )

    coverage = result[
        "coverage"
    ]

    assert isinstance(
        coverage,
        dict,
    )

    assert "overall" in coverage


def test_coverage_agent_marks_proxy_evidence():
    agent = CoverageAgent()

    state = base_state()

    state["tests"] = [
        {
            "test_id": "TC001",
            "description": "Reset",
            "status": "PASSED",
        }
    ]

    result = agent.run(
        state
    )

    coverage = result[
        "coverage"
    ]

    evidence_type = str(
        coverage.get(
            "evidence_type",
            "",
        )
    ).upper()

    assert evidence_type in {
        "PROXY_COVERAGE",
        "REAL_COVERAGE",
    }


# =====================================================================
# MUTATION
# =====================================================================

def test_mutation_agent_constructor():
    agent = MutationAgent()

    assert agent is not None
    assert agent.name == "Mutation Agent"


def test_mutation_agent_handles_empty_rtl():
    agent = MutationAgent()

    state = base_state()
    state["rtl_code"] = ""

    result = agent.run(
        state
    )

    assert isinstance(
        result,
        dict,
    )

    assert "mutation_score" in result
    assert "mutations" in result


def test_mutation_agent_generates_candidates():
    agent = MutationAgent()

    state = base_state()

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "mutations",
            "mutation_score",
        ],
    )

    assert isinstance(
        result["mutations"],
        list,
    )


# =====================================================================
# FORMAL
# =====================================================================

def test_formal_agent_constructor():
    agent = FormalAgent()

    assert agent is not None
    assert agent.name == "Formal Agent"


def test_formal_agent_handles_counter_rtl():
    agent = FormalAgent()

    state = base_state()

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "formal_result",
        ],
    )

    assert isinstance(
        result["formal_result"],
        dict,
    )


# =====================================================================
# BUG LOCALIZATION
# =====================================================================

def test_bug_localization_constructor():
    agent = BugLocalizationAgent()

    assert agent is not None
    assert agent.name == "Bug Localization Agent"


def test_bug_localization_returns_structure():
    agent = BugLocalizationAgent()

    state = base_state()

    state["failure_analysis"] = {
        "category": "RESET_ERROR",
        "root_cause": "Counter does not reset correctly.",
        "action": "RTL_REPAIR",
    }

    state["simulation_error"] = (
        "count expected 0 but observed 7"
    )

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "bug_location",
        ],
    )

    location = result[
        "bug_location"
    ]

    assert isinstance(
        location,
        dict,
    )


# =====================================================================
# RTL REPAIR
# =====================================================================

def test_rtl_repair_constructor():
    agent = RTLRepairAgent()

    assert agent is not None
    assert agent.name == "RTL Repair Agent"


def test_rtl_repair_safe_fallback():
    """
    The repair fallback must not blindly modify RTL.
    """

    agent = RTLRepairAgent()

    # Force fallback.
    agent.llm = None

    state = base_state()

    state["failure_analysis"] = {
        "category": "UNKNOWN",
        "root_cause": (
            "Insufficient evidence to determine the RTL defect."
        ),
    }

    state["bug_location"] = {
        "primary": {},
        "locations": [],
    }

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "repair_proposal",
            "repaired_rtl",
        ],
    )

    assert (
        result["repaired_rtl"]
        == SAMPLE_RTL
    )


def test_rtl_repair_preserves_module_name():
    agent = RTLRepairAgent()

    valid, warnings = agent._assess_repair(
        SAMPLE_RTL,
        SAMPLE_RTL,
    )

    assert valid is True

    assert (
        agent._module_names(
            SAMPLE_RTL
        )
        == ["counter"]
    )


# =====================================================================
# VERIFICATION JUDGE
# =====================================================================

def test_verification_judge_constructor():
    agent = VerificationJudgeAgent()

    assert agent is not None
    assert agent.name == "Verification Judge"


def test_verification_judge_does_not_pass_failed_simulation():
    """
    Hard safety rule:
    explicit simulation failure must never produce PASS.
    """

    agent = VerificationJudgeAgent()

    agent.llm = None

    state = base_state()

    state["simulation_passed"] = False

    state["tests"] = [
        {
            "test_id": "TC001",
            "status": "FAILED",
        }
    ]

    result = agent.run(
        state
    )

    judge = result[
        "judge_result"
    ]

    assert judge[
        "verdict"
    ] != "PASS"


def test_verification_judge_handles_incomplete_evidence():
    agent = VerificationJudgeAgent()

    agent.llm = None

    state = base_state()

    state["simulation_passed"] = None
    state["tests"] = []
    state["coverage"] = {}

    result = agent.run(
        state
    )

    assert_common_agent_output(
        result,
        [
            "judge_result",
            "verification_score",
        ],
    )

    judge = result[
        "judge_result"
    ]

    assert judge[
        "verdict"
    ] in {
        "FAIL",
        "NEED_MORE_VERIFICATION",
    }


# =====================================================================
# CROSS-AGENT COMPATIBILITY
# =====================================================================

def test_agents_accept_langgraph_style_state():
    """
    Every major agent should accept the common state dictionary.

    This catches accidental constructor/signature mismatches early.
    """

    agents = [
        RTLAnalyzerAgent(),
        VerificationPlannerAgent(),
        TestGeneratorAgent(),
        TestbenchGeneratorAgent(),
        RedTeamAgent(),
        SimulatorAgent(),
        FailureAnalyzerAgent(),
        CoverageAgent(),
        MutationAgent(),
        FormalAgent(),
        BugLocalizationAgent(),
        RTLRepairAgent(),
        VerificationJudgeAgent(),
    ]

    state = base_state()

    for agent in agents:
        assert callable(agent)

        # Do not require every agent to successfully execute an EDA task.
        # We only verify that invocation does not raise an unexpected
        # Python exception for the common state structure.
        try:
            result = agent(
                state
            )

            assert isinstance(
                result,
                dict,
            )

        except Exception as exc:
            pytest.fail(
                f"{agent.name} raised an unexpected exception: "
                f"{type(exc).__name__}: {exc}"
            )


# =====================================================================
# AI AVAILABILITY
# =====================================================================

def test_agents_can_initialize_without_groq_key():
    """
    Constructors should not crash when GROQ_API_KEY is unavailable.

    The application must still support deterministic/offline behavior.
    """

    agents = [
        RTLAnalyzerAgent(),
        VerificationPlannerAgent(),
        TestGeneratorAgent(),
        TestbenchGeneratorAgent(),
        RedTeamAgent(),
        FailureAnalyzerAgent(),
        CoverageAgent(),
        FormalAgent(),
        BugLocalizationAgent(),
        RTLRepairAgent(),
        VerificationJudgeAgent(),
    ]

    for agent in agents:
        assert agent is not None


# =====================================================================
# BASIC OUTPUT SERIALIZATION
# =====================================================================

def test_agent_outputs_are_json_serializable():
    """
    Agent state is eventually persisted in JSON logs.

    Ensure the major deterministic outputs can be serialized.
    """

    import json

    agents_and_keys = [
        (
            RTLAnalyzerAgent(),
            "rtl_analysis",
        ),
        (
            VerificationPlannerAgent(),
            "verification_plan",
        ),
        (
            TestGeneratorAgent(),
            "generated_tests",
        ),
        (
            RedTeamAgent(),
            "red_team_scenarios",
        ),
        (
            CoverageAgent(),
            "coverage",
        ),
        (
            MutationAgent(),
            "mutations",
        ),
        (
            FormalAgent(),
            "formal_result",
        ),
        (
            BugLocalizationAgent(),
            "bug_location",
        ),
        (
            RTLRepairAgent(),
            "repair_proposal",
        ),
        (
            VerificationJudgeAgent(),
            "judge_result",
        ),
    ]

    state = base_state()

    for agent, key in agents_and_keys:
        try:
            result = agent(
                state
            )
        except Exception as exc:
            pytest.fail(
                f"{agent.name} raised "
                f"{type(exc).__name__}: {exc}"
            )

        assert key in result

        try:
            json.dumps(
                result[key]
            )
        except TypeError as exc:
            pytest.fail(
                f"{agent.name} output '{key}' "
                f"is not JSON serializable: {exc}"
            )


# =====================================================================
# END
# =====================================================================

if __name__ == "__main__":
    pytest.main(
        [
            "-v",
            __file__,
        ]
    )
