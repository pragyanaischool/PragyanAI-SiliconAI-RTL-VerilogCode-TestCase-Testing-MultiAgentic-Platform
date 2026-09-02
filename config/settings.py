"""
PragyanAI SiliconAI
Application Settings

Centralized configuration for:
- Streamlit
- Groq / LangChain
- Verification limits
- EDA tools
- Logging
- Agent execution
"""

import os
from pathlib import Path


# ============================================================
# APPLICATION
# ============================================================

APP_NAME = os.getenv(
    "PRAGYANAI_APP_NAME",
    "PragyanAI SiliconAI - Autonomous RTL Verification"
)

APP_VERSION = os.getenv(
    "PRAGYANAI_APP_VERSION",
    "1.0.0"
)

APP_DESCRIPTION = (
    "AI-powered autonomous RTL verification, "
    "test generation, simulation, coverage analysis "
    "and verification evidence platform."
)


# ============================================================
# DIRECTORY STRUCTURE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = BASE_DIR / "config"
AGENTS_DIR = BASE_DIR / "agents"
GRAPH_DIR = BASE_DIR / "graph"
EDA_DIR = BASE_DIR / "eda"
VERIFICATION_DIR = BASE_DIR / "verification"
LOGGING_DIR = BASE_DIR / "logging"
REPORTS_DIR = BASE_DIR / "reports"
UI_DIR = BASE_DIR / "ui"
PROMPTS_DIR = BASE_DIR / "prompts"
EXAMPLES_DIR = BASE_DIR / "examples"

LOG_ROOT = BASE_DIR / "verification_logs"
RUNS_DIR = LOG_ROOT / "runs"


# Create runtime directories if they do not exist.
for directory in [
    LOG_ROOT,
    RUNS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# GROQ / LLM CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Current recommended model for the platform.
DEFAULT_MODEL = os.getenv(
    "PRAGYANAI_MODEL",
    "openai/gpt-oss-120b"
)

# Conservative temperature because RTL verification
# requires deterministic and precise reasoning.
DEFAULT_TEMPERATURE = float(
    os.getenv("PRAGYANAI_TEMPERATURE", "0.1")
)

# Important for Groq free-tier TPM constraints.
# Keep outputs compact.
DEFAULT_MAX_TOKENS = int(
    os.getenv("PRAGYANAI_MAX_TOKENS", "2500")
)

# Maximum number of autonomous repair/verification iterations.
DEFAULT_MAX_ITERATIONS = int(
    os.getenv("PRAGYANAI_MAX_ITERATIONS", "5")
)


# ============================================================
# AGENT-SPECIFIC TOKEN LIMITS
# ============================================================

RTL_ANALYZER_MAX_TOKENS = int(
    os.getenv("RTL_ANALYZER_MAX_TOKENS", "1800")
)

PLANNER_MAX_TOKENS = int(
    os.getenv("PLANNER_MAX_TOKENS", "1800")
)

TEST_GENERATOR_MAX_TOKENS = int(
    os.getenv("TEST_GENERATOR_MAX_TOKENS", "2200")
)

TESTBENCH_GENERATOR_MAX_TOKENS = int(
    os.getenv("TESTBENCH_GENERATOR_MAX_TOKENS", "2500")
)

FAILURE_ANALYZER_MAX_TOKENS = int(
    os.getenv("FAILURE_ANALYZER_MAX_TOKENS", "1800")
)

COVERAGE_AGENT_MAX_TOKENS = int(
    os.getenv("COVERAGE_AGENT_MAX_TOKENS", "1800")
)

RED_TEAM_MAX_TOKENS = int(
    os.getenv("RED_TEAM_MAX_TOKENS", "1800")
)

MUTATION_AGENT_MAX_TOKENS = int(
    os.getenv("MUTATION_AGENT_MAX_TOKENS", "1800")
)

FORMAL_AGENT_MAX_TOKENS = int(
    os.getenv("FORMAL_AGENT_MAX_TOKENS", "1800")
)

BUG_LOCALIZATION_MAX_TOKENS = int(
    os.getenv("BUG_LOCALIZATION_MAX_TOKENS", "1800")
)

RTL_REPAIR_MAX_TOKENS = int(
    os.getenv("RTL_REPAIR_MAX_TOKENS", "3000")
)

JUDGE_MAX_TOKENS = int(
    os.getenv("JUDGE_MAX_TOKENS", "1800")
)


# ============================================================
# VERIFICATION CONFIGURATION
# ============================================================

VERIFICATION_TARGET = float(
    os.getenv("VERIFICATION_TARGET", "95.0")
)

MUTATION_TARGET = float(
    os.getenv("MUTATION_TARGET", "80.0")
)

ASSERTION_TARGET = float(
    os.getenv("ASSERTION_TARGET", "80.0")
)

COVERAGE_TARGET = float(
    os.getenv("COVERAGE_TARGET", "95.0")
)


# ============================================================
# TEST GENERATION
# ============================================================

MAX_TEST_SCENARIOS = int(
    os.getenv("MAX_TEST_SCENARIOS", "10")
)

MAX_TESTBENCH_LINES = int(
    os.getenv("MAX_TESTBENCH_LINES", "500")
)

MAX_RTL_CHARS_FOR_LLM = int(
    os.getenv("MAX_RTL_CHARS_FOR_LLM", "30000")
)

MAX_LOG_CHARS_FOR_LLM = int(
    os.getenv("MAX_LOG_CHARS_FOR_LLM", "5000")
)

MAX_ERROR_CHARS_FOR_LLM = int(
    os.getenv("MAX_ERROR_CHARS_FOR_LLM", "4000")
)


# ============================================================
# ITERATION CONTROL
# ============================================================

MAX_REPAIR_ATTEMPTS = int(
    os.getenv("MAX_REPAIR_ATTEMPTS", "3")
)

MAX_COVERAGE_ITERATIONS = int(
    os.getenv("MAX_COVERAGE_ITERATIONS", "5")
)

STOP_ON_COMPILE_ERROR = os.getenv(
    "STOP_ON_COMPILE_ERROR",
    "false"
).lower() == "true"


# ============================================================
# EDA TOOLS
# ============================================================

IVERILOG_EXECUTABLE = os.getenv(
    "IVERILOG_EXECUTABLE",
    "iverilog"
)

VVP_EXECUTABLE = os.getenv(
    "VVP_EXECUTABLE",
    "vvp"
)

VERILATOR_EXECUTABLE = os.getenv(
    "VERILATOR_EXECUTABLE",
    "verilator"
)

YOSYS_EXECUTABLE = os.getenv(
    "YOSYS_EXECUTABLE",
    "yosys"
)

SBY_EXECUTABLE = os.getenv(
    "SBY_EXECUTABLE",
    "sby"
)


# ============================================================
# EDA TIMEOUTS
# ============================================================

IVERILOG_TIMEOUT = int(
    os.getenv("IVERILOG_TIMEOUT", "30")
)

VERILATOR_TIMEOUT = int(
    os.getenv("VERILATOR_TIMEOUT", "60")
)

YOSYS_TIMEOUT = int(
    os.getenv("YOSYS_TIMEOUT", "60")
)

FORMAL_TIMEOUT = int(
    os.getenv("FORMAL_TIMEOUT", "120")
)


# ============================================================
# FILE EXTENSIONS
# ============================================================

RTL_EXTENSIONS = [
    ".v",
    ".sv",
    ".vh",
    ".svh",
]

TESTBENCH_EXTENSIONS = [
    ".v",
    ".sv",
]

WAVEFORM_EXTENSIONS = [
    ".vcd",
    ".fst",
    ".wlf",
]


# ============================================================
# STATUS VALUES
# ============================================================

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_PASSED = "PASSED"
STATUS_FAILED = "FAILED"
STATUS_BLOCKED = "BLOCKED"
STATUS_COMPLETED = "COMPLETED"
STATUS_ERROR = "ERROR"
STATUS_SKIPPED = "SKIPPED"


# ============================================================
# AGENT NAMES
# ============================================================

AGENT_RTL_ANALYZER = "RTL Analyzer"

AGENT_VERIFICATION_PLANNER = "Verification Planner"

AGENT_TEST_GENERATOR = "Test Generator"

AGENT_TESTBENCH_GENERATOR = "Testbench Generator"

AGENT_SIMULATOR = "Simulation Agent"

AGENT_FAILURE_ANALYZER = "Failure Analyzer"

AGENT_COVERAGE = "Coverage Agent"

AGENT_RED_TEAM = "Red Team Agent"

AGENT_MUTATION = "Mutation Agent"

AGENT_FORMAL = "Formal Verification Agent"

AGENT_BUG_LOCALIZATION = "Bug Localization Agent"

AGENT_RTL_REPAIR = "RTL Repair Agent"

AGENT_VERIFICATION_JUDGE = "Verification Judge"


# ============================================================
# LOGGING
# ============================================================

ENABLE_AGENT_LOGGING = os.getenv(
    "ENABLE_AGENT_LOGGING",
    "true"
).lower() == "true"

ENABLE_SIMULATION_LOGGING = os.getenv(
    "ENABLE_SIMULATION_LOGGING",
    "true"
).lower() == "true"

ENABLE_WAVEFORMS = os.getenv(
    "ENABLE_WAVEFORMS",
    "false"
).lower() == "true"

SAVE_FULL_LLM_OUTPUT = os.getenv(
    "SAVE_FULL_LLM_OUTPUT",
    "true"
).lower() == "true"


# ============================================================
# STREAMLIT
# ============================================================

PAGE_TITLE = os.getenv(
    "PRAGYANAI_PAGE_TITLE",
    "PragyanAI SiliconAI - Autonomous RTL Verification"
)

PAGE_ICON = os.getenv(
    "PRAGYANAI_PAGE_ICON",
    "🔬"
)

LAYOUT = os.getenv(
    "PRAGYANAI_LAYOUT",
    "wide"
)


# ============================================================
# FEATURE FLAGS
# ============================================================

ENABLE_RED_TEAM = os.getenv(
    "ENABLE_RED_TEAM",
    "true"
).lower() == "true"

ENABLE_MUTATION = os.getenv(
    "ENABLE_MUTATION",
    "true"
).lower() == "true"

ENABLE_FORMAL = os.getenv(
    "ENABLE_FORMAL",
    "true"
).lower() == "true"

ENABLE_RTL_REPAIR = os.getenv(
    "ENABLE_RTL_REPAIR",
    "true"
).lower() == "true"

ENABLE_VERIFICATION_JUDGE = os.getenv(
    "ENABLE_VERIFICATION_JUDGE",
    "true"
).lower() == "true"


# ============================================================
# MODEL FALLBACK
# ============================================================

FALLBACK_MODEL = os.getenv(
    "PRAGYANAI_FALLBACK_MODEL",
    "openai/gpt-oss-20b"
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_setting(name: str, default=None):
    """
    Safely retrieve an environment setting.
    """
    return os.getenv(name, default)


def ensure_runtime_directories():
    """
    Ensure all runtime directories exist.
    """
    for directory in [
        LOG_ROOT,
        RUNS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    return True


def get_model_config() -> dict:
    """
    Return the primary LLM configuration.
    """
    return {
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
    }


def get_eda_config() -> dict:
    """
    Return EDA executable configuration.
    """
    return {
        "iverilog": IVERILOG_EXECUTABLE,
        "vvp": VVP_EXECUTABLE,
        "verilator": VERILATOR_EXECUTABLE,
        "yosys": YOSYS_EXECUTABLE,
        "sby": SBY_EXECUTABLE,
    }


def is_groq_configured() -> bool:
    """
    Return True when a Groq API key is configured.
    """
    return bool(GROQ_API_KEY.strip())
