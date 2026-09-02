"""
PragyanAI SiliconAI
RTL Verification Agentic Platform

Standalone HTML Verification Report Generator.

The generated HTML does not require Streamlit.
It can be opened directly in a browser.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, Optional

from .report_generator import build_report_data


# ---------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------

def esc(value: Any) -> str:
    """Escape content before inserting it into HTML."""

    if value is None:
        return ""

    return html.escape(str(value))


def status_class(status: str) -> str:
    """Return CSS status class."""

    status = str(status).upper()

    if status in {
        "PASSED",
        "PASS",
        "VERIFIED",
        "COMPLETED",
    }:
        return "success"

    if status in {
        "FAILED",
        "FAIL",
        "ERROR",
    }:
        return "danger"

    if status in {
        "RUNNING",
        "ACTIVE",
    }:
        return "warning"

    return "neutral"


def status_icon(status: str) -> str:
    """Return status icon."""

    status = str(status).upper()

    if status in {
        "PASSED",
        "PASS",
        "VERIFIED",
        "COMPLETED",
    }:
        return "✓"

    if status in {
        "FAILED",
        "FAIL",
        "ERROR",
    }:
        return "✕"

    if status in {
        "RUNNING",
        "ACTIVE",
    }:
        return "↻"

    return "•"


def metric_card(
    title: str,
    value: Any,
    subtitle: str = "",
) -> str:

    return f"""
    <div class="metric-card">
        <div class="metric-title">{esc(title)}</div>
        <div class="metric-value">{esc(value)}</div>
        <div class="metric-subtitle">{esc(subtitle)}</div>
    </div>
    """


def progress_bar(
    value: float,
    label: str,
) -> str:

    try:
        value = float(value)
    except Exception:
        value = 0.0

    value = max(
        0.0,
        min(
            value,
            100.0,
        ),
    )

    return f"""
    <div class="coverage-item">
        <div class="coverage-header">
            <span>{esc(label)}</span>
            <strong>{value:.2f}%</strong>
        </div>

        <div class="progress-track">
            <div
                class="progress-fill"
                style="width:{value:.2f}%"
            ></div>
        </div>
    </div>
    """


# ---------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------

def generate_html_report(
    report_data: Dict[str, Any],
) -> str:
    """
    Generate a standalone HTML verification report.
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

    rtl = report_data.get(
        "rtl",
        {},
    )

    assessment = report_data.get(
        "assessment",
        {},
    )

    metadata = report_data.get(
        "report_metadata",
        {},
    )

    score = float(
        overview.get(
            "verification_score",
            0,
        )
    )

    status = overview.get(
        "status",
        "UNKNOWN",
    )

    status_css = status_class(
        status
    )

    # -------------------------------------------------------------
    # Test rows
    # -------------------------------------------------------------

    test_rows = []

    for test in tests:

        test_status = test.get(
            "status",
            "UNKNOWN",
        )

        test_rows.append(
            f"""
            <tr>
                <td>
                    <strong>
                        {esc(test.get('test_id'))}
                    </strong>
                </td>

                <td>
                    <span class="status {status_class(test_status)}">
                        {status_icon(test_status)}
                        {esc(test_status)}
                    </span>
                </td>

                <td>
                    {esc(test.get('description'))}
                </td>

                <td>
                    {esc(test.get('rtl_version'))}
                </td>

                <td>
                    {esc(test.get('iteration'))}
                </td>

                <td>
                    {float(test.get('duration_seconds', 0)):.2f}s
                </td>
            </tr>
            """
        )

    if not test_rows:

        test_rows.append(
            """
            <tr>
                <td colspan="6">
                    No tests recorded.
                </td>
            </tr>
            """
        )

    # -------------------------------------------------------------
    # Failed test cards
    # -------------------------------------------------------------

    failure_cards = []

    for test in failed_tests:

        error_message = test.get(
            "error_message",
            "",
        )

        failure_cards.append(
            f"""
            <div class="failure-card">

                <div class="failure-title">
                    <span>✕</span>
                    {esc(test.get('test_id'))}
                </div>

                <div class="failure-description">
                    {esc(test.get('description'))}
                </div>

                <div class="evidence-grid">

                    <div>
                        <span class="evidence-label">
                            Inputs
                        </span>

                        <code>
                            {esc(test.get('inputs'))}
                        </code>
                    </div>

                    <div>
                        <span class="evidence-label">
                            Expected
                        </span>

                        <code>
                            {esc(test.get('expected'))}
                        </code>
                    </div>

                    <div>
                        <span class="evidence-label">
                            Actual
                        </span>

                        <code>
                            {esc(test.get('actual'))}
                        </code>
                    </div>

                    <div>
                        <span class="evidence-label">
                            RTL Version
                        </span>

                        <code>
                            {esc(test.get('rtl_version'))}
                        </code>
                    </div>

                </div>

                <div class="error-box">

                    <div class="evidence-label">
                        Simulation / Error Evidence
                    </div>

                    <pre>{esc(error_message)}</pre>

                </div>

            </div>
            """
        )

    if not failure_cards:

        failure_cards.append(
            """
            <div class="success-box">
                ✓ No failed tests were recorded.
            </div>
            """
        )

    # -------------------------------------------------------------
    # Agent rows
    # -------------------------------------------------------------

    agent_rows = []

    for agent in agents:

        agent_status = agent.get(
            "status",
            "UNKNOWN",
        )

        agent_rows.append(
            f"""
            <tr>

                <td>
                    <strong>
                        {esc(agent.get('agent'))}
                    </strong>
                </td>

                <td>
                    <span class="status {status_class(agent_status)}">
                        {status_icon(agent_status)}
                        {esc(agent_status)}
                    </span>
                </td>

                <td>
                    {esc(agent.get('iteration'))}
                </td>

                <td>
                    {float(agent.get('duration_seconds', 0)):.2f}s
                </td>

                <td>
                    {esc(agent.get('message'))}
                </td>

            </tr>
            """
        )

    if not agent_rows:

        agent_rows.append(
            """
            <tr>
                <td colspan="5">
                    No agent activity recorded.
                </td>
            </tr>
            """
        )

    # -------------------------------------------------------------
    # Coverage bars
    # -------------------------------------------------------------

    coverage_html = "\n".join(
        [
            progress_bar(
                coverage.get("line", 0),
                "Line Coverage",
            ),

            progress_bar(
                coverage.get("branch", 0),
                "Branch Coverage",
            ),

            progress_bar(
                coverage.get("toggle", 0),
                "Toggle Coverage",
            ),

            progress_bar(
                coverage.get("fsm", 0),
                "FSM Coverage",
            ),

            progress_bar(
                coverage.get("functional", 0),
                "Functional Coverage",
            ),

            progress_bar(
                coverage.get("assertion", 0),
                "Assertion Coverage",
            ),

            progress_bar(
                coverage.get("mutation", 0),
                "Mutation Score",
            ),
        ]
    )

    # -------------------------------------------------------------
    # Coverage gaps
    # -------------------------------------------------------------

    gaps = coverage.get(
        "gaps",
        [],
    )

    gap_rows = []

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

        gap_rows.append(
            f"""
            <tr>
                <td>
                    <strong>{esc(gap_id)}</strong>
                </td>

                <td>
                    {esc(description)}
                </td>

                <td>
                    {esc(recommendation)}
                </td>
            </tr>
            """
        )

    if not gap_rows:

        gap_rows.append(
            """
            <tr>
                <td colspan="3">
                    No coverage gaps recorded.
                </td>
            </tr>
            """
        )

    # -------------------------------------------------------------
    # Sign-off banner
    # -------------------------------------------------------------

    ready_for_signoff = assessment.get(
        "ready_for_signoff",
        False,
    )

    if ready_for_signoff:

        signoff_html = """
        <div class="signoff success-box">
            <div class="signoff-title">
                ✓ VERIFICATION READY FOR SIGN-OFF
            </div>

            <div>
                The current verification run reports no failed
                tests and a successful verification status.
            </div>
        </div>
        """

    else:

        signoff_html = """
        <div class="signoff warning-box">
            <div class="signoff-title">
                ⚠ VERIFICATION CLOSURE REQUIRED
            </div>

            <div>
                Additional verification work is recommended.
                Review failed tests, coverage gaps, mutation
                escapes and unresolved root causes.
            </div>
        </div>
        """

    # -------------------------------------------------------------
    # RTL source
    # -------------------------------------------------------------

    rtl_code = rtl.get(
        "code",
        "",
    )

    # -------------------------------------------------------------
    # Full HTML
    # -------------------------------------------------------------

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1.0"
>

<title>
PragyanAI SiliconAI - RTL Verification Report
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 0;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    background: #f5f7fb;
    color: #1f2937;

    line-height: 1.5;
}}

.container {{
    width: min(1400px, 94%);
    margin: 0 auto;
}}

.header {{
    background: #111827;
    color: white;

    padding: 42px 0;

    margin-bottom: 30px;
}}

.header h1 {{
    margin: 0;
    font-size: 34px;
    letter-spacing: -0.5px;
}}

.header p {{
    margin: 8px 0 0;
    color: #cbd5e1;
}}

.status-banner {{
    margin-top: 25px;
    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding: 8px 15px;

    border-radius: 999px;

    font-weight: 700;
}}

.status-banner.success {{
    background: #dcfce7;
    color: #166534;
}}

.status-banner.danger {{
    background: #fee2e2;
    color: #991b1b;
}}

.status-banner.warning {{
    background: #fef3c7;
    color: #92400e;
}}

.status-banner.neutral {{
    background: #e5e7eb;
    color: #374151;
}}

.section {{
    background: white;

    border: 1px solid #e5e7eb;

    border-radius: 14px;

    padding: 25px;

    margin-bottom: 25px;

    box-shadow:
        0 2px 8px
        rgba(0, 0, 0, 0.04);
}}

.section h2 {{
    margin-top: 0;

    font-size: 21px;

    border-bottom:
        1px solid #e5e7eb;

    padding-bottom: 12px;
}}

.metrics {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px, 1fr)
        );

    gap: 15px;

    margin-bottom: 25px;
}}

.metric-card {{
    background: white;

    border: 1px solid #e5e7eb;

    border-radius: 12px;

    padding: 20px;
}}

.metric-title {{
    font-size: 13px;

    color: #6b7280;

    font-weight: 600;

    text-transform: uppercase;

    letter-spacing: 0.4px;
}}

.metric-value {{
    margin-top: 5px;

    font-size: 28px;

    font-weight: 800;

    color: #111827;
}}

.metric-subtitle {{
    margin-top: 3px;

    font-size: 12px;

    color: #9ca3af;
}}

table {{
    width: 100%;

    border-collapse: collapse;

    font-size: 14px;
}}

th {{
    background: #f8fafc;

    color: #475569;

    font-weight: 700;

    text-align: left;
}}

th,
td {{
    padding: 12px;

    border-bottom:
        1px solid #e5e7eb;

    vertical-align: top;
}}

tr:hover {{
    background: #fafafa;
}}

.status {{
    display: inline-flex;

    align-items: center;

    gap: 5px;

    border-radius: 999px;

    padding: 4px 9px;

    font-size: 12px;

    font-weight: 700;
}}

.status.success {{
    background: #dcfce7;
    color: #166534;
}}

.status.danger {{
    background: #fee2e2;
    color: #991b1b;
}}

.status.warning {{
    background: #fef3c7;
    color: #92400e;
}}

.status.neutral {{
    background: #e5e7eb;
    color: #374151;
}}

.coverage-grid {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px, 1fr)
        );

    gap: 20px;
}}

.coverage-item {{
    margin-bottom: 12px;
}}

.coverage-header {{
    display: flex;

    justify-content: space-between;

    margin-bottom: 6px;

    font-size: 14px;
}}

.progress-track {{
    width: 100%;

    height: 10px;

    background: #e5e7eb;

    border-radius: 999px;

    overflow: hidden;
}}

.progress-fill {{
    height: 100%;

    background: #2563eb;

    border-radius: 999px;

    transition: width 0.3s ease;
}}

.score-box {{
    text-align: center;

    padding: 25px;

    background: #f8fafc;

    border-radius: 12px;

    margin-bottom: 20px;
}}

.score {{
    font-size: 52px;

    font-weight: 900;

    color: #111827;
}}

.score-label {{
    color: #64748b;

    font-size: 14px;
}}

pre {{
    white-space: pre-wrap;

    overflow-x: auto;

    background: #0f172a;

    color: #e2e8f0;

    padding: 18px;

    border-radius: 10px;

    font-size: 13px;

    line-height: 1.55;
}}

code {{
    background: #f1f5f9;

    padding: 2px 5px;

    border-radius: 4px;

    font-family:
        "SFMono-Regular",
        Consolas,
        monospace;
}}

.failure-card {{
    border: 1px solid #fecaca;

    background: #fffafa;

    border-radius: 12px;

    padding: 20px;

    margin-bottom: 15px;
}}

.failure-title {{
    color: #991b1b;

    font-weight: 800;

    font-size: 17px;

    margin-bottom: 8px;
}}

.failure-description {{
    color: #475569;

    margin-bottom: 18px;
}}

.evidence-grid {{
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );

    gap: 12px;
}}

.evidence-grid > div {{
    background: white;

    border: 1px solid #e5e7eb;

    border-radius: 8px;

    padding: 12px;
}}

.evidence-label {{
    display: block;

    font-size: 11px;

    font-weight: 700;

    color: #64748b;

    text-transform: uppercase;

    margin-bottom: 5px;
}}

.error-box {{
    margin-top: 15px;
}}

.error-box pre {{
    background: #450a0a;

    color: #fecaca;
}}

.success-box {{
    border: 1px solid #86efac;

    background: #f0fdf4;

    color: #166534;

    padding: 18px;

    border-radius: 10px;
}}

.warning-box {{
    border: 1px solid #fcd34d;

    background: #fffbeb;

    color: #92400e;

    padding: 18px;

    border-radius: 10px;
}}

.signoff-title {{
    font-weight: 900;

    margin-bottom: 5px;
}}

.footer {{
    text-align: center;

    color: #94a3b8;

    font-size: 12px;

    padding: 30px 0 50px;
}}

.trace-message {{
    max-width: 500px;

    word-break: break-word;
}}

@media(max-width: 700px) {{

    .header h1 {{
        font-size: 26px;
    }}

    .section {{
        padding: 17px;
    }}

    table {{
        display: block;

        overflow-x: auto;
    }}

}}

</style>

</head>

<body>

<header class="header">

<div class="container">

<h1>
PragyanAI SiliconAI
</h1>

<p>
Autonomous RTL Verification &amp; Coverage Closure
</p>

<div class="status-banner {status_css}">

{status_icon(status)}

{esc(status)}

</div>

</div>

</header>


<main class="container">


<!-- ========================================================= -->
<!-- KPI DASHBOARD -->
<!-- ========================================================= -->

<div class="metrics">

{metric_card(
    "Verification Score",
    f"{score:.2f}%",
    "Platform heuristic score"
)}

{metric_card(
    "Tests",
    overview.get("total_tests", 0),
    "Total executed tests"
)}

{metric_card(
    "Pass Rate",
    f"{overview.get('pass_rate', 0):.2f}%",
    "Test execution success"
)}

{metric_card(
    "Coverage",
    f"{overview.get('coverage', 0):.2f}%",
    "Overall coverage"
)}

{metric_card(
    "Mutation Score",
    f"{overview.get('mutation_score', 0):.2f}%",
    "Mutation effectiveness"
)}

{metric_card(
    "Coverage Gaps",
    overview.get("coverage_gap_count", 0),
    "Open verification gaps"
)}

</div>


<!-- ========================================================= -->
<!-- EXECUTIVE SUMMARY -->
<!-- ========================================================= -->

<section class="section">

<h2>
1. Executive Summary
</h2>

<div class="score-box">

<div class="score">
{score:.2f}
</div>

<div class="score-label">
Verification Score / 100
</div>

</div>

{signoff_html}

</section>


<!-- ========================================================= -->
<!-- RUN INFORMATION -->
<!-- ========================================================= -->

<section class="section">

<h2>
2. Run Information
</h2>

<table>

<tr>
<th>Status</th>
<td>
<span class="status {status_css}">
{status_icon(status)}
{esc(status)}
</span>
</td>
</tr>

<tr>
<th>RTL Version</th>
<td>{esc(overview.get("rtl_version"))}</td>
</tr>

<tr>
<th>Iteration</th>
<td>{esc(overview.get("iteration"))}</td>
</tr>

<tr>
<th>Report Generated</th>
<td>{esc(metadata.get("generated_at"))}</td>
</tr>

<tr>
<th>Report Version</th>
<td>{esc(metadata.get("report_version"))}</td>
</tr>

</table>

</section>


<!-- ========================================================= -->
<!-- SPECIFICATION -->
<!-- ========================================================= -->

<section class="section">

<h2>
3. Specification
</h2>

<pre>{esc(specification)}</pre>

</section>


<!-- ========================================================= -->
<!-- RTL -->
<!-- ========================================================= -->

<section class="section">

<h2>
4. RTL Under Verification
</h2>

<p>
<strong>
Version:
</strong>

{esc(overview.get("rtl_version"))}

</p>

<details>

<summary>
View RTL Source
</summary>

<pre>{esc(rtl_code)}</pre>

</details>

</section>


<!-- ========================================================= -->
<!-- TEST RESULTS -->
<!-- ========================================================= -->

<section class="section">

<h2>
5. Test Execution
</h2>

<table>

<thead>

<tr>
<th>Test ID</th>
<th>Status</th>
<th>Description</th>
<th>RTL</th>
<th>Iteration</th>
<th>Duration</th>
</tr>

</thead>

<tbody>

{"".join(test_rows)}

</tbody>

</table>

</section>


<!-- ========================================================= -->
<!-- FAILURES -->
<!-- ========================================================= -->

<section class="section">

<h2>
6. Failures &amp; Debugging Evidence
</h2>

{"".join(failure_cards)}

</section>


<!-- ========================================================= -->
<!-- COVERAGE -->
<!-- ========================================================= -->

<section class="section">

<h2>
7. Coverage Analysis
</h2>

<div class="coverage-grid">

{coverage_html}

</div>

<br>

<div class="score-box">

<div class="score">
{float(coverage.get("overall", 0)):.2f}%
</div>

<div class="score-label">
Overall Coverage
</div>

</div>

</section>


<!-- ========================================================= -->
<!-- COVERAGE GAPS -->
<!-- ========================================================= -->

<section class="section">

<h2>
8. Coverage Gaps
</h2>

<table>

<thead>

<tr>
<th>Gap ID</th>
<th>Description</th>
<th>Recommendation</th>
</tr>

</thead>

<tbody>

{"".join(gap_rows)}

</tbody>

</table>

</section>


<!-- ========================================================= -->
<!-- AGENTS -->
<!-- ========================================================= -->

<section class="section">

<h2>
9. Agent Activity Trace
</h2>

<table>

<thead>

<tr>
<th>Agent</th>
<th>Status</th>
<th>Iteration</th>
<th>Duration</th>
<th>Message</th>
</tr>

</thead>

<tbody>

{"".join(agent_rows)}

</tbody>

</table>

</section>


<!-- ========================================================= -->
<!-- TRACEABILITY -->
<!-- ========================================================= -->

<section class="section">

<h2>
10. Verification Evidence Chain
</h2>

<div class="score-box">

<strong>
Specification
</strong>

↓

<strong>
RTL
</strong>

↓

<strong>
Verification Plan
</strong>

↓

<strong>
Test Generation
</strong>

↓

<strong>
Simulation
</strong>

↓

<strong>
PASS / FAIL Evidence
</strong>

↓

<strong>
Coverage
</strong>

↓

<strong>
Failure Analysis
</strong>

↓

<strong>
Closure / Sign-Off
</strong>

</div>

</section>


<!-- ========================================================= -->
<!-- FINAL ASSESSMENT -->
<!-- ========================================================= -->

<section class="section">

<h2>
11. Final Assessment
</h2>

{signoff_html}

</section>


</main>


<footer class="footer">

PragyanAI SiliconAI
<br>

Autonomous RTL Verification &amp; Coverage Closure

<br><br>

Generated:
{esc(metadata.get("generated_at"))}

</footer>


</body>

</html>
"""


# ---------------------------------------------------------------------
# Build report from state
# ---------------------------------------------------------------------

def create_html_report(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
) -> str:
    """
    Build report data and return HTML.
    """

    report_data = build_report_data(
        state=state,
        run_dir=run_dir,
    )

    return generate_html_report(
        report_data
    )


# ---------------------------------------------------------------------
# Save report
# ---------------------------------------------------------------------

def save_html_report(
    html_content: str,
    output_path: str | Path,
) -> Path:
    """
    Save standalone HTML report.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        html_content,
        encoding="utf-8",
    )

    return output_path


# ---------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------

def generate_and_save_html_report(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
    output_path: Optional[str | Path] = None,
) -> Path:
    """
    Generate and save an HTML report.
    """

    if output_path is None:

        if run_dir:

            output_path = (
                Path(run_dir)
                / "reports"
                / "verification_report.html"
            )

        else:

            output_path = Path(
                "verification_report.html"
            )

    html_content = create_html_report(
        state=state,
        run_dir=run_dir,
    )

    return save_html_report(
        html_content,
        output_path,
    )
