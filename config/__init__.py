"""
PragyanAI SiliconAI
Configuration Package

Central configuration, model definitions, and prompt utilities.
"""

from .settings import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_ITERATIONS,
    VERIFICATION_TARGET,
    GROQ_API_KEY,
    IVERILOG_EXECUTABLE,
    VVP_EXECUTABLE,
    VERILATOR_EXECUTABLE,
    YOSYS_EXECUTABLE,
    SBY_EXECUTABLE,
    LOG_ROOT,
)

from .models import (
    RTLAnalysis,
    VerificationPlan,
    TestScenario,
    FailureAnalysis,
    CoverageResult,
    RedTeamScenario,
    MutationResult,
    FormalResult,
    BugLocation,
    RepairProposal,
    JudgeResult,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MAX_ITERATIONS",
    "VERIFICATION_TARGET",
    "GROQ_API_KEY",
    "IVERILOG_EXECUTABLE",
    "VVP_EXECUTABLE",
    "VERILATOR_EXECUTABLE",
    "YOSYS_EXECUTABLE",
    "SBY_EXECUTABLE",
    "LOG_ROOT",
    "RTLAnalysis",
    "VerificationPlan",
    "TestScenario",
    "FailureAnalysis",
    "CoverageResult",
    "RedTeamScenario",
    "MutationResult",
    "FormalResult",
    "BugLocation",
    "RepairProposal",
    "JudgeResult",
]
