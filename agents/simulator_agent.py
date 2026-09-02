"""
PragyanAI SiliconAI
Simulator Agent

Purpose
-------
Execute generated RTL and verification testbenches using the
deterministic EDA simulation layer.

Primary simulator:
    Icarus Verilog

The AI agent does NOT decide whether compilation succeeded.
Compilation and simulation are determined by the EDA runner.

Responsibilities
----------------
1. Execute RTL + testbench.
2. Capture compile output.
3. Capture simulation output.
4. Detect explicit TEST_RESULT / TEST_ERROR records.
5. Preserve failure evidence.
6. Return structured state for LangGraph.
7. Maintain compact logs to avoid Groq TPM problems.
8. Remain useful even when no LLM/API is configured.

Expected state fields
---------------------
rtl_code
testbench
test_code
iteration
run_dir

Returned state fields
---------------------
compile_output
compile_error
simulation_output
simulation_error
simulation_passed
run_output
tests
agent_log
agent_trace
status
messages
errors
warnings
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from eda.iverilog_runner import IcarusRunner
from verification.test_parser import parse_test_results


class SimulatorAgent:
    """
    Deterministic RTL simulation agent.

    This agent intentionally does not call an LLM.

    Simulation is an execution task and should be handled by
    deterministic EDA tooling rather than probabilistic reasoning.
    """

    AGENT_NAME = "Simulation Agent"

    def __init__(
        self,
        runner: Optional[IcarusRunner] = None,
        timeout: Optional[int] = None,
    ) -> None:

        self.runner = runner or IcarusRunner()

        self.timeout = timeout

        if timeout is not None:
            try:
                self.runner.timeout = timeout
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _compact(text: Any, limit: int = 5000) -> str:
        """
        Compact long simulator output.

        Full output should be stored as an artifact.
        Only a bounded portion is returned in LangGraph state.
        """

        if text is None:
            return ""

        text = str(text)

        if len(text) <= limit:
            return text

        head = limit // 2
        tail = limit - head

        return (
            text[:head]
            + "\n...[OUTPUT TRUNCATED]...\n"
            + text[-tail:]
        )

    @staticmethod
    def _contains_failure(text: str) -> bool:
        """
        Detect explicit failure indicators.

        The EDA runner remains the primary authority.
        """

        if not text:
            return False

        upper = text.upper()

        failure_patterns = [
            "TEST_ERROR",
            "FAILED",
            "FAILURE",
            "ERROR:",
            "ERROR ",
            "FATAL",
            "ASSERTION FAILED",
            "ASSERTION_FAILURE",
            "MISMATCH",
            "TIMEOUT",
            "SEGMENTATION FAULT",
        ]

        return any(
            pattern in upper
            for pattern in failure_patterns
        )

    @staticmethod
    def _contains_pass(text: str) -> bool:
        if not text:
            return False

        upper = text.upper()

        return (
            "TEST_RESULT" in upper
            and "PASS" in upper
            and "TEST_ERROR" not in upper
        )

    @staticmethod
    def _normalize_test_results(
        parsed: Any,
    ) -> List[Dict[str, Any]]:
        """
        Normalize results returned by verification.test_parser.

        Supports either:
            list
        or:
            {"tests": [...]}
        """

        if isinstance(parsed, dict):
            parsed = (
                parsed.get("tests")
                or parsed.get("results")
                or parsed.get("test_results")
                or []
            )

        if not isinstance(parsed, list):
            return []

        normalized: List[Dict[str, Any]] = []

        for index, item in enumerate(parsed, start=1):

            if isinstance(item, str):
                normalized.append(
                    {
                        "test_id": f"TC{index:03d}",
                        "status": "FAILED",
                        "description": item[:300],
                        "actual": "",
                        "expected": "",
                        "error_message": item[:500],
                    }
                )
                continue

            if not isinstance(item, dict):
                continue

            test_id = str(
                item.get("test_id")
                or item.get("id")
                or f"TC{index:03d}"
            )

            status = str(
                item.get("status")
                or item.get("result")
                or "UNKNOWN"
            ).upper()

            if status in {"PASS", "PASSED", "SUCCESS"}:
                status = "PASSED"

            elif status in {"FAIL", "FAILED", "ERROR"}:
                status = "FAILED"

            else:
                status = "UNKNOWN"

            normalized.append(
                {
                    "test_id": test_id,
                    "description": str(
                        item.get("description")
                        or item.get("name")
                        or ""
                    )[:300],
                    "status": status,
                    "inputs": str(
                        item.get("inputs")
                        or item.get("input")
                        or ""
                    )[:500],
                    "expected": str(
                        item.get("expected")
                        or ""
                    )[:500],
                    "actual": str(
                        item.get("actual")
                        or ""
                    )[:500],
                    "error_message": str(
                        item.get("error_message")
                        or item.get("error")
                        or ""
                    )[:800],
                }
            )

        return normalized

    # ------------------------------------------------------------------
    # Artifact storage
    # ------------------------------------------------------------------

    def _save_artifact(
        self,
        path: Path,
        content: str,
    ) -> Optional[str]:

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                content or "",
                encoding="utf-8",
            )

            return str(path)

        except Exception:
            return None

    def _get_artifact_dir(
        self,
        state: Dict[str, Any],
    ) -> Path:

        run_dir = state.get("run_dir")

        if run_dir:
            return Path(run_dir) / "simulation"

        return Path("verification_logs") / "simulation"

    # ------------------------------------------------------------------
    # Testbench resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _get_testbench(
        state: Dict[str, Any],
    ) -> str:

        candidates = [
            state.get("testbench"),
            state.get("test_code"),
        ]

        for candidate in candidates:

            if candidate is None:
                continue

            text = str(candidate).strip()

            if text:
                return text

        return ""

    # ------------------------------------------------------------------
    # Result interpretation
    # ------------------------------------------------------------------

    def _interpret_result(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:

        compile_success = bool(
            result.get("compile_success")
            or result.get("compile_passed")
        )

        simulation_success = bool(
            result.get("simulation_success")
            or result.get("simulation_passed")
        )

        compile_output = str(
            result.get("compile_output")
            or result.get("stdout")
            or ""
        )

        compile_error = str(
            result.get("compile_error")
            or result.get("compile_stderr")
            or result.get("stderr")
            or ""
        )

        simulation_output = str(
            result.get("simulation_output")
            or result.get("vvp_output")
            or result.get("output")
            or ""
        )

        simulation_error = str(
            result.get("simulation_error")
            or ""
        )

        combined_output = "\n".join(
            [
                compile_output,
                compile_error,
                simulation_output,
                simulation_error,
            ]
        )

        # --------------------------------------------------------------
        # Parse machine-readable test records.
        # --------------------------------------------------------------

        parsed_tests: List[Dict[str, Any]] = []

        try:
            parsed = parse_test_results(
                simulation_output
            )

            parsed_tests = self._normalize_test_results(
                parsed
            )

        except Exception:
            parsed_tests = []

        # --------------------------------------------------------------
        # Determine final simulation status.
        # --------------------------------------------------------------

        explicit_failure = self._contains_failure(
            simulation_output
        )

        explicit_compile_failure = self._contains_failure(
            compile_error
        )

        final_passed = (
            compile_success
            and simulation_success
            and not explicit_compile_failure
            and not explicit_failure
        )

        # If explicit TEST_RESULT records exist, use them.
        if parsed_tests:

            has_failed_test = any(
                test.get("status") == "FAILED"
                for test in parsed_tests
            )

            all_known = all(
                test.get("status")
                in {"PASSED", "FAILED"}
                for test in parsed_tests
            )

            if has_failed_test:
                final_passed = False

            elif all_known and parsed_tests:
                final_passed = (
                    compile_success
                    and simulation_success
                )

        return {
            "compile_success": compile_success,
            "simulation_success": simulation_success,
            "simulation_passed": final_passed,
            "compile_output": compile_output,
            "compile_error": compile_error,
            "simulation_output": simulation_output,
            "simulation_error": simulation_error,
            "tests": parsed_tests,
            "combined_output": combined_output,
        }

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.time()

        rtl_code = str(
            state.get("rtl_code")
            or ""
        ).strip()

        testbench_code = self._get_testbench(
            state
        )

        iteration = int(
            state.get("iteration") or 1
        )

        artifact_dir = self._get_artifact_dir(
            state
        )

        warnings: List[str] = []
        errors: List[str] = []

        # --------------------------------------------------------------
        # Validate input
        # --------------------------------------------------------------

        if not rtl_code:

            message = "Simulation skipped: RTL code is empty."

            errors.append(message)

            elapsed = round(
                time.time() - start,
                3,
            )

            trace_entry = {
                "agent": self.AGENT_NAME,
                "status": "FAILED",
                "timestamp": self._timestamp(),
                "message": message,
                "duration_seconds": elapsed,
            }

            return {
                "compile_output": "",
                "compile_error": message,
                "simulation_output": "",
                "simulation_error": message,
                "simulation_passed": False,
                "run_output": message,
                "tests": [],
                "agent_trace": (
                    list(state.get("agent_trace") or [])
                    + [trace_entry]
                ),
                "agent_log": (
                    list(state.get("agent_log") or [])
                    + [
                        {
                            "agent": self.AGENT_NAME,
                            "status": "FAILED",
                            "timestamp": self._timestamp(),
                            "duration_seconds": elapsed,
                        }
                    ]
                ),
                "errors": (
                    list(state.get("errors") or [])
                    + errors
                ),
                "status": "FAILED",
            }

        if not testbench_code:

            message = (
                "Simulation skipped: testbench code is empty."
            )

            errors.append(message)

            elapsed = round(
                time.time() - start,
                3,
            )

            trace_entry = {
                "agent": self.AGENT_NAME,
                "status": "FAILED",
                "timestamp": self._timestamp(),
                "message": message,
                "duration_seconds": elapsed,
            }

            return {
                "compile_output": "",
                "compile_error": message,
                "simulation_output": "",
                "simulation_error": message,
                "simulation_passed": False,
                "run_output": message,
                "tests": [],
                "agent_trace": (
                    list(state.get("agent_trace") or [])
                    + [trace_entry]
                ),
                "agent_log": (
                    list(state.get("agent_log") or [])
                    + [
                        {
                            "agent": self.AGENT_NAME,
                            "status": "FAILED",
                            "timestamp": self._timestamp(),
                            "duration_seconds": elapsed,
                        }
                    ]
                ),
                "errors": (
                    list(state.get("errors") or [])
                    + errors
                ),
                "status": "FAILED",
            }

        # --------------------------------------------------------------
        # Save source artifacts
        # --------------------------------------------------------------

        rtl_path = self._save_artifact(
            artifact_dir / f"design_iteration_{iteration}.v",
            rtl_code,
        )

        testbench_path = self._save_artifact(
            artifact_dir / f"testbench_iteration_{iteration}.v",
            testbench_code,
        )

        # --------------------------------------------------------------
        # Execute Icarus
        # --------------------------------------------------------------

        try:

            runner_result = self.runner.run(
                rtl_code=rtl_code,
                testbench_code=testbench_code,
                filename_prefix=(
                    f"iteration_{iteration}"
                ),
            )

        except TypeError:

            # Compatibility fallback for older runner signatures.
            try:
                runner_result = self.runner.run(
                    rtl_code,
                    testbench_code,
                )

            except Exception as exc:

                runner_result = {
                    "compile_success": False,
                    "simulation_success": False,
                    "compile_output": "",
                    "compile_error": str(exc),
                    "simulation_output": "",
                    "simulation_error": str(exc),
                }

        except Exception as exc:

            runner_result = {
                "compile_success": False,
                "simulation_success": False,
                "compile_output": "",
                "compile_error": str(exc),
                "simulation_output": "",
                "simulation_error": str(exc),
            }

        if not isinstance(runner_result, dict):
            runner_result = {
                "compile_success": False,
                "simulation_success": False,
                "compile_output": "",
                "compile_error": (
                    "IcarusRunner returned an invalid result."
                ),
                "simulation_output": "",
                "simulation_error": "",
            }

        interpreted = self._interpret_result(
            runner_result
        )

        # --------------------------------------------------------------
        # Save full simulation evidence
        # --------------------------------------------------------------

        compile_log_path = self._save_artifact(
            artifact_dir / f"iteration_{iteration}_compile.log",
            interpreted["compile_output"]
            + (
                "\n"
                + interpreted["compile_error"]
                if interpreted["compile_error"]
                else ""
            ),
        )

        simulation_log_path = self._save_artifact(
            artifact_dir / f"iteration_{iteration}_simulation.log",
            interpreted["simulation_output"]
            + (
                "\n"
                + interpreted["simulation_error"]
                if interpreted["simulation_error"]
                else ""
            ),
        )

        # Save structured result.
        result_path = None

        try:

            artifact_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            result_path = artifact_dir / (
                f"iteration_{iteration}_result.json"
            )

            result_path.write_text(
                json.dumps(
                    {
                        "iteration": iteration,
                        "timestamp": self._timestamp(),
                        "compile_success": interpreted[
                            "compile_success"
                        ],
                        "simulation_success": interpreted[
                            "simulation_success"
                        ],
                        "simulation_passed": interpreted[
                            "simulation_passed"
                        ],
                        "tests": interpreted["tests"],
                        "compile_output": interpreted[
                            "compile_output"
                        ],
                        "compile_error": interpreted[
                            "compile_error"
                        ],
                        "simulation_output": interpreted[
                            "simulation_output"
                        ],
                        "simulation_error": interpreted[
                            "simulation_error"
                        ],
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

        except Exception as exc:
            warnings.append(
                f"Could not save structured simulation result: {exc}"
            )

        # --------------------------------------------------------------
        # Construct concise run output.
        # --------------------------------------------------------------

        run_output = self._compact(
            "\n".join(
                [
                    interpreted["compile_output"],
                    interpreted["compile_error"],
                    interpreted["simulation_output"],
                    interpreted["simulation_error"],
                ]
            ),
            limit=7000,
        )

        # --------------------------------------------------------------
        # Add test evidence metadata.
        # --------------------------------------------------------------

        enriched_tests: List[Dict[str, Any]] = []

        for test in interpreted["tests"]:

            enriched = dict(test)

            enriched.update(
                {
                    "iteration": iteration,
                    "agent": self.AGENT_NAME,
                    "rtl_version": state.get(
                        "rtl_version",
                        f"v{iteration}",
                    ),
                    "simulation_log": (
                        str(simulation_log_path)
                        if simulation_log_path
                        else ""
                    ),
                    "duration_seconds": round(
                        time.time() - start,
                        3,
                    ),
                }
            )

            enriched_tests.append(enriched)

        # --------------------------------------------------------------
        # Final status
        # --------------------------------------------------------------

        passed = bool(
            interpreted["simulation_passed"]
        )

        if passed:

            status = "COMPLETED"

            message = (
                "Simulation completed successfully. "
                f"Detected {len(enriched_tests)} structured test result(s)."
            )

        else:

            status = "FAILED"

            if interpreted["compile_error"]:
                message = (
                    "Simulation failed during compilation."
                )

            elif interpreted["simulation_error"]:
                message = (
                    "Simulation failed during execution."
                )

            elif enriched_tests:
                message = (
                    "Simulation completed but one or more "
                    "verification tests failed."
                )

            else:
                message = (
                    "Simulation did not produce a verified PASS result."
                )

        elapsed = round(
            time.time() - start,
            3,
        )

        # --------------------------------------------------------------
        # Agent trace
        # --------------------------------------------------------------

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": status,
            "timestamp": self._timestamp(),
            "message": message,
            "duration_seconds": elapsed,
            "iteration": iteration,
            "compile_success": interpreted[
                "compile_success"
            ],
            "simulation_success": interpreted[
                "simulation_success"
            ],
            "simulation_passed": passed,
            "tests_detected": len(
                enriched_tests
            ),
        }

        # --------------------------------------------------------------
        # Agent log
        # --------------------------------------------------------------

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "timestamp": self._timestamp(),
            "status": status,
            "iteration": iteration,
            "duration_seconds": elapsed,
            "input_summary": {
                "rtl_length": len(rtl_code),
                "testbench_length": len(testbench_code),
            },
            "output_summary": {
                "compile_success": interpreted[
                    "compile_success"
                ],
                "simulation_success": interpreted[
                    "simulation_success"
                ],
                "simulation_passed": passed,
                "tests_detected": len(
                    enriched_tests
                ),
                "failed_tests": sum(
                    1
                    for test in enriched_tests
                    if test.get("status") == "FAILED"
                ),
            },
            "artifacts": {
                "rtl": rtl_path or "",
                "testbench": testbench_path or "",
                "compile_log": compile_log_path or "",
                "simulation_log": simulation_log_path or "",
                "result_json": (
                    str(result_path)
                    if result_path
                    else ""
                ),
            },
        }

        # --------------------------------------------------------------
        # Return LangGraph state update.
        # --------------------------------------------------------------

        return {
            "compile_output": self._compact(
                interpreted["compile_output"],
                4000,
            ),
            "compile_error": self._compact(
                interpreted["compile_error"],
                4000,
            ),
            "simulation_output": self._compact(
                interpreted["simulation_output"],
                6000,
            ),
            "simulation_error": self._compact(
                interpreted["simulation_error"],
                4000,
            ),
            "simulation_passed": passed,
            "run_output": run_output,
            "tests": enriched_tests,
            "agent_log": (
                list(state.get("agent_log") or [])
                + [agent_log_entry]
            ),
            "agent_trace": (
                list(state.get("agent_trace") or [])
                + [trace_entry]
            ),
            "messages": (
                list(state.get("messages") or [])
                + [message]
            ),
            "warnings": (
                list(state.get("warnings") or [])
                + warnings
            ),
            "errors": (
                list(state.get("errors") or [])
                + errors
                + (
                    [interpreted["compile_error"]]
                    if interpreted["compile_error"]
                    else []
                )
            ),
            "status": status,
        }

    # ------------------------------------------------------------------
    # LangGraph interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.run(state)


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def run_simulator_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience function for direct LangGraph integration.
    """

    agent = SimulatorAgent()

    return agent.run(state)


__all__ = [
    "SimulatorAgent",
    "run_simulator_agent",
]
