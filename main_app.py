"""
PragyanAI SiliconAI
Agentic RTL Verification Platform

Streamlit application for:

    RTL
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
    RTL Repair / Bug Localization
     ↓
    Red Team
     ↓
    Mutation Testing
     ↓
    Formal Analysis
     ↓
    Verification Judge
     ↓
    Verification Report

Supported EDA tools:
    Icarus Verilog
    Verilator
    Yosys

SymbiYosys is intentionally NOT required by this application.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st


# =====================================================================
# PAGE CONFIG
# =====================================================================

st.set_page_config(
    page_title="PragyanAI SiliconAI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================================
# PATHS
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent

EXAMPLES_DIR = BASE_DIR / "examples"
LOG_DIR = BASE_DIR / "verification_logs"
RUNS_DIR = LOG_DIR / "runs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# OPTIONAL WORKFLOW IMPORT
# =====================================================================

workflow = None
WORKFLOW_ERROR = None

try:
    from graph.workflow import workflow as compiled_workflow

    workflow = compiled_workflow

except Exception:
    import traceback

    WORKFLOW_ERROR = traceback.format_exc()
    workflow = None


# =====================================================================
# EXAMPLES
# =====================================================================

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
            "Synchronous FIFO with full/empty handling, read/write "
            "pointers and occupancy tracking."
        ),
    },
    "UART TX": {
        "rtl": EXAMPLES_DIR / "uart" / "uart.v",
        "tb": EXAMPLES_DIR / "uart" / "uart_tb.v",
        "description": (
            "UART transmitter with start bit, eight data bits and "
            "stop bit."
        ),
    },
    "ALU": {
        "rtl": EXAMPLES_DIR / "alu" / "alu.v",
        "tb": EXAMPLES_DIR / "alu" / "alu_tb.v",
        "description": (
            "Combinational ALU covering arithmetic and logical "
            "operations."
        ),
    },
}


# =====================================================================
# DEFAULT SPECIFICATION
# =====================================================================

DEFAULT_SPECIFICATION = """
Verify the RTL comprehensively.

1. Verify reset behavior.
2. Verify normal functional operation.
3. Verify enable/control behavior.
4. Verify minimum input values.
5. Verify maximum input values.
6. Verify boundary conditions.
7. Verify overflow behavior.
8. Verify underflow behavior where applicable.
9. Verify back-to-back transactions.
10. Verify idle behavior.
11. Verify state transitions.
12. Verify illegal or unexpected inputs.
13. Verify protocol behavior.
14. Verify timing-sensitive behavior.
15. Verify output stability.
16. Verify corner cases.
17. Verify error handling.
18. Identify potential RTL bugs.
19. Generate adversarial/red-team scenarios.
20. Perform mutation testing and assess verification strength.
"""


# =====================================================================
# CSS
# =====================================================================

st.markdown(
    """
<style>

.main-title {
    font-size: 2.45rem;
    font-weight: 750;
    margin-bottom: 0.1rem;
}

.subtitle {
    font-size: 1.05rem;
    opacity: 0.78;
    margin-bottom: 1.2rem;
}

.pipeline {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 12px 0 20px 0;
}

.pipeline-item {
    border: 1px solid rgba(128,128,128,0.35);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.82rem;
    background: rgba(128,128,128,0.07);
}

.section-card {
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
}

.small-muted {
    opacity: 0.65;
    font-size: 0.82rem;
}

</style>
""",
    unsafe_allow_html=True,
)


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def safe_json(value: Any) -> Any:
    """
    Convert arbitrary Python objects into JSON-safe structures.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(k): safe_json(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            safe_json(v)
            for v in value
        ]

    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def read_text_file(path: Path) -> str:
    """
    Read a text file safely.
    """

    try:
        if path.exists():
            return path.read_text(
                encoding="utf-8",
                errors="replace",
            )
    except Exception:
        pass

    return ""


def tool_available(name: str) -> bool:
    """
    Check whether an executable is available.

    SymbiYosys is intentionally not checked.
    """

    return shutil.which(name) is not None


def detect_tools() -> Dict[str, bool]:
    """
    Detect supported EDA tools.
    """

    return {
        "iverilog": tool_available("iverilog"),
        "vvp": tool_available("vvp"),
        "verilator": tool_available("verilator"),
        "yosys": tool_available("yosys"),
    }


def create_run() -> tuple[str, Path]:
    """
    Create a unique verification run directory.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique = str(int(time.time() * 1000))[-6:]

    run_id = f"RUN_{timestamp}_{unique}"

    run_dir = RUNS_DIR / run_id

    subdirs = [
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
    ]

    for directory in subdirs:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return run_id, run_dir


def load_example(
    example_name: str,
) -> tuple[str, str]:
    """
    Load example RTL and testbench.
    """

    item = EXAMPLES.get(example_name)

    if not item:
        return "", ""

    rtl = read_text_file(item["rtl"])
    tb = read_text_file(item["tb"])

    return rtl, tb


def normalize_list(value: Any) -> List[Any]:
    """
    Normalize None/scalar/list-like values to a list.
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


def get_verdict(state: Dict[str, Any]) -> str:
    """
    Extract final verification verdict.
    """

    judge = state.get("judge_result", {})

    if not isinstance(judge, dict):
        judge = {}

    verdict = (
        judge.get("verdict")
        or judge.get("status")
        or judge.get("result")
        or state.get("status")
        or ""
    )

    text = str(verdict).strip().upper()

    if text in {
        "PASS",
        "PASSED",
        "VERIFIED",
        "SIGNOFF",
        "SIGNOFF_READY",
    }:
        return "PASS"

    if text in {
        "FAIL",
        "FAILED",
        "FAILURE",
        "NOT_VERIFIED",
    }:
        return "FAIL"

    return "NEED_MORE_VERIFICATION"


def get_coverage(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return coverage dictionary.
    """

    coverage = state.get("coverage", {})

    if isinstance(coverage, dict):
        return coverage

    return {}


def get_mutation_score(
    state: Dict[str, Any],
) -> float:
    """
    Return mutation score.
    """

    value = state.get(
        "mutation_score",
        0.0,
    )

    if isinstance(
        value,
        dict,
    ):
        value = (
            value.get("score")
            or value.get("mutation_score")
            or 0.0
        )

    try:
        return float(value)
    except Exception:
        return 0.0


def get_tests(
    state: Dict[str, Any],
) -> List[Any]:
    """
    Return generated tests.
    """

    tests = state.get(
        "tests",
        state.get(
            "generated_tests",
            [],
        ),
    )

    return normalize_list(tests)


def get_test_counts(
    tests: List[Any],
) -> tuple[int, int, int]:
    """
    Calculate total/pass/fail test counts.
    """

    total = len(tests)
    passed = 0
    failed = 0

    for test in tests:

        if not isinstance(test, dict):
            continue

        status = str(
            test.get("status", "")
        ).upper()

        if status in {
            "PASS",
            "PASSED",
        }:
            passed += 1

        elif status in {
            "FAIL",
            "FAILED",
        }:
            failed += 1

    return total, passed, failed


def get_mutation_counts(
    state: Dict[str, Any],
) -> tuple[int, int, int]:
    """
    Calculate mutation totals.
    """

    mutations = normalize_list(
        state.get("mutations", [])
    )

    total = len(mutations)
    killed = 0
    survived = 0

    for mutation in mutations:

        if not isinstance(mutation, dict):
            continue

        status = str(
            mutation.get("status", "")
        ).upper()

        if status == "KILLED":
            killed += 1

        elif status == "SURVIVED":
            survived += 1

    return total, killed, survived


def save_initial_artifacts(
    run_dir: Path,
    rtl_code: str,
    specification: str,
    testbench: str = "",
) -> None:
    """
    Save initial user inputs.
    """

    (run_dir / "rtl" / "original_rtl.v").write_text(
        rtl_code or "",
        encoding="utf-8",
    )

    (run_dir / "specification.txt").write_text(
        specification or "",
        encoding="utf-8",
    )

    if testbench:
        (
            run_dir
            / "testcases"
            / "initial_testbench.v"
        ).write_text(
            testbench,
            encoding="utf-8",
        )


def save_run_state(
    run_dir: Path,
    state: Dict[str, Any],
) -> None:
    """
    Save complete verification state as JSON.
    """

    output = run_dir / "run.json"

    try:
        output.write_text(
            json.dumps(
                safe_json(state),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as exc:

        fallback = {
            "error": str(exc),
            "state": str(state),
        }

        output.write_text(
            json.dumps(
                fallback,
                indent=2,
            ),
            encoding="utf-8",
        )


def create_report(
    run_dir: Path,
    state: Dict[str, Any],
) -> Path:
    """
    Create a simple Markdown verification report.

    This fallback report does not depend on the report package,
    making the Streamlit application more robust.
    """

    verdict = get_verdict(state)
    coverage = get_coverage(state)
    tests = get_tests(state)

    total_tests, passed_tests, failed_tests = (
        get_test_counts(tests)
    )

    mutation_total, mutation_killed, mutation_survived = (
        get_mutation_counts(state)
    )

    mutation_score = get_mutation_score(state)

    lines = [
        "# PragyanAI SiliconAI Verification Report",
        "",
        f"**Run ID:** `{state.get('run_id', '')}`",
        "",
        f"**Verdict:** **{verdict}**",
        "",
        "## RTL Analysis",
        "",
        "```text",
        str(
            state.get(
                "rtl_analysis",
                {},
            )
        ),
        "```",
        "",
        "## Verification Plan",
        "",
        "```text",
        str(
            state.get(
                "verification_plan",
                {},
            )
        ),
        "```",
        "",
        "## Test Summary",
        "",
        f"- Total tests: {total_tests}",
        f"- Passed: {passed_tests}",
        f"- Failed: {failed_tests}",
        "",
        "## Simulation",
        "",
        f"- Passed: {state.get('simulation_passed', False)}",
        "",
        "### Compile Output",
        "",
        "```text",
        str(
            state.get(
                "compile_output",
                "",
            )
        ),
        "```",
        "",
        "### Simulation Output",
        "",
        "```text",
        str(
            state.get(
                "simulation_output",
                "",
            )
        ),
        "```",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(
            safe_json(coverage),
            indent=2,
        ),
        "```",
        "",
        "## Mutation Testing",
        "",
        f"- Total mutations: {mutation_total}",
        f"- Killed: {mutation_killed}",
        f"- Survived: {mutation_survived}",
        f"- Mutation score: {mutation_score:.1f}%",
        "",
        "## Failure Analysis",
        "",
        "```text",
        str(
            state.get(
                "failure_analysis",
                {},
            )
        ),
        "```",
        "",
        "## Bug Localization",
        "",
        "```text",
        str(
            state.get(
                "bug_location",
                {},
            )
        ),
        "```",
        "",
        "## RTL Repair",
        "",
        "```text",
        str(
            state.get(
                "repair_proposal",
                {},
            )
        ),
        "```",
        "",
        "## Formal Verification",
        "",
        "```json",
        json.dumps(
            safe_json(
                state.get(
                    "formal_result",
                    {},
                )
            ),
            indent=2,
        ),
        "```",
        "",
        "## Verification Judge",
        "",
        "```json",
        json.dumps(
            safe_json(
                state.get(
                    "judge_result",
                    {},
                )
            ),
            indent=2,
        ),
        "```",
        "",
    ]

    report_path = (
        run_dir
        / "reports"
        / "verification_report.md"
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return report_path


# =====================================================================
# SESSION STATE
# =====================================================================

if "verification_state" not in st.session_state:
    st.session_state.verification_state = None

if "run_id" not in st.session_state:
    st.session_state.run_id = None

if "run_dir" not in st.session_state:
    st.session_state.run_dir = None


# =====================================================================
# SIDEBAR
# =====================================================================

with st.sidebar:

    st.header("🔬 Verification Setup")

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
            "Select Design",
            list(EXAMPLES.keys()),
        )

        if selected_example:
            st.caption(
                EXAMPLES[selected_example][
                    "description"
                ]
            )

    elif input_mode == "Upload RTL":

        uploaded_file = st.file_uploader(
            "Upload Verilog/SystemVerilog",
            type=[
                "v",
                "sv",
                "vh",
                "svh",
            ],
        )

    st.divider()

    max_iterations = st.slider(
        "Maximum Verification Iterations",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    st.divider()

    st.subheader("Verification Engines")

    run_mutation = st.checkbox(
        "Enable Mutation Testing",
        value=True,
        help=(
            "Create RTL mutants and measure whether "
            "the verification environment detects them."
        ),
    )

    run_formal = st.checkbox(
        "Enable Formal Analysis",
        value=False,
        help=(
            "Run the optional formal verification agent. "
            "SymbiYosys is not required by this application."
        ),
    )

    st.divider()

    st.subheader("EDA Tools")

    tools = detect_tools()

    st.write(
        f"**Icarus Verilog:** "
        f"{'✅ Available' if tools['iverilog'] else '❌ Not found'}"
    )

    st.write(
        f"**VVP:** "
        f"{'✅ Available' if tools['vvp'] else '❌ Not found'}"
    )

    st.write(
        f"**Verilator:** "
        f"{'✅ Available' if tools['verilator'] else '❌ Not found'}"
    )

    st.write(
        f"**Yosys:** "
        f"{'✅ Available' if tools['yosys'] else '❌ Not found'}"
    )

    st.caption(
        "SymbiYosys is intentionally not used."
    )


# =====================================================================
# MAIN HEADER
# =====================================================================

st.markdown(
    '<div class="main-title">🔬 PragyanAI SiliconAI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Agentic RTL Verification • AI Test Generation • "
    "Simulation • Coverage • Mutation • Formal • Repair"
    "</div>",
    unsafe_allow_html=True,
)


# =====================================================================
# WORKFLOW STATUS
# =====================================================================

if workflow is None:

    st.error(
        "Verification workflow could not be loaded."
    )

    with st.expander(
        "Show workflow loading error",
        expanded=True,
    ):

        if WORKFLOW_ERROR:
            st.code(
                WORKFLOW_ERROR,
                language="text",
            )
        else:
            st.write(
                "Unknown workflow loading error."
            )

    st.info(
        "Check graph/state.py, graph/router.py and "
        "graph/workflow.py before running verification."
    )

    st.stop()


# =====================================================================
# PIPELINE
# =====================================================================

pipeline = [
    "RTL Analysis",
    "Planning",
    "Test Generation",
    "Testbench",
    "Simulation",
    "Failure Analysis",
    "Coverage",
    "Red Team",
    "Mutation",
    "Formal",
    "Judge",
]

pipeline_html = '<div class="pipeline">'

for index, item in enumerate(pipeline):

    pipeline_html += (
        f'<div class="pipeline-item">'
        f"{index + 1}. {item}"
        f"</div>"
    )

pipeline_html += "</div>"

st.markdown(
    pipeline_html,
    unsafe_allow_html=True,
)


# =====================================================================
# RTL INPUT
# =====================================================================

st.subheader("1. RTL Design")


rtl_code = ""
initial_testbench = ""

if input_mode == "Example Design":

    rtl_code, initial_testbench = load_example(
        selected_example
    )

elif input_mode == "Upload RTL":

    if uploaded_file is not None:

        try:
            rtl_code = uploaded_file.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            rtl_code = ""

else:

    rtl_code = ""


if input_mode == "Paste RTL":

    rtl_code = st.text_area(
        "Paste Verilog/SystemVerilog RTL",
        value=(
            st.session_state.get(
                "rtl_editor_value",
                "",
            )
        ),
        height=350,
        key="rtl_editor",
    )

else:

    rtl_code = st.text_area(
        "RTL",
        value=rtl_code,
        height=350,
        key="rtl_display",
    )


# =====================================================================
# SPECIFICATION
# =====================================================================

st.subheader("2. Verification Specification")

specification = st.text_area(
    "Specification / Verification Requirements",
    value=st.session_state.get(
        "specification_value",
        DEFAULT_SPECIFICATION.strip(),
    ),
    height=280,
    key="specification_editor",
)


# =====================================================================
# TESTBENCH INPUT
# =====================================================================

with st.expander(
    "Optional: Inspect Example Testbench",
    expanded=False,
):

    if initial_testbench:

        st.code(
            initial_testbench,
            language="verilog",
        )

    else:

        st.caption(
            "The AI Testbench Generator will create the testbench."
        )


# =====================================================================
# START VERIFICATION
# =====================================================================

st.subheader("3. Run Verification")

col1, col2, col3 = st.columns(
    [2, 2, 2]
)

with col1:

    st.metric(
        "RTL Lines",
        len(
            (rtl_code or "").splitlines()
        ),
    )

with col2:

    st.metric(
        "Specification Lines",
        len(
            (specification or "").splitlines()
        ),
    )

with col3:

    st.metric(
        "Max Iterations",
        max_iterations,
    )


start_button = st.button(
    "🚀 Start Agentic Verification",
    type="primary",
    use_container_width=True,
    disabled=not bool(
        (rtl_code or "").strip()
    ),
)


# =====================================================================
# VERIFICATION EXECUTION
# =====================================================================

if start_button:

    if not rtl_code.strip():

        st.error(
            "Please provide RTL before starting verification."
        )

        st.stop()

    if not specification.strip():

        st.error(
            "Please provide a verification specification."
        )

        st.stop()

    if not tools["iverilog"]:

        st.warning(
            "Icarus Verilog was not detected. "
            "Simulation may fail until Icarus is installed."
        )

    # -------------------------------------------------------------
    # Create run
    # -------------------------------------------------------------

    run_id, run_dir = create_run()

    save_initial_artifacts(
        run_dir=run_dir,
        rtl_code=rtl_code,
        specification=specification,
        testbench=initial_testbench,
    )

    # -------------------------------------------------------------
    # Initial state
    # -------------------------------------------------------------

    initial_state = {
        "prompt": specification,
        "specification": specification,

        "rtl_code": rtl_code,
        "rtl_version": 1,
        "rtl_history": [],

        "rtl_analysis": {},
        "verification_plan": {},

        "generated_tests": [],
        "tests": [],

        "testbench": initial_testbench,
        "test_code": initial_testbench,

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

        "status": "READY",

        "run_id": run_id,
        "run_dir": str(run_dir),

        "next_action": "rtl_analysis",

        "retry_required": False,
        "stop_reason": "",

        "run_mutation": run_mutation,
        "run_formal": run_formal,

        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # -------------------------------------------------------------
    # Save initial state
    # -------------------------------------------------------------

    save_run_state(
        run_dir,
        initial_state,
    )

    # -------------------------------------------------------------
    # UI containers
    # -------------------------------------------------------------

    st.divider()

    st.subheader(
        f"Running Verification — `{run_id}`"
    )

    progress_bar = st.progress(0)

    status_placeholder = st.empty()

    trace_placeholder = st.empty()

    progress_steps = {
        "rtl_analysis": 8,
        "planning": 15,
        "test_generation": 25,
        "testbench_generation": 35,
        "simulation": 50,
        "failure_analysis": 58,
        "rtl_repair": 65,
        "bug_localization": 70,
        "coverage": 78,
        "red_team": 84,
        "mutation": 90,
        "formal": 95,
        "judge": 99,
    }

    final_state = None

    # -------------------------------------------------------------
    # Execute graph
    # -------------------------------------------------------------

    try:

        status_placeholder.info(
            "Initializing verification workflow..."
        )

        # ---------------------------------------------------------
        # Prefer streaming execution
        # ---------------------------------------------------------

        try:

            stream = workflow.stream(
                initial_state,
                stream_mode="updates",
            )

            accumulated = dict(initial_state)

            for event in stream:

                if not isinstance(event, dict):
                    continue

                # LangGraph update format:
                #
                # {
                #     "node_name": {
                #         "state_key": value,
                #         ...
                #     }
                # }
                #

                for node_name, node_update in event.items():

                    if isinstance(
                        node_update,
                        dict,
                    ):

                        accumulated.update(
                            node_update
                        )

                    progress = progress_steps.get(
                        str(node_name),
                        5,
                    )

                    progress_bar.progress(
                        min(
                            max(
                                int(progress),
                                0,
                            ),
                            100,
                        )
                    )

                    status_placeholder.info(
                        f"Running agent: **{node_name}**"
                    )

                    # -------------------------------------------------
                    # Lightweight trace
                    # -------------------------------------------------

                    trace = accumulated.get(
                        "agent_trace",
                        [],
                    )

                    if isinstance(trace, list):

                        recent = trace[-5:]

                        if recent:

                            trace_text = []

                            for item in recent:

                                if isinstance(
                                    item,
                                    dict,
                                ):

                                    agent_name = (
                                        item.get(
                                            "agent"
                                        )
                                        or item.get(
                                            "name"
                                        )
                                        or item.get(
                                            "node"
                                        )
                                        or "Agent"
                                    )

                                    trace_text.append(
                                        f"• {agent_name}"
                                    )

                            if trace_text:

                                trace_placeholder.caption(
                                    "Recent agent activity\n"
                                    + "\n".join(
                                        trace_text
                                    )
                                )

            final_state = accumulated

        except Exception as stream_exc:

            # ---------------------------------------------------------
            # Fallback to invoke
            # ---------------------------------------------------------

            status_placeholder.warning(
                "Streaming execution failed. "
                "Retrying using standard workflow invocation..."
            )

            try:

                result = workflow.invoke(
                    initial_state
                )

                if isinstance(
                    result,
                    dict,
                ):

                    final_state = result

                else:

                    final_state = dict(
                        initial_state
                    )

                    final_state["errors"] = [
                        (
                            "Workflow returned unsupported "
                            "result type: "
                            f"{type(result).__name__}"
                        )
                    ]

            except Exception as invoke_exc:

                raise RuntimeError(
                    "Workflow execution failed.\n\n"
                    "Streaming error:\n"
                    f"{stream_exc}\n\n"
                    "Invoke error:\n"
                    f"{invoke_exc}"
                ) from invoke_exc

        # ---------------------------------------------------------
        # Ensure dictionary
        # ---------------------------------------------------------

        if final_state is None:

            final_state = dict(
                initial_state
            )

        if not isinstance(
            final_state,
            dict,
        ):

            final_state = dict(
                initial_state
            )

        # ---------------------------------------------------------
        # Save state
        # ---------------------------------------------------------

        save_run_state(
            run_dir,
            final_state,
        )

        # ---------------------------------------------------------
        # Create report
        # ---------------------------------------------------------

        report_path = create_report(
            run_dir,
            final_state,
        )

        # ---------------------------------------------------------
        # Session state
        # ---------------------------------------------------------

        st.session_state.verification_state = (
            final_state
        )

        st.session_state.run_id = run_id
        st.session_state.run_dir = str(
            run_dir
        )

        progress_bar.progress(100)

        status_placeholder.success(
            "Verification workflow completed."
        )

        # ---------------------------------------------------------
        # Final verdict
        # ---------------------------------------------------------

        verdict = get_verdict(
            final_state
        )

        if verdict == "PASS":

            st.success(
                "✅ Verification PASS"
            )

        elif verdict == "FAIL":

            st.error(
                "❌ Verification FAIL"
            )

        else:

            st.warning(
                "⚠️ Verification requires more verification."
            )

    except Exception as exc:

        error_text = (
            f"{type(exc).__name__}: {exc}"
        )

        st.error(
            "Verification execution failed."
        )

        with st.expander(
            "Show execution error",
            expanded=True,
        ):

            import traceback

            st.code(
                traceback.format_exc(),
                language="text",
            )

        # Save failure state
        failure_state = dict(
            initial_state
        )

        failure_state["status"] = "ERROR"

        failure_state["errors"] = list(
            failure_state.get(
                "errors",
                [],
            )
        ) + [
            error_text
        ]

        save_run_state(
            run_dir,
            failure_state,
        )

        st.session_state.verification_state = (
            failure_state
        )

        st.session_state.run_id = run_id

        st.session_state.run_dir = str(
            run_dir
        )


# =====================================================================
# LOAD PREVIOUS STATE
# =====================================================================

state = st.session_state.get(
    "verification_state"
)


# =====================================================================
# RESULT DASHBOARD
# =====================================================================

if state:

    st.divider()

    st.header("4. Verification Results")

    verdict = get_verdict(
        state
    )

    coverage = get_coverage(
        state
    )

    tests = get_tests(
        state
    )

    total_tests, passed_tests, failed_tests = (
        get_test_counts(tests)
    )

    mutation_total, mutation_killed, mutation_survived = (
        get_mutation_counts(state)
    )

    mutation_score = get_mutation_score(
        state
    )

    # -------------------------------------------------------------
    # Summary metrics
    # -------------------------------------------------------------

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.metric(
            "Verdict",
            verdict,
        )

    with c2:

        st.metric(
            "Tests",
            total_tests,
        )

    with c3:

        st.metric(
            "Passed",
            passed_tests,
        )

    with c4:

        overall_coverage = (
            coverage.get("overall")
            or coverage.get(
                "overall_coverage",
                0,
            )
        )

        try:
            coverage_display = (
                f"{float(overall_coverage):.1f}%"
            )
        except Exception:
            coverage_display = "0%"

        st.metric(
            "Coverage",
            coverage_display,
        )

    with c5:

        st.metric(
            "Mutation",
            f"{mutation_score:.1f}%",
        )


# =====================================================================
# RESULT TABS
# =====================================================================

if state:

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

    # -------------------------------------------------------------
    # Overview
    # -------------------------------------------------------------

    with tabs[0]:

        st.subheader(
            "Verification Overview"
        )

        judge = state.get(
            "judge_result",
            {},
        )

        if isinstance(
            judge,
            dict,
        ):

            st.json(
                safe_json(judge)
            )

        st.markdown(
            f"**Run ID:** `{state.get('run_id', '')}`"
        )

        st.markdown(
            f"**Status:** `{state.get('status', '')}`"
        )

        st.markdown(
            f"**Iteration:** "
            f"`{state.get('iteration', 0)}` / "
            f"`{state.get('max_iterations', 0)}`"
        )

        if state.get("errors"):

            st.error(
                "\n".join(
                    str(x)
                    for x in normalize_list(
                        state.get("errors")
                    )
                )
            )

        if state.get("warnings"):

            st.warning(
                "\n".join(
                    str(x)
                    for x in normalize_list(
                        state.get("warnings")
                    )
                )
            )

    # -------------------------------------------------------------
    # RTL
    # -------------------------------------------------------------

    with tabs[1]:

        st.subheader(
            "RTL Analysis"
        )

        st.code(
            state.get(
                "rtl_code",
                "",
            ),
            language="verilog",
        )

        st.subheader(
            "RTL Analysis Result"
        )

        st.json(
            safe_json(
                state.get(
                    "rtl_analysis",
                    {},
                )
            )
        )

    # -------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------

    with tabs[2]:

        st.subheader(
            "Generated Tests"
        )

        if tests:

            for index, test in enumerate(
                tests,
                start=1,
            ):

                with st.expander(
                    f"Test {index}"
                ):

                    if isinstance(
                        test,
                        dict,
                    ):

                        st.json(
                            safe_json(test)
                        )

                    else:

                        st.write(test)

        else:

            st.info(
                "No generated tests were returned."
            )

        st.subheader(
            "Testbench"
        )

        testbench = (
            state.get("testbench")
            or state.get(
                "test_code",
                "",
            )
        )

        if testbench:

            st.code(
                testbench,
                language="verilog",
            )

        else:

            st.info(
                "No testbench generated."
            )

    # -------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------

    with tabs[3]:

        st.subheader(
            "Simulation Result"
        )

        simulation_passed = state.get(
            "simulation_passed",
            False,
        )

        if simulation_passed:

            st.success(
                "Simulation passed."
            )

        else:

            st.error(
                "Simulation did not pass."
            )

        st.markdown(
            "### Compile Output"
        )

        st.code(
            state.get(
                "compile_output",
                "",
            ),
            language="text",
        )

        if state.get(
            "compile_error"
        ):

            st.markdown(
                "### Compile Error"
            )

            st.code(
                state.get(
                    "compile_error",
                    "",
                ),
                language="text",
            )

        st.markdown(
            "### Simulation Output"
        )

        st.code(
            state.get(
                "simulation_output",
                state.get(
                    "run_output",
                    "",
                ),
            ),
            language="text",
        )

        if state.get(
            "simulation_error"
        ):

            st.markdown(
                "### Simulation Error"
            )

            st.code(
                state.get(
                    "simulation_error",
                    "",
                ),
                language="text",
            )

    # -------------------------------------------------------------
    # Coverage
    # -------------------------------------------------------------

    with tabs[4]:

        st.subheader(
            "Coverage"
        )

        st.json(
            safe_json(
                coverage
            )
        )

        gaps = normalize_list(
            state.get(
                "coverage_gaps",
                [],
            )
        )

        st.subheader(
            "Coverage Gaps"
        )

        if gaps:

            for gap in gaps:

                if isinstance(
                    gap,
                    dict,
                ):

                    st.write(
                        gap
                    )

                else:

                    st.write(
                        str(gap)
                    )

        else:

            st.success(
                "No explicit coverage gaps reported."
            )

    # -------------------------------------------------------------
    # Red Team
    # -------------------------------------------------------------

    with tabs[5]:

        st.subheader(
            "Adversarial / Red-Team Scenarios"
        )

        scenarios = normalize_list(
            state.get(
                "red_team_scenarios",
                [],
            )
        )

        if scenarios:

            for index, scenario in enumerate(
                scenarios,
                start=1,
            ):

                with st.expander(
                    f"Scenario {index}"
                ):

                    if isinstance(
                        scenario,
                        dict,
                    ):

                        st.json(
                            safe_json(
                                scenario
                            )
                        )

                    else:

                        st.write(
                            scenario
                        )

        else:

            st.info(
                "No red-team scenarios generated."
            )

    # -------------------------------------------------------------
    # Mutation
    # -------------------------------------------------------------

    with tabs[6]:

        st.subheader(
            "Mutation Testing"
        )

        st.metric(
            "Mutation Score",
            f"{mutation_score:.1f}%",
        )

        st.write(
            f"Total: {mutation_total}"
        )

        st.write(
            f"Killed: {mutation_killed}"
        )

        st.write(
            f"Survived: {mutation_survived}"
        )

        mutations = normalize_list(
            state.get(
                "mutations",
                [],
            )
        )

        if mutations:

            st.subheader(
                "Mutation Results"
            )

            for index, mutation in enumerate(
                mutations,
                start=1,
            ):

                if isinstance(
                    mutation,
                    dict,
                ):

                    status = str(
                        mutation.get(
                            "status",
                            "UNKNOWN",
                        )
                    ).upper()

                    with st.expander(
                        f"Mutation {index} — {status}"
                    ):

                        st.json(
                            safe_json(
                                mutation
                            )
                        )

        else:

            st.info(
                "No mutation results available."
            )

    # -------------------------------------------------------------
    # Formal
    # -------------------------------------------------------------

    with tabs[7]:

        st.subheader(
            "Formal Verification"
        )

        formal_result = state.get(
            "formal_result",
            {},
        )

        if formal_result:

            st.json(
                safe_json(
                    formal_result
                )
            )

        else:

            st.info(
                "No formal verification result available."
            )

        st.caption(
            "Formal analysis is optional. "
            "This application does not require SymbiYosys."
        )

    # -------------------------------------------------------------
    # Failures
    # -------------------------------------------------------------

    with tabs[8]:

        st.subheader(
            "Failure Analysis"
        )

        failure_analysis = state.get(
            "failure_analysis",
            {},
        )

        if failure_analysis:

            st.json(
                safe_json(
                    failure_analysis
                )
            )

        else:

            st.info(
                "No failure analysis available."
            )

        if state.get(
            "root_cause"
        ):

            st.markdown(
                "### Root Cause"
            )

            st.write(
                state.get(
                    "root_cause"
                )
            )

    # -------------------------------------------------------------
    # Repair
    # -------------------------------------------------------------

    with tabs[9]:

        st.subheader(
            "RTL Repair"
        )

        repair_proposal = state.get(
            "repair_proposal",
            {},
        )

        if repair_proposal:

            st.json(
                safe_json(
                    repair_proposal
                )
            )

        else:

            st.info(
                "No RTL repair proposal available."
            )

        bug_location = state.get(
            "bug_location",
            {},
        )

        if bug_location:

            st.subheader(
                "Bug Localization"
            )

            st.json(
                safe_json(
                    bug_location
                )
            )

        repaired_rtl = state.get(
            "repaired_rtl",
            "",
        )

        if repaired_rtl:

            st.subheader(
                "Repaired RTL"
            )

            st.code(
                repaired_rtl,
                language="verilog",
            )

    # -------------------------------------------------------------
    # Judge
    # -------------------------------------------------------------

    with tabs[10]:

        st.subheader(
            "Independent Verification Judge"
        )

        judge_result = state.get(
            "judge_result",
            {},
        )

        if judge_result:

            st.json(
                safe_json(
                    judge_result
                )
            )

        else:

            st.info(
                "Judge result not available."
            )

        st.markdown(
            f"### Final Verdict: **{verdict}**"
        )

    # -------------------------------------------------------------
    # Agent Trace
    # -------------------------------------------------------------

    with tabs[11]:

        st.subheader(
            "Agent Execution Trace"
        )

        trace = normalize_list(
            state.get(
                "agent_trace",
                [],
            )
        )

        if trace:

            for index, event in enumerate(
                trace,
                start=1,
            ):

                with st.expander(
                    f"Event {index}"
                ):

                    if isinstance(
                        event,
                        dict,
                    ):

                        st.json(
                            safe_json(
                                event
                            )
                        )

                    else:

                        st.write(
                            event
                        )

        else:

            st.info(
                "No agent trace available."
            )

        agent_log = normalize_list(
            state.get(
                "agent_log",
                [],
            )
        )

        if agent_log:

            st.subheader(
                "Agent Log"
            )

            st.json(
                safe_json(
                    agent_log
                )
            )

    # -------------------------------------------------------------
    # Raw State
    # -------------------------------------------------------------

    with tabs[12]:

        st.subheader(
            "Raw Verification State"
        )

        st.json(
            safe_json(
                state
            )
        )


# =====================================================================
# DOWNLOADS
# =====================================================================

if state:

    st.divider()

    st.subheader(
        "5. Verification Artifacts"
    )

    run_dir_value = state.get(
        "run_dir"
    )

    if run_dir_value:

        run_dir_path = Path(
            str(run_dir_value)
        )

        json_path = (
            run_dir_path
            / "run.json"
        )

        report_path = (
            run_dir_path
            / "reports"
            / "verification_report.md"
        )

        rtl_path = (
            run_dir_path
            / "rtl"
            / "original_rtl.v"
        )

        d1, d2, d3 = st.columns(3)

        with d1:

            if json_path.exists():

                st.download_button(
                    "⬇️ Download Run JSON",
                    data=json_path.read_text(
                        encoding="utf-8"
                    ),
                    file_name=(
                        f"{state.get('run_id', 'run')}.json"
                    ),
                    mime="application/json",
                    use_container_width=True,
                )

        with d2:

            if report_path.exists():

                st.download_button(
                    "⬇️ Download Markdown Report",
                    data=report_path.read_text(
                        encoding="utf-8"
                    ),
                    file_name=(
                        f"{state.get('run_id', 'run')}_report.md"
                    ),
                    mime="text/markdown",
                    use_container_width=True,
                )

        with d3:

            if rtl_path.exists():

                st.download_button(
                    "⬇️ Download Original RTL",
                    data=rtl_path.read_text(
                        encoding="utf-8"
                    ),
                    file_name="original_rtl.v",
                    mime="text/plain",
                    use_container_width=True,
                )


# =====================================================================
# LANDING PAGE / INFORMATION
# =====================================================================

if not state:

    st.divider()

    st.subheader(
        "Agentic Verification Pipeline"
    )

    st.markdown(
        """
### From RTL to Verification Evidence

PragyanAI SiliconAI combines deterministic EDA execution with
AI-assisted verification reasoning.

**Core flow**

```text
RTL
 │
 ▼
RTL Analysis
 │
 ▼
Verification Planning
 │
 ▼
AI Test Generation
 │
 ▼
AI Testbench Generation
 │
 ▼
Icarus Simulation
 │
 ├───────────────┐
 │               │
 PASS            FAIL
 │               │
 ▼               ▼
Coverage     Failure Analysis
 │               │
 ▼               ├── Test Generation
Red Team         │
 │               └── RTL Repair
 ▼
Mutation
 │
 ▼
Formal Analysis
 │
 ▼
Independent Judge
 │
 ▼
Verification Report

       """)
