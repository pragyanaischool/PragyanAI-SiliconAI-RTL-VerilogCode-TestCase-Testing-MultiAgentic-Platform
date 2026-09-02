# ui/coverage_dashboard.py

import json
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# Coverage Normalization
# ============================================================

def normalize_coverage(
    coverage
):

    if not coverage:
        return {}

    return {

        "Line Coverage":
            float(
                coverage.get(
                    "line",
                    coverage.get(
                        "line_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "Branch Coverage":
            float(
                coverage.get(
                    "branch",
                    coverage.get(
                        "branch_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "Toggle Coverage":
            float(
                coverage.get(
                    "toggle",
                    coverage.get(
                        "toggle_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "FSM Coverage":
            float(
                coverage.get(
                    "fsm",
                    coverage.get(
                        "fsm_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "Functional Coverage":
            float(
                coverage.get(
                    "functional",
                    coverage.get(
                        "functional_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "Assertion Coverage":
            float(
                coverage.get(
                    "assertion",
                    coverage.get(
                        "assertion_coverage",
                        0,
                    ),
                )
                or 0
            ),

        "Mutation Score":
            float(
                coverage.get(
                    "mutation",
                    coverage.get(
                        "mutation_score",
                        0,
                    ),
                )
                or 0
            ),

        "Overall":
            float(
                coverage.get(
                    "overall",
                    coverage.get(
                        "overall_proxy",
                        0,
                    ),
                )
                or 0
            ),
    }


# ============================================================
# Coverage File
# ============================================================

def load_coverage(
    state,
    run_dir=None,
):

    coverage = state.get(
        "coverage",
        {},
    )

    if coverage:
        return coverage

    if not run_dir:
        return {}

    coverage_file = (
        Path(run_dir)
        / "coverage"
        / "coverage.json"
    )

    if not coverage_file.exists():
        return {}

    try:

        with open(
            coverage_file,
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    except Exception:

        return {}


# ============================================================
# Coverage Dashboard
# ============================================================

def render_coverage_dashboard(
    state,
    run_dir=None,
):

    st.subheader(
        "📈 Coverage Intelligence"
    )

    coverage_raw = load_coverage(
        state,
        run_dir,
    )

    coverage = normalize_coverage(
        coverage_raw
    )

    if not coverage:

        st.info(
            "No coverage information is available yet."
        )

        return

    # --------------------------------------------------------
    # Main Metrics
    # --------------------------------------------------------

    overall = coverage.get(
        "Overall",
        0,
    )

    if overall >= 95:

        st.success(
            f"🏆 Excellent verification coverage: {overall}%"
        )

    elif overall >= 80:

        st.warning(
            f"⚠️ Verification coverage: {overall}%"
        )

    else:

        st.error(
            f"❌ Low verification coverage: {overall}%"
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Overall",
        f"{overall:.1f}%",
    )

    c2.metric(
        "Line",
        f"{coverage.get('Line Coverage', 0):.1f}%",
    )

    c3.metric(
        "Branch",
        f"{coverage.get('Branch Coverage', 0):.1f}%",
    )

    c4.metric(
        "Functional",
        f"{coverage.get('Functional Coverage', 0):.1f}%",
    )

    # --------------------------------------------------------
    # Coverage Table
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "Coverage Metrics"
    )

    coverage_rows = []

    for metric, value in coverage.items():

        coverage_rows.append({
            "Metric": metric,
            "Coverage": value,
            "Gap": max(
                0,
                100 - value,
            ),
        })

    df = pd.DataFrame(
        coverage_rows
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # Visual Bars
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "Coverage Profile"
    )

    for metric, value in coverage.items():

        if metric == "Overall":
            continue

        st.write(
            f"**{metric} — {value:.1f}%**"
        )

        st.progress(
            min(
                max(
                    int(value),
                    0,
                ),
                100,
            )
        )

    # --------------------------------------------------------
    # Coverage Gaps
    # --------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "⚠️ Coverage Gaps"
    )

    gaps = coverage_raw.get(
        "gaps",
        coverage_raw.get(
            "coverage_gaps",
            [],
        ),
    )

    if gaps:

        for gap in gaps:

            if isinstance(
                gap,
                dict,
            ):

                gap_id = gap.get(
                    "id",
                    "GAP",
                )

                description = gap.get(
                    "description",
                    gap.get(
                        "reason",
                        "",
                    ),
                )

                recommendation = gap.get(
                    "recommendation",
                    "",
                )

                st.warning(
                    f"**{gap_id}** — {description}"
                )

                if recommendation:

                    st.info(
                        f"Recommended action: {recommendation}"
                    )

            else:

                st.warning(
                    str(gap)
                )

    else:

        low_metrics = [
            (name, value)
            for name, value
            in coverage.items()
            if value < 90
            and name != "Overall"
        ]

        if low_metrics:

            for name, value in low_metrics:

                st.warning(
                    f"{name}: {value:.1f}% "
                    f"— gap {100-value:.1f}%"
                )

        else:

            st.success(
                "No major coverage gaps detected."
            )

    # --------------------------------------------------------
    # Recommended Tests
    # --------------------------------------------------------

    recommendations = coverage_raw.get(
        "recommended_tests",
        [],
    )

    if recommendations:

        st.markdown("---")

        st.subheader(
            "🧪 Recommended Tests to Close Gaps"
        )

        for index, recommendation in enumerate(
            recommendations,
            start=1,
        ):

            if isinstance(
                recommendation,
                dict,
            ):

                name = recommendation.get(
                    "name",
                    f"TEST_{index}",
                )

                reason = recommendation.get(
                    "reason",
                    "",
                )

                st.write(
                    f"**{name}**"
                )

                if reason:
                    st.caption(
                        reason
                    )

            else:

                st.write(
                    f"**TC-{index:03d}** "
                    f"{recommendation}"
                )

    # --------------------------------------------------------
    # Mutation Score
    # --------------------------------------------------------

    mutation = coverage.get(
        "Mutation Score",
        0,
    )

    if mutation:

        st.markdown("---")

        st.subheader(
            "🧬 Mutation Testing"
        )

        st.metric(
            "Mutation Score",
            f"{mutation:.1f}%",
        )

        if mutation >= 90:

            st.success(
                "Strong fault-detection capability."
            )

        elif mutation >= 70:

            st.warning(
                "Additional fault-oriented tests are recommended."
            )

        else:

            st.error(
                "Test suite may miss injected RTL faults."
            )
