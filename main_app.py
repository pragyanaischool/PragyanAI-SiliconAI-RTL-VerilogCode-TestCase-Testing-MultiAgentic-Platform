"""
PragyanAI SiliconAI
Autonomous RTL Verification & Coverage Closure Platform

Streamlit entry point.

Run:

    streamlit run main_app.py
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="PragyanAI SiliconAI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# PROJECT PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

EXAMPLES_DIR = BASE_DIR / "examples"
LOG_DIR = BASE_DIR / "verification_logs"
RUNS_DIR = LOG_DIR / "runs"

RUNS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# APPLICATION CONSTANTS
# ============================================================================

APP_NAME = "PragyanAI SiliconAI"
APP_TAGLINE = "Autonomous RTL Verification & Coverage Closure"

DEFAULT_SPECIFICATION = """
Verify the supplied RTL thoroughly.

Requirements:

1. Analyze the RTL architecture and interfaces.
2. Identify functional requirements.
3. Generate functional verification scenarios.
4. Generate boundary and corner-case tests.
5. Verify reset behavior.
6. Verify normal operating behavior.
7. Verify illegal or unexpected inputs where applicable.
8. Generate an executable Verilog/SystemVerilog testbench.
9. Compile and simulate the RTL.
10. Analyze failures and classify likely root causes.
11. Analyze verification coverage.
12. Identify coverage gaps.
13. Generate adversarial/red-team scenarios.
14. Perform mutation testing.
15. Run formal verification where supported.
16. Localize likely RTL bugs.
17. Propose conservative RTL repair when justified.
18. Re-run verification after repair.
19. Produce an independent verification judgment.
20. Never claim PASS without sufficient evidence.
""".strip()


EXAMPLES = {
    "Counter": {
        "rtl": EXAMPLES_DIR / "counter" / "counter.v",
        "tb": EXAMPLES_DIR / "counter" / "counter_tb.v",
        "description": (
            "Parameterized synchronous counter with reset, enable "
            "and wrap-around behavior."
        ),
    },
    "FIFO": {
        "rtl": EXAMPLES_DIR / "fifo" / "fifo.v",
        "tb": EXAMPLES_DIR / "fifo" / "fifo_tb.v",
        "description": (
            "Synchronous FIFO with full/empty flags, pointers and "
            "occupancy tracking."
        ),
    },
    "UART TX": {
        "rtl": EXAMPLES_DIR / "uart" / "uart.v",
        "tb": EXAMPLES_DIR / "uart" / "uart_tb.v",
        "description": (
            "UART transmitter demonstrating FSM, timing and "
            "serial protocol verification."
        ),
    },
    "ALU": {
        "rtl": EXAMPLES_DIR / "alu" / "alu.v",
        "tb": EXAMPLES_DIR / "alu" / "alu_tb.v",
        "description": (
            "Combinational ALU covering arithmetic, logic and "
            "boundary operations."
        ),
    },
}


# ============================================================================
# OPTIONAL WORKFLOW IMPORT
# ============================================================================

workflow = None
WORKFLOW_ERROR = ""

try:
    from graph.workflow import workflow as compiled_workflow
    workflow = compiled_workflow
except Exception as exc:
    WORKFLOW_ERROR = str(exc)


# ============================================================================
# CSS
# ============================================================================

st.markdown(
    """
<style>
.main-title {
    font-size: 2.4rem;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitle {
    font-size: 1.05rem;
    opacity: 0.72;
    margin-top: 0.15rem;
    margin-bottom: 1.4rem;
}

.pipeline-card {
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 10px;
    padding: 0.7rem;
    min-height: 90px;
    text-align: center;
}

.pipeline-number {
    font-size: 1.2rem;
    font-weight: 800;
}

.pipeline-name {
    font-size: 0.78rem;
    opacity: 0.75;
}

.small-muted {
    font-size: 0.82rem;
    opacity: 0.65;
}

.section-header {
    font-size: 1.35rem;
    font-weight: 700;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# HELPERS
# ============================================================================

def safe_json(value: Any) -> str:
    """Serialize an object safely for UI/download."""
    try:
        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return str(value)


def read_text_file(path: Path) -> str:
    """Read a text file."""
    try:
        return path.read_text(
            encoding="utf-8"
        )
    except Exception:
        return ""


def tool_available(name: str) -> bool:
    """Check whether a command-line EDA tool is available."""
    return shutil.which(name) is not None


def detect_tools() -> Dict[str, bool]:
    """Detect EDA/formal tools."""
    return {
        "iverilog": tool_available("iverilog"),
        "vvp": tool_available("vvp"),
        "verilator": tool_available("verilator"),
        "yosys": tool_available("yosys"),
        "sby": tool_available("sby"),
        "boolector": tool_available("boolector"),
        "z3": tool_available("z3"),
    }


def create_run() -> Tuple[str, Path]:
    """Create a unique verification run directory."""

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique = str(
        time.time_ns() % 100000
    ).zfill(5)

    run_id = (
        f"RUN_{timestamp}_{unique}"
    )

    run_dir = RUNS_DIR / run_id

    folders = [
        run_dir,
        run_dir / "rtl",
        run_dir / "testcases",
        run_dir / "simulation",
        run_dir / "failures",
        run_dir / "coverage",
        run_dir / "mutations",
        run_dir / "agents",
        run_dir / "reports",
        run_dir / "waveforms",
    ]

    for folder in folders:
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    return run_id, run_dir


def load_example(
    example_name: str,
) -> Tuple[str, str]:
    """Load example RTL and testbench."""

    config = EXAMPLES[example_name]

    rtl = read_text_file(
        config["rtl"]
    )

    tb = read_text_file(
        config["tb"]
    )

    return rtl, tb


def normalize_list(value: Any) -> List[Any]:
    """Convert common state values into a list."""

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, dict):
        return [value]

    return [value]


def get_verdict(
    state: Dict[str, Any],
) -> str:
    """Extract verification judge verdict."""

    judge = state.get(
        "judge_result",
        {},
    )

    if isinstance(judge, dict):

        for key in (
            "verdict",
            "status",
            "decision",
            "result",
        ):

            value = judge.get(key)

            if value:
                return str(
                    value
                ).upper()

    return "NOT AVAILABLE"


def get_coverage(
    state: Dict[str, Any],
) -> float:
    """Extract overall coverage."""

    coverage = state.get(
        "coverage",
        {},
    )

    if isinstance(coverage, dict):

        for key in (
            "overall",
            "overall_coverage",
            "coverage",
            "score",
        ):

            value = coverage.get(key)

            if isinstance(
                value,
                (int, float),
            ):
                return float(value)

    return 0.0


def get_mutation_score(
    state: Dict[str, Any],
) -> float:
    """Extract mutation score."""

    try:
        return float(
            state.get(
                "mutation_score",
                0,
            )
        )
    except Exception:
        return 0.0


def get_tests(
    state: Dict[str, Any],
) -> List[Any]:
    """Extract tests."""

    tests = state.get("tests")

    if tests:
        return normalize_list(tests)

    return normalize_list(
        state.get(
            "generated_tests",
            [],
        )
    )


def get_test_counts(
    state: Dict[str, Any],
) -> Tuple[int, int]:
    """Return total and passed tests."""

    tests = get_tests(state)

    total = len(tests)
    passed = 0

    for test in tests:

        if not isinstance(
            test,
            dict,
        ):
            continue

        status = str(
            test.get(
                "status",
                "",
            )
        ).upper()

        if status in {
            "PASS",
            "PASSED",
            "SUCCESS",
            "PASSING",
        }:
            passed += 1

    return total, passed


def get_mutation_counts(
    state: Dict[str, Any],
) -> Tuple[int, int, int]:
    """Return total, killed and survived mutations."""

    mutations = normalize_list(
        state.get(
            "mutations",
            [],
        )
    )

    total = len(mutations)
    killed = 0
    survived = 0

    for mutation in mutations:

        if not isinstance(
            mutation,
            dict,
        ):
            continue

        status = str(
            mutation.get(
                "status",
                mutation.get(
                    "result",
                    "",
                ),
            )
        ).upper()

        if mutation.get(
            "killed"
        ) is True:
            killed += 1

        elif mutation.get(
            "survived"
        ) is True:
            survived += 1

        elif "KILL" in status:
            killed += 1

        elif "SURVIV" in status:
            survived += 1

    return total, killed, survived


def save_initial_artifacts(
    run_dir: Path,
    specification: str,
    rtl: str,
    testbench: str,
) -> None:
    """Save initial inputs."""

    (
        run_dir / "specification.txt"
    ).write_text(
        specification or "",
        encoding="utf-8",
    )

    (
        run_dir
        / "rtl"
        / "input_rtl.v"
    ).write_text(
        rtl or "",
        encoding="utf-8",
    )

    if testbench:

        (
            run_dir
            / "testcases"
            / "input_testbench.v"
        ).write_text(
            testbench,
            encoding="utf-8",
        )


def save_run_state(
    run_dir: Path,
    state: Dict[str, Any],
) -> Path:
    """Save final state as JSON."""

    path = (
        run_dir
        / "run.json"
    )

    path.write_text(
        safe_json(state),
        encoding="utf-8",
    )

    return path


def create_report(
    run_dir: Path,
    state: Dict[str, Any],
) -> Path:
    """Create a Markdown verification report."""

    total_tests, passed_tests = (
        get_test_counts(state)
    )

    total_mutations, killed, survived = (
        get_mutation_counts(state)
    )

    lines = [
        "# PragyanAI SiliconAI",
        "",
        "# Autonomous RTL Verification Report",
        "",
        f"**Run ID:** `{state.get('run_id', '')}`",
        "",
        "## Summary",
        "",
        f"- Status: **{state.get('status', '')}**",
        f"- Verdict: **{get_verdict(state)}**",
        f"- Coverage: **{get_coverage(state):.2f}%**",
        f"- Mutation Score: **{get_mutation_score(state):.2f}%**",
        f"- Tests: **{total_tests}**",
        f"- Tests Passed: **{passed_tests}**",
        f"- Mutations: **{total_mutations}**",
        f"- Mutations Killed: **{killed}**",
        f"- Mutations Survived: **{survived}**",
        f"- Iteration: **{state.get('iteration', 0)}**",
        "",
        "## RTL Analysis",
        "",
        "```json",
        safe_json(
            state.get(
                "rtl_analysis",
                {},
            )
        ),
        "```",
        "",
        "## Verification Plan",
        "",
        "```json",
        safe_json(
            state.get(
                "verification_plan",
                {},
            )
        ),
        "```",
        "",
        "## Tests",
        "",
        "```json",
        safe_json(get_tests(state)),
        "```",
        "",
        "## Coverage",
        "",
        "```json",
        safe_json(
            state.get(
                "coverage",
                {},
            )
        ),
        "```",
        "",
        "## Coverage Gaps",
        "",
    ]

    gaps = normalize_list(
        state.get(
            "coverage_gaps",
            [],
        )
    )

    if gaps:

        for gap in gaps:
            lines.append(
                f"- {gap}"
            )

    else:

        lines.append(
            "- No coverage gaps reported."
        )

    lines.extend(
        [
            "",
            "## Red-Team Scenarios",
            "",
            "```json",
            safe_json(
                state.get(
                    "red_team_scenarios",
                    [],
                )
            ),
            "```",
            "",
            "## Mutation Results",
            "",
            "```json",
            safe_json(
                state.get(
                    "mutations",
                    [],
                )
            ),
            "```",
            "",
            "## Formal Verification",
            "",
            "```json",
            safe_json(
                state.get(
                    "formal_result",
                    {},
                )
            ),
            "```",
            "",
            "## Failure Analysis",
            "",
            "```json",
            safe_json(
                state.get(
                    "failure_analysis",
                    {},
                )
            ),
            "```",
            "",
            "## Bug Localization",
            "",
            "```json",
            safe_json(
                state.get(
                    "bug_location",
                    {},
                )
            ),
            "```",
            "",
            "## RTL Repair",
            "",
            "```json",
            safe_json(
                state.get(
                    "repair_proposal",
                    {},
                )
            ),
            "```",
            "",
            "## Verification Judge",
            "",
            "```json",
            safe_json(
                state.get(
                    "judge_result",
                    {},
                )
            ),
            "```",
            "",
            "## Agent Trace",
            "",
            "```json",
            safe_json(
                state.get(
                    "agent_trace",
                    [],
                )
            ),
            "```",
            "",
        ]
    )

    path = (
        run_dir
        / "reports"
        / "verification_report.md"
    )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return path


# ============================================================================
# SESSION STATE
# ============================================================================

if "verification_state" not in st.session_state:
    st.session_state.verification_state = None

if "run_id" not in st.session_state:
    st.session_state.run_id = ""

if "run_dir" not in st.session_state:
    st.session_state.run_dir = ""


# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    f"""
<div class="main-title">
    🔬 {APP_NAME}
</div>
<div class="subtitle">
    {APP_TAGLINE}
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:

    st.header(
        "⚙️ Verification Setup"
    )

    input_mode = st.radio(
        "RTL Input",
        [
            "Example Design",
            "Upload RTL",
            "Paste RTL",
        ],
    )

    selected_example = None
    uploaded_file = None

    if input_mode == "Example Design":

        selected_example = st.selectbox(
            "Select Example",
            list(EXAMPLES.keys()),
        )

        st.caption(
            EXAMPLES[
                selected_example
            ]["description"]
        )

    elif input_mode == "Upload RTL":

        uploaded_file = st.file_uploader(
            "Upload RTL",
            type=[
                "v",
                "sv",
                "vh",
                "svh",
            ],
        )

    else:

        st.info(
            "Paste your RTL in the editor "
            "on the main page."
        )

    st.divider()

    st.subheader(
        "Verification Controls"
    )

    max_iterations = st.slider(
        "Maximum Iterations",
        min_value=1,
        max_value=10,
        value=3,
    )

    enable_mutation = st.checkbox(
        "Enable Mutation Testing",
        value=True,
    )

    enable_formal = st.checkbox(
        "Enable Formal Verification",
        value=True,
    )

    st.divider()

    st.subheader(
        "EDA Environment"
    )

    tools = detect_tools()

    tool_labels = {
        "iverilog": "Icarus Verilog",
        "vvp": "VVP",
        "verilator": "Verilator",
        "yosys": "Yosys",
        "sby": "SymbiYosys",
        "boolector": "Boolector",
        "z3": "Z3",
    }

    for key, available in tools.items():

        label = tool_labels[key]

        if available:
            st.success(
                f"✓ {label}"
            )
        else:
            st.warning(
                f"○ {label}"
            )

    st.divider()

    if workflow is None:

        st.error(
            "Verification workflow could not be loaded."
        )

        if WORKFLOW_ERROR:
            st.caption(
                WORKFLOW_ERROR
            )


# ============================================================================
# LOAD RTL
# ============================================================================

rtl_code = ""
example_testbench = ""

if input_mode == "Example Design":

    rtl_code, example_testbench = (
        load_example(
            selected_example
        )
    )

elif input_mode == "Upload RTL":

    if uploaded_file is not None:

        try:

            rtl_code = (
                uploaded_file
                .getvalue()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

        except Exception as exc:

            st.error(
                f"Unable to read RTL: {exc}"
            )

else:

    rtl_code = st.session_state.get(
        "pasted_rtl",
        "",
    )


# ============================================================================
# MAIN INPUT
# ============================================================================

left_col, right_col = st.columns(
    [1.35, 1]
)


with left_col:

    st.subheader(
        "🧩 RTL Design"
    )

    if input_mode == "Paste RTL":

        rtl_code = st.text_area(
            "Verilog / SystemVerilog",
            value=rtl_code,
            height=430,
            key="pasted_rtl",
            placeholder=(
                "Paste your Verilog/SystemVerilog RTL here..."
            ),
        )

    else:

        st.code(
            rtl_code
            if rtl_code
            else "// No RTL loaded.",
            language="verilog",
        )


with right_col:

    st.subheader(
        "📋 Verification Specification"
    )

    specification = st.text_area(
        "Requirements",
        value=DEFAULT_SPECIFICATION,
        height=330,
    )

    st.info(
        "SiliconAI uses the specification, RTL structure, "
        "simulation evidence, coverage, mutation results "
        "and formal results to build verification evidence."
    )


# ============================================================================
# PIPELINE
# ============================================================================

st.subheader(
    "🤖 Autonomous Verification Pipeline"
)

pipeline = [
    "RTL Analysis",
    "Planning",
    "Test Generation",
    "Testbench",
    "Simulation",
    "Failure / Coverage",
    "Red Team",
    "Mutation",
    "Formal",
    "Judge",
]

pipeline_columns = st.columns(
    len(pipeline)
)

for index, (
    column,
    name,
) in enumerate(
    zip(
        pipeline_columns,
        pipeline,
    ),
    start=1,
):

    with column:

        st.markdown(
            f"""
<div class="pipeline-card">
    <div class="pipeline-number">{index}</div>
    <div class="pipeline-name">{name}</div>
</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================================
# RUN CONTROLS
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

    reset_clicked = st.button(
        "Reset",
        use_container_width=True,
    )

    if reset_clicked:

        st.session_state.verification_state = None
        st.session_state.run_id = ""
        st.session_state.run_dir = ""

        st.rerun()


# ============================================================================
# EXECUTE WORKFLOW
# ============================================================================

if run_clicked:

    run_id, run_dir = create_run()

    st.session_state.run_id = run_id
    st.session_state.run_dir = str(
        run_dir
    )

    save_initial_artifacts(
        run_dir=run_dir,
        specification=specification,
        rtl=rtl_code,
        testbench=example_testbench,
    )

    initial_state: Dict[str, Any] = {
        "prompt": specification,
        "specification": specification,
        "rtl_code": rtl_code,
        "rtl_version": 1,
        "rtl_history": [],
        "rtl_analysis": {},
        "verification_plan": {},
        "generated_tests": [],
        "tests": [],
        "testbench": example_testbench,
        "test_code": example_testbench,
        "run_output": "",
        "simulation_output": "",
        "compile_output": "",
        "compile_error": "",
        "simulation_error": "",
        "simulation_passed": False,
        "failure_analysis": {},
        "root_cause": "",
        "coverage": {},
        "coverage_gaps": [],
        "red_team_scenarios": [],
        "mutations": [],
        "mutation_score": 0.0,
        "formal_result": {},
        "bug_location": {},
        "repair_proposal": {},
        "repaired_rtl": "",
        "verification_score": 0.0,
        "judge_result": {},
        "agent_log": [],
        "agent_trace": [],
        "iteration": 0,
        "max_iterations": max_iterations,
        "status": "STARTED",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "next_action": "",
        "retry_required": False,
        "stop_reason": "",
        "messages": [],
        "warnings": [],
        "errors": [],
        "run_mutation": enable_mutation,
        "run_formal": enable_formal,
    }

    progress = st.progress(
        0,
        text="Starting verification...",
    )

    status_area = st.empty()

    final_state = dict(
        initial_state
    )

    try:

        # ================================================================
        # Preferred streaming execution
        # ================================================================

        if hasattr(
            workflow,
            "stream",
        ):

            progress_map = {
                "rtl_analysis": 10,
                "verification_planning": 20,
                "test_generation": 30,
                "testbench_generation": 40,
                "simulation": 50,
                "failure_analysis": 57,
                "coverage": 65,
                "red_team": 73,
                "mutation": 82,
                "formal": 90,
                "judge": 97,
            }

            try:

                events = workflow.stream(
                    initial_state,
                    stream_mode="updates",
                )

                for event in events:

                    if not isinstance(
                        event,
                        dict,
                    ):
                        continue

                    for node_name, update in (
                        event.items()
                    ):

                        if isinstance(
                            update,
                            dict,
                        ):

                            final_state.update(
                                update
                            )

                        percent = progress_map.get(
                            node_name
                        )

                        if percent is not None:

                            progress.progress(
                                percent,
                                text=(
                                    "Running: "
                                    + node_name
                                    .replace(
                                        "_",
                                        " ",
                                    )
                                    .title()
                                ),
                            )

                            status_area.info(
                                "Agent: **"
                                + node_name
                                .replace(
                                    "_",
                                    " ",
                                )
                                .title()
                                + "**"
                            )

            except TypeError:

                final_state = workflow.invoke(
                    initial_state
                )

        else:

            final_state = workflow.invoke(
                initial_state
            )

        if not isinstance(
            final_state,
            dict,
        ):
            final_state = dict(
                final_state
            )

        final_state.setdefault(
            "run_id",
            run_id,
        )

        final_state.setdefault(
            "run_dir",
            str(run_dir),
        )

        save_run_state(
            run_dir,
            final_state,
        )

        create_report(
            run_dir,
            final_state,
        )

        st.session_state.verification_state = (
            final_state
        )

        progress.progress(
            100,
            text="Verification completed.",
        )

        verdict = get_verdict(
            final_state
        )

        if verdict == "PASS":

            status_area.success(
                "✅ Verification completed — PASS"
            )

        elif verdict == "FAIL":

            status_area.error(
                "❌ Verification completed — FAIL"
            )

        else:

            status_area.warning(
                "⚠️ Verification completed — "
                + verdict
            )

    except Exception as exc:

        final_state["status"] = "ERROR"

        final_state["errors"] = (
            final_state.get(
                "errors",
                [],
            )
            + [str(exc)]
        )

        save_run_state(
            run_dir,
            final_state,
        )

        st.session_state.verification_state = (
            final_state
        )

        status_area.error(
            "Verification execution failed."
        )

        st.exception(exc)


# ============================================================================
# RESULTS
# ============================================================================

state = st.session_state.verification_state


if state:

    st.divider()

    st.header(
        "📊 Verification Results"
    )

    total_tests, passed_tests = (
        get_test_counts(state)
    )

    total_mutations, killed, survived = (
        get_mutation_counts(state)
    )

    coverage = get_coverage(
        state
    )

    mutation_score = get_mutation_score(
        state
    )

    verdict = get_verdict(
        state
    )

    # ========================================================================
    # KPI CARDS
    # ========================================================================

    metrics = st.columns(6)

    with metrics[0]:

        st.metric(
            "Verdict",
            verdict,
        )

    with metrics[1]:

        st.metric(
            "Coverage",
            f"{coverage:.1f}%",
        )

    with metrics[2]:

        st.metric(
            "Mutation",
            f"{mutation_score:.1f}%",
        )

    with metrics[3]:

        st.metric(
            "Tests",
            total_tests,
        )

    with metrics[4]:

        st.metric(
            "Passed",
            passed_tests,
        )

    with metrics[5]:

        st.metric(
            "Iteration",
            f"{state.get('iteration', 0)}"
            f"/"
            f"{state.get('max_iterations', 0)}",
        )

    # ========================================================================
    # VERDICT
    # ========================================================================

    if verdict == "PASS":

        st.success(
            "### ✅ Verification PASS\n"
            "The verification judge accepted the available evidence."
        )

    elif verdict == "FAIL":

        st.error(
            "### ❌ Verification FAIL\n"
            "The verification evidence contains unresolved failures."
        )

    else:

        st.warning(
            "### ⚠️ Verification Status: "
            + verdict
        )

    # ========================================================================
    # RESULT TABS
    # ========================================================================

    tabs = st.tabs(
        [
            "Overview",
            "RTL",
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
    # OVERVIEW
    # ========================================================================

    with tabs[0]:

        st.subheader(
            "Verification Overview"
        )

        left, right = st.columns(2)

        with left:

            st.markdown(
                "### Run Information"
            )

            st.json(
                {
                    "run_id": state.get(
                        "run_id"
                    ),
                    "status": state.get(
                        "status"
                    ),
                    "iteration": state.get(
                        "iteration"
                    ),
                    "max_iterations": state.get(
                        "max_iterations"
                    ),
                    "next_action": state.get(
                        "next_action"
                    ),
                    "stop_reason": state.get(
                        "stop_reason"
                    ),
                }
            )

        with right:

            st.markdown(
                "### Verification Evidence"
            )

            formal = state.get(
                "formal_result",
                {},
            )

            formal_status = None

            if isinstance(
                formal,
                dict,
            ):
                formal_status = formal.get(
                    "status"
                )

            st.json(
                {
                    "simulation_passed": state.get(
                        "simulation_passed"
                    ),
                    "coverage": coverage,
                    "mutation_score": mutation_score,
                    "formal_status": formal_status,
                    "judge_verdict": verdict,
                }
            )

        st.markdown(
            "### Overall Verification Score"
        )

        try:
            score = float(
                state.get(
                    "verification_score",
                    0,
                )
            )
        except Exception:
            score = 0.0

        score = max(
            0.0,
            min(
                100.0,
                score,
            ),
        )

        st.progress(
            score / 100.0
        )

        st.caption(
            f"{score:.2f}%"
        )

    # ========================================================================
    # RTL
    # ========================================================================

    with tabs[1]:

        st.subheader(
            "RTL Analysis"
        )

        analysis = state.get(
            "rtl_analysis",
            {},
        )

        if analysis:

            st.json(
                analysis
            )

        else:

            st.info(
                "No RTL analysis available."
            )

        with st.expander(
            "RTL Source"
        ):

            st.code(
                state.get(
                    "rtl_code",
                    "",
                ),
                language="verilog",
            )

        repaired_rtl = state.get(
            "repaired_rtl",
            "",
        )

        if repaired_rtl:

            with st.expander(
                "Repaired RTL"
            ):

                st.code(
                    repaired_rtl,
                    language="verilog",
                )

    # ========================================================================
    # TESTS
    # ========================================================================

    with tabs[2]:

        st.subheader(
            "Generated Tests"
        )

        tests = get_tests(
            state
        )

        if not tests:

            st.info(
                "No generated tests available."
            )

        for index, test in enumerate(
            tests,
            start=1,
        ):

            if isinstance(
                test,
                dict,
            ):

                title = (
                    test.get("id")
                    or test.get("name")
                    or f"Test {index}"
                )

                with st.expander(
                    str(title)
                ):

                    st.json(
                        test
                    )

            else:

                st.write(
                    f"{index}. {test}"
                )

    # ========================================================================
    # SIMULATION
    # ========================================================================

    with tabs[3]:

        st.subheader(
            "Simulation Results"
        )

        sim_cols = st.columns(3)

        with sim_cols[0]:

            st.metric(
                "Simulation",
                (
                    "PASS"
                    if state.get(
                        "simulation_passed"
                    )
                    else "FAIL"
                ),
            )

        with sim_cols[1]:

            st.metric(
                "Compile Error",
                (
                    "Yes"
                    if state.get(
                        "compile_error"
                    )
                    else "No"
                ),
            )

        with sim_cols[2]:

            st.metric(
                "Runtime Error",
                (
                    "Yes"
                    if state.get(
                        "simulation_error"
                    )
                    else "No"
                ),
            )

        if state.get(
            "compile_output"
        ):

            with st.expander(
                "Compile Output"
            ):

                st.code(
                    str(
                        state.get(
                            "compile_output"
                        )
                    )
                )

        if state.get(
            "compile_error"
        ):

            st.error(
                str(
                    state.get(
                        "compile_error"
                    )
                )
            )

        if state.get(
            "simulation_output"
        ):

            with st.expander(
                "Simulation Output",
                expanded=True,
            ):

                st.code(
                    str(
                        state.get(
                            "simulation_output"
                        )
                    )
                )

        if state.get(
            "simulation_error"
        ):

            st.error(
                str(
                    state.get(
                        "simulation_error"
                    )
                )
            )

        testbench = state.get(
            "testbench",
            "",
        )

        if testbench:

            with st.expander(
                "Testbench"
            ):

                st.code(
                    testbench,
                    language="verilog",
                )

    # ========================================================================
    # COVERAGE
    # ========================================================================

    with tabs[4]:

        st.subheader(
            "Coverage Analysis"
        )

        coverage_data = state.get(
            "coverage",
            {},
        )

        if isinstance(
            coverage_data,
            dict,
        ):

            coverage_fields = [
                "line",
                "branch",
                "toggle",
                "fsm",
                "functional",
                "assertion",
                "mutation",
                "overall",
            ]

            coverage_values = []

            for field in coverage_fields:

                value = coverage_data.get(
                    field
                )

                if isinstance(
                    value,
                    (int, float),
                ):

                    coverage_values.append(
                        (
                            field,
                            float(value),
                        )
                    )

            if coverage_values:

                cols = st.columns(4)

                for index, (
                    field,
                    value,
                ) in enumerate(
                    coverage_values
                ):

                    with cols[
                        index % 4
                    ]:

                        st.metric(
                            field.title(),
                            f"{value:.1f}%",
                        )

            st.json(
                coverage_data
            )

        gaps = normalize_list(
            state.get(
                "coverage_gaps",
                [],
            )
        )

        st.markdown(
            "### Coverage Gaps"
        )

        if gaps:

            for gap in gaps:

                st.warning(
                    str(gap)
                )

        else:

            st.success(
                "No coverage gaps reported."
            )

    # ========================================================================
    # RED TEAM
    # ========================================================================

    with tabs[5]:

        st.subheader(
            "🔴 Red-Team Scenarios"
        )

        scenarios = normalize_list(
            state.get(
                "red_team_scenarios",
                [],
            )
        )

        if not scenarios:

            st.info(
                "No red-team scenarios available."
            )

        for index, scenario in enumerate(
            scenarios,
            start=1,
        ):

            if isinstance(
                scenario,
                dict,
            ):

                title = (
                    scenario.get(
                        "id"
                    )
                    or scenario.get(
                        "name"
                    )
                    or f"Scenario {index}"
                )

                with st.expander(
                    str(title)
                ):

                    st.json(
                        scenario
                    )

            else:

                st.write(
                    f"{index}. {scenario}"
                )

    # ========================================================================
    # MUTATION
    # ========================================================================

    with tabs[6]:

        st.subheader(
            "🧬 Mutation Testing"
        )

        mutation_cols = st.columns(4)

        with mutation_cols[0]:

            st.metric(
                "Mutation Score",
                f"{mutation_score:.1f}%",
            )

        with mutation_cols[1]:

            st.metric(
                "Mutants",
                total_mutations,
            )

        with mutation_cols[2]:

            st.metric(
                "Killed",
                killed,
            )

        with mutation_cols[3]:

            st.metric(
                "Survived",
                survived,
            )

        mutations = normalize_list(
            state.get(
                "mutations",
                [],
            )
        )

        for index, mutation in enumerate(
            mutations,
            start=1,
        ):

            if isinstance(
                mutation,
                dict,
            ):

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

                    st.json(
                        mutation
                    )

    # ========================================================================
    # FORMAL
    # ========================================================================

    with tabs[7]:

        st.subheader(
            "Formal Verification"
        )

        formal = state.get(
            "formal_result",
            {},
        )

        if isinstance(
            formal,
            dict,
        ):

            formal_status = str(
                formal.get(
                    "status",
                    "NOT AVAILABLE",
                )
            ).upper()

            if formal_status == "PROVEN":

                st.success(
                    "✓ Formal properties proven."
                )

            elif formal_status == "FAILED":

                st.error(
                    "✗ Formal verification failed."
                )

            else:

                st.warning(
                    f"Formal status: {formal_status}"
                )

            st.json(
                formal
            )

        else:

            st.info(
                "No formal verification result."
            )

    # ========================================================================
    # FAILURE ANALYSIS
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

            if isinstance(
                failure,
                dict,
            ):

                st.metric(
                    "Category",
                    str(
                        failure.get(
                            "category",
                            "UNKNOWN",
                        )
                    ),
                )

                st.json(
                    failure
                )

            else:

                st.write(
                    failure
                )

        else:

            st.success(
                "No failure analysis result."
            )

        root_cause = state.get(
            "root_cause",
            "",
        )

        if root_cause:

            st.markdown(
                "### Root Cause"
            )

            st.write(
                root_cause
            )

    # ========================================================================
    # REPAIR
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

            st.json(
                repair
            )

        else:

            st.info(
                "No RTL repair proposal."
            )

        repaired_rtl = state.get(
            "repaired_rtl",
            "",
        )

        if repaired_rtl:

            with st.expander(
                "Repaired RTL"
            ):

                st.code(
                    repaired_rtl,
                    language="verilog",
                )

    # ========================================================================
    # JUDGE
    # ========================================================================

    with tabs[10]:

        st.subheader(
            "⚖️ Independent Verification Judge"
        )

        judge = state.get(
            "judge_result",
            {},
        )

        if isinstance(
            judge,
            dict,
        ):

            judge_verdict = str(
                judge.get(
                    "verdict",
                    "NOT AVAILABLE",
                )
            ).upper()

            if judge_verdict == "PASS":

                st.success(
                    "### ✅ PASS"
                )

            elif judge_verdict == "FAIL":

                st.error(
                    "### ❌ FAIL"
                )

            else:

                st.warning(
                    f"### ⚠️ {judge_verdict}"
                )

            st.json(
                judge
            )

        else:

            st.info(
                "No judge result."
            )

    # ========================================================================
    # AGENT TRACE
    # ========================================================================

    with tabs[11]:

        st.subheader(
            "🤖 Agent Trace"
        )

        trace = state.get(
            "agent_trace",
            [],
        )

        if isinstance(
            trace,
            list,
        ):

            st.metric(
                "Trace Events",
                len(trace),
            )

            for index, event in enumerate(
                trace,
                start=1,
            ):

                if isinstance(
                    event,
                    dict,
                ):

                    title = (
                        event.get(
                            "agent"
                        )
                        or event.get(
                            "node"
                        )
                        or event.get(
                            "name"
                        )
                        or f"Event {index}"
                    )

                    with st.expander(
                        str(title)
                    ):

                        st.json(
                            event
                        )

                else:

                    st.write(
                        f"{index}. {event}"
                    )

        elif trace:

            st.json(
                trace
            )

        else:

            st.info(
                "No agent trace available."
            )

    # ========================================================================
    # RAW STATE
    # ========================================================================

    with tabs[12]:

        st.subheader(
            "Raw Verification State"
        )

        st.json(
            state
        )

    # ========================================================================
    # DOWNLOADS
    # ========================================================================

    st.divider()

    st.subheader(
        "📥 Download Verification Artifacts"
    )

    current_run_dir = Path(
        state.get(
            "run_dir",
            st.session_state.run_dir,
        )
    )

    report_file = (
        current_run_dir
        / "reports"
        / "verification_report.md"
    )

    download_cols = st.columns(3)

    with download_cols[0]:

        st.download_button(
            "⬇️ State JSON",
            data=safe_json(state),
            file_name=(
                f"{state.get('run_id', 'verification')}.json"
            ),
            mime="application/json",
            use_container_width=True,
        )

    with download_cols[1]:

        if report_file.exists():

            report_data = report_file.read_text(
                encoding="utf-8"
            )

            st.download_button(
                "⬇️ Markdown Report",
                data=report_data,
                file_name=(
                    f"{state.get('run_id', 'verification')}.md"
                ),
                mime="text/markdown",
                use_container_width=True,
            )

        else:

            st.button(
                "Report Unavailable",
                disabled=True,
                use_container_width=True,
            )

    with download_cols[2]:

        st.download_button(
            "⬇️ Verified RTL",
            data=state.get(
                "rtl_code",
                "",
            ),
            file_name="verified_rtl.v",
            mime="text/plain",
            use_container_width=True,
        )

    st.caption(
        f"Run directory: {current_run_dir}"
    )


# ============================================================================
# LANDING PAGE
# ============================================================================

else:

    st.divider()

    st.header(
        "🚀 Autonomous Verification Starts Here"
    )

    st.markdown(
        """
### From RTL to Verification Evidence

PragyanAI SiliconAI is designed to go beyond simple
AI-generated testbenches.

The platform creates an autonomous verification loop:

```text
RTL + Specification
        ↓
   RTL Analysis
        ↓
 Verification Plan
        ↓
 Test Generation
        ↓
 Testbench Generation
        ↓
 Compile + Simulate
        ↓
 ┌──────┴──────┐
FAIL           PASS
 ↓              ↓
Failure       Coverage
Analysis        ↓
 ↓            Red Team
Repair          ↓
 ↓           Mutation
Bug Location    ↓
 ↓            Formal
Test Generation ↓
 └──────→ Judge
              ↓
       PASS / FAIL / RETRY

       """)
