"""
PragyanAI SiliconAI
Autonomous RTL Verification & Coverage Closure Platform

Main Streamlit application.

Run locally:

    streamlit run main_app.py

Expected repository structure:

    main_app.py
    config/
    agents/
    graph/
    eda/
    verification/
    logging/
    reports/
    ui/
    prompts/
    examples/
    tests/
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st


# ============================================================================
# Page configuration
# ============================================================================

st.set_page_config(
    page_title="PragyanAI SiliconAI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# Paths
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

EXAMPLES_DIR = BASE_DIR / "examples"
LOG_DIR = BASE_DIR / "verification_logs"
RUNS_DIR = LOG_DIR / "runs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Imports
# ============================================================================

try:
    from graph.workflow import workflow
except Exception as exc:
    workflow = None
    WORKFLOW_IMPORT_ERROR = str(exc)
else:
    WORKFLOW_IMPORT_ERROR = ""


try:
    from eda.iverilog_runner import IcarusRunner
except Exception:
    IcarusRunner = None


# ============================================================================
# Constants
# ============================================================================

APP_NAME = "PragyanAI SiliconAI"
APP_TAGLINE = "Autonomous RTL Verification & Coverage Closure"

DEFAULT_SPEC = """Verify the RTL thoroughly.

Requirements:
1. Verify functional correctness.
2. Verify reset behavior.
3. Verify normal operating conditions.
4. Verify boundary conditions.
5. Verify illegal or unexpected inputs where applicable.
6. Generate meaningful tests.
7. Analyze coverage gaps.
8. Perform adversarial/red-team verification.
9. Perform mutation testing.
10. Run formal verification where supported.
11. Identify likely bugs.
12. Propose RTL repair only when justified.
13. Produce an independent verification judgment.
"""

EXAMPLE_DESIGNS = {
    "Counter": {
        "rtl": EXAMPLES_DIR / "counter" / "counter.v",
        "testbench": EXAMPLES_DIR / "counter" / "counter_tb.v",
        "description": "Parameterized synchronous counter with reset, enable and wrap-around.",
    },
    "FIFO": {
        "rtl": EXAMPLES_DIR / "fifo" / "fifo.v",
        "testbench": EXAMPLES_DIR / "fifo" / "fifo_tb.v",
        "description": "Synchronous FIFO with full/empty, pointers and occupancy tracking.",
    },
    "UART TX": {
        "rtl": EXAMPLES_DIR / "uart" / "uart.v",
        "testbench": EXAMPLES_DIR / "uart" / "uart_tb.v",
        "description": "UART transmitter demonstrating FSM, timing and serial protocol.",
    },
    "ALU": {
        "rtl": EXAMPLES_DIR / "alu" / "alu.v",
        "testbench": EXAMPLES_DIR / "alu" / "alu_tb.v",
        "description": "Combinational ALU covering arithmetic, logic and boundary operations.",
    },
}


# ============================================================================
# Styling
# ============================================================================

st.markdown(
    """
<style>
.main-title {
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.75;
    margin-top: 0.2rem;
    margin-bottom: 1.5rem;
}

.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-top: 1rem;
}

.metric-card {
    padding: 1rem;
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px;
    min-height: 110px;
}

.status-pass {
    font-size: 1.4rem;
    font-weight: 800;
}

.status-fail {
    font-size: 1.4rem;
    font-weight: 800;
}

.small-muted {
    font-size: 0.85rem;
    opacity: 0.65;
}

.pipeline {
    padding: 0.75rem;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# Utility functions
# ============================================================================

def safe_json(value: Any) -> str:
    """Convert arbitrary state data into readable JSON."""
    try:
        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return str(value)


def read_file(path: Path) -> str:
    """Read a text file safely."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def tool_available(tool: str) -> bool:
    """Return True when an executable is available."""
    return shutil.which(tool) is not None


def detect_tools() -> Dict[str, bool]:
    """Detect available EDA/formal tools."""
    return {
        "Icarus Verilog": tool_available("iverilog"),
        "VVP": tool_available("vvp"),
        "Verilator": tool_available("verilator"),
        "Yosys": tool_available("yosys"),
        "SymbiYosys": tool_available("sby"),
        "Boolector": tool_available("boolector"),
        "Z3": tool_available("z3"),
    }


def create_run_directory() -> tuple[str, Path]:
    """
    Create a unique verification run directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    unique = f"{time.time_ns() % 100000:05d}"

    run_id = f"RUN_{timestamp}_{unique}"

    run_dir = RUNS_DIR / run_id

    for folder in (
        run_dir,
        run_dir / "rtl",
        run_dir / "testcases",
        run_dir / "simulation",
        run_dir / "failures",
        run_dir / "coverage",
        run_dir / "agents",
        run_dir / "reports",
        run_dir / "waveforms",
        run_dir / "mutations",
    ):
        folder.mkdir(parents=True, exist_ok=True)

    return run_id, run_dir


def load_example(name: str) -> tuple[str, str]:
    """
    Load example RTL and testbench.
    """
    config = EXAMPLE_DESIGNS[name]

    rtl = read_file(config["rtl"])
    tb = read_file(config["testbench"])

    return rtl, tb


def normalize_list(value: Any) -> List[Any]:
    """Normalize state values into lists."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, dict):
        return [value]

    return [value]


def get_verdict(state: Dict[str, Any]) -> str:
    """
    Extract verification judge verdict.
    """
    judge = state.get("judge_result", {})

    if isinstance(judge, dict):
        for key in (
            "verdict",
            "status",
            "decision",
            "result",
        ):
            value = judge.get(key)

            if value:
                return str(value).upper()

    return "NOT AVAILABLE"


def get_coverage_score(state: Dict[str, Any]) -> float:
    """
    Extract overall coverage score.
    """
    coverage = state.get("coverage", {})

    if isinstance(coverage, dict):
        for key in (
            "overall",
            "overall_coverage",
            "coverage",
            "score",
        ):
            value = coverage.get(key)

            if isinstance(value, (int, float)):
                return float(value)

    value = state.get("verification_score", 0)

    if isinstance(value, (int, float)):
        return float(value)

    return 0.0


def get_mutation_score(state: Dict[str, Any]) -> float:
    value = state.get("mutation_score", 0)

    try:
        return float(value)
    except Exception:
        return 0.0


def get_test_counts(state: Dict[str, Any]) -> tuple[int, int]:
    """
    Return total and passed test counts.
    """
    tests = normalize_list(
        state.get("tests")
        or state.get("generated_tests")
    )

    total = len(tests)
    passed = 0

    for test in tests:
        if not isinstance(test, dict):
            continue

        status = str(
            test.get("status", "")
        ).upper()

        if status in {
            "PASS",
            "PASSED",
            "SUCCESS",
            "PASSING",
        }:
            passed += 1

    return total, passed


def get_mutation_counts(state: Dict[str, Any]) -> tuple[int, int, int]:
    """
    Return mutation totals.

    Returns:
        total, killed, survived
    """
    mutations = normalize_list(state.get("mutations"))

    total = len(mutations)
    killed = 0
    survived = 0

    for mutation in mutations:
        if not isinstance(mutation, dict):
            continue

        status = str(
            mutation.get(
                "status",
                mutation.get("result", ""),
            )
        ).upper()

        if mutation.get("killed") is True:
            killed += 1
        elif mutation.get("survived") is True:
            survived += 1
        elif "KILL" in status:
            killed += 1
        elif "SURVIV" in status:
            survived += 1

    return total, killed, survived


def state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact state summary for UI/logging.
    """
    total_tests, passed_tests = get_test_counts(state)
    total_mutations, killed, survived = get_mutation_counts(state)

    return {
        "run_id": state.get("run_id", ""),
        "status": state.get("status", ""),
        "verdict": get_verdict(state),
        "coverage": get_coverage_score(state),
        "mutation_score": get_mutation_score(state),
        "tests": total_tests,
        "tests_passed": passed_tests,
        "mutations": total_mutations,
        "mutations_killed": killed,
        "mutations_survived": survived,
        "iteration": state.get("iteration", 0),
        "max_iterations": state.get("max_iterations", 0),
    }


def save_state(run_dir: Path, state: Dict[str, Any]) -> Path:
    """
    Persist final state.
    """
    path = run_dir / "run.json"

    path.write_text(
        safe_json(state),
        encoding="utf-8",
    )

    return path


def save_input_artifacts(
    run_dir: Path,
    specification: str,
    rtl_code: str,
    testbench: str = "",
) -> None:
    """
    Save user inputs into the run directory.
    """
    (run_dir / "specification.txt").write_text(
        specification or "",
        encoding="utf-8",
    )

    (run_dir / "rtl" / "input_rtl.v").write_text(
        rtl_code or "",
        encoding="utf-8",
    )

    if testbench:
        (run_dir / "testcases" / "input_testbench.v").write_text(
            testbench,
            encoding="utf-8",
        )


def save_markdown_report(
    run_dir: Path,
    state: Dict[str, Any],
) -> Path:
    """
    Generate a lightweight Markdown report directly from workflow state.

    The dedicated reports/ modules can additionally generate richer reports.
    """
    summary = state_summary(state)

    lines = [
        "# PragyanAI SiliconAI Verification Report",
        "",
        f"**Run ID:** `{summary['run_id']}`",
        "",
        "## Verification Summary",
        "",
        f"- Status: **{summary['status']}**",
        f"- Verdict: **{summary['verdict']}**",
        f"- Coverage: **{summary['coverage']:.2f}%**",
        f"- Mutation Score: **{summary['mutation_score']:.2f}%**",
        f"- Tests: **{summary['tests']}**",
        f"- Tests Passed: **{summary['tests_passed']}**",
        f"- Mutations: **{summary['mutations']}**",
        f"- Mutations Killed: **{summary['mutations_killed']}**",
        f"- Mutations Survived: **{summary['mutations_survived']}**",
        f"- Iteration: **{summary['iteration']} / {summary['max_iterations']}**",
        "",
        "## RTL Analysis",
        "",
        "```json",
        safe_json(state.get("rtl_analysis", {})),
        "```",
        "",
        "## Verification Plan",
        "",
        "```json",
        safe_json(state.get("verification_plan", {})),
        "```",
        "",
        "## Tests",
        "",
        "```json",
        safe_json(
            state.get("tests")
            or state.get("generated_tests", [])
        ),
        "```",
        "",
        "## Coverage",
        "",
        "```json",
        safe_json(state.get("coverage", {})),
        "```",
        "",
        "## Coverage Gaps",
        "",
    ]

    gaps = normalize_list(state.get("coverage_gaps"))

    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- No coverage gaps reported.")

    lines.extend(
        [
            "",
            "## Red-Team Scenarios",
            "",
            "```json",
            safe_json(state.get("red_team_scenarios", [])),
            "```",
            "",
            "## Mutation Results",
            "",
            "```json",
            safe_json(state.get("mutations", [])),
            "```",
            "",
            "## Formal Verification",
            "",
            "```json",
            safe_json(state.get("formal_result", {})),
            "```",
            "",
            "## Failure Analysis",
            "",
            "```json",
            safe_json(state.get("failure_analysis", {})),
            "```",
            "",
            "## Bug Localization",
            "",
            "```json",
            safe_json(state.get("bug_location", {})),
            "```",
            "",
            "## RTL Repair",
            "",
            "```json",
            safe_json(state.get("repair_proposal", {})),
            "```",
            "",
            "## Verification Judge",
            "",
            "```json",
            safe_json(state.get("judge_result", {})),
            "```",
            "",
            "## Agent Trace",
            "",
            "```json",
            safe_json(state.get("agent_trace", [])),
            "```",
            "",
        ]
    )

    path = run_dir / "reports" / "verification_report.md"

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return path


# ============================================================================
# Session state
# ============================================================================

if "verification_state" not in st.session_state:
    st.session_state.verification_state = None

if "run_id" not in st.session_state:
    st.session_state.run_id = ""

if "run_dir" not in st.session_state:
    st.session_state.run_dir = ""

if "running" not in st.session_state:
    st.session_state.running = False


# ============================================================================
# Header
# ============================================================================

st.markdown(
    f"""
<div class="main-title">🔬 {APP_NAME}</div>
<div class="subtitle">
    {APP_TAGLINE}
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:

    st.header("⚙️ Verification Setup")

    mode = st.radio(
        "Input Mode",
        [
            "Example Design",
            "Upload RTL",
            "Paste RTL",
        ],
        index=0,
    )

    st.divider()

    selected_example = None

    if mode == "Example Design":

        selected_example = st.selectbox(
            "Select RTL Example",
            list(EXAMPLE_DESIGNS.keys()),
        )

        config = EXAMPLE_DESIGNS[selected_example]

        st.caption(
            config["description"]
        )

    elif mode == "Upload RTL":

        uploaded_rtl = st.file_uploader(
            "Upload Verilog/SystemVerilog",
            type=[
                "v",
                "sv",
                "vh",
                "svh",
            ],
        )

    else:

        st.caption(
            "Paste the RTL design to verify."
        )

    st.divider()

    st.subheader("Verification Controls")

    max_iterations = st.slider(
        "Maximum Repair/Test Iterations",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    run_mutation = st.checkbox(
        "Enable Mutation Testing",
        value=True,
    )

    run_formal = st.checkbox(
        "Enable Formal Verification",
        value=True,
    )

    st.divider()

    st.subheader("EDA Environment")

    tools = detect_tools()

    for tool, available in tools.items():
        if available:
            st.success(
                f"✓ {tool}",
                icon="✓",
            )
        else:
            st.warning(
                f"○ {tool}",
                icon="○",
            )

    st.divider()

    if workflow is None:
        st.error(
            "Workflow could not be loaded."
        )

        if WORKFLOW_IMPORT_ERROR:
            st.caption(
                WORKFLOW_IMPORT_ERROR
            )

    st.caption(
        "PragyanAI SiliconAI"
    )


# ============================================================================
# Input preparation
# ============================================================================

rtl_code = ""
example_testbench = ""

if mode == "Example Design" and selected_example:

    rtl_code, example_testbench = load_example(
        selected_example
    )

elif mode == "Upload RTL":

    if uploaded_rtl is not None:
        try:
            rtl_code = uploaded_rtl.getvalue().decode(
                "utf-8",
                errors="replace",
            )
        except Exception as exc:
            st.error(
                f"Could not read RTL file: {exc}"
            )

else:
    rtl_code = st.session_state.get(
        "pasted_rtl",
        "",
    )


# ============================================================================
# Main input area
# ============================================================================

left, right = st.columns(
    [1.4, 1]
)

with left:

    st.subheader("RTL Design")

    if mode == "Paste RTL":

        rtl_code = st.text_area(
            "Verilog / SystemVerilog",
            value=rtl_code,
            height=420,
            key="pasted_rtl",
            placeholder="""module example(
    input wire clk,
    input wire rst,
    output reg out
);

always @(posedge clk) begin
    if (rst)
        out <= 1'b0;
    else
        out <= ~out;
end

endmodule
""",
        )

    else:

        st.code(
            rtl_code if rtl_code else
            "// No RTL loaded.",
            language="verilog",
        )

with right:

    st.subheader("Verification Specification")

    specification = st.text_area(
        "Specification / Requirements",
        value=DEFAULT_SPEC,
        height=300,
    )

    st.info(
        "SiliconAI will combine specification-driven tests, "
        "boundary testing, adversarial scenarios, mutation testing "
        "and formal verification where available."
    )


# ============================================================================
# Pipeline visualization
# ============================================================================

st.subheader("🤖 Autonomous Verification Pipeline")

pipeline = [
    ("1", "RTL Analysis"),
    ("2", "Verification Planning"),
    ("3", "Test Generation"),
    ("4", "Testbench Generation"),
    ("5", "Simulation"),
    ("6", "Failure Analysis / Coverage"),
    ("7", "Red Team"),
    ("8", "Mutation Testing"),
    ("9", "Formal Verification"),
    ("10", "Verification Judge"),
]

cols = st.columns(len(pipeline))

for col, (number, label) in zip(cols, pipeline):

    with col:
        st.markdown(
            f"""
            <div class="pipeline">
                <strong>{number}</strong><br>
                <span class="small-muted">{label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================================
# Run button
# ============================================================================

st.divider()

run_col, reset_col = st.columns(
    [4, 1]
)

with run_col:

    run_clicked = st.button(
        "🚀 Start Autonomous Verification",
        type="primary",
        use_container_width=True,
        disabled=(
            workflow is None
            or not rtl_code.strip()
        ),
    )

with reset_col:

    if st.button(
        "Reset",
        use_container_width=True,
    ):
        st.session_state.verification_state = None
        st.session_state.run_id = ""
        st.session_state.run_dir = ""
        st.rerun()


# ============================================================================
# Workflow execution
# ============================================================================

if run_clicked:

    run_id, run_dir = create_run_directory()

    st.session_state.run_id = run_id
    st.session_state.run_dir = str(run_dir)
    st.session_state.running = True

    save_input_artifacts(
        run_dir=run_dir,
        specification=specification,
        rtl_code=rtl_code,
        testbench=example_testbench,
    )

    initial_state: Dict[str, Any] = {
        "prompt": specification,
        "specification": specification,
        "rtl_code": rtl_code,
        "rtl_version": 1,
        "rtl_history": [],
        "tests": [],
        "generated_tests": [],
        "testbench": example_testbench,
        "test_code": example_testbench,
        "simulation_passed": False,
        "coverage": {},
        "coverage_gaps": [],
        "red_team_scenarios": [],
        "mutations": [],
        "mutation_score": 0.0,
        "formal_result": {},
        "bug_location": {},
        "repair_proposal": {},
        "repaired_rtl": "",
        "failure_analysis": {},
        "judge_result": {},
        "agent_trace": [],
        "agent_log": [],
        "warnings": [],
        "errors": [],
        "messages": [],
        "iteration": 0,
        "max_iterations": max_iterations,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "STARTED",
        "next_action": "",
        "retry_required": False,
        "stop_reason": "",
    }

    # Store feature flags in state for optional agents.
    initial_state["run_mutation"] = run_mutation
    initial_state["run_formal"] = run_formal

    progress = st.progress(
        0,
        text="Starting verification...",
    )

    status_box = st.empty()

    try:

        status_box.info(
            f"Run `{run_id}` started."
        )

        # ---------------------------------------------------------------
        # Preferred streaming execution
        # ---------------------------------------------------------------

        final_state = None

        if hasattr(workflow, "stream"):

            progress_steps = {
                "rtl_analysis": 10,
                "verification_planning": 20,
                "test_generation": 30,
                "testbench_generation": 40,
                "simulation": 50,
                "failure_analysis": 55,
                "coverage": 65,
                "red_team": 72,
                "mutation": 80,
                "formal": 90,
                "judge": 97,
            }

            try:

                events = workflow.stream(
                    initial_state,
                    stream_mode="updates",
                )

                for event in events:

                    if not isinstance(event, dict):
                        continue

                    for node_name, update in event.items():

                        if isinstance(update, dict):

                            if final_state is None:
                                final_state = dict(initial_state)

                            final_state.update(update)

                        percentage = progress_steps.get(
                            node_name,
                            None,
                        )

                        if percentage is not None:

                            progress.progress(
                                percentage,
                                text=(
                                    f"Running: "
                                    f"{node_name.replace('_', ' ').title()}"
                                ),
                            )

                            status_box.info(
                                f"Agent active: "
                                f"**{node_name.replace('_', ' ').title()}**"
                            )

                if final_state is None:
                    final_state = dict(initial_state)

            except TypeError:

                # Compatibility fallback for LangGraph versions that
                # expose stream() differently.
                final_state = workflow.invoke(
                    initial_state
                )

        else:

            final_state = workflow.invoke(
                initial_state
            )

        if final_state is None:
            final_state = dict(initial_state)

        if not isinstance(final_state, dict):
            final_state = dict(final_state)

        # Ensure application metadata survives.
        final_state.setdefault(
            "run_id",
            run_id,
        )

        final_state.setdefault(
            "run_dir",
            str(run_dir),
        )

        # ---------------------------------------------------------------
        # Persist result
        # ---------------------------------------------------------------

        save_state(
            run_dir,
            final_state,
        )

        report_path = save_markdown_report(
            run_dir,
            final_state,
        )

        st.session_state.verification_state = final_state
        st.session_state.running = False

        progress.progress(
            100,
            text="Verification completed.",
        )

        verdict = get_verdict(final_state)

        if verdict == "PASS":
            status_box.success(
                "✓ Verification completed — PASS"
            )
        elif verdict == "FAIL":
            status_box.error(
                "✗ Verification completed — FAIL"
            )
        else:
            status_box.warning(
                f"Verification completed — {verdict}"
            )

    except Exception as exc:

        st.session_state.running = False

        progress.progress(
            100,
            text="Verification stopped.",
        )

        status_box.error(
            f"Verification failed: {exc}"
        )

        st.exception(exc)


# ============================================================================
# Results
# ============================================================================

state = st.session_state.verification_state

if state:

    st.divider()

    st.header("📊 Verification Results")

    summary = state_summary(state)

    # ------------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------------

    metric_cols = st.columns(6)

    with metric_cols[0]:
        st.metric(
            "Verdict",
            summary["verdict"],
        )

    with metric_cols[1]:
        st.metric(
            "Coverage",
            f"{summary['coverage']:.1f}%",
        )

    with metric_cols[2]:
        st.metric(
            "Mutation",
            f"{summary['mutation_score']:.1f}%",
        )

    with metric_cols[3]:
        st.metric(
            "Tests",
            summary["tests"],
        )

    with metric_cols[4]:
        st.metric(
            "Passed Tests",
            summary["tests_passed"],
        )

    with metric_cols[5]:
        st.metric(
            "Iteration",
            f"{summary['iteration']}/{summary['max_iterations']}",
        )

    # ------------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------------

    verdict = summary["verdict"]

    if verdict == "PASS":

        st.success(
            "### ✅ Verification PASS\n"
            "The independent verification judge accepted the available evidence."
        )

    elif verdict == "FAIL":

        st.error(
            "### ❌ Verification FAIL\n"
            "The available evidence contains unresolved verification failures."
        )

    else:

        st.warning(
            f"### ⚠️ Verification Status: {verdict}\n"
            "Additional verification may be required."
        )

    # ------------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------------

    tabs = st.tabs(
        [
            "Overview",
            "RTL Analysis",
            "Tests",
            "Simulation",
            "Coverage",
            "Red Team",
            "Mutation",
            "Formal",
            "Failures",
            "Repair",
            "Judge",
            "Agent Trace",
            "Raw State",
        ]
    )

    # ========================================================================
    # Overview
    # ========================================================================

    with tabs[0]:

        st.subheader("Verification Overview")

        overview_left, overview_right = st.columns(2)

        with overview_left:

            st.markdown("### Run")

            st.json(
                {
                    "run_id": state.get("run_id"),
                    "status": state.get("status"),
                    "iteration": state.get("iteration"),
                    "max_iterations": state.get("max_iterations"),
                    "next_action": state.get("next_action"),
                    "stop_reason": state.get("stop_reason"),
                }
            )

        with overview_right:

            st.markdown("### Evidence")

            st.json(
                {
                    "simulation_passed": state.get(
                        "simulation_passed"
                    ),
                    "coverage": get_coverage_score(state),
                    "mutation_score": get_mutation_score(state),
                    "formal_status": (
                        state.get("formal_result", {})
                        .get("status")
                        if isinstance(
                            state.get("formal_result"),
                            dict,
                        )
                        else None
                    ),
                    "judge_verdict": get_verdict(state),
                }
            )

        st.markdown("### Verification Score")

        score = state.get(
            "verification_score",
            0,
        )

        try:
            score = float(score)
        except Exception:
            score = 0.0

        st.progress(
            max(0.0, min(1.0, score / 100.0))
        )

        st.caption(
            f"Overall verification score: {score:.2f}%"
        )

    # ========================================================================
    # RTL Analysis
    # ========================================================================

    with tabs[1]:

        st.subheader("RTL Analysis")

        analysis = state.get(
            "rtl_analysis",
            {},
        )

        if analysis:
            st.json(analysis)
        else:
            st.info(
                "No RTL analysis result available."
            )

        with st.expander("RTL Source"):

            st.code(
                state.get("rtl_code", ""),
                language="verilog",
            )

    # ========================================================================
    # Tests
    # ========================================================================

    with tabs[2]:

        st.subheader("Generated Tests")

        tests = (
            state.get("tests")
            or state.get("generated_tests")
            or []
        )

        tests = normalize_list(tests)

        st.metric(
            "Generated Test Cases",
            len(tests),
        )

        for index, test in enumerate(tests, start=1):

            if isinstance(test, dict):

                title = (
                    test.get("id")
                    or test.get("name")
                    or f"Test {index}"
                )

                with st.expander(
                    f"{title}"
                ):
                    st.json(test)

            else:

                with st.expander(
                    f"Test {index}"
                ):
                    st.write(test)

    # ========================================================================
    # Simulation
    # ========================================================================

    with tabs[3]:

        st.subheader("Simulation")

        simulation_cols = st.columns(3)

        with simulation_cols[0]:

            passed = state.get(
                "simulation_passed",
                False,
            )

            st.metric(
                "Simulation",
                "PASS" if passed else "FAIL",
            )

        with simulation_cols[1]:

            st.metric(
                "Compile Errors",
                "Yes"
                if state.get("compile_error")
                else "No",
            )

        with simulation_cols[2]:

            st.metric(
                "Simulation Errors",
                "Yes"
                if state.get("simulation_error")
                else "No",
            )

        if state.get("compile_output"):

            with st.expander(
                "Compile Output",
                expanded=False,
            ):
                st.code(
                    str(state.get("compile_output"))
                )

        if state.get("compile_error"):

            with st.expander(
                "Compile Error",
                expanded=True,
            ):
                st.error(
                    str(state.get("compile_error"))
                )

        if state.get("simulation_output"):

            with st.expander(
                "Simulation Output",
                expanded=True,
            ):
                st.code(
                    str(state.get("simulation_output"))
                )

        if state.get("simulation_error"):

            with st.expander(
                "Simulation Error",
                expanded=True,
            ):
                st.error(
                    str(state.get("simulation_error"))
                )

        if state.get("testbench"):

            with st.expander(
                "Generated Testbench"
            ):
                st.code(
                    state.get("testbench"),
                    language="verilog",
                )

    # ========================================================================
    # Coverage
    # ========================================================================

    with tabs[4]:

        st.subheader("Coverage Analysis")

        coverage = state.get(
            "coverage",
            {},
        )

        if isinstance(coverage, dict):

            metric_names = [
                "line",
                "branch",
                "toggle",
                "fsm",
                "functional",
                "assertion",
                "mutation",
                "overall",
            ]

            cols = st.columns(4)

            visible_metrics = []

            for name in metric_names:

                value = coverage.get(name)

                if isinstance(value, (int, float)):

                    visible_metrics.append(
                        (name, float(value))
                    )

            for index, (name, value) in enumerate(
                visible_metrics
            ):

                with cols[index % 4]:

                    st.metric(
                        name.title(),
                        f"{value:.1f}%",
                    )

        gaps = normalize_list(
            state.get("coverage_gaps")
        )

        st.markdown("### Coverage Gaps")

        if gaps:

            for gap in gaps:
                st.warning(
                    str(gap)
                )

        else:

            st.success(
                "No coverage gaps reported."
            )

        evidence_type = (
            coverage.get("evidence_type")
            if isinstance(coverage, dict)
            else None
        )

        if evidence_type:

            if evidence_type == "REAL_COVERAGE":
                st.success(
                    "Evidence: REAL_COVERAGE"
                )
            else:
                st.info(
                    f"Evidence: {evidence_type}"
                )

        with st.expander(
            "Coverage Details"
        ):
            st.json(coverage)

    # ========================================================================
    # Red Team
    # ========================================================================

    with tabs[5]:

        st.subheader(
            "🔴 Red-Team Verification Scenarios"
        )

        scenarios = normalize_list(
            state.get(
                "red_team_scenarios"
            )
        )

        if not scenarios:

            st.info(
                "No red-team scenarios were generated."
            )

        for index, scenario in enumerate(
            scenarios,
            start=1,
        ):

            if isinstance(scenario, dict):

                title = (
                    scenario.get("id")
                    or scenario.get("name")
                    or f"Scenario {index}"
                )

                with st.expander(
                    title
                ):
                    st.json(scenario)

            else:

                st.write(
                    f"{index}. {scenario}"
                )

    # ========================================================================
    # Mutation
    # ========================================================================

    with tabs[6]:

        st.subheader(
            "🧬 Mutation Testing"
        )

        total, killed, survived = get_mutation_counts(
            state
        )

        cols = st.columns(4)

        with cols[0]:
            st.metric(
                "Mutation Score",
                f"{get_mutation_score(state):.1f}%",
            )

        with cols[1]:
            st.metric(
                "Executed",
                total,
            )

        with cols[2]:
            st.metric(
                "Killed",
                killed,
            )

        with cols[3]:
            st.metric(
                "Survived",
                survived,
            )

        mutations = normalize_list(
            state.get("mutations")
        )

        if mutations:

            for index, mutation in enumerate(
                mutations,
                start=1,
            ):

                if isinstance(mutation, dict):

                    mutation_id = (
                        mutation.get("id")
                        or mutation.get(
                            "mutation_id"
                        )
                        or mutation.get(
                            "mutant_id"
                        )
                        or f"M{index:03d}"
                    )

                    status = str(
                        mutation.get(
                            "status",
                            mutation.get(
                                "result",
                                "UNKNOWN",
                            ),
                        )
                    ).upper()

                    with st.expander(
                        f"{mutation_id} — {status}"
                    ):
                        st.json(mutation)

        else:

            st.info(
                "No mutation results available."
            )

    # ========================================================================
    # Formal
    # ========================================================================

    with tabs[7]:

        st.subheader(
            "Formal Verification"
        )

        formal = state.get(
            "formal_result",
            {},
        )

        if isinstance(formal, dict):

            status = str(
                formal.get(
                    "status",
                    "NOT AVAILABLE",
                )
            ).upper()

            if status == "PROVEN":

                st.success(
                    "✓ Formal properties proven."
                )

            elif status == "FAILED":

                st.error(
                    "✗ Formal verification found a failure."
                )

            elif status in {
                "UNAVAILABLE",
                "UNSUPPORTED",
                "SKIPPED",
                "NOT_PROVEN",
            }:

                st.warning(
                    f"Formal status: {status}"
                )

            st.json(formal)

        else:

            st.info(
                "No formal verification result."
            )

    # ========================================================================
    # Failures
    # ========================================================================

    with tabs[8]:

        st.subheader(
            "Failure Analysis"
        )

        failure = state.get(
            "failure_analysis",
            {},
        )

        if failure:

            if isinstance(failure, dict):

                category = failure.get(
                    "category",
                    "UNKNOWN",
                )

                st.metric(
                    "Failure Category",
                    str(category),
                )

                st.json(failure)

            else:

                st.write(failure)

        else:

            st.success(
                "No failure analysis result."
            )

        if state.get("root_cause"):

            st.markdown("### Root Cause")

            st.write(
                state.get("root_cause")
            )

    # ========================================================================
    # Repair
    # ========================================================================

    with tabs[9]:

        st.subheader(
            "RTL Repair"
        )

        repair = state.get(
            "repair_proposal",
            {},
        )

        if repair:

            st.json(repair)

        else:

            st.info(
                "No RTL repair proposal was generated."
            )

        repaired_rtl = state.get(
            "repaired_rtl",
            "",
        )

        if repaired_rtl:

            with st.expander(
                "Repaired RTL",
                expanded=False,
            ):

                st.code(
                    repaired_rtl,
                    language="verilog",
                )

    # ========================================================================
    # Judge
    # ========================================================================

    with tabs[10]:

        st.subheader(
            "⚖️ Independent Verification Judge"
        )

        judge = state.get(
            "judge_result",
            {},
        )

        if isinstance(judge, dict):

            verdict = str(
                judge.get(
                    "verdict",
                    "NOT AVAILABLE",
                )
            ).upper()

            if verdict == "PASS":

                st.success(
                    "### ✅ PASS"
                )

            elif verdict == "FAIL":

                st.error(
                    "### ❌ FAIL"
                )

            else:

                st.warning(
                    f"### ⚠️ {verdict}"
                )

            st.json(judge)

        else:

            st.info(
                "No verification judge result."
            )

    # ========================================================================
    # Agent trace
    # ========================================================================

    with tabs[11]:

        st.subheader(
            "🤖 Agent Execution Trace"
        )

        trace = state.get(
            "agent_trace",
            [],
        )

        if isinstance(trace, list):

            st.metric(
                "Trace Events",
                len(trace),
            )

            for index, event in enumerate(
                trace,
                start=1,
            ):

                if isinstance(event, dict):

                    title = (
                        event.get("agent")
                        or event.get("node")
                        or event.get("name")
                        or f"Event {index}"
                    )

                    with st.expander(
                        str(title),
                        expanded=False,
                    ):
                        st.json(event)

                else:

                    st.write(
                        f"{index}. {event}"
                    )

        elif trace:

            st.json(trace)

        else:

            st.info(
                "No agent trace available."
            )

    # ========================================================================
    # Raw state
    # ========================================================================

    with tabs[12]:

        st.subheader(
            "Raw Verification State"
        )

        st.json(state)

    # =========================================================================
    # Downloads
    # =========================================================================

    st.divider()

    st.subheader(
        "📥 Verification Artifacts"
    )

    current_run_dir = Path(
        state.get(
            "run_dir",
            st.session_state.run_dir,
        )
    )

    report_path = (
        current_run_dir
        / "reports"
        / "verification_report.md"
    )

    json_path = (
        current_run_dir
        / "run.json"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.download_button(
            "⬇️ Download State JSON",
            data=safe_json(state),
            file_name=(
                f"{state.get('run_id', 'verification')}.json"
            ),
            mime="application/json",
            use_container_width=True,
        )

    with col2:

        if report_path.exists():

            st.download_button(
                "⬇️ Download Markdown Report",
                data=report_path.read_text(
                    encoding="utf-8"
                ),
                file_name=(
                    f"{state.get('run_id', 'verification')}.md"
                ),
                mime="text/markdown",
                use_container_width=True,
            )

        else:

            st.button(
                "Markdown Report Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with col3:

        st.download_button(
            "⬇️ Download RTL",
            data=state.get(
                "rtl_code",
                "",
            ),
            file_name="verified_rtl.v",
            mime="text/plain",
            use_container_width=True,
        )

    st.caption(
        f"Run artifacts: `{current_run_dir}`"
    )


# ============================================================================
# Initial landing message
# ============================================================================

else:

    st.divider()

    st.subheader(
        "🚀 Autonomous Verification Starts Here"
    )

    st.markdown(
        """
### From RTL to Verification Evidence

PragyanAI SiliconAI is designed to move beyond simple
**AI-generated testbenches**.

It creates a feedback loop:

```text
RTL
 ↓
Understand
 ↓
Plan
 ↓
Generate Tests
 ↓
Generate Testbench
 ↓
Compile + Simulate
 ↓
Analyze Failure / Coverage
 ↓
Attack with Red-Team Scenarios
 ↓
Mutation Testing
 ↓
Formal Verification
 ↓
Independent Verification Judge
 ↓
PASS / FAIL / REPAIR / RETRY│
