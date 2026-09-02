"""
PragyanAI SiliconAI

Yosys synthesis/check runner.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional


class YosysRunner:

    def __init__(
        self,
        executable: str = "yosys",
        work_dir: str | Path = "verification_logs/yosys",
        timeout_seconds: int = 60,
    ):

        self.executable = executable
        self.work_dir = Path(work_dir)
        self.timeout_seconds = timeout_seconds

        self.work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # -----------------------------------------------------------------
    # Check RTL
    # -----------------------------------------------------------------

    def check(
        self,
        rtl_code: str,
        top_module: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.run(
            rtl_code=rtl_code,
            top_module=top_module,
            mode="check",
        )

    # -----------------------------------------------------------------
    # Synthesis
    # -----------------------------------------------------------------

    def synthesize(
        self,
        rtl_code: str,
        top_module: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.run(
            rtl_code=rtl_code,
            top_module=top_module,
            mode="synth",
        )

    # -----------------------------------------------------------------
    # Run
    # -----------------------------------------------------------------

    def run(
        self,
        rtl_code: str,
        top_module: Optional[str] = None,
        mode: str = "check",
    ) -> Dict[str, Any]:

        run_dir = (
            self.work_dir
            / f"run_{int(time.time() * 1000)}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rtl_file = (
            run_dir / "design.v"
        )

        script_file = (
            run_dir / "script.ys"
        )

        rtl_file.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        read_command = (
            f"read_verilog -sv {rtl_file}"
        )

        if mode == "synth":

            if top_module:

                command_script = (
                    f"{read_command}; "
                    f"synth -top {top_module}"
                )

            else:

                command_script = (
                    f"{read_command}; "
                    f"synth"
                )

        else:

            command_script = (
                f"{read_command}; "
                f"hierarchy -check"
            )

            if top_module:

                command_script += (
                    f" -top {top_module}"
                )

        script_file.write_text(
            command_script,
            encoding="utf-8",
        )

        command = [
            self.executable,
            "-s",
            str(script_file),
        ]

        start = time.perf_counter()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            duration = (
                time.perf_counter()
                - start
            )

            output = (
                (result.stdout or "")
                + "\n"
                + (result.stderr or "")
            )

            return {
                "success": (
                    result.returncode == 0
                ),
                "return_code": result.returncode,
                "mode": mode,
                "output": output,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "duration_seconds": round(
                    duration,
                    4,
                ),
                "work_dir": str(run_dir),
                "rtl_file": str(rtl_file),
            }

        except FileNotFoundError as exc:

            return {
                "success": False,
                "return_code": -1,
                "mode": mode,
                "output": str(exc),
                "error_type": "TOOL_NOT_FOUND",
                "duration_seconds": 0.0,
                "work_dir": str(run_dir),
            }

        except subprocess.TimeoutExpired:

            return {
                "success": False,
                "return_code": -1,
                "mode": mode,
                "output": "Yosys timed out.",
                "error_type": "TIMEOUT",
                "duration_seconds": self.timeout_seconds,
                "work_dir": str(run_dir),
            }
