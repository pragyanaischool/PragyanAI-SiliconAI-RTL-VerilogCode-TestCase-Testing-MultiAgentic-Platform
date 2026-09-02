"""
PragyanAI SiliconAI

Verilator runner.

Used for:
- linting
- fast compilation
- additional RTL validation
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional


class VerilatorRunner:

    def __init__(
        self,
        executable: str = "verilator",
        work_dir: str | Path = "verification_logs/verilator",
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
    # Lint
    # -----------------------------------------------------------------

    def lint(
        self,
        rtl_code: str,
        filename: str = "design.sv",
    ) -> Dict[str, Any]:

        run_dir = (
            self.work_dir
            / f"lint_{int(time.time() * 1000)}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rtl_file = (
            run_dir / filename
        )

        rtl_file.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        command = [
            self.executable,
            "--lint-only",
            "-Wall",
            str(rtl_file),
        ]

        return self._execute(
            command,
            run_dir,
        )

    # -----------------------------------------------------------------
    # Compile
    # -----------------------------------------------------------------

    def compile(
        self,
        rtl_code: str,
        top_module: Optional[str] = None,
    ) -> Dict[str, Any]:

        run_dir = (
            self.work_dir
            / f"compile_{int(time.time() * 1000)}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rtl_file = (
            run_dir / "design.sv"
        )

        rtl_file.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        command = [
            self.executable,
            "--cc",
            str(rtl_file),
        ]

        if top_module:

            command.extend(
                [
                    "--top-module",
                    top_module,
                ]
            )

        result = self._execute(
            command,
            run_dir,
        )

        result["rtl_file"] = str(
            rtl_file
        )

        return result

    # -----------------------------------------------------------------
    # Execute
    # -----------------------------------------------------------------

    def _execute(
        self,
        command: list[str],
        run_dir: Path,
    ) -> Dict[str, Any]:

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
                "output": output,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "duration_seconds": round(
                    duration,
                    4,
                ),
                "work_dir": str(run_dir),
            }

        except FileNotFoundError as exc:

            return {
                "success": False,
                "return_code": -1,
                "output": str(exc),
                "stdout": "",
                "stderr": "",
                "error_type": "TOOL_NOT_FOUND",
                "duration_seconds": 0.0,
                "work_dir": str(run_dir),
            }

        except subprocess.TimeoutExpired:

            return {
                "success": False,
                "return_code": -1,
                "output": "Verilator timed out.",
                "stdout": "",
                "stderr": "",
                "error_type": "TIMEOUT",
                "duration_seconds": self.timeout_seconds,
                "work_dir": str(run_dir),
            }
