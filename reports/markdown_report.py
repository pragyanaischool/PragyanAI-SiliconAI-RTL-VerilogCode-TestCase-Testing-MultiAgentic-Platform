"""
PragyanAI SiliconAI
RTL Verification Agentic Platform

Markdown Verification Report Generator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .report_generator import build_report_data


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _safe(value: Any, default: str = "-") -> str:
    """Convert a value into printable Markdown text."""

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def _status_icon(status: str) -> str:
    """Return a simple status symbol."""

    status = str(status).upper()

    if status in {"PASSED", "PASS", "VERIFIED", "COMPLETED"}:
        return "✅"

    if status in {"FAILED", "FAIL", "ERROR"}:
        return "❌"

    if status in {"RUNNING", "ACTIVE"}:
        return "🔄"

    if status in {"SKIPPED"}:
        return "⏭️"

    return "⚠️"


# ---------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------

def generate_markdown_report(
    report_data: Dict[str, Any],
) -> str:
    """
    Generate a complete Markdown verification report.
    """

    overview = report_data.get(
        "overview",
        {},
    )

    coverage = report_data.get(
        "coverage",
        {},
    )

    tests = report_data.get(
        "tests",
        [],
    )

    failed_tests = report_data.get(
        "failed_tests",
        [],
    )

    agents = report_data.get(
        "agents",
        [],
    )

    specification = report_data.get(
        "specification",
        "",
    )

    assessment = report_data.get(
        "assessment",
        {},
    )

    metadata = report_data.get(
        "report_metadata",
        {},
    )

    score = overview.get(
        "verification_score",
        0,
    )

    status = overview.get(
        "status",
        "UNKNOWN",
    )

    # -------------------------------------------------------------
    # Header
    # -------------------------------------------------------------

    lines = []

    lines.append(
        "# PragyanAI SiliconAI\n"
        "# Autonomous RTL Verification Report"
    )

    lines.append("")

    lines.append(
        f"**Generated:** {_safe(metadata.get('generated_at'))}"
    )

    lines.append(
        f"**Report Version:** {_safe(metadata.get('report_version'))}"
    )

    lines.append("")

    # -------------------------------------------------------------
    # Executive Summary
    # -------------------------------------------------------------

    lines.append("## 1. Executive Summary")
    lines.append("")

    lines.append(
        f"### {_status_icon(status)} Verification Status: "
        f"**{status}**"
    )

    lines.append("")

    lines.append(
        f"**Overall Verification Score:** "
        f"**{score:.2f}/100**"
    )

    lines.append("")

    ready = assessment.get(
        "ready_for_signoff",
        False,
    )

    if ready:
        lines.append(
            "> **Sign-off Recommendation:** "
            "Verification criteria currently indicate readiness "
            "for sign-off."
        )
    else:
        lines.append(
            "> **Sign-off Recommendation:** "
            "Verification is not yet ready for final sign-off. "
            "Review failed tests, coverage gaps, and unresolved "
            "verification risks."
        )

    lines.append("")

    # -------------------------------------------------------------
    # KPI table
    # -------------------------------------------------------------

    lines.append("## 2. Verification KPIs")
    lines.append("")

    lines.append("| Metric | Result |")
    lines.append("|---|---:|")

    lines.append(
        f"| Verification Score | "
        f"{overview.get('verification_score', 0):.2f}% |"
    )

    lines.append(
        f"| RTL Version | "
        f"{_safe(overview.get('rtl_version'))} |"
    )

    lines.append(
        f"| Iteration | "
        f"{overview.get('iteration', 0)} |"
    )

    lines.append(
        f"| Total Tests | "
        f"{overview.get('total_tests', 0)} |"
    )

    lines.append(
        f"| Passed Tests | "
        f"{overview.get('passed_tests', 0)} |"
    )

    lines.append(
        f"| Failed Tests | "
        f"{overview.get('failed_tests', 0)} |"
    )

    lines.append(
        f"| Pass Rate | "
        f"{overview.get('pass_rate', 0):.2f}% |"
    )

    lines.append(
        f"| Overall Coverage | "
        f"{overview.get('coverage', 0):.2f}% |"
    )

    lines.append(
        f"| Mutation Score | "
        f"{overview.get('mutation_score', 0):.2f}% |"
    )

    lines.append(
        f"| Coverage Gaps | "
        f"{overview.get('coverage_gap_count', 0)} |"
    )

    lines.append("")

    # -------------------------------------------------------------
    # Specification
    # -------------------------------------------------------------

    lines.append("## 3. Specification")
    lines.append("")

    if specification:
        lines.append("```text")
        lines.append(specification)
        lines.append("```")
    else:
        lines.append(
            "_No specification was recorded for this run._"
        )

    lines.append("")

    # -------------------------------------------------------------
    # RTL
    # -------------------------------------------------------------

    lines.append("## 4. RTL Under Verification")
    lines.append("")

    lines.append(
        f"**RTL Version:** "
        f"{_safe(overview.get('rtl_version'))}"
    )

    lines.append("")

    rtl_code = report_data.get(
        "rtl",
        {},
    ).get(
        "code",
        "",
    )

    if rtl_code:
        lines.append("```verilog")
        lines.append(rtl_code)
        lines.append("```")
    else:
        lines.append(
            "_RTL source was not captured in the report._"
        )

    lines.append("")

    # -------------------------------------------------------------
    # Test Summary
    # -------------------------------------------------------------

    lines.append("## 5. Test Execution Summary")
    lines.append("")

    lines.append("| Test ID | Status | Description | RTL | Iteration |")
    lines.append("|---|---|---|---|---:|")

    for test in tests:

        status_text = _safe(
            test.get("status"),
            "UNKNOWN",
        )

        lines.append(
            f"| {_safe(test.get('test_id'))} "
            f"| {_status_icon(status_text)} {status_text} "
            f"| {_safe(test.get('description'))} "
            f"| {_safe(test.get('rtl_version'))} "
            f"| {test.get('iteration', 0)} |"
        )

    if not tests:
        lines.append(
            "| - | - | No tests recorded | - | - |"
        )

    lines.append("")

    # -------------------------------------------------------------
    # Failed tests
    # -------------------------------------------------------------

    lines.append("## 6. Failed Tests & Debugging Evidence")
    lines.append("")

    if failed_tests:

        for test in failed_tests:

            lines.append(
                f"### ❌ {_safe(test.get('test_id'))}"
            )

            lines.append("")

            lines.append(
                f"**Description:** "
                f"{_safe(test.get('description'))}"
            )

            lines.append("")

            lines.append(
                f"**Inputs:** "
                f"`{_safe(test.get('inputs'))}`"
            )

            lines.append("")

            lines.append(
                f"**Expected:** "
                f"`{_safe(test.get('expected'))}`"
            )

            lines.append("")

            lines.append(
                f"**Actual:** "
                f"`{_safe(test.get('actual'))}`"
            )

            lines.append("")

            error = test.get(
                "error_message",
                "",
            )

            if error:
                lines.append("**Error:**")
                lines.append("")
                lines.append("```text")
                lines.append(str(error))
                lines.append("```")
                lines.append("")

            lines.append(
                f"**RTL Version:** "
                f"{_safe(test.get('rtl_version'))}"
            )

            lines.append("")

            lines.append(
                f"**Iteration:** "
                f"{test.get('iteration', 0)}"
            )

            lines.append("")

    else:

        lines.append(
            "✅ No failed tests were recorded."
        )

    lines.append("")

    # -------------------------------------------------------------
    # Coverage
    # -------------------------------------------------------------

    lines.append("## 7. Coverage Analysis")
    lines.append("")

    coverage_metrics = [
        ("Line", "line"),
        ("Branch", "branch"),
        ("Toggle", "toggle"),
        ("FSM", "fsm"),
        ("Functional", "functional"),
        ("Assertion", "assertion"),
        ("Mutation", "mutation"),
        ("Overall", "overall"),
    ]

    lines.append("| Coverage Type | Percentage |")
    lines.append("|---|---:|")

    for label, key in coverage_metrics:

        value = coverage.get(
            key,
            0,
        )

        lines.append(
            f"| {label} | {value:.2f}% |"
        )

    lines.append("")

    if coverage.get("overall_proxy"):
        lines.append(
            "> **Note:** Overall coverage is a calculated "
            "proxy because a native overall coverage result "
            "was not available."
        )

        lines.append("")

    # -------------------------------------------------------------
    # Coverage gaps
    # -------------------------------------------------------------

    gaps = coverage.get(
        "gaps",
        [],
    )

    lines.append("### Coverage Gaps")
    lines.append("")

    if gaps:

        lines.append(
            "| Gap | Description | Recommendation |"
        )

        lines.append(
            "|---|---|---|"
        )

        for index, gap in enumerate(gaps):

            if isinstance(gap, dict):

                gap_id = gap.get(
                    "id",
                    f"GAP{index + 1:03d}",
                )

                description = gap.get(
                    "description",
                    "",
                )

                recommendation = gap.get(
                    "recommendation",
                    "",
                )

            else:

                gap_id = f"GAP{index + 1:03d}"
                description = str(gap)
                recommendation = ""

            lines.append(
                f"| {_safe(gap_id)} "
                f"| {_safe(description)} "
                f"| {_safe(recommendation)} |"
            )

    else:

        lines.append(
            "✅ No coverage gaps were recorded."
        )

    lines.append("")

    # -------------------------------------------------------------
    # Recommended tests
    # -------------------------------------------------------------

    recommendations = coverage.get(
        "recommended_tests",
        [],
    )

    if recommendations:

        lines.append("### Recommended Additional Tests")
        lines.append("")

        for index, recommendation in enumerate(
            recommendations,
            start=1,
        ):

            lines.append(
                f"{index}. {recommendation}"
            )

        lines.append("")

    # -------------------------------------------------------------
    # Agent Activity
    # -------------------------------------------------------------

    lines.append("## 8. Agent Activity")
    lines.append("")

    lines.append(
        "| Agent | Status | Iteration | Duration | Message |"
    )

    lines.append(
        "|---|---|---:|---:|---|"
    )

    for agent in agents:

        lines.append(
            f"| {_safe(agent.get('agent'))} "
            f"| {_status_icon(agent.get('status'))} "
            f"{_safe(agent.get('status'))} "
            f"| {agent.get('iteration', 0)} "
            f"| {agent.get('duration_seconds', 0):.2f}s "
            f"| {_safe(agent.get('message'))} |"
        )

    if not agents:

        lines.append(
            "| - | - | - | - | No agent trace recorded |"
        )

    lines.append("")

    # -------------------------------------------------------------
    # Final Assessment
    # -------------------------------------------------------------

    lines.append("## 9. Final Assessment")
    lines.append("")

    if ready:

        lines.append(
            "### ✅ Verification Ready"
        )

        lines.append("")

        lines.append(
            "The current verification run has no recorded "
            "failed tests and the workflow reports a successful "
            "verification status."
        )

    else:

        lines.append(
            "### ⚠️ Verification Closure Required"
        )

        lines.append("")

        lines.append(
            "The design should continue through the verification "
            "closure loop. Priority should be given to failed "
            "tests, coverage gaps, mutation escapes, and "
            "unresolved root causes."
        )

    lines.append("")

    # -------------------------------------------------------------
    # Evidence
    # -------------------------------------------------------------

    lines.append("## 10. Evidence & Traceability")
    lines.append("")

    lines.append(
        "The verification evidence should maintain traceability "
        "between:"
    )

    lines.append("")

    lines.append(
        "Specification → RTL → Verification Plan → "
        "Test → Simulation → Result → Coverage → "
        "Failure Analysis → Closure"
    )

    lines.append("")

    lines.append(
        "---"
    )

    lines.append("")

    lines.append(
        "*Generated by PragyanAI SiliconAI "
        "Autonomous RTL Verification Platform.*"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------
# Generate from state
# ---------------------------------------------------------------------

def create_markdown_report(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
) -> str:
    """
    Build report data and return Markdown.
    """

    report_data = build_report_data(
        state=state,
        run_dir=run_dir,
    )

    return generate_markdown_report(
        report_data
    )


# ---------------------------------------------------------------------
# Save Markdown
# ---------------------------------------------------------------------

def save_markdown_report(
    markdown: str,
    output_path: str | Path,
) -> Path:
    """Save Markdown report to disk."""

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        markdown,
        encoding="utf-8",
    )

    return output_path


# ---------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------

def generate_and_save_markdown_report(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
    output_path: Optional[str | Path] = None,
) -> Path:

    if output_path is None:

        if run_dir:
            output_path = (
                Path(run_dir)
                / "reports"
                / "verification_report.md"
            )
        else:
            output_path = Path(
                "verification_report.md"
            )

    markdown = create_markdown_report(
        state=state,
        run_dir=run_dir,
    )

    return save_markdown_report(
        markdown,
        output_path,
    )
