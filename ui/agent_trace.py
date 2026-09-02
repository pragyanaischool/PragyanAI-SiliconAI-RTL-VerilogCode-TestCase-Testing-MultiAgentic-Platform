# ui/agent_trace.py

import json
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# Load Agent Logs
# ============================================================

def load_agent_trace(
    state,
    run_dir=None,
):

    trace = state.get(
        "agent_trace",
        [],
    )

    if trace:
        return trace

    logs = state.get(
        "agent_log",
        [],
    )

    result = []

    for index, log in enumerate(
        logs,
        start=1,
    ):

        result.append({

            "step": index,

            "agent": "Agent",

            "status": "COMPLETED",

            "message": str(log),
        })

    if result:
        return result

    # --------------------------------------------------------
    # Agent JSON files
    # --------------------------------------------------------

    if run_dir:

        agents_dir = (
            Path(run_dir)
            / "agents"
        )

        if not agents_dir.exists():

            agents_dir = (
                Path(run_dir)
                / "reports"
                / "agents"
            )

        if agents_dir.exists():

            for file in sorted(
                agents_dir.glob(
                    "*.json"
                )
            ):

                try:

                    with open(
                        file,
                        "r",
                        encoding="utf-8",
                    ) as f:

                        data = json.load(f)

                    if isinstance(
                        data,
                        list,
                    ):

                        result.extend(
                            data
                        )

                    elif isinstance(
                        data,
                        dict,
                    ):

                        result.append(
                            data
                        )

                except Exception:

                    continue

    return result


# ============================================================
# Agent Summary
# ============================================================

def render_agent_summary(
    trace
):

    if not trace:

        return

    agents = {}

    for event in trace:

        agent = event.get(
            "agent",
            "Unknown",
        )

        agents.setdefault(
            agent,
            {
                "total": 0,
                "success": 0,
                "failed": 0,
            },
        )

        agents[agent]["total"] += 1

        status = str(
            event.get(
                "status",
                "",
            )
        ).upper()

        if status in [
            "SUCCESS",
            "PASSED",
            "COMPLETED",
            "DONE",
        ]:

            agents[agent]["success"] += 1

        elif status in [
            "FAILED",
            "ERROR",
        ]:

            agents[agent]["failed"] += 1

    rows = []

    for agent, values in agents.items():

        rows.append({

            "Agent":
                agent,

            "Executions":
                values["total"],

            "Successful":
                values["success"],

            "Failed":
                values["failed"],
        })

    df = pd.DataFrame(
        rows
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Agent Event
# ============================================================

def render_agent_event(
    event,
    index,
):

    agent = event.get(
        "agent",
        event.get(
            "agent_name",
            "Unknown Agent",
        ),
    )

    status = str(
        event.get(
            "status",
            "INFO",
        )
    ).upper()

    message = event.get(
        "message",
        event.get(
            "output",
            event.get(
                "description",
                "",
            ),
        ),
    )

    timestamp = event.get(
        "timestamp",
        "",
    )

    if status in [
        "SUCCESS",
        "PASSED",
        "COMPLETED",
        "DONE",
    ]:

        icon = "✅"

    elif status in [
        "FAILED",
        "ERROR",
    ]:

        icon = "❌"

    elif status in [
        "RUNNING",
        "ACTIVE",
    ]:

        icon = "🔄"

    else:

        icon = "ℹ️"

    title = (
        f"{icon} Step {index}: "
        f"{agent}"
    )

    with st.expander(
        title,
        expanded=False,
    ):

        st.write(
            "**Status:**",
            status,
        )

        if timestamp:

            st.write(
                "**Timestamp:**",
                timestamp,
            )

        if message:

            st.markdown(
                "### Message / Output"
            )

            if isinstance(
                message,
                str,
            ):

                st.markdown(
                    message
                )

            else:

                st.json(
                    message
                )

        # ----------------------------------------------------
        # Input
        # ----------------------------------------------------

        input_data = event.get(
            "input",
            event.get(
                "input_text",
                None,
            ),
        )

        if input_data:

            with st.expander(
                "📥 Agent Input"
            ):

                if isinstance(
                    input_data,
                    str,
                ):

                    st.code(
                        input_data
                    )

                else:

                    st.json(
                        input_data
                    )

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        output_data = event.get(
            "output",
            None,
        )

        if output_data:

            with st.expander(
                "📤 Agent Output"
            ):

                if isinstance(
                    output_data,
                    str,
                ):

                    st.code(
                        output_data
                    )

                else:

                    st.json(
                        output_data
                    )

        # ----------------------------------------------------
        # Decision
        # ----------------------------------------------------

        decision = event.get(
            "decision",
            "",
        )

        if decision:

            st.info(
                f"Decision: {decision}"
            )


# ============================================================
# Main
# ============================================================

def render_agent_trace(
    state,
    run_dir=None,
):

    st.subheader(
        "🤖 Multi-Agent Execution Trace"
    )

    trace = load_agent_trace(
        state,
        run_dir,
    )

    if not trace:

        st.info(
            "No agent execution trace is available."
        )

        return

    render_agent_summary(
        trace
    )

    st.markdown("---")

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    agent_names = sorted(
        set(
            event.get(
                "agent",
                event.get(
                    "agent_name",
                    "Unknown",
                ),
            )
            for event in trace
        )
    )

    selected_agent = st.selectbox(
        "Agent",
        ["ALL"] + agent_names,
    )

    filtered = trace

    if selected_agent != "ALL":

        filtered = [
            event
            for event in trace
            if event.get(
                "agent",
                event.get(
                    "agent_name",
                    "Unknown",
                ),
            )
            == selected_agent
        ]

    # --------------------------------------------------------
    # Timeline
    # --------------------------------------------------------

    st.subheader(
        "Execution Timeline"
    )

    for index, event in enumerate(
        filtered,
        start=1,
    ):

        render_agent_event(
            event,
            index,
        )

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    trace_json = json.dumps(
        trace,
        indent=2,
        default=str,
    )

    st.download_button(
        "⬇️ Download Agent Trace",
        trace_json,
        file_name="agent_trace.json",
        mime="application/json",
        use_container_width=True,
    )
