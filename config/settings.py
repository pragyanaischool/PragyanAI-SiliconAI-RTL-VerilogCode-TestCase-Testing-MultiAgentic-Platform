"""
PragyanAI SiliconAI
Agentic RTL Verification Platform

Central application configuration.

Supports:
    - Streamlit / Streamlit Cloud
    - LangChain / LangGraph
    - Groq
    - Icarus Verilog
    - Verilator
    - Yosys

SymbiYosys is NOT required.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict


# =============================================================================
# PROJECT PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROJECT_ROOT = BASE_DIR

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


# =============================================================================
# LEGACY PATH COMPATIBILITY
# =============================================================================

PROJECT_ROOT = BASE_DIR

CONFIG_ROOT = CONFIG_DIR
AGENT_ROOT = AGENTS_DIR
AGENTS_ROOT = AGENTS_DIR
GRAPH_ROOT = GRAPH_DIR
EDA_ROOT = EDA_DIR
VERIFICATION_ROOT = VERIFICATION_DIR
LOGGING_ROOT = LOGGING_DIR
REPORTS_ROOT = REPORTS_DIR
PROMPTS_ROOT = PROMPTS_DIR
EXAMPLES_ROOT = EXAMPLES_DIR
TESTS_ROOT = TESTS_DIR
DOCS_ROOT = DOCS_DIR
ASSETS_ROOT = ASSETS_DIR

RUN_ROOT = RUNS_DIR
RUNS_ROOT = RUNS_DIR
TEMP_ROOT = TEMP_DIR
TMP_ROOT = TEMP_DIR
LOG_ROOT = LOG_DIR
REPORT_ROOT = REPORT_DIR


# =============================================================================
# APPLICATION
# =============================================================================

APP_NAME = "PragyanAI SiliconAI"

APP_VERSION = "1.0.0"

VERSION = APP_VERSION

PROJECT_NAME = (
    "PragyanAI SiliconAI - Agentic RTL Verification"
)

APP_DESCRIPTION = (
    "Agentic RTL Verification Platform for AI-assisted "
    "RTL analysis, verification planning, test generation, "
    "simulation, coverage, mutation testing, formal verification "
    "and RTL repair."
)

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    os.getenv("APP_ENV", "production"),
)

APP_ENV = ENVIRONMENT

DEBUG = (
    os.getenv("DEBUG", "false").lower()
    in {"1", "true", "yes", "on"}
)


# =============================================================================
# GROQ / LLM
# =============================================================================

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
GROQ_MODEL_NAME = GROQ_MODEL


# =============================================================================
# GLOBAL LLM SETTINGS
# =============================================================================

LLM_TEMPERATURE = float(
    os.getenv(
        "LLM_TEMPERATURE",
        "0.1",
    )
)

DEFAULT_TEMPERATURE = LLM_TEMPERATURE
TEMPERATURE = LLM_TEMPERATURE


LLM_MAX_TOKENS = int(
    os.getenv(
        "LLM_MAX_TOKENS",
        "1800",
    )
)

DEFAULT_MAX_TOKENS = LLM_MAX_TOKENS
MAX_TOKENS = LLM_MAX_TOKENS


# =============================================================================
# AGENT TOKEN LIMITS
# =============================================================================

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


# =============================================================================
# AGENT TOKEN COMPATIBILITY ALIASES
# =============================================================================
#
# Existing agent modules may use either:
#
#   RTL_ANALYZER_MAX_TOKENS
#   PLANNER_MAX_TOKENS
#   TEST_MAX_TOKENS
#   ...
#
# Keep all aliases mapped to the central configuration above.
# =============================================================================

RTL_ANALYZER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["rtl_analyzer"]
)

PLANNER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_planner"]
)

VERIFICATION_PLANNER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_planner"]
)

TEST_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["test_generator"]
)

TEST_GENERATOR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["test_generator"]
)

TESTBENCH_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["testbench_generator"]
)

TB_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["testbench_generator"]
)

TESTBENCH_GENERATOR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["testbench_generator"]
)

SIMULATION_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["simulator_agent"]
)

SIM_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["simulator_agent"]
)

SIMULATOR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["simulator_agent"]
)

SIMULATOR_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["simulator_agent"]
)

FAILURE_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["failure_analyzer"]
)

FAILURE_ANALYSIS_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["failure_analyzer"]
)

FAILURE_ANALYZER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["failure_analyzer"]
)

COVERAGE_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["coverage_agent"]
)

COVERAGE_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["coverage_agent"]
)

REDTEAM_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["red_team_agent"]
)

RED_TEAM_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["red_team_agent"]
)

RED_TEAM_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["red_team_agent"]
)

MUTATION_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["mutation_agent"]
)

MUTATION_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["mutation_agent"]
)

FORMAL_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["formal_agent"]
)

FORMAL_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["formal_agent"]
)

BUG_LOCALIZATION_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["bug_localization_agent"]
)

BUG_LOCALIZER_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["bug_localization_agent"]
)

RTL_REPAIR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["rtl_repair_agent"]
)

REPAIR_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["rtl_repair_agent"]
)

RTL_REPAIR_AGENT_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["rtl_repair_agent"]
)

JUDGE_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_judge"]
)

VERIFICATION_JUDGE_MAX_TOKENS = (
    AGENT_TOKEN_LIMITS["verification_judge"]
)


# =============================================================================
# AGENT TEMPERATURES
# =============================================================================

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


# =============================================================================
# AGENT TEMPERATURE COMPATIBILITY ALIASES
# =============================================================================

RTL_ANALYZER_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_analyzer"]
)

PLANNER_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_planner"]
)

VERIFICATION_PLANNER_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_planner"]
)

TEST_TEMPERATURE = (
    AGENT_TEMPERATURES["test_generator"]
)

TEST_GENERATOR_TEMPERATURE = (
    AGENT_TEMPERATURES["test_generator"]
)

TESTBENCH_TEMPERATURE = (
    AGENT_TEMPERATURES["testbench_generator"]
)

TB_TEMPERATURE = (
    AGENT_TEMPERATURES["testbench_generator"]
)

TESTBENCH_GENERATOR_TEMPERATURE = (
    AGENT_TEMPERATURES["testbench_generator"]
)

SIMULATION_TEMPERATURE = (
    AGENT_TEMPERATURES["simulator_agent"]
)

SIM_TEMPERATURE = (
    AGENT_TEMPERATURES["simulator_agent"]
)

SIMULATOR_TEMPERATURE = (
    AGENT_TEMPERATURES["simulator_agent"]
)

SIMULATOR_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["simulator_agent"]
)

FAILURE_TEMPERATURE = (
    AGENT_TEMPERATURES["failure_analyzer"]
)

FAILURE_ANALYSIS_TEMPERATURE = (
    AGENT_TEMPERATURES["failure_analyzer"]
)

FAILURE_ANALYZER_TEMPERATURE = (
    AGENT_TEMPERATURES["failure_analyzer"]
)

COVERAGE_TEMPERATURE = (
    AGENT_TEMPERATURES["coverage_agent"]
)

COVERAGE_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["coverage_agent"]
)

REDTEAM_TEMPERATURE = (
    AGENT_TEMPERATURES["red_team_agent"]
)

RED_TEAM_TEMPERATURE = (
    AGENT_TEMPERATURES["red_team_agent"]
)

RED_TEAM_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["red_team_agent"]
)

MUTATION_TEMPERATURE = (
    AGENT_TEMPERATURES["mutation_agent"]
)

MUTATION_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["mutation_agent"]
)

FORMAL_TEMPERATURE = (
    AGENT_TEMPERATURES["formal_agent"]
)

FORMAL_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["formal_agent"]
)

BUG_LOCALIZATION_TEMPERATURE = (
    AGENT_TEMPERATURES["bug_localization_agent"]
)

BUG_LOCALIZER_TEMPERATURE = (
    AGENT_TEMPERATURES["bug_localization_agent"]
)

REPAIR_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_repair_agent"]
)

RTL_REPAIR_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_repair_agent"]
)

RTL_REPAIR_AGENT_TEMPERATURE = (
    AGENT_TEMPERATURES["rtl_repair_agent"]
)

JUDGE_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_judge"]
)

VERIFICATION_JUDGE_TEMPERATURE = (
    AGENT_TEMPERATURES["verification_judge"]
)


# =============================================================================
# PROMPT / CONTEXT LIMITS
# =============================================================================

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


# =============================================================================
# LLM CONTEXT LIMIT COMPATIBILITY
# =============================================================================

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


# =============================================================================
# CONTEXT LEGACY ALIASES
# =============================================================================

RTL_CHAR_LIMIT = MAX_RTL_CHARS

SPECIFICATION_CHAR_LIMIT = MAX_SPECIFICATION_CHARS

TESTBENCH_CHAR_LIMIT = MAX_TESTBENCH_CHARS

SIMULATION_OUTPUT_CHAR_LIMIT = (
    MAX_SIMULATION_OUTPUT_CHARS
)

FAILURE_OUTPUT_CHAR_LIMIT = (
    MAX_FAILURE_OUTPUT_CHARS
)

COVERAGE_OUTPUT_CHAR_LIMIT = (
    MAX_COVERAGE_OUTPUT_CHARS
)

AGENT_CONTEXT_CHAR_LIMIT = (
    MAX_AGENT_CONTEXT_CHARS
)


# =============================================================================
# EDA TOOLS
# =============================================================================

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


# Compatibility aliases
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


# =============================================================================
# FORMAL VERIFICATION
# =============================================================================
#
# SymbiYosys has deliberately been removed from the required toolchain.
#
# Formal verification remains optional. The application should gracefully
# disable it if the available backend is not installed.
# =============================================================================

FORMAL_ENABLED_BY_DEFAULT = (
    os.getenv(
        "FORMAL_ENABLED_BY_DEFAULT",
        "false",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# Backwards compatibility only.
# These are deliberately None.
SYMBIYOSYS_EXECUTABLE = None
SBY_EXECUTABLE = None

UNSUPPORTED_OR_OPTIONAL_TOOLS = {
    "symbiyosys": False,
}


# =============================================================================
# TIMEOUTS
# =============================================================================

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


# Compatibility aliases
SIM_TIMEOUT = SIMULATION_TIMEOUT_SECONDS
FORMAL_TIMEOUT = FORMAL_TIMEOUT_SECONDS


# =============================================================================
# VERIFICATION TARGETS
# =============================================================================

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


# Critical compatibility alias
VERIFICATION_TARGET = VERIFICATION_SCORE_TARGET

# Additional aliases
TARGET_COVERAGE = COVERAGE_TARGET

TARGET_MUTATION_SCORE = MUTATION_TARGET

TARGET_VERIFICATION_SCORE = (
    VERIFICATION_SCORE_TARGET
)

COVERAGE_THRESHOLD = COVERAGE_TARGET

MUTATION_THRESHOLD = MUTATION_TARGET

VERIFICATION_THRESHOLD = (
    VERIFICATION_SCORE_TARGET
)


# =============================================================================
# ITERATION CONTROL
# =============================================================================

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


# =============================================================================
# FEATURE FLAGS
# =============================================================================

RED_TEAM_ENABLED_BY_DEFAULT = (
    os.getenv(
        "RED_TEAM_ENABLED_BY_DEFAULT",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)

MUTATION_ENABLED_BY_DEFAULT = (
    os.getenv(
        "MUTATION_ENABLED_BY_DEFAULT",
        "false",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# =============================================================================
# RTL DEFAULTS
# =============================================================================

DEFAULT_VERILOG_STANDARD = os.getenv(
    "DEFAULT_VERILOG_STANDARD",
    "2012",
)

DEFAULT_TOP_MODULE = os.getenv(
    "DEFAULT_TOP_MODULE",
    "dut",
)


# =============================================================================
# TESTING DEFAULTS
# =============================================================================

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


# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

ENABLE_AGENT_LOGGING = (
    os.getenv(
        "ENABLE_AGENT_LOGGING",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)

ENABLE_AGENT_TRACE = (
    os.getenv(
        "ENABLE_AGENT_TRACE",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# =============================================================================
# REPORTING
# =============================================================================

DEFAULT_REPORT_FORMAT = os.getenv(
    "DEFAULT_REPORT_FORMAT",
    "markdown",
)

ENABLE_HTML_REPORT = (
    os.getenv(
        "ENABLE_HTML_REPORT",
        "true",
    ).lower()
    in {"1", "true", "yes", "on"}
)


# =============================================================================
# SECURITY / RESOURCE LIMITS
# =============================================================================

MAX_UPLOAD_SIZE_MB = int(
    os.getenv(
        "MAX_UPLOAD_SIZE_MB",
        "5",
    )
)

MAX_RTL_FILE_SIZE_BYTES = (
    MAX_UPLOAD_SIZE_MB * 1024 * 1024
)


# =============================================================================
# WORKFLOW STATUS
# =============================================================================

STATUS_INITIALIZED = "initialized"

STATUS_RUNNING = "running"

STATUS_COMPLETED = "completed"

STATUS_FAILED = "failed"

STATUS_ERROR = "error"

STATUS_STOPPED = "stopped"


# =============================================================================
# VERDICTS
# =============================================================================

VERDICT_PASS = "PASS"

VERDICT_FAIL = "FAIL"

VERDICT_NEED_MORE = "NEED_MORE"


# =============================================================================
# FAILURE CATEGORIES
# =============================================================================

FAILURE_RTL = "rtl"

FAILURE_TESTBENCH = "testbench"

FAILURE_TEST = "test"

FAILURE_COMPILATION = "compilation"

FAILURE_SIMULATION = "simulation"

FAILURE_PROTOCOL = "protocol"

FAILURE_COVERAGE = "coverage"

FAILURE_UNKNOWN = "unknown"


# =============================================================================
# FILE EXTENSIONS
# =============================================================================

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


# =============================================================================
# DIRECTORY INITIALIZATION
# =============================================================================

def ensure_directories() -> None:
    """
    Safely create runtime directories.

    Failure to create a runtime directory should never prevent
    the Streamlit application from importing.
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
            # Streamlit Cloud or restricted environments may prevent
            # directory creation during import. Do not crash the app.
            pass


# =============================================================================
# AGENT HELPERS
# =============================================================================

def get_agent_token_limit(
    agent_name: str,
) -> int:
    """
    Return max output token count for an agent.
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
    Return temperature for an agent.
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


# =============================================================================
# EDA HELPERS
# =============================================================================

def tool_available(
    executable: str,
) -> bool:
    """
    Check whether an executable is available on PATH.
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


# =============================================================================
# SETTINGS SUMMARY
# =============================================================================

def get_settings_summary() -> Dict[str, Any]:
    """
    Return a safe configuration summary.

    The Groq API key is intentionally never returned.
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

        "coverage_target": COVERAGE_TARGET,
        "mutation_target": MUTATION_TARGET,
        "verification_target": VERIFICATION_TARGET,

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

        "eda_tools": (
            get_available_eda_tools()
        ),

        "symbiyosys_enabled": False,

        "symbiyosys_required": False,
    }


# =============================================================================
# INITIALIZE RUNTIME
# =============================================================================

ensure_directories()


# =============================================================================
# PUBLIC EXPORTS
# =============================================================================

__all__ = [

    # Application
    "APP_NAME",
    "APP_VERSION",
    "VERSION",
    "PROJECT_NAME",
    "APP_DESCRIPTION",
    "ENVIRONMENT",
    "APP_ENV",
    "DEBUG",

    # Paths
    "BASE_DIR",
    "PROJECT_ROOT",

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

    "CONFIG_ROOT",
    "AGENT_ROOT",
    "AGENTS_ROOT",
    "GRAPH_ROOT",
    "EDA_ROOT",
    "VERIFICATION_ROOT",
    "LOGGING_ROOT",
    "REPORTS_ROOT",
    "PROMPTS_ROOT",
    "EXAMPLES_ROOT",
    "TESTS_ROOT",
    "DOCS_ROOT",
    "ASSETS_ROOT",

    "RUN_ROOT",
    "RUNS_ROOT",
    "TEMP_ROOT",
    "TMP_ROOT",
    "LOG_ROOT",
    "REPORT_ROOT",

    # LLM
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

    # Agent token dictionaries
    "AGENT_TOKEN_LIMITS",
    "AGENT_MAX_TOKENS",
    "TOKEN_LIMITS",

    # Agent token aliases
    "RTL_ANALYZER_MAX_TOKENS",
    "PLANNER_MAX_TOKENS",
    "VERIFICATION_PLANNER_MAX_TOKENS",
    "TEST_MAX_TOKENS",
    "TEST_GENERATOR_MAX_TOKENS",
    "TESTBENCH_MAX_TOKENS",
    "TB_MAX_TOKENS",
    "TESTBENCH_GENERATOR_MAX_TOKENS",
    "SIMULATION_MAX_TOKENS",
    "SIM_MAX_TOKENS",
    "SIMULATOR_MAX_TOKENS",
    "SIMULATOR_AGENT_MAX_TOKENS",
    "FAILURE_MAX_TOKENS",
    "FAILURE_ANALYSIS_MAX_TOKENS",
    "FAILURE_ANALYZER_MAX_TOKENS",
    "COVERAGE_MAX_TOKENS",
    "COVERAGE_AGENT_MAX_TOKENS",
    "REDTEAM_MAX_TOKENS",
    "RED_TEAM_MAX_TOKENS",
    "RED_TEAM_AGENT_MAX_TOKENS",
    "MUTATION_MAX_TOKENS",
    "MUTATION_AGENT_MAX_TOKENS",
    "FORMAL_MAX_TOKENS",
    "FORMAL_AGENT_MAX_TOKENS",
    "BUG_LOCALIZATION_MAX_TOKENS",
    "BUG_LOCALIZER_MAX_TOKENS",
    "RTL_REPAIR_MAX_TOKENS",
    "REPAIR_MAX_TOKENS",
    "RTL_REPAIR_AGENT_MAX_TOKENS",
    "JUDGE_MAX_TOKENS",
    "VERIFICATION_JUDGE_MAX_TOKENS",

    # Agent temperatures
    "AGENT_TEMPERATURES",
    "RTL_ANALYZER_TEMPERATURE",
    "PLANNER_TEMPERATURE",
    "VERIFICATION_PLANNER_TEMPERATURE",
    "TEST_TEMPERATURE",
    "TEST_GENERATOR_TEMPERATURE",
    "TESTBENCH_TEMPERATURE",
    "TB_TEMPERATURE",
    "TESTBENCH_GENERATOR_TEMPERATURE",
    "SIMULATION_TEMPERATURE",
    "SIM_TEMPERATURE",
    "SIMULATOR_TEMPERATURE",
    "SIMULATOR_AGENT_TEMPERATURE",
    "FAILURE_TEMPERATURE",
    "FAILURE_ANALYSIS_TEMPERATURE",
    "FAILURE_ANALYZER_TEMPERATURE",
    "COVERAGE_TEMPERATURE",
    "COVERAGE_AGENT_TEMPERATURE",
    "REDTEAM_TEMPERATURE",
    "RED_TEAM_TEMPERATURE",
    "RED_TEAM_AGENT_TEMPERATURE",
    "MUTATION_TEMPERATURE",
    "MUTATION_AGENT_TEMPERATURE",
    "FORMAL_TEMPERATURE",
    "FORMAL_AGENT_TEMPERATURE",
    "BUG_LOCALIZATION_TEMPERATURE",
    "BUG_LOCALIZER_TEMPERATURE",
    "REPAIR_TEMPERATURE",
    "RTL_REPAIR_TEMPERATURE",
    "RTL_REPAIR_AGENT_TEMPERATURE",
    "JUDGE_TEMPERATURE",
    "VERIFICATION_JUDGE_TEMPERATURE",

    # Context
    "MAX_RTL_CHARS",
    "MAX_SPECIFICATION_CHARS",
    "MAX_TESTBENCH_CHARS",
    "MAX_SIMULATION_OUTPUT_CHARS",
    "MAX_FAILURE_OUTPUT_CHARS",
    "MAX_COVERAGE_OUTPUT_CHARS",
    "MAX_AGENT_CONTEXT_CHARS",

    # LLM context
    "MAX_RTL_CHARS_FOR_LLM",
    "MAX_SPECIFICATION_CHARS_FOR_LLM",
    "MAX_TESTBENCH_CHARS_FOR_LLM",
    "MAX_SIMULATION_OUTPUT_CHARS_FOR_LLM",
    "MAX_FAILURE_OUTPUT_CHARS_FOR_LLM",
    "MAX_COVERAGE_OUTPUT_CHARS_FOR_LLM",
    "MAX_AGENT_CONTEXT_CHARS_FOR_LLM",

    # Context aliases
    "RTL_CHAR_LIMIT",
    "SPECIFICATION_CHAR_LIMIT",
    "TESTBENCH_CHAR_LIMIT",
    "SIMULATION_OUTPUT_CHAR_LIMIT",
    "FAILURE_OUTPUT_CHAR_LIMIT",
    "COVERAGE_OUTPUT_CHAR_LIMIT",
    "AGENT_CONTEXT_CHAR_LIMIT",

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
    "SYMBIYOSYS_EXECUTABLE",
    "SBY_EXECUTABLE",
    "UNSUPPORTED_OR_OPTIONAL_TOOLS",

    # Timeouts
    "SIMULATION_TIMEOUT_SECONDS",
    "COMPILE_TIMEOUT_SECONDS",
    "VERILATOR_TIMEOUT_SECONDS",
    "YOSYS_TIMEOUT_SECONDS",
    "FORMAL_TIMEOUT_SECONDS",

    "SIM_TIMEOUT",
    "FORMAL_TIMEOUT",

    # Verification targets
    "COVERAGE_TARGET",
    "MUTATION_TARGET",
    "VERIFICATION_SCORE_TARGET",
    "VERIFICATION_TARGET",

    "TARGET_COVERAGE",
    "TARGET_MUTATION_SCORE",
    "TARGET_VERIFICATION_SCORE",

    "COVERAGE_THRESHOLD",
    "MUTATION_THRESHOLD",
    "VERIFICATION_THRESHOLD",

    # Iterations
    "DEFAULT_MAX_ITERATIONS",
    "MIN_ITERATIONS",
    "MAX_ITERATIONS",

    # Feature flags
    "RED_TEAM_ENABLED_BY_DEFAULT",
    "MUTATION_ENABLED_BY_DEFAULT",

    # RTL
    "DEFAULT_VERILOG_STANDARD",
    "DEFAULT_TOP_MODULE",

    # Testing
    "DEFAULT_CLOCK_PERIOD_NS",
    "DEFAULT_RESET_CYCLES",
    "DEFAULT_TEST_TIMEOUT_NS",

    # Logging
    "LOG_LEVEL",
    "ENABLE_AGENT_LOGGING",
    "ENABLE_AGENT_TRACE",

    # Reporting
    "DEFAULT_REPORT_FORMAT",
    "ENABLE_HTML_REPORT",

    # Security
    "MAX_UPLOAD_SIZE_MB",
    "MAX_RTL_FILE_SIZE_BYTES",

    # Status
    "STATUS_INITIALIZED",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_ERROR",
    "STATUS_STOPPED",

    # Verdict
    "VERDICT_PASS",
    "VERDICT_FAIL",
    "VERDICT_NEED_MORE",

    # Failure categories
    "FAILURE_RTL",
    "FAILURE_TESTBENCH",
    "FAILURE_TEST",
    "FAILURE_COMPILATION",
    "FAILURE_SIMULATION",
    "FAILURE_PROTOCOL",
    "FAILURE_COVERAGE",
    "FAILURE_UNKNOWN",

    # Extensions
    "VERILOG_EXTENSIONS",
    "SYSTEMVERILOG_EXTENSIONS",
    "RTL_EXTENSIONS",

    # Helpers
    "ensure_directories",
    "get_agent_token_limit",
    "get_agent_temperature",
    "tool_available",
    "get_available_eda_tools",
    "get_settings_summary",
]

