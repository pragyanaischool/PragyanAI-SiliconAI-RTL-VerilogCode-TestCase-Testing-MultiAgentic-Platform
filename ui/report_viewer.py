# ui/report_viewer.py

import json
from pathlib import Path
from datetime import datetime

import streamlit as st


# ============================================================
# Load Summary
# ============================================================

def load_summary(
    state,
    run_dir=None,
):

    summary = state.get(
        "summary",
        {},
    )

    if summary:
        return summary

    if not run_dir:
        return {}

    possible_files = [

        Path(run_dir)
        / "reports"
        / "summary.json",

        Path(run_dir)
        / "summary.json",
    ]

    for file in possible_files:

        if not file.exists():
            continue

        try:

            with open(
                file,
                "r",
                encoding="utf-8",
            ) as f:

                return json.load(f)

        except Exception:

            pass

    return {}


# ============================================================
# Build Report
# ============================================================

def build_report(
    state,
    summary,
):

    specification = state.get(
        "specification",
        "",
    )

    rtl_version = state.get(
        "rtl_version",
        f"V{state.get('iteration', 1)}",
    )

    status = state.get(
        "status",
        summary.get(
            "status",
            "UNKNOWN",
        ),
    )

    verification_score = state.get(
        "verification_score",
        summary.get(
            "verification_score",
            0,
        ),
    )

    coverage = state.get(
        "coverage",
        {},
    )

    tests = state.get(
        "tests",
        [],
    )

    total = summary.get(
        "total_tests",
        len(tests),
    )

    passed = summary.get(
        "passed_tests",
        sum(
            1
            for test in tests
            if str(
                test.get(
                    "status",
                    "",
                )
            ).upper()
            in ["PASS", "PASSED"]
        ),
    )

    failed = summary.get(
        "failed_tests",
        sum(
            1
            for test in tests
            if str(
                test.get(
                    "status",
                    "",
                )
            ).upper()
            in ["FAIL", "FAILED"]
        ),
    )

    pass_rate = (
        passed / total * 100
        if total
        else 0
    )

    lines = []

    lines.append(
        "# PragyanAI SiliconAI"
    )

    lines.append(
        "## Autonomous RTL Verification Report"
    )

    lines.append("")

    lines.append(
        f"Generated: {datetime.now().isoformat()}"
    )

    lines.append("")

    lines.append(
        "## Verification Status"
    )

    lines.append(
        f"**Status:** {status}"
    )

    lines.append(
        f"**Verification Score:** {verification_score}%"
    )

    lines.append(
        f"**RTL Version:** {rtl_version}"
    )

    lines.append("")

    lines.append(
        "## Specification"
    )

    lines.append(
        specification
    )

    lines.append("")

    lines.append(
        "## Test Summary"
    )

    lines.append(
        f"- Total Tests: {total}"
    )

    lines.append(
        f"- Passed: {passed}"
    )

    lines.append(
        f"- Failed: {failed}"
    )

    lines.append(
        f"- Pass Rate: {pass_rate:.1f}%"
    )

    lines.append("")

    lines.append(
        "## Coverage"
    )

    for name, value in coverage.items():

        lines.append(
            f"- {name}: {value}%"
        )

    lines.append("")

    lines.append(
        "## Failed Tests"
    )

    failed_tests = [
        test
        for test in tests
        if str(
            test.get(
                "status",
                "",
            )
        ).upper()
        in [
            "FAIL",
            "FAILED",
        ]
    ]

    if failed_tests:

        for test in failed_tests:

            lines.append(
                f"### {test.get('test_id', 'UNKNOWN')}"
            )

            lines.append(
                f"Description: "
                f"{test.get('description', '')}"
            )

            lines.append(
                f"Expected: "
                f"{test.get('expected', '')}"
            )

            lines.append(
                f"Actual: "
                f"{test.get('actual', '')}"
            )

            lines.append(
                f"Error: "
                f"{test.get('error_message', '')}"
            )

    else:

        lines.append(
            "No failed tests."
        )

    lines.append("")

    lines.append(
        "## Agent Activity"
    )

    agent_log = state.get(
        "agent_log",
        [],
    )

    for item in agent_log:

        lines.append(
            f"- {item}"
        )

    lines.append("")

    lines.append(
        "## Final Assessment"
    )

    if (
        failed == 0
        and total > 0
        and verification_score >= 80
    ):

        lines.append(
            "Verification evidence indicates successful closure "
            "under the configured verification criteria."
        )

    elif failed > 0:

        lines.append(
            "Verification remains open because one or more "
            "test cases failed."
        )

    else:

        lines.append(
            "Verification evidence is incomplete."
        )

    return "\n".join(
        lines
    )


# ============================================================
# Report Viewer
# ============================================================

def render_report_viewer(
    state,
    run_dir=None,
):

    st.subheader(
        "📑 Verification Report"
    )

    summary = load_summary(
        state,
        run_dir,
    )

    report = build_report(
        state,
        summary,
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = state.get(
        "status",
        summary.get(
            "status",
            "UNKNOWN",
        ),
    )

    score = state.get(
        "verification_score",
        summary.get(
            "verification_score",
            0,
        ),
    )

    if str(status).upper() in [
        "VERIFIED",
        "PASSED",
        "SUCCESS",
    ]:

        st.success(
            f"✅ Verification Status: {status}"
        )

    elif str(status).upper() in [
        "FAILED",
        "ERROR",
        "STOPPED",
    ]:

        st.error(
            f"❌ Verification Status: {status}"
        )

    else:

        st.warning(
            f"⚠️ Verification Status: {status}"
        )

    st.metric(
        "Verification Score",
        f"{score}%",
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    st.markdown("---")

    st.markdown(
        report
    )

    # --------------------------------------------------------
    # Downloads
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "⬇️ Export Verification Evidence"
    )

    c1, c2 = st.columns(2)

    with c1:

        st.download_button(
            "⬇️ Download Markdown Report",
            report,
            file_name="verification_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with c2:

        report_json = json.dumps(
            {
                "summary": summary,
                "verification_score": score,
                "status": status,
                "coverage": state.get(
                    "coverage",
                    {},
                ),
                "tests": state.get(
                    "tests",
                    [],
                ),
                "agent_log": state.get(
                    "agent_log",
                    [],
                ),
            },
            indent=2,
            default=str,
        )

        st.download_button(
            "⬇️ Download Evidence JSON",
            report_json,
            file_name="verification_evidence.json",
            mime="application/json",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Report Directory
    # --------------------------------------------------------

    if run_dir:

        st.markdown("---")

        st.caption(
            f"Verification run directory: `{run_dir}`"
        )
