# ui/rtl_viewer.py

import re
from pathlib import Path

import streamlit as st


# ============================================================
# RTL Statistics
# ============================================================

def rtl_statistics(rtl):

    if not rtl:
        return {}

    return {
        "modules": len(
            re.findall(
                r"\bmodule\b",
                rtl,
                re.IGNORECASE,
            )
        ),

        "always_blocks": len(
            re.findall(
                r"\balways\b",
                rtl,
                re.IGNORECASE,
            )
        ),

        "always_ff": len(
            re.findall(
                r"\balways_ff\b",
                rtl,
                re.IGNORECASE,
            )
        ),

        "always_comb": len(
            re.findall(
                r"\balways_comb\b",
                rtl,
                re.IGNORECASE,
            )
        ),

        "if_statements": len(
            re.findall(
                r"\bif\s*\(",
                rtl,
                re.IGNORECASE,
            )
        ),

        "case_statements": len(
            re.findall(
                r"\bcase\s*\(",
                rtl,
                re.IGNORECASE,
            )
        ),

        "assignments": len(
            re.findall(
                r"\bassign\b",
                rtl,
                re.IGNORECASE,
            )
        ),

        "assertions": len(
            re.findall(
                r"\bassert\b",
                rtl,
                re.IGNORECASE,
            )
        ),
    }


# ============================================================
# RTL Version Discovery
# ============================================================

def find_rtl_versions(run_dir):

    if not run_dir:
        return []

    rtl_dir = Path(run_dir) / "rtl"

    if not rtl_dir.exists():
        return []

    files = list(
        rtl_dir.glob("*.v")
    )

    files += list(
        rtl_dir.glob("*.sv")
    )

    return sorted(
        files,
        key=lambda x: x.name,
    )


# ============================================================
# RTL Viewer
# ============================================================

def render_rtl_viewer(
    state,
    run_dir=None,
):

    st.subheader(
        "🧩 RTL Design Viewer"
    )

    rtl_code = state.get(
        "rtl_code",
        "",
    )

    testbench = state.get(
        "testbench",
        "",
    )

    if not rtl_code:

        st.warning(
            "No RTL code available."
        )

        return

    versions = find_rtl_versions(
        run_dir
    )

    if versions:

        selected = st.selectbox(
            "RTL Version",
            versions,
            format_func=lambda x: x.name,
        )

        try:

            selected_code = selected.read_text(
                encoding="utf-8"
            )

        except Exception:

            selected_code = rtl_code

    else:

        selected_code = rtl_code

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    stats = rtl_statistics(
        selected_code
    )

    cols = st.columns(4)

    with cols[0]:
        st.metric(
            "Modules",
            stats.get("modules", 0),
        )

    with cols[1]:
        st.metric(
            "Always Blocks",
            stats.get("always_blocks", 0),
        )

    with cols[2]:
        st.metric(
            "Branches",
            stats.get("if_statements", 0),
        )

    with cols[3]:
        st.metric(
            "Case Statements",
            stats.get("case_statements", 0),
        )

    # --------------------------------------------------------
    # Code
    # --------------------------------------------------------

    st.markdown(
        "### RTL Code"
    )

    st.code(
        selected_code,
        language="verilog",
    )

    st.download_button(
        "⬇️ Download RTL",
        selected_code,
        file_name="design.v",
        mime="text/plain",
    )

    # --------------------------------------------------------
    # Analysis
    # --------------------------------------------------------

    analysis = state.get(
        "analysis",
        "",
    )

    if analysis:

        with st.expander(
            "🧠 AI RTL Analysis",
            expanded=False,
        ):

            st.markdown(
                analysis
            )

    # --------------------------------------------------------
    # Testbench
    # --------------------------------------------------------

    if testbench:

        st.markdown("---")

        st.subheader(
            "🧪 Generated Testbench"
        )

        st.code(
            testbench,
            language="verilog",
        )

        st.download_button(
            "⬇️ Download Testbench",
            testbench,
            file_name="testbench.v",
            mime="text/plain",
        )

    # --------------------------------------------------------
    # RTL History
    # --------------------------------------------------------

    if len(versions) > 1:

        st.markdown("---")

        st.subheader(
            "🔄 RTL Revision History"
        )

        for version in versions:

            st.write(
                f"📄 `{version.name}`"
            )
