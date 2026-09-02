"""
PragyanAI SiliconAI
Application Settings

Central configuration for:
- Groq / LangChain
- Agent token limits
- Verification workflow
- EDA tools
- Simulation
- Coverage
- Mutation testing
- Formal analysis

SymbiYosys is intentionally NOT included.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


# =====================================================================
# PROJECT PATHS
# =====================================================================

BASE_DIR = Path(
    os.getenv(
        "SILICONAI_BASE_DIR",
        Path(__file__).resolve().parent.parent,
    )
).resolve()

CONFIG_DIR = BASE_DIR / "config"
AGENTS_DIR = BASE_DIR / "agents"
GRAPH_DIR = BASE_DIR / "graph"
EDA_DIR = BASE_DIR / "eda"
VERIFICATION_DIR = BASE_DIR / "verification"
LOG_DIR = BASE_DIR / "verification_logs"
RUNS_DIR = LOG_DIR / "runs"
REPORTS_DIR = BASE_DIR / "reports"
EXAMPLES_DIR = BASE_DIR / "examples"


# =====================================================================
# ENVIRONMENT
# =====================================================================

ENVIRONMENT = os.getenv(
    "SILICONAI_ENV",
    "production",
).lower()


DEBUG = os.getenv(
    "SILICONAI_DEBUG",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


# =====================================================================
# GROQ
# =====================================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
)


GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


# Compatibility aliases
MODEL_NAME = GROQ_MODEL
LLM_MODEL = GROQ_MODEL
DEFAULT_MODEL = GROQ_MODEL


# =====================================================================
# LLM PARAMETERS
# =====================================================================

LLM_TEMPERATURE = float(
    os.getenv(
        "LLM_TEMPERATURE",
        "0.1",
    )
)


DEFAULT_TEMPERATURE = LLM_TEMPERATURE


LLM_MAX_TOKENS = int(
    os.getenv(
        "LLM_MAX_TOKENS",
        "1800",
    )
)


DEFAULT_MAX_TOKENS = LLM_MAX_TOKENS


# =====================================================================
# AGENT TOKEN LIMITS
# =====================================================================

"""
Per-agent output-token limits.

These are deliberately conservative.

The Groq free tier can reject oversized requests when the combined
prompt/context/output exceeds the available TPM budget.

Keep agent prompts compact and use these limits to prevent individual
agents from generating unnecessarily large responses.
"""

AGENT_TOKEN_LIMITS: Dict[str, int] = {
    "rtl_analyzer": 1600,
    "verification_planner": 1800,
    "test_generator": 1800,
    "testbench_generator": 2200,
    "simulator_agent": 800,
    "failure_analyzer": 1600,
    "coverage_agent": 1600,
    "red_team_agent": 1800,
    "mutation_agent": 800,
    "formal_agent": 1600,
    "bug_localization_agent": 1400,
    "rtl_repair_agent": 2200,
    "verification_judge": 1400,
}


# Compatibility aliases
AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS
TOKEN_LIMITS = AGENT_TOKEN_LIMITS


# =====================================================================
# AGENT TEMPERATURES
# =====================================================================

AGENT_TEMPERATURES: Dict[str, float] = {
    "rtl_analyzer": 0.1,
    "verification_planner": 0.1,
    "test_generator": 0.1,
    "testbench_generator": 0.1,
    "simulator_agent": 0.0,
    "failure_analyzer": 0.1,
    "coverage_agent": 0.1,
    "red_team_agent": 0.1,
    "mutation_agent": 0.0,
    "formal_agent": 0.1,
    "bug_localization_agent": 0.1,
    "rtl_repair_agent": 0.1,
    "verification_judge": 0.0,
}


# =====================================================================
# HELPER FUNCTIONS FOR AGENTS
# =====================================================================

def get_agent_token_limit(
    agent_name: str,
    default: int | None = None,
) -> int:
    """
    Return the configured token limit for an agent.

    Accepts:
        rtl_repair_agent
        rtl_repair
        RTLRepairAgent

    and normalizes them.
    """

    if default is None:
        default = LLM_MAX_TOKENS

    if not agent_name:
        return default

    name = str(
        agent_name
    ).strip().lower()

    aliases = {
        "rtlanalyzer": "rtl_analyzer",
        "rtl_analyzer": "rtl_analyzer",

        "verificationplanner": "verification_planner",
        "verification_planner": "verification_planner",

        "testgenerator": "test_generator",
        "test_generator": "test_generator",

        "testbenchgenerator": "testbench_generator",
        "testbench_generator": "testbench_generator",

        "simulatoragent": "simulator_agent",
        "simulator_agent": "simulator_agent",

        "failureanalyzer": "failure_analyzer",
        "failure_analyzer": "failure_analyzer",

        "coverageagent": "coverage_agent",
        "coverage_agent": "coverage_agent",

        "redteamagent": "red_team_agent",
        "red_team_agent": "red_team_agent",

        "mutationagent": "mutation_agent",
        "mutation_agent": "mutation_agent",

        "formalagent": "formal_agent",
        "formal_agent": "formal_agent",

        "buglocalizationagent": "bug_localization_agent",
        "bug_localization_agent": "bug_localization_agent",

        "rtlrepairagent": "rtl_repair_agent",
        "rtl_repair_agent": "rtl_repair_agent",

        "verificationjudge": "verification_judge",
        "verification_judge": "verification_judge",
    }

    normalized = aliases.get(
        name,
        name,
    )

    return int(
        AGENT_TOKEN_LIMITS.get(
            normalized,
            default,
        )
    )


def get_agent_temperature(
    agent_name: str,
    default: float | None = None,
) -> float:
    """Return configured temperature for an agent."""

    if default is None:
        default = LLM_TEMPERATURE

    if not agent_name:
        return default

    name = str(
        agent_name
    ).strip().lower()

    return float(
        AGENT_TEMPERATURES.get(
            name,
            default,
        )
    )


# =====================================================================
# LLM REQUEST LIMITS
# =====================================================================

# Maximum characters allowed in individual prompt components.
MAX_RTL_CHARS = int(
    os.getenv(
        "MAX_RTL_CHARS",
        "6000",
    )
)


MAX_SPEC_CHARS = int(
    os.getenv(
        "MAX_SPEC_CHARS",
        "4000",
    )
)


MAX_ANALYSIS_CHARS = int(
    os.getenv(
        "MAX_ANALYSIS_CHARS",
        "3000",
    )
)


MAX_TEST_CHARS = int(
    os.getenv(
        "MAX_TEST_CHARS",
        "5000",
    )
)


MAX_LOG_CHARS = int(
    os.getenv(
        "MAX_LOG_CHARS",
        "6000",
    )
)


# =====================================================================
# SIMULATION
# =====================================================================

IVERILOG_EXECUTABLE = os.getenv(
    "IVERILOG_EXECUTABLE",
    "iverilog",
)


VVP_EXECUTABLE = os.getenv(
    "VVP_EXECUTABLE",
    "vvp",
)


VERILATOR_EXECUTABLE = os.getenv(
    "VERILATOR_EXECUTABLE",
    "verilator",
)


YOSYS_EXECUTABLE = os.getenv(
    "YOSYS_EXECUTABLE",
    "yosys",
)


SIMULATION_TIMEOUT = int(
    os.getenv(
        "SIMULATION_TIMEOUT",
        "30",
    )
)


# Compatibility aliases
IVERILOG = IVERILOG_EXECUTABLE
VVP = VVP_EXECUTABLE
VERILATOR = VERILATOR_EXECUTABLE
YOSYS = YOSYS_EXECUTABLE


# =====================================================================
# FORMAL
# =====================================================================

"""
Formal analysis is optional.

The application does NOT require SymbiYosys.

The FormalAgent can detect unavailable formal infrastructure and
return an appropriate status such as:

    PROVEN
    FAILED
    NOT_PROVEN
    UNSUPPORTED
    UNAVAILABLE
    SKIPPED
"""

FORMAL_ENABLED_BY_DEFAULT = False


FORMAL_TIMEOUT = int(
    os.getenv(
        "FORMAL_TIMEOUT",
        "60",
    )
)


# =====================================================================
# VERIFICATION TARGETS
# =====================================================================

COVERAGE_TARGET = float(
    os.getenv(
        "COVERAGE_TARGET",
        "95",
    )
)


MUTATION_TARGET = float(
    os.getenv(
        "MUTATION_TARGET",
        "90",
    )
)


VERIFICATION_SCORE_TARGET = float(
    os.getenv(
        "VERIFICATION_SCORE_TARGET",
        "90",
    )
)


# =====================================================================
# ITERATION CONTROL
# =====================================================================

DEFAULT_MAX_ITERATIONS = int(
    os.getenv(
        "DEFAULT_MAX_ITERATIONS",
        "3",
    )
)


MIN_ITERATIONS = 1
MAX_ITERATIONS = 10


# =====================================================================
# WORKFLOW FLAGS
# =====================================================================

ENABLE_RED_TEAM = os.getenv(
    "ENABLE_RED_TEAM",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


ENABLE_MUTATION = os.getenv(
    "ENABLE_MUTATION",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


ENABLE_FORMAL = os.getenv(
    "ENABLE_FORMAL",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


# =====================================================================
# LOGGING
# =====================================================================

ENABLE_LOGGING = os.getenv(
    "ENABLE_LOGGING",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


MAX_AGENT_TRACE_EVENTS = int(
    os.getenv(
        "MAX_AGENT_TRACE_EVENTS",
        "500",
    )
)


MAX_LOG_FILE_SIZE = int(
    os.getenv(
        "MAX_LOG_FILE_SIZE",
        str(5 * 1024 * 1024),
    )
)


# =====================================================================
# REPORTING
# =====================================================================

REPORT_FORMAT = os.getenv(
    "REPORT_FORMAT",
    "markdown",
).lower()


GENERATE_HTML_REPORT = os.getenv(
    "GENERATE_HTML_REPORT",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


# =====================================================================
# SECURITY / PRIVACY
# =====================================================================

"""
Never log API keys.

These values exist as policy/configuration only.
"""

REDACT_SECRETS = True

SECRET_PATTERNS = [
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "API_KEY",
    "TOKEN",
    "PASSWORD",
    "SECRET",
]


# =====================================================================
# SUPPORTED EDA TOOLS
# =====================================================================

SUPPORTED_EDA_TOOLS = {
    "iverilog": IVERILOG_EXECUTABLE,
    "vvp": VVP_EXECUTABLE,
    "verilator": VERILATOR_EXECUTABLE,
    "yosys": YOSYS_EXECUTABLE,
}


# Explicitly document what is NOT required.
UNSUPPORTED_OR_OPTIONAL_TOOLS = {
    "symbiyosys": False,
}


# =====================================================================
# DIRECTORY INITIALIZATION
# =====================================================================

def ensure_directories() -> None:
    """
    Create application directories if they do not exist.
    """

    directories = [
        LOG_DIR,
        RUNS_DIR,
        REPORTS_DIR,
    ]

    for directory in directories:

        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except Exception:
            pass


# Do not make directory creation mandatory during import.
# Streamlit Cloud and unit tests can import settings safely.
try:
    ensure_directories()
except Exception:
    pass


# =====================================================================
# CONFIGURATION SUMMARY
# =====================================================================

def get_settings_summary() -> Dict[str, object]:
    """
    Return a safe configuration summary.

    Secrets are intentionally excluded.
    """

    return {
        "environment": ENVIRONMENT,
        "debug": DEBUG,

        "model": GROQ_MODEL,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,

        "agent_token_limits": dict(
            AGENT_TOKEN_LIMITS
        ),

        "coverage_target": COVERAGE_TARGET,
        "mutation_target": MUTATION_TARGET,
        "verification_score_target": (
            VERIFICATION_SCORE_TARGET
        ),

        "default_max_iterations": (
            DEFAULT_MAX_ITERATIONS
        ),

        "iverilog": IVERILOG_EXECUTABLE,
        "vvp": VVP_EXECUTABLE,
        "verilator": VERILATOR_EXECUTABLE,
        "yosys": YOSYS_EXECUTABLE,

        "formal_enabled": ENABLE_FORMAL,

        "symbiyosys_required": False,
    }


# =====================================================================
# PUBLIC EXPORTS
# =====================================================================

__all__ = [
    # Paths
    "BASE_DIR",
    "CONFIG_DIR",
    "AGENTS_DIR",
    "GRAPH_DIR",
    "EDA_DIR",
    "VERIFICATION_DIR",
    "LOG_DIR",
    "RUNS_DIR",
    "REPORTS_DIR",
    "EXAMPLES_DIR",

    # Environment
    "ENVIRONMENT",
    "DEBUG",

    # Groq / LLM
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "MODEL_NAME",
    "LLM_MODEL",
    "DEFAULT_MODEL",

    "LLM_TEMPERATURE",
    "DEFAULT_TEMPERATURE",

    "LLM_MAX_TOKENS",
    "DEFAULT_MAX_TOKENS",

    # Agent limits
    "AGENT_TOKEN_LIMITS",
    "AGENT_MAX_TOKENS",
    "TOKEN_LIMITS",
    "AGENT_TEMPERATURES",

    "get_agent_token_limit",
    "get_agent_temperature",

    # Prompt limits
    "MAX_RTL_CHARS",
    "MAX_SPEC_CHARS",
    "MAX_ANALYSIS_CHARS",
    "MAX_TEST_CHARS",
    "MAX_LOG_CHARS",

    # EDA
    "IVERILOG_EXECUTABLE",
    "VVP_EXECUTABLE",
    "VERILATOR_EXECUTABLE",
    "YOSYS_EXECUTABLE",

    "IVERILOG",
    "VVP",
    "VERILATOR",
    "YOSYS",

    "SIMULATION_TIMEOUT",

    # Formal
    "FORMAL_ENABLED_BY_DEFAULT",
    "FORMAL_TIMEOUT",

    # Targets
    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_SCORE_TARGET",

    # Iterations
    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",

    # Feature flags
    "ENABLE_RED_TEAM",
    "ENABLE_MUTATION",
    "ENABLE_FORMAL",

    # Logging
    "ENABLE_LOGGING",
    "MAX_AGENT_TRACE_EVENTS",
    "MAX_LOG_FILE_SIZE",

    # Reporting
    "REPORT_FORMAT",
    "GENERATE_HTML_REPORT",

    # Security
    "REDACT_SECRETS",
    "SECRET_PATTERNS",

    # EDA support
    "SUPPORTED_EDA_TOOLS",
    "UNSUPPORTED_OR_OPTIONAL_TOOLS",

    # Helpers
    "ensure_directories",
    "get_settings_summary",
]

