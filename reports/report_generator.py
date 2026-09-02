"""
PragyanAI SiliconAI
RTL Verification Agentic Platform

Central report-generation utilities.

Responsibilities:
- Build normalized verification summaries
- Calculate verification score
- Collect test/coverage/agent statistics
- Generate report data consumed by Markdown/HTML renderers
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_status(status: Any) -> str:
    """Normalize status strings."""
    if status is None:
        return "UNKNOWN"

    value = str(status).strip().upper()

    aliases = {
        "PASS": "PASSED",
        "SUCCESS": "PASSED",
        "OK": "PASSED",
        "FAIL": "FAILED",
        "ERROR": "FAILED",
        "RUNNING": "RUNNING",
        "ACTIVE": "RUNNING",
        "DONE": "COMPLETED",
    }

    return aliases.get(value, value)


def _read_json(path: Path, default: Any = None) -> Any:
    """Read JSON safely."""
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ---------------------------------------------------------------------
# Test normalization
# ---------------------------------------------------------------------

def normalize_test(test: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """
    Normalize a test record into a common schema.
    """

    test_id = (
        test.get("test_id")
        or test.get("id")
        or test.get("name")
        or f"TC{index + 1:03d}"
    )

    status = _normalize_status(
        test.get("status")
        or test.get("result")
        or test.get("outcome")
    )

    return {
        "test_id": str(test_id),
        "description": str(
            test.get("description")
            or test.get("test_description")
            or test.get("name")
            or ""
        ),
        "status": status,
        "inputs": test.get("inputs", ""),
        "expected": test.get("expected", ""),
        "actual": test.get("actual", ""),
        "error_message": test.get(
            "error_message",
            test.get("error", "")
        ),
        "rtl_version": test.get("rtl_version", ""),
        "iteration": _safe_int(test.get("iteration"), 0),
        "agent": test.get("agent", "Testbench Generator"),
        "duration_seconds": _safe_float(
            test.get("duration_seconds"),
            0.0,
        ),
        "test_code_file": test.get("test_code_file", ""),
        "simulation_log": test.get("simulation_log", ""),
        "timestamp": test.get("timestamp", ""),
    }


# ---------------------------------------------------------------------
# Coverage normalization
# ---------------------------------------------------------------------

def normalize_coverage(
    coverage: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Normalize coverage information.

    Supported:
    line
    branch
    toggle
    fsm
    functional
    assertion
    mutation
    overall
    """

    coverage = coverage or {}

    normalized = {
        "line": _safe_float(
            coverage.get("line", coverage.get("line_coverage"))
        ),
        "branch": _safe_float(
            coverage.get("branch", coverage.get("branch_coverage"))
        ),
        "toggle": _safe_float(
            coverage.get("toggle", coverage.get("toggle_coverage"))
        ),
        "fsm": _safe_float(
            coverage.get("fsm", coverage.get("fsm_coverage"))
        ),
        "functional": _safe_float(
            coverage.get(
                "functional",
                coverage.get("functional_coverage"),
            )
        ),
        "assertion": _safe_float(
            coverage.get(
                "assertion",
                coverage.get("assertion_coverage"),
            )
        ),
        "mutation": _safe_float(
            coverage.get(
                "mutation",
                coverage.get("mutation_score"),
            )
        ),
        "overall": _safe_float(
            coverage.get("overall"),
            -1.0,
        ),
        "gaps": coverage.get("gaps", []) or [],
        "recommended_tests": coverage.get(
            "recommended_tests",
            [],
        ) or [],
    }

    # If no explicit overall coverage exists, calculate a proxy.
    if normalized["overall"] < 0:
        values = [
            normalized["line"],
            normalized["branch"],
            normalized["toggle"],
            normalized["fsm"],
            normalized["functional"],
            normalized["assertion"],
        ]

        valid = [v for v in values if v > 0]

        if valid:
            normalized["overall"] = sum(valid) / len(valid)
            normalized["overall_proxy"] = True
        else:
            normalized["overall"] = 0.0
            normalized["overall_proxy"] = True
    else:
        normalized["overall_proxy"] = False

    return normalized


# ---------------------------------------------------------------------
# Agent normalization
# ---------------------------------------------------------------------

def normalize_agent(agent: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an agent execution record."""

    return {
        "agent": str(
            agent.get("agent")
            or agent.get("name")
            or "Unknown Agent"
        ),
        "status": _normalize_status(
            agent.get("status", "UNKNOWN")
        ),
        "timestamp": agent.get("timestamp", ""),
        "message": agent.get(
            "message",
            agent.get("output", ""),
        ),
        "decision": agent.get("decision", ""),
        "duration_seconds": _safe_float(
            agent.get("duration_seconds"),
            0.0,
        ),
        "iteration": _safe_int(
            agent.get("iteration"),
            0,
        ),
    }


# ---------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------

def calculate_verification_score(
    tests: List[Dict[str, Any]],
    coverage: Dict[str, Any],
    status: str = "",
) -> float:
    """
    Calculate an overall verification score.

    Score components:

    35% - test pass rate
    35% - coverage
    15% - mutation score
    15% - execution/status quality

    This is a platform-level heuristic score, not an industry
    certification metric.
    """

    total = len(tests)

    if total:
        passed = sum(
            1
            for test in tests
            if _normalize_status(test.get("status"))
            == "PASSED"
        )

        pass_rate = (passed / total) * 100.0
    else:
        pass_rate = 0.0

    overall_coverage = _safe_float(
        coverage.get("overall"),
        0.0,
    )

    mutation_score = _safe_float(
        coverage.get("mutation"),
        0.0,
    )

    status_normalized = _normalize_status(status)

    if status_normalized in {"VERIFIED", "PASSED", "COMPLETED"}:
        execution_quality = 100.0
    elif status_normalized in {"RUNNING", "ACTIVE"}:
        execution_quality = 70.0
    elif status_normalized in {"FAILED", "ERROR"}:
        execution_quality = 30.0
    else:
        execution_quality = 50.0

    score = (
        pass_rate * 0.35
        + overall_coverage * 0.35
        + mutation_score * 0.15
        + execution_quality * 0.15
    )

    return round(max(0.0, min(score, 100.0)), 2)


# ---------------------------------------------------------------------
# Run loader
# ---------------------------------------------------------------------

def load_run_data(run_dir: str | Path) -> Dict[str, Any]:
    """
    Load verification information from a run directory.
    """

    run_dir = Path(run_dir)

    data: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "metadata": {},
        "specification": "",
        "rtl_code": "",
        "testbench": "",
        "tests": [],
        "coverage": {},
        "agent_trace": [],
        "summary": {},
    }

    # -------------------------------------------------------------
    # run.json
    # -------------------------------------------------------------

    run_json = _read_json(
        run_dir / "run.json",
        {},
    )

    if isinstance(run_json, dict):
        data["metadata"] = run_json

        data["specification"] = (
            run_json.get("specification")
            or run_json.get("prompt")
            or ""
        )

        data["rtl_code"] = (
            run_json.get("rtl_code")
            or ""
        )

        data["testbench"] = (
            run_json.get("testbench")
            or run_json.get("test_code")
            or ""
        )

        if isinstance(run_json.get("tests"), list):
            data["tests"] = run_json["tests"]

        if isinstance(run_json.get("coverage"), dict):
            data["coverage"] = run_json["coverage"]

        if isinstance(run_json.get("agent_trace"), list):
            data["agent_trace"] = run_json["agent_trace"]

        elif isinstance(run_json.get("agent_log"), list):
            data["agent_trace"] = run_json["agent_log"]

    # -------------------------------------------------------------
    # Specification
    # -------------------------------------------------------------

    specification_file = run_dir / "specification.txt"

    if not data["specification"] and specification_file.exists():
        try:
            data["specification"] = specification_file.read_text(
                encoding="utf-8"
            )
        except Exception:
            pass

    # -------------------------------------------------------------
    # RTL
    # -------------------------------------------------------------

    if not data["rtl_code"]:
        rtl_dir = run_dir / "rtl"

        if rtl_dir.exists():
            rtl_files = sorted(rtl_dir.glob("*.v"))

            if rtl_files:
                try:
                    data["rtl_code"] = rtl_files[-1].read_text(
                        encoding="utf-8"
                    )
                except Exception:
                    pass

    # -------------------------------------------------------------
    # Testbench
    # -------------------------------------------------------------

    if not data["testbench"]:
        candidates = [
            run_dir / "testbench.v",
            run_dir / "test_bench.v",
        ]

        for candidate in candidates:
            if candidate.exists():
                try:
                    data["testbench"] = candidate.read_text(
                        encoding="utf-8"
                    )
                    break
                except Exception:
                    pass

    # -------------------------------------------------------------
    # Coverage
    # -------------------------------------------------------------

    coverage_file = (
        run_dir
        / "coverage"
        / "coverage.json"
    )

    if not data["coverage"] and coverage_file.exists():
        data["coverage"] = _read_json(
            coverage_file,
            {},
        )

    # -------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------

    test_results_file = (
        run_dir
        / "reports"
        / "test_results.json"
    )

    if not data["tests"] and test_results_file.exists():
        loaded_tests = _read_json(
            test_results_file,
            [],
        )

        if isinstance(loaded_tests, list):
            data["tests"] = loaded_tests

    # -------------------------------------------------------------
    # Agent trace
    # -------------------------------------------------------------

    agent_file = (
        run_dir
        / "agents"
        / "agent_trace.json"
    )

    if not data["agent_trace"] and agent_file.exists():
        loaded_agents = _read_json(
            agent_file,
            [],
        )

        if isinstance(loaded_agents, list):
            data["agent_trace"] = loaded_agents

    return data


# ---------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------

def build_report_data(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Build a complete normalized report model.

    Priority:
        state values
        ↓
        run directory values
        ↓
        defaults
    """

    state = state or {}

    disk_data: Dict[str, Any] = {}

    if run_dir:
        disk_data = load_run_data(run_dir)

    # -------------------------------------------------------------
    # Merge primary data
    # -------------------------------------------------------------

    specification = (
        state.get("specification")
        or state.get("prompt")
        or disk_data.get("specification")
        or ""
    )

    rtl_code = (
        state.get("rtl_code")
        or disk_data.get("rtl_code")
        or ""
    )

    testbench = (
        state.get("testbench")
        or state.get("test_code")
        or disk_data.get("testbench")
        or ""
    )

    raw_tests = (
        state.get("tests")
        or disk_data.get("tests")
        or []
    )

    tests = [
        normalize_test(test, index)
        for index, test in enumerate(raw_tests)
        if isinstance(test, dict)
    ]

    coverage = normalize_coverage(
        state.get("coverage")
        or disk_data.get("coverage")
        or {}
    )

    raw_agents = (
        state.get("agent_trace")
        or state.get("agent_log")
        or disk_data.get("agent_trace")
        or []
    )

    agents = [
        normalize_agent(agent)
        for agent in raw_agents
        if isinstance(agent, dict)
    ]

    # -------------------------------------------------------------
    # Test statistics
    # -------------------------------------------------------------

    total_tests = len(tests)

    passed_tests = sum(
        1
        for test in tests
        if test["status"] == "PASSED"
    )

    failed_tests = sum(
        1
        for test in tests
        if test["status"] == "FAILED"
    )

    skipped_tests = sum(
        1
        for test in tests
        if test["status"] in {"SKIPPED", "UNKNOWN"}
    )

    pass_rate = (
        (passed_tests / total_tests) * 100
        if total_tests
        else 0.0
    )

    status = _normalize_status(
        state.get("status")
        or disk_data.get("metadata", {}).get("status")
        or "UNKNOWN"
    )

    score = state.get("verification_score")

    if score is None:
        score = calculate_verification_score(
            tests,
            coverage,
            status,
        )

    # -------------------------------------------------------------
    # Failed tests
    # -------------------------------------------------------------

    failed_test_details = [
        test
        for test in tests
        if test["status"] == "FAILED"
    ]

    # -------------------------------------------------------------
    # Coverage gaps
    # -------------------------------------------------------------

    gaps = coverage.get("gaps", [])

    if not isinstance(gaps, list):
        gaps = []

    # -------------------------------------------------------------
    # Agent statistics
    # -------------------------------------------------------------

    completed_agents = sum(
        1
        for agent in agents
        if agent["status"] == "COMPLETED"
        or agent["status"] == "PASSED"
    )

    failed_agents = sum(
        1
        for agent in agents
        if agent["status"] == "FAILED"
    )

    # -------------------------------------------------------------
    # RTL metadata
    # -------------------------------------------------------------

    rtl_version = (
        state.get("rtl_version")
        or disk_data.get("metadata", {}).get(
            "rtl_version"
        )
        or "v1"
    )

    iteration = _safe_int(
        state.get("iteration")
        or disk_data.get("metadata", {}).get(
            "iteration"
        ),
        0,
    )

    # -------------------------------------------------------------
    # Final report object
    # -------------------------------------------------------------

    report = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "run_dir": str(run_dir) if run_dir else "",
            "platform": (
                "PragyanAI SiliconAI "
                "Autonomous RTL Verification"
            ),
            "report_version": "1.0",
        },

        "overview": {
            "status": status,
            "verification_score": round(
                _safe_float(score),
                2,
            ),
            "rtl_version": rtl_version,
            "iteration": iteration,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "pass_rate": round(pass_rate, 2),
            "coverage": round(
                coverage["overall"],
                2,
            ),
            "mutation_score": round(
                coverage["mutation"],
                2,
            ),
            "agent_count": len(agents),
            "completed_agents": completed_agents,
            "failed_agents": failed_agents,
            "coverage_gap_count": len(gaps),
        },

        "specification": specification,

        "rtl": {
            "version": rtl_version,
            "code": rtl_code,
        },

        "testbench": {
            "code": testbench,
        },

        "tests": tests,

        "test_summary": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "pass_rate": round(
                pass_rate,
                2,
            ),
        },

        "coverage": coverage,

        "failed_tests": failed_test_details,

        "agents": agents,

        "agent_summary": {
            "total": len(agents),
            "completed": completed_agents,
            "failed": failed_agents,
        },

        "assessment": {
            "score": round(
                _safe_float(score),
                2,
            ),
            "status": status,
            "ready_for_signoff": (
                status in {
                    "VERIFIED",
                    "PASSED",
                    "COMPLETED",
                }
                and failed_tests == 0
            ),
        },
    }

    return report


# ---------------------------------------------------------------------
# Save report data
# ---------------------------------------------------------------------

def save_report_data(
    report_data: Dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Save normalized report data as JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report_data,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return output_path


# ---------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------

def generate_report_data(
    state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str | Path] = None,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Build and optionally save report data.
    """

    report_data = build_report_data(
        state=state,
        run_dir=run_dir,
    )

    if output_path:
        save_report_data(
            report_data,
            output_path,
        )

    return report_data
