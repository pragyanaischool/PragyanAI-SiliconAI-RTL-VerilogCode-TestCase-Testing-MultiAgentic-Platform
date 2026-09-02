import os
import re
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import TypedDict, List, Dict, Any

import streamlit as st

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END


# ============================================================
# PragyanAI SiliconAI
# Autonomous RTL Verification Studio V2
# ============================================================

st.set_page_config(
    page_title="PragyanAI SiliconAI - Autonomous RTL Verification",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# Styling
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #777;
        font-size: 1rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,.25);
        text-align: center;
    }

    .agent-card {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,.2);
        margin-bottom: 8px;
    }

    .pass {
        color: #0a8f3c;
        font-weight: 700;
    }

    .fail {
        color: #d62828;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Header
# ============================================================

st.markdown(
    '<div class="main-title">⚡ PragyanAI SiliconAI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Autonomous RTL Verification & Coverage Intelligence Studio"
    "</div>",
    unsafe_allow_html=True,
)

st.caption(
    "Specification → RTL → Testbench → Simulation → Failure Analysis "
    "→ Coverage Intelligence → Adversarial Testing → Refinement"
)


# ============================================================
# API KEY
# ============================================================

groq_api_key = None

try:
    if "GROQ_API_KEY" in st.secrets:
        groq_api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not groq_api_key:
    groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    groq_api_key = st.sidebar.text_input(
        "Groq API Key",
        type="password",
    )

if not groq_api_key:
    st.info("Enter GROQ_API_KEY in Streamlit Secrets.")
    st.stop()


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.1,
    api_key=groq_api_key,
)


# ============================================================
# Utilities
# ============================================================

def extract_code(text: str, language: str = "verilog") -> str:
    """
    Robust extraction of code from LLM response.
    """

    pattern = rf"```(?:{language}|systemverilog|sv|verilog)?\s*(.*?)```"

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return text.strip()


def run_command(
    cmd: List[str],
    timeout: int = 30,
) -> Dict[str, Any]:

    start = time.time()

    try:

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": round(time.time() - start, 3),
        }

    except subprocess.TimeoutExpired:

        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "PROCESS TIMEOUT",
            "duration": round(time.time() - start, 3),
        }

    except Exception as exc:

        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "duration": round(time.time() - start, 3),
        }


def count_rtl_features(rtl: str) -> Dict[str, int]:

    return {
        "modules": len(re.findall(r"\bmodule\b", rtl)),
        "always_blocks": len(re.findall(r"\balways\b", rtl)),
        "always_ff": len(re.findall(r"\balways_ff\b", rtl)),
        "always_comb": len(re.findall(r"\balways_comb\b", rtl)),
        "if_statements": len(re.findall(r"\bif\s*\(", rtl)),
        "case_statements": len(re.findall(r"\bcase\s*\(", rtl)),
        "states": len(
            re.findall(
                r"\b(?:IDLE|READY|BUSY|DONE|ERROR|RESET)\b",
                rtl,
                re.IGNORECASE,
            )
        ),
        "assertions": len(re.findall(r"\bassert\b", rtl)),
    }


def calculate_proxy_coverage(
    rtl: str,
    tb: str,
    simulation_output: str,
) -> Dict[str, float]:

    features = count_rtl_features(rtl)

    exercised = 0
    total = 0

    # Approximate structural targets.
    # This is NOT a replacement for simulator coverage.
    targets = {
        "if": features["if_statements"],
        "case": features["case_statements"],
        "always": features["always_blocks"],
    }

    total = sum(targets.values())

    if "if" in tb.lower():
        exercised += features["if_statements"]

    if "case" in tb.lower():
        exercised += features["case_statements"]

    if "posedge" in tb.lower():
        exercised += max(1, features["always_blocks"])

    if total == 0:
        structural = 50.0
    else:
        structural = min(
            100.0,
            100.0 * exercised / max(total, 1),
        )

    tests = len(
        re.findall(
            r"\$display|assert|check|expected",
            tb,
            re.IGNORECASE,
        )
    )

    checks = min(
        100.0,
        tests * 10.0,
    )

    simulation = 100.0 if simulation_output else 0.0

    overall = round(
        0.5 * structural
        + 0.3 * checks
        + 0.2 * simulation,
        1,
    )

    return {
        "structural_proxy": round(structural, 1),
        "check_strength": round(checks, 1),
        "simulation": round(simulation, 1),
        "overall_proxy": overall,
    }


# ============================================================
# LangGraph State
# ============================================================

class RTLState(TypedDict, total=False):

    specification: str
    rtl_code: str
    testbench: str

    analysis: str
    test_plan: str
    adversarial_plan: str

    compile_output: str
    simulation_output: str
    failure_analysis: str

    coverage: Dict[str, float]

    iteration: int
    max_iterations: int

    status: str

    agent_log: List[str]

    verification_score: float

    work_dir: str


# ============================================================
# Agent: RTL Analyzer
# ============================================================

def rtl_analyzer(state: RTLState) -> dict:

    rtl = state.get("rtl_code", "")

    if not rtl:

        return {
            "analysis": "No RTL available yet.",
            "agent_log": state.get("agent_log", [])
            + ["RTL Analyzer: waiting for RTL"],
        }

    features = count_rtl_features(rtl)

    system = """
You are an expert RTL design reviewer.

Analyze the supplied Verilog RTL.

Identify:

1. Modules
2. Inputs and outputs
3. Clock/reset
4. Sequential logic
5. Combinational logic
6. FSM/state behavior
7. Important conditions
8. Boundary conditions
9. Potential corner cases
10. Verification risks

Return a concise structured engineering analysis.
"""

    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(
                content=f"""
RTL:

{rtl}

Static features:

{json.dumps(features, indent=2)}
"""
            ),
        ]
    )

    return {
        "analysis": response.content,
        "agent_log": state.get("agent_log", [])
        + ["RTL Analyzer: completed"],
    }


# ============================================================
# Agent: Test Planner
# ============================================================

def test_planner(state: RTLState) -> dict:

    prompt = f"""
Specification:

{state.get("specification", "")}

RTL:

{state.get("rtl_code", "")}

RTL Analysis:

{state.get("analysis", "")}

Create a verification plan.

Include:

- reset tests
- normal operation
- boundary values
- minimum values
- maximum values
- illegal inputs
- simultaneous events
- repeated transactions
- corner cases
- expected outputs

Create at least 10 concrete test scenarios.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a senior semiconductor verification "
                    "engineer creating a directed verification plan."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "test_plan": response.content,
        "agent_log": state.get("agent_log", [])
        + ["Test Planner: generated verification strategy"],
    }


# ============================================================
# Agent: Adversarial Planner
# ============================================================

def adversarial_planner(state: RTLState) -> dict:

    prompt = f"""
Act as an RTL red-team verification engineer.

Specification:
{state.get("specification", "")}

RTL:
{state.get("rtl_code", "")}

Analysis:
{state.get("analysis", "")}

Generate adversarial scenarios designed to break the RTL.

Consider:

- reset during operation
- back-to-back transactions
- simultaneous enables
- illegal sequences
- overflow
- underflow
- maximum/minimum values
- repeated events
- timing boundaries
- state transitions
- unexpected protocol sequences

Return a prioritized attack list.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are an adversarial hardware verification expert."
            ),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "adversarial_plan": response.content,
        "agent_log": state.get("agent_log", [])
        + ["Red Team Agent: generated adversarial scenarios"],
    }


# ============================================================
# Agent: Testbench Generator
# ============================================================

def testbench_generator(state: RTLState) -> dict:

    prompt = f"""
Generate a self-checking Verilog/SystemVerilog testbench.

SPECIFICATION:
{state.get("specification", "")}

RTL:
{state.get("rtl_code", "")}

VERIFICATION PLAN:
{state.get("test_plan", "")}

ADVERSARIAL TEST PLAN:
{state.get("adversarial_plan", "")}

Previous failure:
{state.get("failure_analysis", "")}

Requirements:

1. Instantiate the DUT.
2. Generate clock if required.
3. Apply reset correctly.
4. Exercise normal cases.
5. Exercise corner cases.
6. Exercise adversarial cases.
7. Check expected outputs.
8. Produce PASS/FAIL messages.
9. Count passed and failed tests.
10. Finish automatically.
11. Avoid false PASS.
12. Do not simply print PASS without checking outputs.

Use:

TEST_PASS
TEST_FAIL
TEST_SUMMARY

Return ONLY code.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are an expert SystemVerilog verification engineer."
            ),
            HumanMessage(content=prompt),
        ]
    )

    tb = extract_code(response.content)

    return {
        "testbench": tb,
        "agent_log": state.get("agent_log", [])
        + ["Testbench Agent: generated self-checking testbench"],
    }


# ============================================================
# Agent: Compiler + Simulator
# ============================================================

def simulator_agent(state: RTLState) -> dict:

    rtl = state.get("rtl_code", "")
    tb = state.get("testbench", "")

    work_dir = tempfile.mkdtemp(
        prefix="siliconai_rtl_"
    )

    rtl_file = Path(work_dir) / "design.v"
    tb_file = Path(work_dir) / "testbench.v"
    sim_file = Path(work_dir) / "sim.out"

    rtl_file.write_text(rtl)
    tb_file.write_text(tb)

    compile_cmd = [
        "iverilog",
        "-g2012",
        "-o",
        str(sim_file),
        str(rtl_file),
        str(tb_file),
    ]

    compile_result = run_command(
        compile_cmd,
        timeout=30,
    )

    if compile_result["returncode"] != 0:

        error = (
            "COMPILATION FAILED\n\n"
            + compile_result["stderr"]
        )

        return {
            "compile_output": error,
            "simulation_output": "",
            "failure_analysis": error,
            "status": "FAILED",
            "iteration": state.get("iteration", 0) + 1,
            "work_dir": work_dir,
            "agent_log": state.get("agent_log", [])
            + ["Simulator: compilation failed"],
        }

    sim_result = run_command(
        ["vvp", str(sim_file)],
        timeout=30,
    )

    output = (
        sim_result["stdout"]
        + "\n"
        + sim_result["stderr"]
    )

    failed = (
        sim_result["returncode"] != 0
        or "TEST_FAIL" in output.upper()
        or "ERROR" in output.upper()
        or "FATAL" in output.upper()
    )

    return {
        "compile_output": (
            "COMPILATION PASSED\n"
            f"Duration: {compile_result['duration']} sec"
        ),
        "simulation_output": output,
        "failure_analysis": output if failed else "",
        "status": "FAILED" if failed else "SIMULATION_PASSED",
        "iteration": state.get("iteration", 0) + 1,
        "work_dir": work_dir,
        "agent_log": state.get("agent_log", [])
        + [
            "Simulator: compilation passed"
            if not failed
            else "Simulator: test failure detected"
        ],
    }


# ============================================================
# Agent: Failure Analyzer
# ============================================================

def failure_analyzer(state: RTLState) -> dict:

    failure = state.get("failure_analysis", "")

    if not failure:

        return {
            "failure_analysis": "",
            "agent_log": state.get("agent_log", [])
            + ["Failure Analyzer: no failure detected"],
        }

    response = llm.invoke(
        [
            SystemMessage(
                content="""
You are a silicon verification debug engineer.

Analyze the failure.

Determine:

1. Failure type
2. Likely root cause
3. Relevant RTL logic
4. Failing scenario
5. Expected behavior
6. Observed behavior
7. Recommended RTL fix
8. Recommended new testcase

Do not claim certainty when evidence is insufficient.
"""
            ),
            HumanMessage(
                content=f"""
RTL:
{state.get("rtl_code", "")}

Testbench:
{state.get("testbench", "")}

Failure log:
{failure}
"""
            ),
        ]
    )

    return {
        "failure_analysis": response.content,
        "agent_log": state.get("agent_log", [])
        + ["Failure Analyzer: root-cause analysis completed"],
    }


# ============================================================
# Agent: Coverage Intelligence
# ============================================================

def coverage_agent(state: RTLState) -> dict:

    coverage = calculate_proxy_coverage(
        state.get("rtl_code", ""),
        state.get("testbench", ""),
        state.get("simulation_output", ""),
    )

    return {
        "coverage": coverage,
        "agent_log": state.get("agent_log", [])
        + [
            f"Coverage Agent: proxy score "
            f"{coverage['overall_proxy']}%"
        ],
    }


# ============================================================
# Agent: Verification Judge
# ============================================================

def verification_judge(state: RTLState) -> dict:

    coverage = state.get("coverage", {})

    simulation_passed = (
        state.get("status") == "SIMULATION_PASSED"
    )

    score = 0

    if simulation_passed:
        score += 50

    score += 0.5 * coverage.get(
        "overall_proxy",
        0,
    )

    score = round(
        min(score, 100),
        1,
    )

    if simulation_passed and score >= 80:

        status = "VERIFIED"

    elif state.get("iteration", 0) >= state.get(
        "max_iterations",
        3,
    ):

        status = "STOPPED"

    else:

        status = "REFINE"

    return {
        "verification_score": score,
        "status": status,
        "agent_log": state.get("agent_log", [])
        + [
            f"Verification Judge: score={score}, "
            f"decision={status}"
        ],
    }


# ============================================================
# Agent: RTL Repair
# ============================================================

def rtl_repair_agent(state: RTLState) -> dict:

    prompt = f"""
Repair the RTL based on verification evidence.

SPECIFICATION:
{state.get("specification", "")}

CURRENT RTL:
{state.get("rtl_code", "")}

FAILURE ANALYSIS:
{state.get("failure_analysis", "")}

COVERAGE:
{json.dumps(state.get("coverage", {}), indent=2)}

VERIFICATION SCORE:
{state.get("verification_score", 0)}

Rules:

- Preserve the intended specification.
- Make the smallest safe change.
- Do not remove functionality merely to pass the testbench.
- Return synthesizable Verilog.
- Return ONLY the RTL code.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are a senior RTL debugging engineer."
            ),
            HumanMessage(content=prompt),
        ]
    )

    rtl = extract_code(response.content)

    return {
        "rtl_code": rtl,
        "agent_log": state.get("agent_log", [])
        + ["RTL Repair Agent: candidate repair generated"],
    }


# ============================================================
# LangGraph
# ============================================================

def build_graph():

    graph = StateGraph(RTLState)

    graph.add_node(
        "rtl_analyzer",
        rtl_analyzer,
    )

    graph.add_node(
        "test_planner",
        test_planner,
    )

    graph.add_node(
        "adversarial_planner",
        adversarial_planner,
    )

    graph.add_node(
        "testbench_generator",
        testbench_generator,
    )

    graph.add_node(
        "simulator",
        simulator_agent,
    )

    graph.add_node(
        "failure_analyzer",
        failure_analyzer,
    )

    graph.add_node(
        "coverage_agent",
        coverage_agent,
    )

    graph.add_node(
        "verification_judge",
        verification_judge,
    )

    graph.add_node(
        "rtl_repair",
        rtl_repair_agent,
    )

    graph.set_entry_point(
        "rtl_analyzer"
    )

    graph.add_edge(
        "rtl_analyzer",
        "test_planner",
    )

    graph.add_edge(
        "test_planner",
        "adversarial_planner",
    )

    graph.add_edge(
        "adversarial_planner",
        "testbench_generator",
    )

    graph.add_edge(
        "testbench_generator",
        "simulator",
    )

    graph.add_edge(
        "simulator",
        "failure_analyzer",
    )

    graph.add_edge(
        "failure_analyzer",
        "coverage_agent",
    )

    graph.add_edge(
        "coverage_agent",
        "verification_judge",
    )

    def route(state: RTLState):

        if state.get("status") == "VERIFIED":
            return "end"

        if state.get("iteration", 0) >= state.get(
            "max_iterations",
            3,
        ):
            return "end"

        return "repair"

    graph.add_conditional_edges(
        "verification_judge",
        route,
        {
            "repair": "rtl_repair",
            "end": END,
        },
    )

    graph.add_edge(
        "rtl_repair",
        "rtl_analyzer",
    )

    return graph.compile()


app = build_graph()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header("⚙️ Verification Configuration")

    max_iterations = st.slider(
        "Autonomous Refinement Loops",
        1,
        6,
        3,
    )

    st.markdown("---")

    st.markdown("### Agent Team")

    agents = [
        "RTL Analyzer",
        "Verification Planner",
        "Red Team Agent",
        "Testbench Agent",
        "Simulation Agent",
        "Failure Analyzer",
        "Coverage Agent",
        "Verification Judge",
        "RTL Repair Agent",
    ]

    for agent in agents:
        st.write("🤖 " + agent)

    st.markdown("---")

    st.caption(
        "Deterministic execution is performed by "
        "Icarus Verilog. AI agents propose and analyze."
    )


# ============================================================
# Main Input
# ============================================================

st.subheader("1️⃣ Design Specification")

specification = st.text_area(
    "Describe the RTL requirement",
    value=(
        "Design a 4-bit synchronous up-counter with "
        "active-low asynchronous reset rst_n and "
        "enable en. Counter increments on each positive "
        "clock edge when en is high and wraps around "
        "after 15."
    ),
    height=130,
)

st.subheader("2️⃣ Optional Existing RTL")

existing_rtl = st.text_area(
    "Paste existing Verilog RTL, or leave blank to generate it",
    height=220,
    placeholder="module ... endmodule",
)


run = st.button(
    "🚀 START AUTONOMOUS VERIFICATION",
    type="primary",
    use_container_width=True,
)


# ============================================================
# Execution
# ============================================================

if run:

    initial_state: RTLState = {

        "specification": specification,

        "rtl_code": existing_rtl,

        "testbench": "",

        "analysis": "",

        "test_plan": "",

        "adversarial_plan": "",

        "compile_output": "",

        "simulation_output": "",

        "failure_analysis": "",

        "coverage": {},

        "iteration": 0,

        "max_iterations": max_iterations,

        "status": "RUNNING",

        "agent_log": [],

        "verification_score": 0,

    }

    st.markdown("---")

    st.subheader("🤖 Autonomous Agent Execution")

    current = dict(initial_state)

    progress = st.progress(0)

    status_box = st.status(
        "Running verification agents...",
        expanded=True,
    )

    node_count = 0

    try:

        for step in app.stream(
            initial_state,
            stream_mode="updates",
        ):

            node_count += 1

            node_name = list(step.keys())[0]

            update = step[node_name]

            if update:
                current.update(update)

            progress.progress(
                min(
                    node_count / 20,
                    1.0,
                )
            )

            status_box.write(
                f"**Agent:** `{node_name}`"
            )

            logs = current.get(
                "agent_log",
                [],
            )

            if logs:
                status_box.write(
                    logs[-1]
                )

        status_box.update(
            label=(
                "✅ Verification workflow completed"
                if current.get("status")
                in ["VERIFIED", "SIMULATION_PASSED"]
                else "⚠️ Verification stopped"
            ),
            state=(
                "complete"
                if current.get("status")
                == "VERIFIED"
                else "error"
            ),
        )

    except Exception as exc:

        status_box.update(
            label="❌ Workflow execution error",
            state="error",
        )

        st.exception(exc)
        st.stop()


    # ========================================================
    # Metrics
    # ========================================================

    st.markdown("---")

    st.subheader("📊 Verification Intelligence")

    coverage = current.get(
        "coverage",
        {},
    )

    score = current.get(
        "verification_score",
        0,
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Verification Score",
        f"{score}%",
    )

    c2.metric(
        "Coverage Proxy",
        f"{coverage.get('overall_proxy', 0)}%",
    )

    c3.metric(
        "Structural",
        f"{coverage.get('structural_proxy', 0)}%",
    )

    c4.metric(
        "Test Strength",
        f"{coverage.get('check_strength', 0)}%",
    )

    c5.metric(
        "Iteration",
        current.get("iteration", 0),
    )


    # ========================================================
    # Status
    # ========================================================

    status = current.get(
        "status",
        "UNKNOWN",
    )

    if status == "VERIFIED":

        st.success(
            "🎉 VERIFIED: The design passed simulation and "
            "the verification judge accepted the evidence."
        )

    elif status == "SIMULATION_PASSED":

        st.warning(
            "Simulation passed, but the verification "
            "evidence did not reach the configured threshold."
        )

    else:

        st.error(
            "Verification did not reach closure."
        )


    # ========================================================
    # Tabs
    # ========================================================

    tabs = st.tabs(
        [
            "🧩 RTL",
            "🧪 Testbench",
            "🧠 RTL Analysis",
            "📋 Test Plan",
            "🔴 Red Team",
            "💥 Failure Analysis",
            "📈 Coverage",
            "📜 Simulation",
            "🤖 Agent Trace",
        ]
    )


    with tabs[0]:

        st.code(
            current.get(
                "rtl_code",
                "",
            ),
            language="verilog",
        )

        st.download_button(
            "⬇️ Download RTL",
            current.get(
                "rtl_code",
                "",
            ),
            file_name="verified_design.v",
            mime="text/plain",
        )


    with tabs[1]:

        st.code(
            current.get(
                "testbench",
                "",
            ),
            language="verilog",
        )

        st.download_button(
            "⬇️ Download Testbench",
            current.get(
                "testbench",
                "",
            ),
            file_name="generated_testbench.v",
            mime="text/plain",
        )


    with tabs[2]:

        st.markdown(
            current.get(
                "analysis",
                "No analysis.",
            )
        )


    with tabs[3]:

        st.markdown(
            current.get(
                "test_plan",
                "No test plan.",
            )
        )


    with tabs[4]:

        st.markdown(
            current.get(
                "adversarial_plan",
                "No adversarial plan.",
            )
        )


    with tabs[5]:

        failure = current.get(
            "failure_analysis",
            "",
        )

        if failure:

            st.error(
                "Failure / Debug Evidence"
            )

            st.markdown(
                failure
            )

        else:

            st.success(
                "No simulation failure was detected."
            )


    with tabs[6]:

        st.subheader(
            "Coverage Intelligence"
        )

        coverage_data = {
            "Metric": [
                "Structural Proxy",
                "Test Check Strength",
                "Simulation",
                "Overall Verification Proxy",
            ],
            "Score": [
                coverage.get(
                    "structural_proxy",
                    0,
                ),
                coverage.get(
                    "check_strength",
                    0,
                ),
                coverage.get(
                    "simulation",
                    0,
                ),
                coverage.get(
                    "overall_proxy",
                    0,
                ),
            ],
        }

        st.dataframe(
            coverage_data,
            use_container_width=True,
        )

        st.info(
            "The current implementation uses a lightweight "
            "coverage proxy. For production-grade coverage, "
            "integrate Verilator/coverage.py or simulator "
            "coverage databases."
        )


    with tabs[7]:

        st.code(
            current.get(
                "compile_output",
                "",
            )
            + "\n\n"
            + current.get(
                "simulation_output",
                "",
            )
        )


    with tabs[8]:

        for log in current.get(
            "agent_log",
            [],
        ):

            st.write(
                "✓ " + log
            )


    # ========================================================
    # Final Engineering Report
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📑 Autonomous Verification Report"
    )

    report = f"""
# PragyanAI SiliconAI Verification Report

## Design

{specification}

## Verification Score

{score}%

## Coverage Proxy

{coverage.get("overall_proxy", 0)}%

## Structural Proxy

{coverage.get("structural_proxy", 0)}%

## Test Check Strength

{coverage.get("check_strength", 0)}%

## Simulation

{"PASSED" if current.get("status") in ["VERIFIED", "SIMULATION_PASSED"] else "FAILED"}

## Refinement Iterations

{current.get("iteration", 0)}

## Final Status

{current.get("status", "UNKNOWN")}
"""

    st.download_button(
        "⬇️ Download Verification Report",
        report,
        file_name="siliconai_verification_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
