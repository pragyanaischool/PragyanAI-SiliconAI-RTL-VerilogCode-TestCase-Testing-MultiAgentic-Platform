"""
PragyanAI SiliconAI
Agentic RTL Verification Platform

Central application configuration.

Designed for:
- Streamlit
- GitHub / Streamlit Cloud
- LangChain / LangGraph
- Groq
- Icarus Verilog
- Verilator
- Yosys

SymbiYosys is intentionally NOT required.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


# ============================================================================
# PROJECT PATHS
# ============================================================================

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

RUNTIME_DIR = BASE_DIR / "runtime"
RUNS_DIR = RUNTIME_DIR / "runs"
TEMP_DIR = RUNTIME_DIR / "tmp"
LOG_DIR = RUNTIME_DIR / "logs"
REPORT_DIR = RUNTIME_DIR / "reports"


# ============================================================================
# APPLICATION IDENTITY
# ============================================================================

APP_NAME = "PragyanAI SiliconAI"

APP_VERSION = "1.0.0"

PROJECT_NAME = "PragyanAI SiliconAI - Agentic RTL Verification"

APP_DESCRIPTION = (
    "Agentic RTL Verification Platform for AI Test Generation, "
    "Simulation, Coverage, Mutation, Formal Verification and RTL Repair."
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    os.getenv("APP_ENV", "production"),
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


# ============================================================================
# GROQ / LLM CONFIGURATION
# ============================================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
).strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()

# Compatibility aliases
MODEL_NAME = GROQ_MODEL
LLM_MODEL = GROQ_MODEL
DEFAULT_MODEL = GROQ_MODEL

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


# ============================================================================
# AGENT TOKEN LIMITS
# ============================================================================

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

AGENT_MAX_TOKENS = AGENT_TOKEN_LIMITS
TOKEN_LIMITS = AGENT_TOKEN_LIMITS


# ============================================================================
# INDIVIDUAL TOKEN CONSTANTS
# ============================================================================

RTL_ANALYZER_MAX_TOKENS = AGENT_TOKEN_LIMITS["rtl_analyzer"]

VERIFICATION_PLANNER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_planner"]
)

TEST_GENERATOR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["test_generator"]
)

TESTBENCH_GENERATOR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["testbench_generator"]
)

SIMULATOR_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["simulator_agent"]
)

FAILURE_ANALYZER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["failure_analyzer"]
)

COVERAGE_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["coverage_agent"]
)

RED_TEAM_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["red_team_agent"]
)

MUTATION_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["mutation_agent"]
)

FORMAL_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["formal_agent"]
)

BUG_LOCALIZATION_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["bug_localization_agent"]
)

RTL_REPAIR_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["rtl_repair_agent"]
)

VERIFICATION_JUDGE_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_judge"]
)


# ============================================================================
# AGENT TEMPERATURES
# ============================================================================

AGENT_TEMPERATURES: Dict[str, float] = {
    "rtl_analyzer": 0.1,
    "verification_planner": 0.1,
    "test_generator": 0.2,
    "testbench_generator": 0.1,
    "simulator_agent": 0.0,
    "failure_analyzer": 0.1,
    "coverage_agent": 0.1,
    "red_team_agent": 0.2,
    "mutation_agent": 0.0,
    "formal_agent": 0.0,
    "bug_localization_agent": 0.1,
    "rtl_repair_agent": 0.1,
    "verification_judge": 0.0,
}

RTL_ANALYZER_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_analyzer"]
)

VERIFICATION_PLANNER_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_planner"]
)

TEST_GENERATOR_TEMPERATURE = (
    AGENT_TEMPERATURES["test_generator"]
)

TESTBENCH_GENERATOR_TEMPERATURE = (
    AGENT_TEMPERATURES["testbench_generator"]
)

SIMULATOR_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["simulator_agent"]
)

FAILURE_ANALYZER_TEMPERATURE = (
    AGENT_TEMPERATURES["failure_analyzer"]
)

COVERAGE_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["coverage_agent"]
)

RED_TEAM_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["red_team_agent"]
)

MUTATION_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["mutation_agent"]
)

FORMAL_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["formal_agent"]
)

BUG_LOCALIZATION_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["bug_localization_agent"]
)

RTL_REPAIR_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_repair_agent"]
)

VERIFICATION_JUDGE_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_judge"]
)


# ============================================================================
# PROMPT / CONTEXT LIMITS
# ============================================================================

# Character limits, not token limits.

MAX_RTL_CHARS = int(
    os.getenv(
        "MAX_RTL_CHARS",
        "12000",
    )
)

MAX_SPECIFICATION_CHARS = int(
    os.getenv(
        "MAX_SPECIFICATION_CHARS",
        "8000",
    )
)

MAX_TESTBENCH_CHARS = int(
    os.getenv(
        "MAX_TESTBENCH_CHARS",
        "12000",
    )
)

MAX_SIMULATION_OUTPUT_CHARS = int(
    os.getenv(
        "MAX_SIMULATION_OUTPUT_CHARS",
        "8000",
    )
)

MAX_FAILURE_OUTPUT_CHARS = int(
    os.getenv(
        "MAX_FAILURE_OUTPUT_CHARS",
        "6000",
    )
)

MAX_COVERAGE_OUTPUT_CHARS = int(
    os.getenv(
        "MAX_COVERAGE_OUTPUT_CHARS",
        "6000",
    )
)

MAX_AGENT_CONTEXT_CHARS = int(
    os.getenv(
        "MAX_AGENT_CONTEXT_CHARS",
        "18000",
    )
)


# ============================================================================
# LLM-SPECIFIC CONTEXT LIMITS
# ============================================================================
#
# Compatibility names required by agent implementations.
#
# These are character limits, not token limits.
# They default to the general context limits above.
# ============================================================================

MAX_RTL_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_RTL_CHARS_FOR_LLM",
        str(MAX_RTL_CHARS),
    )
)

MAX_SPECIFICATION_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_SPECIFICATION_CHARS_FOR_LLM",
        str(MAX_SPECIFICATION_CHARS),
    )
)

MAX_TESTBENCH_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_TESTBENCH_CHARS_FOR_LLM",
        str(MAX_TESTBENCH_CHARS),
    )
)

MAX_SIMULATION_OUTPUT_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_SIMULATION_OUTPUT_CHARS_FOR_LLM",
        str(MAX_SIMULATION_OUTPUT_CHARS),
    )
)

MAX_FAILURE_OUTPUT_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_FAILURE_OUTPUT_CHARS_FOR_LLM",
        str(MAX_FAILURE_OUTPUT_CHARS),
    )
)

MAX_COVERAGE_OUTPUT_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_COVERAGE_OUTPUT_CHARS_FOR_LLM",
        str(MAX_COVERAGE_OUTPUT_CHARS),
    )
)

MAX_AGENT_CONTEXT_CHARS_FOR_LLM = int(
    os.getenv(
        "MAX_AGENT_CONTEXT_CHARS_FOR_LLM",
        str(MAX_AGENT_CONTEXT_CHARS),
    )
)


# ============================================================================
# COMPATIBILITY CONTEXT ALIASES
# ============================================================================

RTL_CHAR_LIMIT = MAX_RTL_CHARS
SPECIFICATION_CHAR_LIMIT = MAX_SPECIFICATION_CHARS
TESTBENCH_CHAR_LIMIT = MAX_TESTBENCH_CHARS
SIMULATION_OUTPUT_CHAR_LIMIT = MAX_SIMULATION_OUTPUT_CHARS
AGENT_CONTEXT_CHAR_LIMIT = MAX_AGENT_CONTEXT_CHARS

RTL_LLM_CHAR_LIMIT = MAX_RTL_CHARS_FOR_LLM
SPECIFICATION_LLM_CHAR_LIMIT = MAX_SPECIFICATION_CHARS_FOR_LLM
TESTBENCH_LLM_CHAR_LIMIT = MAX_TESTBENCH_CHARS_FOR_LLM
SIMULATION_OUTPUT_LLM_CHAR_LIMIT = (
    MAX_SIMULATION_OUTPUT_CHARS_FOR_LLM
)
FAILURE_OUTPUT_LLM_CHAR_LIMIT = (
    MAX_FAILURE_OUTPUT_CHARS_FOR_LLM
)
COVERAGE_OUTPUT_LLM_CHAR_LIMIT = (
    MAX_COVERAGE_OUTPUT_CHARS_FOR_LLM
)
AGENT_CONTEXT_LLM_CHAR_LIMIT = (
    MAX_AGENT_CONTEXT_CHARS_FOR_LLM
)


# ============================================================================
# EDA TOOL CONFIGURATION
# ============================================================================

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

IVERILOG = IVERILOG_EXECUTABLE
VVP = VVP_EXECUTABLE
VERILATOR = VERILATOR_EXECUTABLE
YOSYS = YOSYS_EXECUTABLE

SUPPORTED_EDA_TOOLS = {
    "iverilog",
    "vvp",
    "verilator",
    "yosys",
}


# ============================================================================
# FORMAL VERIFICATION
# ============================================================================
#
# SymbiYosys is NOT required.
#
# Formal is optional and should gracefully report unavailable if the
# selected formal backend is not installed.
# ============================================================================

FORMAL_ENABLED_BY_DEFAULT = (
    os.getenv(
        "FORMAL_ENABLED_BY_DEFAULT",
        "false",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

# Backwards-compatible placeholders.
# They intentionally do not point to an executable.
SYMBIYOSYS_EXECUTABLE = None
SBY_EXECUTABLE = None

UNSUPPORTED_OR_OPTIONAL_TOOLS = {
    "symbiyosys": False,
}


# ============================================================================
# TIMEOUTS
# ============================================================================

SIMULATION_TIMEOUT_SECONDS = int(
    os.getenv(
        "SIMULATION_TIMEOUT_SECONDS",
        "30",
    )
)

COMPILE_TIMEOUT_SECONDS = int(
    os.getenv(
        "COMPILE_TIMEOUT_SECONDS",
        "30",
    )
)

VERILATOR_TIMEOUT_SECONDS = int(
    os.getenv(
        "VERILATOR_TIMEOUT_SECONDS",
        "60",
    )
)

YOSYS_TIMEOUT_SECONDS = int(
    os.getenv(
        "YOSYS_TIMEOUT_SECONDS",
        "60",
    )
)

FORMAL_TIMEOUT_SECONDS = int(
    os.getenv(
        "FORMAL_TIMEOUT_SECONDS",
        "60",
    )
)

SIM_TIMEOUT = SIMULATION_TIMEOUT_SECONDS
FORMAL_TIMEOUT = FORMAL_TIMEOUT_SECONDS


# ============================================================================
# VERIFICATION TARGETS
# ============================================================================

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

# ---------------------------------------------------------------------------
# IMPORTANT COMPATIBILITY FIX
# ---------------------------------------------------------------------------
#
# Some agents import VERIFICATION_TARGET directly.
#
# Keep this alias so older/newer agent implementations both work.
# ---------------------------------------------------------------------------

VERIFICATION_TARGET = VERIFICATION_SCORE_TARGET

TARGET_COVERAGE = COVERAGE_TARGET
TARGET_MUTATION_SCORE = MUTATION_TARGET
TARGET_VERIFICATION_SCORE = VERIFICATION_SCORE_TARGET

COVERAGE_THRESHOLD = COVERAGE_TARGET
MUTATION_THRESHOLD = MUTATION_TARGET
VERIFICATION_THRESHOLD = VERIFICATION_SCORE_TARGET


# ============================================================================
# ITERATION CONTROL
# ============================================================================

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


# ============================================================================
# FEATURE FLAGS
# ============================================================================

RED_TEAM_ENABLED_BY_DEFAULT = (
    os.getenv(
        "RED_TEAM_ENABLED_BY_DEFAULT",
        "true",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

MUTATION_ENABLED_BY_DEFAULT = (
    os.getenv(
        "MUTATION_ENABLED_BY_DEFAULT",
        "false",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ============================================================================
# RTL DEFAULTS
# ============================================================================

DEFAULT_VERILOG_STANDARD = os.getenv(
    "DEFAULT_VERILOG_STANDARD",
    "2012",
)

DEFAULT_TOP_MODULE = os.getenv(
    "DEFAULT_TOP_MODULE",
    "dut",
)


# ============================================================================
# TESTING DEFAULTS
# ============================================================================

DEFAULT_CLOCK_PERIOD_NS = int(
    os.getenv(
        "DEFAULT_CLOCK_PERIOD_NS",
        "10",
    )
)

DEFAULT_RESET_CYCLES = int(
    os.getenv(
        "DEFAULT_RESET_CYCLES",
        "2",
    )
)

DEFAULT_TEST_TIMEOUT_NS = int(
    os.getenv(
        "DEFAULT_TEST_TIMEOUT_NS",
        "1000",
    )
)


# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

ENABLE_AGENT_LOGGING = (
    os.getenv(
        "ENABLE_AGENT_LOGGING",
        "true",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

ENABLE_AGENT_TRACE = (
    os.getenv(
        "ENABLE_AGENT_TRACE",
        "true",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ============================================================================
# REPORTING
# ============================================================================

DEFAULT_REPORT_FORMAT = os.getenv(
    "DEFAULT_REPORT_FORMAT",
    "markdown",
)

ENABLE_HTML_REPORT = (
    os.getenv(
        "ENABLE_HTML_REPORT",
        "true",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ============================================================================
# SECURITY / RESOURCE LIMITS
# ============================================================================

MAX_UPLOAD_SIZE_MB = int(
    os.getenv(
        "MAX_UPLOAD_SIZE_MB",
        "5",
    )
)

MAX_RTL_FILE_SIZE_BYTES = (
    MAX_UPLOAD_SIZE_MB * 1024 * 1024
)


# ============================================================================
# WORKFLOW STATUS
# ============================================================================

STATUS_INITIALIZED = "initialized"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"
STATUS_STOPPED = "stopped"


# ============================================================================
# VERDICT CONSTANTS
# ============================================================================

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NEED_MORE = "NEED_MORE"


# ============================================================================
# FAILURE CATEGORIES
# ============================================================================

FAILURE_RTL = "rtl"
FAILURE_TESTBENCH = "testbench"
FAILURE_TEST = "test"
FAILURE_COMPILATION = "compilation"
FAILURE_SIMULATION = "simulation"
FAILURE_PROTOCOL = "protocol"
FAILURE_COVERAGE = "coverage"
FAILURE_UNKNOWN = "unknown"


# ============================================================================
# FILE EXTENSIONS
# ============================================================================

VERILOG_EXTENSIONS = {
    ".v",
    ".vh",
}

SYSTEMVERILOG_EXTENSIONS = {
    ".sv",
    ".svh",
}

RTL_EXTENSIONS = (
    VERILOG_EXTENSIONS
    | SYSTEMVERILOG_EXTENSIONS
)


# ============================================================================
# DIRECTORY INITIALIZATION
# ============================================================================

def ensure_directories() -> None:
    """
    Create runtime directories used by the application.

    Safe for Streamlit Cloud.
    """

    directories = [
        RUNTIME_DIR,
        RUNS_DIR,
        TEMP_DIR,
        LOG_DIR,
        REPORT_DIR,
    ]

    for directory in directories:
        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except Exception:
            # Never fail application import because a runtime directory
            # cannot be created.
            pass


# ============================================================================
# AGENT CONFIG HELPERS
# ============================================================================

def get_agent_token_limit(
    agent_name: str,
) -> int:
    """
    Return configured max output tokens for an agent.
    """

    key = str(
        agent_name
    ).strip().lower()

    return int(
        AGENT_TOKEN_LIMITS.get(
            key,
            DEFAULT_MAX_TOKENS,
        )
    )


def get_agent_temperature(
    agent_name: str,
) -> float:
    """
    Return configured temperature for an agent.
    """

    key = str(
        agent_name
    ).strip().lower()

    return float(
        AGENT_TEMPERATURES.get(
            key,
            DEFAULT_TEMPERATURE,
        )
    )


# ============================================================================
# EDA HELPERS
# ============================================================================

def tool_available(
    executable: str,
) -> bool:
    """
    Return True when an executable is available on PATH.
    """

    if not executable:
        return False

    try:
        return shutil.which(
            executable
        ) is not None
    except Exception:
        return False


def get_available_eda_tools() -> Dict[str, bool]:
    """
    Return availability of supported EDA tools.

    SymbiYosys is intentionally excluded.
    """

    return {
        "iverilog": tool_available(
            IVERILOG_EXECUTABLE
        ),
        "vvp": tool_available(
            VVP_EXECUTABLE
        ),
        "verilator": tool_available(
            VERILATOR_EXECUTABLE
        ),
        "yosys": tool_available(
            YOSYS_EXECUTABLE
        ),
    }


# ============================================================================
# SETTINGS SUMMARY
# ============================================================================

def get_settings_summary() -> Dict[str, Any]:
    """
    Return safe settings summary.

    API keys are never returned.
    """

    return {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "project_name": PROJECT_NAME,
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

        "verification_target": (
            VERIFICATION_TARGET
        ),

        "default_max_iterations": (
            DEFAULT_MAX_ITERATIONS
        ),

        "min_iterations": MIN_ITERATIONS,
        "max_iterations": MAX_ITERATIONS,

        "red_team_enabled": (
            RED_TEAM_ENABLED_BY_DEFAULT
        ),

        "mutation_enabled": (
            MUTATION_ENABLED_BY_DEFAULT
        ),

        "formal_enabled": (
            FORMAL_ENABLED_BY_DEFAULT
        ),

        "default_verilog_standard": (
            DEFAULT_VERILOG_STANDARD
        ),

        "default_top_module": (
            DEFAULT_TOP_MODULE
        ),

        "simulation_timeout": (
            SIMULATION_TIMEOUT_SECONDS
        ),

        "formal_timeout": (
            FORMAL_TIMEOUT_SECONDS
        ),

        "eda_tools": get_available_eda_tools(),

        "symbiyosys_enabled": False,
        "symbiyosys_required": False,
    }


# ============================================================================
# GLOBAL COMPATIBILITY ALIASES
# ============================================================================

APP_ENV = ENVIRONMENT

VERSION = APP_VERSION

GROQ_MODEL_NAME = GROQ_MODEL

MAX_TOKENS = LLM_MAX_TOKENS

TEMPERATURE = LLM_TEMPERATURE

COVERAGE = COVERAGE_TARGET

MUTATION_SCORE = MUTATION_TARGET

VERIFICATION_SCORE = VERIFICATION_SCORE_TARGET


# ============================================================================
# INITIALIZE SAFE RUNTIME DIRECTORIES
# ============================================================================

ensure_directories()


# ============================================================================
# PUBLIC EXPORTS
# ============================================================================

__all__ = [

    # ------------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------------

    "APP_NAME",
    "APP_VERSION",
    "PROJECT_NAME",
    "APP_DESCRIPTION",
    "ENVIRONMENT",
    "APP_ENV",
    "DEBUG",
    "VERSION",

    # ------------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------------

    "GROQ_API_KEY",
    "GROQ_MODEL",
    "GROQ_MODEL_NAME",
    "MODEL_NAME",
    "LLM_MODEL",
    "DEFAULT_MODEL",

    "LLM_TEMPERATURE",
    "DEFAULT_TEMPERATURE",
    "TEMPERATURE",

    "LLM_MAX_TOKENS",
    "DEFAULT_MAX_TOKENS",
    "MAX_TOKENS",

    # ------------------------------------------------------------------------
    # Agent limits
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Agent temperatures
    # ------------------------------------------------------------------------

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

    # ------------------------------------------------------------------------
    # Prompt/context limits
    # ------------------------------------------------------------------------

    "MAX_RTL_CHARS",
    "MAX_SPECIFICATION_CHARS",
    "MAX_TESTBENCH_CHARS",
    "MAX_SIMULATION_OUTPUT_CHARS",
    "MAX_FAILURE_OUTPUT_CHARS",
    "MAX_COVERAGE_OUTPUT_CHARS",
    "MAX_AGENT_CONTEXT_CHARS",

    # ------------------------------------------------------------------------
    # LLM-specific context limits
    # ------------------------------------------------------------------------

    "MAX_RTL_CHARS_FOR_LLM",
    "MAX_SPECIFICATION_CHARS_FOR_LLM",
    "MAX_TESTBENCH_CHARS_FOR_LLM",
    "MAX_SIMULATION_OUTPUT_CHARS_FOR_LLM",
    "MAX_FAILURE_OUTPUT_CHARS_FOR_LLM",
    "MAX_COVERAGE_OUTPUT_CHARS_FOR_LLM",
    "MAX_AGENT_CONTEXT_CHARS_FOR_LLM",

    # ------------------------------------------------------------------------
    # Context aliases
    # ------------------------------------------------------------------------

    "RTL_CHAR_LIMIT",
    "SPECIFICATION_CHAR_LIMIT",
    "TESTBENCH_CHAR_LIMIT",
    "SIMULATION_OUTPUT_CHAR_LIMIT",
    "AGENT_CONTEXT_CHAR_LIMIT",

    "RTL_LLM_CHAR_LIMIT",
    "SPECIFICATION_LLM_CHAR_LIMIT",
    "TESTBENCH_LLM_CHAR_LIMIT",
    "SIMULATION_OUTPUT_LLM_CHAR_LIMIT",
    "FAILURE_OUTPUT_LLM_CHAR_LIMIT",
    "COVERAGE_OUTPUT_LLM_CHAR_LIMIT",
    "AGENT_CONTEXT_LLM_CHAR_LIMIT",

    # ------------------------------------------------------------------------
    # EDA
    # ------------------------------------------------------------------------

    "IVERILOG_EXECUTABLE",
    "VVP_EXECUTABLE",
    "VERILATOR_EXECUTABLE",
    "YOSYS_EXECUTABLE",

    "IVERILOG",
    "VVP",
    "VERILATOR",
    "YOSYS",

    "SUPPORTED_EDA_TOOLS",

    # ------------------------------------------------------------------------
    # Formal
    # ------------------------------------------------------------------------

    "FORMAL_ENABLED_BY_DEFAULT",

    # Kept for compatibility only.
    "SYMBIYOSYS_EXECUTABLE",
    "SBY_EXECUTABLE",

    "UNSUPPORTED_OR_OPTIONAL_TOOLS",

    # ------------------------------------------------------------------------
    # Timeouts
    # ------------------------------------------------------------------------

    "SIMULATION_TIMEOUT_SECONDS",
    "COMPILE_TIMEOUT_SECONDS",
    "VERILATOR_TIMEOUT_SECONDS",
    "YOSYS_TIMEOUT_SECONDS",
    "FORMAL_TIMEOUT_SECONDS",

    "SIM_TIMEOUT",
    "FORMAL_TIMEOUT",

    # ------------------------------------------------------------------------
    # Verification targets
    # ------------------------------------------------------------------------

    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_SCORE_TARGET",

    # IMPORTANT compatibility name
    "VERIFICATION_TARGET",

    "TARGET_COVERAGE",
    "TARGET_MUTATION_SCORE",
    "TARGET_VERIFICATION_SCORE",

    "COVERAGE_THRESHOLD",
    "MUTATION_THRESHOLD",
    "VERIFICATION_THRESHOLD",

    "COVERAGE",
    "MUTATION_SCORE",
    "VERIFICATION_SCORE",

    # ------------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------------

    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",

    # ------------------------------------------------------------------------
    # Features
    # ------------------------------------------------------------------------

    "RED_TEAM_ENABLED_BY_DEFAULT",
    "MUTATION_ENABLED_BY_DEFAULT",

    # ------------------------------------------------------------------------
    # RTL
    # ------------------------------------------------------------------------

    "DEFAULT_VERILOG_STANDARD",
    "DEFAULT_TOP_MODULE",

    # ------------------------------------------------------------------------
    # Test defaults
    # ------------------------------------------------------------------------

    "DEFAULT_CLOCK_PERIOD_NS",
    "DEFAULT_RESET_CYCLES",
    "DEFAULT_TEST_TIMEOUT_NS",

    # ------------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------------

    "LOG_LEVEL",
    "ENABLE_AGENT_LOGGING",
    "ENABLE_AGENT_TRACE",

    # ------------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------------

    "DEFAULT_REPORT_FORMAT",
    "ENABLE_HTML_REPORT",

    # ------------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------------

    "MAX_UPLOAD_SIZE_MB",
    "MAX_RTL_FILE_SIZE_BYTES",

    # ------------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------------

    "STATUS_INITIALIZED",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_ERROR",
    "STATUS_STOPPED",

    # ------------------------------------------------------------------------
    # Verdicts
    # ------------------------------------------------------------------------

    "VERDICT_PASS",
    "VERDICT_FAIL",
    "VERDICT_NEED_MORE",

    # ------------------------------------------------------------------------
    # Failure categories
    # ------------------------------------------------------------------------

    "FAILURE_RTL",
    "FAILURE_TESTBENCH",
    "FAILURE_TEST",
    "FAILURE_COMPILATION",
    "FAILURE_SIMULATION",
    "FAILURE_PROTOCOL",
    "FAILURE_COVERAGE",
    "FAILURE_UNKNOWN",

    # ------------------------------------------------------------------------
    # File extensions
    # ------------------------------------------------------------------------

    "VERILOG_EXTENSIONS",
    "SYSTEMVERILOG_EXTENSIONS",
    "RTL_EXTENSIONS",

    # ------------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------------

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

    "RUNTIME_DIR",
    "RUNS_DIR",
    "TEMP_DIR",
    "LOG_DIR",
    "REPORT_DIR",

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    "ensure_directories",
    "get_agent_token_limit",
    "get_agent_temperature",
    "tool_available",
    "get_available_eda_tools",
    "get_settings_summary",
]


