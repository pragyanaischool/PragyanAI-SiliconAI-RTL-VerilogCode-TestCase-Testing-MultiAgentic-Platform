# ui/dashboard.py

import streamlit as st
import pandas as pd

from ui.rtl_viewer import render_rtl_viewer
from ui.test_dashboard import render_test_dashboard
from ui.coverage_dashboard import render_coverage_dashboard
from ui.agent_trace import render_agent_trace
from ui.report_viewer import render_report_viewer


# ============================================================
# Page Styling
# ============================================================

def inject_dashboard_css():

    st.markdown(
        """
        <style>

        .silicon-header {
            padding: 1.2rem 1.4rem;
            border-radius: 14px;
            border: 1px solid rgba(128,128,128,.25);
            margin-bottom: 1rem;
        }

        .silicon-title {
            font-size: 2rem;
            font-weight: 800;
        }

        .silicon-subtitle {
            color: #777;
            font-size: 0.95rem;
        }

        .metric-box {
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,.25);
            text-align: center;
        }

        .metric-value {
            font-size: 1.7rem;
            font-weight: 800;
        }

        .metric-label {
            font-size: .8rem;
            color: #777;
        }

        .agent-running {
            border-left: 5px solid #ff9800;
            padding: .7rem;
        }

        .agent-success {
            border-left: 5px solid #2e7d32;
            padding: .7rem;
        }

        .agent-failed {
            border-left: 5px solid #c62828;
            padding: .7rem;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Safe Helpers
# ============================================================

def get_value(data, key, default=None):

    if data is None:
        return default

    if isinstance(data, dict):
        return data.get(key, default)

    return default


def calculate_test_metrics(tests):

    if not tests:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0,
        }

    total = len(tests)

    passed = sum(
        1
        for test in tests
        if str(
            test.get("status", "")
        ).upper()
        in ["PASS", "PASSED", "SUCCESS"]
    )

    failed = sum(
        1
        for test in tests
        if str(
            test.get("status", "")
        ).upper()
        in ["FAIL", "FAILED", "ERROR"]
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(
            (passed / total) * 100,
            1,
        )
        if total
        else 0,
    }


# ============================================================
# Header
# ============================================================

def render_header():

    st.markdown(
        """
        <div class="silicon-header">

        <div class="silicon-title">
        ⚡ PragyanAI SiliconAI
        </div>

        <div class="silicon-subtitle">
        Autonomous RTL Verification & Coverage Intelligence
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Summary Metrics
# ============================================================

def render_summary_metrics(state):

    tests = get_value(
        state,
        "tests",
        [],
    )

    metrics = calculate_test_metrics(
        tests
    )

    coverage = get_value(
        state,
        "coverage",
        {},
    )

    verification_score = get_value(
        state,
        "verification_score",
        0,
    )

    iteration = get_value(
        state,
        "iteration",
        0,
    )

    rtl_version = get_value(
        state,
        "rtl_version",
        f"V{iteration or 1}",
    )

    status = get_value(
        state,
        "status",
        "UNKNOWN",
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.metric(
            "Verification",
            f"{verification_score}%",
        )

    with c2:
        st.metric(
            "Coverage",
            f"{coverage.get('overall', coverage.get('overall_proxy', 0))}%",
        )

    with c3:
        st.metric(
            "Tests",
            metrics["total"],
        )

    with c4:
        st.metric(
            "Passed",
            metrics["passed"],
        )

    with c5:
        st.metric(
            "Failed",
            metrics["failed"],
        )

    with c6:
        st.metric(
            "RTL",
            rtl_version,
        )

    if status.upper() in [
        "VERIFIED",
        "PASSED",
        "SUCCESS",
        "SIMULATION_PASSED",
    ]:

        st.success(
            "✅ Verification workflow completed successfully."
        )

    elif status.upper() in [
        "FAILED",
        "ERROR",
        "STOPPED",
    ]:

        st.error(
            "❌ Verification did not reach closure."
        )

    else:

        st.info(
            f"Verification status: {status}"
        )


# ============================================================
# Agent Status
# ============================================================

def render_agent_status(state):

    st.subheader(
        "🤖 Agent Status"
    )

    agent_status = get_value(
        state,
        "agent_status",
        {},
    )

    default_agents = [
        "RTL Analyzer",
        "Verification Planner",
        "Test Generator",
        "Testbench Generator",
        "Red Team Agent",
        "Simulation Agent",
        "Failure Analyzer",
        "Coverage Agent",
        "Mutation Agent",
        "Formal Agent",
        "RTL Repair Agent",
        "Verification Judge",
    ]

    if not agent_status:

        cols = st.columns(4)

        for index, agent in enumerate(
            default_agents
        ):

            with cols[index % 4]:

                st.markdown(
                    f"""
                    <div class="agent-success">
                    🤖 <b>{agent}</b><br>
                    <small>Available</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        return

    cols = st.columns(4)

    for index, agent in enumerate(
        default_agents
    ):

        status = str(
            agent_status.get(
                agent,
                "PENDING",
            )
        ).upper()

        if status in [
            "DONE",
            "PASSED",
            "SUCCESS",
            "COMPLETED",
        ]:

            icon = "✅"
            css = "agent-success"

        elif status in [
            "RUNNING",
                       "ACTIVE",
        ]:

            icon = "🔄"
            css = "agent-running"

        elif status in [
            "FAILED",
            "ERROR",
        ]:

            icon = "❌"
            css = "agent-failed"

        else:

            icon = "⏳"
            css = "agent-running"

        with cols[index % 4]:

            st.markdown(
                f"""
                <div class="{css}">
                {icon} <b>{agent}</b><br>
                <small>{status}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# Main Dashboard
# ============================================================

def render_dashboard(
    state,
    run_dir=None,
):

    inject_dashboard_css()

    render_header()

    render_summary_metrics(
        state
    )

    st.markdown("---")

    render_agent_status(
        state
    )

    st.markdown("---")

    tabs = st.tabs(
        [
            "🧩 RTL",
            "🧪 Tests",
            "📈 Coverage",
            "🤖 Agents",
            "📑 Reports",
        ]
    )

    with tabs[0]:

        render_rtl_viewer(
            state,
            run_dir,
        )

    with tabs[1]:

        render_test_dashboard(
            state,
            run_dir,
        )

    with tabs[2]:

        render_coverage_dashboard(
            state,
            run_dir,
        )

    with tabs[3]:

        render_agent_trace(
            state,
            run_dir,
        )

    with tabs[4]:

        render_report_viewer(
            state,
            run_dir,
        )
