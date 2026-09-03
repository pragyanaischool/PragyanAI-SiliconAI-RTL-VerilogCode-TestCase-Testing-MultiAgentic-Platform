"""
PragyanAI SiliconAI
===================

Autonomous RTL Verification Agent Package.

This package contains the verification agents used by the LangGraph
workflow:

    1. RTLAnalyzerAgent
    2. VerificationPlannerAgent
    3. TestGeneratorAgent
    4. TestbenchGeneratorAgent
    5. SimulatorAgent
    6. FailureAnalyzerAgent
    7. CoverageAgent
    8. RedTeamAgent
    9. MutationAgent
    10. FormalAgent
    11. BugLocalizationAgent
    12. RTLRepairAgent
    13. VerificationJudgeAgent

IMPORTANT
---------
Agents are intentionally loaded lazily.

Do NOT eagerly import every agent here. A failure in one optional or
configuration-dependent agent must not prevent unrelated agents from
being imported.

This is especially important for Streamlit Cloud deployments where:

    graph.workflow
        -> agents
        -> individual agents
        -> configuration / optional dependencies

should fail only at the point where the problematic agent is actually used.

SymbiYosys is NOT required by this package.
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# PUBLIC AGENT NAMES
# =============================================================================

__all__ = [
    "RTLAnalyzerAgent",
    "VerificationPlannerAgent",
    "TestGeneratorAgent",
    "TestbenchGeneratorAgent",
    "SimulatorAgent",
    "FailureAnalyzerAgent",
    "CoverageAgent",
    "RedTeamAgent",
    "MutationAgent",
    "FormalAgent",
    "BugLocalizationAgent",
    "RTLRepairAgent",
    "VerificationJudgeAgent",
]


# =============================================================================
# LAZY AGENT LOADER
# =============================================================================

def __getattr__(name: str) -> Any:
    """
    Lazily load an agent class.

    This prevents Python from importing every agent whenever code executes:

        import agents

    or:

        from agents.rtl_analyzer import RTLAnalyzerAgent

    Only the requested agent module is imported.

    Parameters
    ----------
    name:
        Requested attribute/class name.

    Returns
    -------
    Any
        Requested agent class.

    Raises
    ------
    AttributeError
        If the requested agent does not exist.
    """

    if name == "RTLAnalyzerAgent":
        from .rtl_analyzer import RTLAnalyzerAgent

        return RTLAnalyzerAgent

    if name == "VerificationPlannerAgent":
        from .verification_planner import VerificationPlannerAgent

        return VerificationPlannerAgent

    if name == "TestGeneratorAgent":
        from .test_generator import TestGeneratorAgent

        return TestGeneratorAgent

    if name == "TestbenchGeneratorAgent":
        from .testbench_generator import TestbenchGeneratorAgent

        return TestbenchGeneratorAgent

    if name == "SimulatorAgent":
        from .simulator_agent import SimulatorAgent

        return SimulatorAgent

    if name == "FailureAnalyzerAgent":
        from .failure_analyzer import FailureAnalyzerAgent

        return FailureAnalyzerAgent

    if name == "CoverageAgent":
        from .coverage_agent import CoverageAgent

        return CoverageAgent

    if name == "RedTeamAgent":
        from .red_team_agent import RedTeamAgent

        return RedTeamAgent

    if name == "MutationAgent":
        from .mutation_agent import MutationAgent

        return MutationAgent

    if name == "FormalAgent":
        from .formal_agent import FormalAgent

        return FormalAgent

    if name == "BugLocalizationAgent":
        from .bug_localization_agent import BugLocalizationAgent

        return BugLocalizationAgent

    if name == "RTLRepairAgent":
        from .rtl_repair_agent import RTLRepairAgent

        return RTLRepairAgent

    if name == "VerificationJudgeAgent":
        from .verification_judge import VerificationJudgeAgent

        return VerificationJudgeAgent

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


# =============================================================================
# OPTIONAL: LAZY IMPORT SUPPORT
# =============================================================================

def __dir__() -> list[str]:
    """
    Return public names for IDEs, autocomplete and introspection.
    """

    return sorted(
        set(
            globals().keys()
        )
        | set(__all__)
    )
    
