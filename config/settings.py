"""
PragyanAI SiliconAI
RTL / Verilog Verification Multi-Agent Platform

Central configuration for:
- Groq / LLM
- Agent token limits
- Agent temperatures
- RTL verification targets
- EDA tool paths
- Simulation settings
- Formal verification settings
- Iteration control
- Logging / reports
- Streamlit deployment

IMPORTANT:
SymbiYosys is intentionally NOT required.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = BASE_DIR / "config"
AGENTS_DIR = BASE_DIR / "agents"
GRAPH_DIR = BASE_DIR / "graph"
EDA_DIR = BASE_DIR / "eda"
VERIFICATION_DIR = BASE_DIR / "verification"
LOGGING_DIR = BASE_DIR / "logging"
REPORTS_DIR = BASE_DIR / "reports"
PROMPTS_DIR = BASE_DIR / "prompts"
EXAMPLES_DIR = BASE_DIR / "examples"
TESTS_DIR = BASE_DIR / "tests"
DOCS_DIR = BASE_DIR / "docs"
ASSETS_DIR = BASE_DIR / "assets"

DATA_DIR = BASE_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
TEMP_DIR = DATA_DIR / "tmp"


# ============================================================
# ENVIRONMENT
# ============================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production",
)

DEBUG = os.getenv(
    "DEBUG",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


# ============================================================
# GROQ / LLM CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
).strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()

# Common compatibility aliases
MODEL_NAME = GROQ_MODEL
LLM_MODEL = GROQ_MODEL
DEFAULT_MODEL = GROQ_MODEL


# ============================================================
# LLM GENERATION SETTINGS
# ============================================================

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


# ============================================================
# AGENT TOKEN LIMITS
# ============================================================
#
# Keep these reasonably small because Groq free-tier requests
# can fail when prompts + generated tokens exceed TPM limits.
#

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


# Generic compatibility aliases
AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS
TOKEN_LIMITS = AGENT_TOKEN_LIMITS


# ============================================================
# AGENT-SPECIFIC TOKEN COMPATIBILITY
# ============================================================
#
# Older versions of the agents import these constants directly.
# Keep them even though the newer architecture uses the
# AGENT_TOKEN_LIMITS dictionary.
#

RTL_ANALYZER_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "rtl_analyzer",
    1600,
)

VERIFICATION_PLANNER_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "verification_planner",
    1800,
)

TEST_GENERATOR_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "test_generator",
    1800,
)

TESTBENCH_GENERATOR_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "testbench_generator",
    2200,
)

SIMULATOR_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "simulator_agent",
    800,
)

FAILURE_ANALYZER_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "failure_analyzer",
    1600,
)

COVERAGE_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "coverage_agent",
    1600,
)

RED_TEAM_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "red_team_agent",
    1800,
)

MUTATION_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "mutation_agent",
    800,
)

FORMAL_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "formal_agent",
    1600,
)

BUG_LOCALIZATION_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "bug_localization_agent",
    1400,
)

RTL_REPAIR_AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "rtl_repair_agent",
    2200,
)

VERIFICATION_JUDGE_MAX_TOKENS = AGENT_TOKEN_LIMITS.get(
    "verification_judge",
    1400,
)


# ============================================================
# TOKEN LIMIT ALIASES
# ============================================================

RTL_ANALYZER_TOKEN_LIMIT = RTL_ANALYZER_MAX_TOKENS
VERIFICATION_PLANNER_TOKEN_LIMIT = VERIFICATION_PLANNER_MAX_TOKENS
TEST_GENERATOR_TOKEN_LIMIT = TEST_GENERATOR_MAX_TOKENS
TESTBENCH_GENERATOR_TOKEN_LIMIT = TESTBENCH_GENERATOR_MAX_TOKENS
SIMULATOR_AGENT_TOKEN_LIMIT = SIMULATOR_AGENT_MAX_TOKENS
FAILURE_ANALYZER_TOKEN_LIMIT = FAILURE_ANALYZER_MAX_TOKENS
COVERAGE_AGENT_TOKEN_LIMIT = COVERAGE_AGENT_MAX_TOKENS
RED_TEAM_AGENT_TOKEN_LIMIT = RED_TEAM_AGENT_MAX_TOKENS
MUTATION_AGENT_TOKEN_LIMIT = MUTATION_AGENT_MAX_TOKENS
FORMAL_AGENT_TOKEN_LIMIT = FORMAL_AGENT_MAX_TOKENS
BUG_LOCALIZATION_AGENT_TOKEN_LIMIT = BUG_LOCALIZATION_AGENT_MAX_TOKENS
RTL_REPAIR_AGENT_TOKEN_LIMIT = RTL_REPAIR_AGENT_MAX_TOKENS
VERIFICATION_JUDGE_TOKEN_LIMIT = VERIFICATION_JUDGE_MAX_TOKENS


# ============================================================
# AGENT TEMPERATURES
# ============================================================

AGENT_TEMPERATURES: Dict[str, float] = {

    "rtl_analyzer": 0.05,

    "verification_planner": 0.10,

    "test_generator": 0.15,

    "testbench_generator": 0.10,

    "simulator_agent": 0.00,

    "failure_analyzer": 0.05,

    "coverage_agent": 0.05,

    "red_team_agent": 0.20,

    "mutation_agent": 0.00,

    "formal_agent": 0.05,

    "bug_localization_agent": 0.05,

    "rtl_repair_agent": 0.10,

    "verification_judge": 0.00,
}


# ============================================================
# AGENT TEMPERATURE COMPATIBILITY
# ============================================================

RTL_ANALYZER_TEMPERATURE = AGENT_TEMPERATURES.get(
    "rtl_analyzer",
    LLM_TEMPERATURE,
)

VERIFICATION_PLANNER_TEMPERATURE = AGENT_TEMPERATURES.get(
    "verification_planner",
    LLM_TEMPERATURE,
)

TEST_GENERATOR_TEMPERATURE = AGENT_TEMPERATURES.get(
    "test_generator",
    LLM_TEMPERATURE,
)

TESTBENCH_GENERATOR_TEMPERATURE = AGENT_TEMPERATURES.get(
    "testbench_generator",
    LLM_TEMPERATURE,
)

SIMULATOR_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "simulator_agent",
    0.0,
)

FAILURE_ANALYZER_TEMPERATURE = AGENT_TEMPERATURES.get(
    "failure_analyzer",
    LLM_TEMPERATURE,
)

COVERAGE_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "coverage_agent",
    LLM_TEMPERATURE,
)

RED_TEAM_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "red_team_agent",
    LLM_TEMPERATURE,
)

MUTATION_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "mutation_agent",
    0.0,
)

FORMAL_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "formal_agent",
    LLM_TEMPERATURE,
)

BUG_LOCALIZATION_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "bug_localization_agent",
    LLM_TEMPERATURE,
)

RTL_REPAIR_AGENT_TEMPERATURE = AGENT_TEMPERATURES.get(
    "rtl_repair_agent",
    LLM_TEMPERATURE,
)

VERIFICATION_JUDGE_TEMPERATURE = AGENT_TEMPERATURES.get(
    "verification_judge",
    0.0,
)


# ============================================================
# PROMPT SIZE LIMITS
# ============================================================
#
# These limits help avoid oversized Groq requests.
#

MAX_RTL_CHARS = int(
    os.getenv(
        "MAX_RTL_CHARS",
        "14000",
    )
)

MAX_TESTBENCH_CHARS = int(
    os.getenv(
        "MAX_TESTBENCH_CHARS",
        "14000",
    )
)

MAX_ANALYSIS_CHARS = int(
    os.getenv(
        "MAX_ANALYSIS_CHARS",
        "9000",
    )
)

MAX_FAILURE_OUTPUT_CHARS = int(
    os.getenv(
        "MAX_FAILURE_OUTPUT_CHARS",
        "7000",
    )
)

MAX_COVERAGE_CHARS = int(
    os.getenv(
        "MAX_COVERAGE_CHARS",
        "7000",
    )
)

MAX_TRACE_CHARS = int(
    os.getenv(
        "MAX_TRACE_CHARS",
        "12000",
    )
)


# Compatibility aliases

PROMPT_RTL_CHAR_LIMIT = MAX_RTL_CHARS
PROMPT_TESTBENCH_CHAR_LIMIT = MAX_TESTBENCH_CHARS
PROMPT_ANALYSIS_CHAR_LIMIT = MAX_ANALYSIS_CHARS
PROMPT_OUTPUT_CHAR_LIMIT = MAX_FAILURE_OUTPUT_CHARS


# ============================================================
# EDA EXECUTABLES
# ============================================================

IVERILOG_EXECUTABLE = os.getenv(
    "IVERILOG_EXECUTABLE",
    "",
).strip()

VVP_EXECUTABLE = os.getenv(
    "VVP_EXECUTABLE",
    "",
).strip()

VERILATOR_EXECUTABLE = os.getenv(
    "VERILATOR_EXECUTABLE",
    "",
).strip()

YOSYS_EXECUTABLE = os.getenv(
    "YOSYS_EXECUTABLE",
    "",
).strip()


# ------------------------------------------------------------
# Automatically discover binaries when environment variables
# are not explicitly configured.
# ------------------------------------------------------------

if not IVERILOG_EXECUTABLE:
    IVERILOG_EXECUTABLE = shutil.which(
        "iverilog"
    ) or "iverilog"

if not VVP_EXECUTABLE:
    VVP_EXECUTABLE = shutil.which(
        "vvp"
    ) or "vvp"

if not VERILATOR_EXECUTABLE:
    VERILATOR_EXECUTABLE = shutil.which(
        "verilator"
    ) or "verilator"

if not YOSYS_EXECUTABLE:
    YOSYS_EXECUTABLE = shutil.which(
        "yosys"
    ) or "yosys"


# Compatibility aliases

IVERILOG = IVERILOG_EXECUTABLE
VVP = VVP_EXECUTABLE
VERILATOR = VERILATOR_EXECUTABLE
YOSYS = YOSYS_EXECUTABLE


# ============================================================
# EDA TOOL AVAILABILITY
# ============================================================

SUPPORTED_EDA_TOOLS = {
    "iverilog": IVERILOG_EXECUTABLE,
    "vvp": VVP_EXECUTABLE,
    "verilator": VERILATOR_EXECUTABLE,
    "yosys": YOSYS_EXECUTABLE,
}


# ============================================================
# SYMBIYOSYS
# ============================================================
#
# INTENTIONALLY DISABLED.
#
# PragyanAI SiliconAI does not require SymbiYosys.
#
# Formal verification must gracefully degrade if a suitable
# formal backend is unavailable.
#

FORMAL_ENABLED_BY_DEFAULT = False

ENABLE_FORMAL = os.getenv(
    "ENABLE_FORMAL",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


UNSUPPORTED_OR_OPTIONAL_TOOLS = {
    "symbiyosys": False,
}


# Explicit compatibility values.
# These do NOT invoke or require SymbiYosys.

SYMBIYOSYS_EXECUTABLE = None
SBY_EXECUTABLE = None


# ============================================================
# SIMULATION
# ============================================================

SIMULATION_TIMEOUT = int(
    os.getenv(
        "SIMULATION_TIMEOUT",
        "30",
    )
)

COMPILE_TIMEOUT = int(
    os.getenv(
        "COMPILE_TIMEOUT",
        "30",
    )
)

VERILATOR_TIMEOUT = int(
    os.getenv(
        "VERILATOR_TIMEOUT",
        "30",
    )
)

YOSYS_TIMEOUT = int(
    os.getenv(
        "YOSYS_TIMEOUT",
        "30",
    )
)


# ============================================================
# FORMAL VERIFICATION
# ============================================================

FORMAL_TIMEOUT = int(
    os.getenv(
        "FORMAL_TIMEOUT",
        "30",
    )
)

FORMAL_MAX_DEPTH = int(
    os.getenv(
        "FORMAL_MAX_DEPTH",
        "20",
    )
)


# ============================================================
# VERIFICATION TARGETS
# ============================================================

TARGET_COVERAGE = float(
    os.getenv(
        "TARGET_COVERAGE",
        "95",
    )
)

TARGET_MUTATION_SCORE = float(
    os.getenv(
        "TARGET_MUTATION_SCORE",
        "90",
    )
)

TARGET_VERIFICATION_SCORE = float(
    os.getenv(
        "TARGET_VERIFICATION_SCORE",
        "90",
    )
)


# Compatibility aliases

COVERAGE_TARGET = TARGET_COVERAGE
MUTATION_TARGET = TARGET_MUTATION_SCORE
VERIFICATION_TARGET = TARGET_VERIFICATION_SCORE


# ============================================================
# ITERATION CONTROL
# ============================================================

DEFAULT_MAX_ITERATIONS = int(
    os.getenv(
        "DEFAULT_MAX_ITERATIONS",
        "3",
    )
)

MIN_ITERATIONS = int(
    os.getenv(
        "MIN_ITERATIONS",
        "1",
    )
)

MAX_ITERATIONS = int(
    os.getenv(
        "MAX_ITERATIONS",
        "10",
    )
)


# Compatibility aliases

MAX_VERIFICATION_ITERATIONS = MAX_ITERATIONS
DEFAULT_ITERATIONS = DEFAULT_MAX_ITERATIONS


# ============================================================
# FEATURE FLAGS
# ============================================================

ENABLE_RED_TEAM = os.getenv(
    "ENABLE_RED_TEAM",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


ENABLE_MUTATION = os.getenv(
    "ENABLE_MUTATION",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


# Formal remains opt-in.
ENABLE_FORMAL = ENABLE_FORMAL


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

ENABLE_AGENT_LOGGING = os.getenv(
    "ENABLE_AGENT_LOGGING",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ENABLE_TRACE_LOGGING = os.getenv(
    "ENABLE_TRACE_LOGGING",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

MAX_LOG_ENTRIES = int(
    os.getenv(
        "MAX_LOG_ENTRIES",
        "500",
    )
)


# ============================================================
# REPORTING
# ============================================================

ENABLE_REPORTS = os.getenv(
    "ENABLE_REPORTS",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


REPORT_FORMAT = os.getenv(
    "REPORT_FORMAT",
    "markdown",
).lower()


# ============================================================
# SECURITY / EXECUTION
# ============================================================

ALLOW_EXTERNAL_COMMANDS = os.getenv(
    "ALLOW_EXTERNAL_COMMANDS",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


MAX_RTL_FILE_SIZE_BYTES = int(
    os.getenv(
        "MAX_RTL_FILE_SIZE_BYTES",
        str(1024 * 1024),
    )
)


MAX_TESTBENCH_FILE_SIZE_BYTES = int(
    os.getenv(
        "MAX_TESTBENCH_FILE_SIZE_BYTES",
        str(1024 * 1024),
    )
)


# ============================================================
# DEFAULT RTL SETTINGS
# ============================================================

DEFAULT_VERILOG_STANDARD = os.getenv(
    "DEFAULT_VERILOG_STANDARD",
    "2012",
)

IVERILOG_STANDARD = DEFAULT_VERILOG_STANDARD


DEFAULT_TOP_MODULE = os.getenv(
    "DEFAULT_TOP_MODULE",
    "dut",
)


# ============================================================
# SIMULATION OUTPUT MARKERS
# ============================================================

TEST_PASS_MARKER = os.getenv(
    "TEST_PASS_MARKER",
    "TEST_RESULT: PASS",
)

TEST_FAIL_MARKER = os.getenv(
    "TEST_FAIL_MARKER",
    "TEST_RESULT: FAIL",
)

TEST_ERROR_MARKER = os.getenv(
    "TEST_ERROR_MARKER",
    "TEST_ERROR",
)


# ============================================================
# WORKFLOW STATUS VALUES
# ============================================================

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"
STATUS_COMPLETED = "completed"
STATUS_NEEDS_REVIEW = "needs_review"


# ============================================================
# JUDGE VERDICTS
# ============================================================

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NEED_MORE = "NEED_MORE"


# ============================================================
# DIRECTORY CREATION
# ============================================================

def ensure_directories() -> None:
    """
    Create runtime directories required by the application.

    Safe to call multiple times.
    """

    directories = [
        DATA_DIR,
        RUNS_DIR,
        TEMP_DIR,
        REPORTS_DIR,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# AGENT CONFIG HELPERS
# ============================================================

def get_agent_token_limit(
    agent_name: str,
    default: int | None = None,
) -> int:
    """
    Return token limit for an agent.

    Supports names with or without '_agent' suffix.
    """

    name = str(
        agent_name
    ).strip().lower()

    if name in AGENT_TOKEN_LIMITS:
        return AGENT_TOKEN_LIMITS[name]

    normalized = name.replace(
        "-",
        "_",
    )

    if normalized in AGENT_TOKEN_LIMITS:
        return AGENT_TOKEN_LIMITS[
            normalized
        ]

    if normalized.endswith(
        "_agent"
    ):
        shortened = normalized[
            :-len("_agent")
        ]

        if shortened in AGENT_TOKEN_LIMITS:
            return AGENT_TOKEN_LIMITS[
                shortened
            ]

    if default is not None:
        return int(default)

    return int(
        DEFAULT_MAX_TOKENS
    )


def get_agent_temperature(
    agent_name: str,
    default: float | None = None,
) -> float:
    """
    Return temperature for an agent.
    """

    name = str(
        agent_name
    ).strip().lower()

    if name in AGENT_TEMPERATURES:
        return AGENT_TEMPERATURES[name]

    normalized = name.replace(
        "-",
        "_",
    )

    if normalized in AGENT_TEMPERATURES:
        return AGENT_TEMPERATURES[
            normalized
        ]

    if normalized.endswith(
        "_agent"
    ):
        shortened = normalized[
            :-len("_agent")
        ]

        if shortened in AGENT_TEMPERATURES:
            return AGENT_TEMPERATURES[
                shortened
            ]

    if default is not None:
        return float(default)

    return float(
        LLM_TEMPERATURE
    )


# ============================================================
# TOOL HELPERS
# ============================================================

def tool_available(
    tool_name: str,
) -> bool:
    """
    Check whether an EDA executable is available.
    """

    name = str(
        tool_name
    ).strip().lower()

    if name == "symbiyosys":
        return False

    executable = SUPPORTED_EDA_TOOLS.get(
        name
    )

    if not executable:
        return False

    return (
        shutil.which(executable)
        is not None
        or Path(executable).exists()
    )


def get_available_eda_tools() -> Dict[str, bool]:
    """
    Return availability of supported EDA tools.
    """

    return {
        name: tool_available(name)
        for name in SUPPORTED_EDA_TOOLS
    }


# ============================================================
# SETTINGS SUMMARY
# ============================================================

def get_settings_summary() -> Dict[str, Any]:
    """
    Return a safe configuration summary.

    Secrets such as GROQ_API_KEY are never returned.
    """

    return {
        "environment": ENVIRONMENT,

        "debug": DEBUG,

        "model": GROQ_MODEL,

        "groq_configured": bool(
            GROQ_API_KEY
        ),

        "llm_temperature": LLM_TEMPERATURE,

        "llm_max_tokens": LLM_MAX_TOKENS,

        "agent_token_limits": dict(
            AGENT_TOKEN_LIMITS
        ),

        "coverage_target": TARGET_COVERAGE,

        "mutation_target": TARGET_MUTATION_SCORE,

        "verification_target": TARGET_VERIFICATION_SCORE,

        "default_max_iterations":
            DEFAULT_MAX_ITERATIONS,

        "max_iterations":
            MAX_ITERATIONS,

        "red_team_enabled":
            ENABLE_RED_TEAM,

        "mutation_enabled":
            ENABLE_MUTATION,

        "formal_enabled":
            ENABLE_FORMAL,

        "formal_default":
            FORMAL_ENABLED_BY_DEFAULT,

        "eda_tools":
            get_available_eda_tools(),

        "symbiyosys":
            False,
    }


# ============================================================
# INITIALIZE DIRECTORIES
# ============================================================

try:
    ensure_directories()
except Exception:
    # Streamlit Cloud / restricted environments may prevent
    # directory creation during import. Runtime code can call
    # ensure_directories() again.
    pass


# ============================================================
# DEBUG INFORMATION
# ============================================================

if DEBUG:
    print(
        "PragyanAI SiliconAI settings loaded."
    )

    print(
        f"Environment : {ENVIRONMENT}"
    )

    print(
        f"Model       : {GROQ_MODEL}"
    )

    print(
        f"Max Tokens  : {LLM_MAX_TOKENS}"
    )

    print(
        f"Coverage    : {TARGET_COVERAGE}%"
    )

    print(
        f"Mutation    : {TARGET_MUTATION_SCORE}%"
    )

    print(
        f"Verification: {TARGET_VERIFICATION_SCORE}%"
    )

    print(
        f"Formal      : {ENABLE_FORMAL}"
    )

    print(
        "SymbiYosys  : DISABLED"
    )


# ============================================================
# PUBLIC EXPORTS
# ============================================================

__all__ = [

    # Paths
    "BASE_DIR",
    "CONFIG_DIR",
    "AGENTS_DIR",
    "GRAPH_DIR",
    "EDA_DIR",
    "VERIFICATION_DIR",
    "LOGGING_DIR",
    "REPORTS_DIR",
    "PROMPTS_DIR",
    "EXAMPLES_DIR",
    "TESTS_DIR",
    "DOCS_DIR",
    "ASSETS_DIR",
    "DATA_DIR",
    "RUNS_DIR",
    "TEMP_DIR",

    # Environment
    "ENVIRONMENT",
    "DEBUG",

    # LLM
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "MODEL_NAME",
    "LLM_MODEL",
    "DEFAULT_MODEL",
    "LLM_TEMPERATURE",
    "DEFAULT_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "DEFAULT_MAX_TOKENS",

    # Agent token limits
    "AGENT_TOKEN_LIMITS",
    "AGENT_MAX_TOKENS",
    "TOKEN_LIMITS",

    "RTL_ANALYZER_MAX_TOKENS",
    "VERIFICATION_PLANNER_MAX_TOKENS",
    "TEST_GENERATOR_MAX_TOKENS",
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    "SIMULATOR_AGENT_MAX_TOKENS",
    "FAILURE_ANALYZER_MAX_TOKENS",
    "COVERAGE_AGENT_MAX_TOKENS",
    "RED_TEAM_AGENT_MAX_TOKENS",
    "MUTATION_AGENT_MAX_TOKENS",
    "FORMAL_AGENT_MAX_TOKENS",
    "BUG_LOCALIZATION_AGENT_MAX_TOKENS",
    "RTL_REPAIR_AGENT_MAX_TOKENS",
    "VERIFICATION_JUDGE_MAX_TOKENS",

    # Temperatures
    "AGENT_TEMPERATURES",
    "RTL_ANALYZER_TEMPERATURE",
    "VERIFICATION_PLANNER_TEMPERATURE",
    "TEST_GENERATOR_TEMPERATURE",
    "TESTBENCH_GENERATOR_TEMPERATURE",
    "SIMULATOR_AGENT_TEMPERATURE",
    "FAILURE_ANALYZER_TEMPERATURE",
    "COVERAGE_AGENT_TEMPERATURE",
    "RED_TEAM_AGENT_TEMPERATURE",
    "MUTATION_AGENT_TEMPERATURE",
    "FORMAL_AGENT_TEMPERATURE",
    "BUG_LOCALIZATION_AGENT_TEMPERATURE",
    "RTL_REPAIR_AGENT_TEMPERATURE",
    "VERIFICATION_JUDGE_TEMPERATURE",

    # Prompt limits
    "MAX_RTL_CHARS",
    "MAX_TESTBENCH_CHARS",
    "MAX_ANALYSIS_CHARS",
    "MAX_FAILURE_OUTPUT_CHARS",
    "MAX_COVERAGE_CHARS",
    "MAX_TRACE_CHARS",

    # EDA
    "IVERILOG_EXECUTABLE",
    "VVP_EXECUTABLE",
    "VERILATOR_EXECUTABLE",
    "YOSYS_EXECUTABLE",
    "IVERILOG",
    "VVP",
    "VERILATOR",
    "YOSYS",
    "SUPPORTED_EDA_TOOLS",

    # Formal
    "FORMAL_ENABLED_BY_DEFAULT",
    "ENABLE_FORMAL",
    "FORMAL_TIMEOUT",
    "FORMAL_MAX_DEPTH",
    "SYMBIYOSYS_EXECUTABLE",
    "SBY_EXECUTABLE",
    "UNSUPPORTED_OR_OPTIONAL_TOOLS",

    # Simulation
    "SIMULATION_TIMEOUT",
    "COMPILE_TIMEOUT",
    "VERILATOR_TIMEOUT",
    "YOSYS_TIMEOUT",

    # Targets
    "TARGET_COVERAGE",
    "TARGET_MUTATION_SCORE",
    "TARGET_VERIFICATION_SCORE",
    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_TARGET",

    # Iterations
    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",
    "MAX_VERIFICATION_ITERATIONS",
    "DEFAULT_ITERATIONS",

    # Features
    "ENABLE_RED_TEAM",
    "ENABLE_MUTATION",

    # Logging
    "LOG_LEVEL",
    "ENABLE_AGENT_LOGGING",
    "ENABLE_TRACE_LOGGING",
    "MAX_LOG_ENTRIES",

    # Reports
    "ENABLE_REPORTS",
    "REPORT_FORMAT",

    # Security
    "ALLOW_EXTERNAL_COMMANDS",
    "MAX_RTL_FILE_SIZE_BYTES",
    "MAX_TESTBENCH_FILE_SIZE_BYTES",

    # RTL
    "DEFAULT_VERILOG_STANDARD",
    "IVERILOG_STANDARD",
    "DEFAULT_TOP_MODULE",

    # Markers
    "TEST_PASS_MARKER",
    "TEST_FAIL_MARKER",
    "TEST_ERROR_MARKER",

    # Status
    "STATUS_IDLE",
    "STATUS_RUNNING",
    "STATUS_PASSED",
    "STATUS_FAILED",
    "STATUS_ERROR",
    "STATUS_COMPLETED",
    "STATUS_NEEDS_REVIEW",

    # Verdicts
    "VERDICT_PASS",
    "VERDICT_FAIL",
    "VERDICT_NEED_MORE",

    # Functions
    "ensure_directories",
    "get_agent_token_limit",
    "get_agent_temperature",
    "tool_available",
    "get_available_eda_tools",
    "get_settings_summary",
]


