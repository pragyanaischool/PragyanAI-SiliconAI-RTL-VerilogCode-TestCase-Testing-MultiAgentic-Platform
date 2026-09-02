# ui/test_dashboard.py

import json
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# Helpers
# ============================================================

def normalize_status(status):

    value = str(
        status or ""
    ).upper()

    if value in [
        "PASS",
        "PASSED",
        "SUCCESS",
    ]:
        return "PASSED"

    if value in [
        "FAIL",
        "FAILED",
        "ERROR",
    ]:
        return "FAILED"

    return value or "UNKNOWN"


def load_run_tests(
    state,
    run_dir=None,
):

    tests = state.get(
        "tests",
        [],
    )

    if tests:
        return tests

    if not run_dir:
        return []

    run_file = (
        Path(run_dir)
        / "run.json"
    )

    if not run_file.exists():
        return []

    try:

        with open(
            run_file,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        return data.get(
            "tests",
            [],
        )

    except Exception:

        return []


# ============================================================
# Test Metrics
# ============================================================

def render_test_metrics(
    tests
):

    normalized = [
        normalize_status(
            test.get("status")
        )
        for test in tests
    ]

    total = len(
        normalized
    )

    passed = normalized.count(
        "PASSED"
    )

    failed = normalized.count(
        "FAILED"
    )

    unknown = total - passed - failed

    pass_rate = (
        passed / total * 100
        if total
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Tests",
        total,
    )

    c2.metric(
        "Passed",
        passed,
    )

    c3.metric(
        "Failed",
        failed,
    )

    c4.metric(
        "Pass Rate",
        f"{pass_rate:.1f}%",
    )

    if failed == 0 and total > 0:

        st.success(
            "🎉 All recorded tests passed."
        )

    elif failed > 0:

        st.error(
            f"❌ {failed} test(s) failed."
        )

    if unknown:

        st.warning(
            f"{unknown} test(s) have an unknown status."
        )


# ============================================================
# Test Details
# ============================================================

def render_test_details(
    test,
):

    test_id = test.get(
        "test_id",
        "UNKNOWN",
    )

    status = normalize_status(
        test.get("status")
    )

    description = test.get(
        "description",
        "No description",
    )

    if status == "PASSED":

        icon = "✅"

    elif status == "FAILED":

        icon = "❌"

    else:

        icon = "❓"

    with st.expander(
        f"{icon} {test_id} — {description}",
        expanded=False,
    ):

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                "### Test Information"
            )

            st.write(
                "**Test ID:**",
                test_id,
            )

            st.write(
                "**Status:**",
                status,
            )

            st.write(
                "**Agent:**",
                test.get(
                    "agent",
                    "Unknown",
                ),
            )

            st.write(
                "**Iteration:**",
                test.get(
                    "iteration",
                    "-",
                ),
            )

            st.write(
                "**RTL Version:**",
                test.get(
                    "rtl_version",
                    "-",
                ),
            )

            st.write(
                "**Duration:**",
                test.get(
                    "duration_seconds",
                    "-",
                ),
            )

        with c2:

            st.markdown(
                "### Result"
            )

            st.write(
                "**Inputs:**"
            )

            st.code(
                str(
                    test.get(
                        "inputs",
                        "",
                    )
                )
            )

            st.write(
                "**Expected:**"
            )

            st.code(
                str(
                    test.get(
                        "expected",
                        "",
                    )
                )
            )

            st.write(
                "**Actual:**"
            )

            st.code(
                str(
                    test.get(
                        "actual",
                        "",
                    )
                )
            )

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        error = test.get(
            "error_message",
            "",
        )

        if error:

            st.markdown(
                "### ❌ Failure / Error"
            )

            st.error(
                error
            )

        # ----------------------------------------------------
        # Test Code
        # ----------------------------------------------------

        test_code = test.get(
            "test_code",
            "",
        )

        test_code_file = test.get(
            "test_code_file",
            "",
        )

        if test_code_file:

            try:

                path = Path(
                    test_code_file
                )

                if path.exists():

                    test_code = path.read_text(
                        encoding="utf-8"
                    )

            except Exception:
                pass

        if test_code:

            st.markdown(
                "### 🧪 Testbench / Test Code"
            )

            st.code(
                test_code,
                language="verilog",
            )

            st.download_button(
                "⬇️ Download Test Code",
                test_code,
                file_name=f"{test_id}.v",
                mime="text/plain",
                key=f"download_{test_id}",
            )

        # ----------------------------------------------------
        # Simulation Evidence
        # ----------------------------------------------------

        simulation_log = test.get(
            "simulation_output",
            "",
        )

        simulation_file = test.get(
            "simulation_log",
            "",
        )

        if simulation_file:

            try:

                path = Path(
                    simulation_file
                )

                if path.exists():

                    simulation_log = path.read_text(
                        encoding="utf-8"
                    )

            except Exception:
                pass

        if simulation_log:

            with st.expander(
                "📜 Simulation Output"
            ):

                st.code(
                    simulation_log
                )


# ============================================================
# Main Test Dashboard
# ============================================================

def render_test_dashboard(
    state,
    run_dir=None,
):

    st.subheader(
        "🧪 Test Execution & Evidence Dashboard"
    )

    tests = load_run_tests(
        state,
        run_dir,
    )

    if not tests:

        st.info(
            "No test execution records are available yet."
        )

        return

    render_test_metrics(
        tests
    )

    st.markdown("---")

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    rows = []

    for test in tests:

        rows.append({

            "Test ID":
                test.get(
                    "test_id",
                    "",
                ),

            "Description":
                test.get(
                    "description",
                    "",
                ),

            "Status":
                normalize_status(
                    test.get(
                        "status"
                    )
                ),

            "Expected":
                test.get(
                    "expected",
                    "",
                ),

            "Actual":
                test.get(
                    "actual",
                    "",
                ),

            "Iteration":
                test.get(
                    "iteration",
                    "",
                ),

            "RTL":
                test.get(
                    "rtl_version",
                    "",
                ),

            "Duration":
                test.get(
                    "duration_seconds",
                    "",
                ),
        })

    df = pd.DataFrame(
        rows
    )

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        selected_status = st.selectbox(
            "Filter by Status",
            [
                "ALL",
                "PASSED",
                "FAILED",
            ],
        )

    with col2:

        search = st.text_input(
            "Search Test ID / Description",
        )

    filtered = df.copy()

    if selected_status != "ALL":

        filtered = filtered[
            filtered["Status"]
            == selected_status
        ]

    if search:

        mask = (
            filtered["Test ID"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
            |
            filtered["Description"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
        )

        filtered = filtered[
            mask
        ]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # Failed Tests
    # --------------------------------------------------------

    failed_tests = [
        test
        for test in tests
        if normalize_status(
            test.get("status")
        )
        == "FAILED"
    ]

    if failed_tests:

        st.subheader(
            "❌ Failed Test Cases"
        )

        for test in failed_tests:

            render_test_details(
                test
            )

    # --------------------------------------------------------
    # All Tests
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "📋 Complete Test Evidence"
    )

    for test in tests:

        render_test_details(
            test
        )

    # --------------------------------------------------------
    # CSV Export
    # --------------------------------------------------------

    csv_data = df.to_csv(
        index=False
    )

    st.download_button(
        "⬇️ Download Test Results CSV",
        csv_data,
        file_name="test_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
