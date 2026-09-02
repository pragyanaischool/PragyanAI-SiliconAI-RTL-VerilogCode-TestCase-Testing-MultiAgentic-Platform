"""
PragyanAI SiliconAI

Icarus Verilog deterministic simulation runner.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class IcarusRunner:
    """
    Run Verilog/SystemVerilog simulations using Icarus Verilog.
    """

    def __init__(
        self,
        executable: str = "iverilog",
        vvp_executable: str = "vvp",
        work_dir: str | Path = "verification_logs/iverilog",
        timeout_seconds: int = 30,
    ):

        self.executable = executable
        self.vvp_executable = vvp_executable
        self.work_dir = Path(work_dir)
        self.timeout_seconds = timeout_seconds

        self.work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # -----------------------------------------------------------------
    # Run simulation
    # -----------------------------------------------------------------

    def run(
        self,
        rtl_code: str,
        testbench_code: str,
        top_module: Optional[str] = None,
        filename_prefix: str = "simulation",
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        run_dir = (
            self.work_dir
            / f"{filename_prefix}_{int(time.time() * 1000)}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rtl_file = (
            run_dir / "design.v"
        )

        tb_file = (
            run_dir / "testbench.v"
        )

        output_file = (
            run_dir / "sim_output"
        )

        rtl_file.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        tb_file.write_text(
            testbench_code or "",
            encoding="utf-8",
        )

        # -------------------------------------------------------------
        # Compile command
        # -------------------------------------------------------------

        compile_command = [
            self.executable,
            "-g2012",
            "-o",
            str(output_file),
            str(rtl_file),
            str(tb_file),
        ]

        if top_module:

            compile_command.extend(
                [
                    "-s",
                    top_module,
                ]
            )

        if extra_args:

            compile_command.extend(
                extra_args
            )

        start = time.perf_counter()

        try:

            compile_result = subprocess.run(
                compile_command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            compile_duration = (
                time.perf_counter()
                - start
            )

        except FileNotFoundError as exc:

            return {
                "success": False,
                "compile_success": False,
                "simulation_success": False,
                "error_type": "TOOL_NOT_FOUND",
                "compile_output": "",
                "simulation_output": "",
                "error": str(exc),
                "duration_seconds": 0.0,
                "work_dir": str(run_dir),
            }

        except subprocess.TimeoutExpired as exc:

            return {
                "success": False,
                "compile_success": False,
                "simulation_success": False,
                "error_type": "COMPILE_TIMEOUT",
                "compile_output": str(
                    exc.stdout or ""
                ),
                "simulation_output": "",
                "error": "Icarus compilation timed out.",
                "duration_seconds": self.timeout_seconds,
                "work_dir": str(run_dir),
            }

        compile_output = (
            (compile_result.stdout or "")
            + "\n"
            + (compile_result.stderr or "")
        )

        if compile_result.returncode != 0:

            return {
                "success": False,
                "compile_success": False,
                "simulation_success": False,
                "error_type": "COMPILE_ERROR",
                "compile_output": compile_output,
                "simulation_output": "",
                "error": compile_output,
                "duration_seconds": round(
                    compile_duration,
                    4,
                ),
                "work_dir": str(run_dir),
            }

        # -------------------------------------------------------------
        # Simulation
        # -------------------------------------------------------------

        start = time.perf_counter()

        try:

            simulation_result = subprocess.run(
                [
                    self.vvp_executable,
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            simulation_duration = (
                time.perf_counter()
                - start
            )

        except FileNotFoundError as exc:

            return {
                "success": False,
                "compile_success": True,
                "simulation_success": False,
                "error_type": "VVP_NOT_FOUND",
                "compile_output": compile_output,
                "simulation_output": "",
                "error": str(exc),
                "duration_seconds": round(
                    compile_duration,
                    4,
                ),
                "work_dir": str(run_dir),
            }

        except subprocess.TimeoutExpired:

            return {
                "success": False,
                "compile_success": True,
                "simulation_success": False,
                "error_type": "SIMULATION_TIMEOUT",
                "compile_output": compile_output,
                "simulation_output": "",
                "error": (
                    "Simulation exceeded timeout."
                ),
                "duration_seconds": self.timeout_seconds,
                "work_dir": str(run_dir),
            }

        simulation_output = (
            (simulation_result.stdout or "")
            + "\n"
            + (simulation_result.stderr or "")
        )

        # -------------------------------------------------------------
        # Result
        # -------------------------------------------------------------

        simulation_success = (
            simulation_result.returncode == 0
        )

        upper_output = (
            simulation_output.upper()
        )

        explicit_failure = (
            "TEST_RESULT" in upper_output
            and "|FAIL|" in upper_output
        )

        explicit_error = (
            "TEST_ERROR" in upper_output
        )

        success = (
            simulation_success
            and not explicit_failure
            and not explicit_error
        )

        # -------------------------------------------------------------
        # Save raw outputs
        # -------------------------------------------------------------

        (
            run_dir / "compile.log"
        ).write_text(
            compile_output,
            encoding="utf-8",
        )

        (
            run_dir / "simulation.log"
        ).write_text(
            simulation_output,
            encoding="utf-8",
        )

        return {
            "success": success,
            "compile_success": True,
            "simulation_success": simulation_success,
            "explicit_test_failure": explicit_failure,
            "explicit_test_error": explicit_error,
            "error_type": (
                ""
                if success
                else "SIMULATION_FAILURE"
            ),
            "compile_output": compile_output,
            "simulation_output": simulation_output,
            "error": (
                ""
                if success
                else simulation_output
            ),
            "duration_seconds": round(
                compile_duration
                + simulation_duration,
                4,
            ),
            "compile_duration_seconds": round(
                compile_duration,
                4,
            ),
            "simulation_duration_seconds": round(
                simulation_duration,
                4,
            ),
            "work_dir": str(run_dir),
            "rtl_file": str(rtl_file),
            "testbench_file": str(tb_file),
        }

    # -----------------------------------------------------------------
    # Simple API compatible with existing main_app.py
    # -----------------------------------------------------------------

    def simulate(
        self,
        rtl_code: str,
        testbench_code: str,
    ) -> Dict[str, Any]:

        return self.run(
            rtl_code=rtl_code,
            testbench_code=testbench_code,
        )
