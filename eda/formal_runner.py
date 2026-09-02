"""
PragyanAI SiliconAI

Formal verification runner.

Designed to provide a common interface for:
- SymbiYosys
- Yosys formal flows
- Future formal engines
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class FormalRunner:

    def __init__(
        self,
        executable: str = "sby",
        work_dir: str | Path = "verification_logs/formal",
        timeout_seconds: int = 120,
    ):

        self.executable = executable
        self.work_dir = Path(work_dir)
        self.timeout_seconds = timeout_seconds

        self.work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # -----------------------------------------------------------------
    # Run formal verification
    # -----------------------------------------------------------------

    def run(
        self,
        rtl_code: str,
        properties: str = "",
        top_module: Optional[str] = None,
        mode: str = "bmc",
        depth: int = 20,
    ) -> Dict[str, Any]:

        run_dir = (
            self.work_dir
            / f"formal_{int(time.time() * 1000)}"
        )

        run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        rtl_file = (
            run_dir / "design.sv"
        )

        property_file = (
            run_dir / "properties.sv"
        )

        sby_file = (
            run_dir / "formal.sby"
        )

        rtl_file.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        property_file.write_text(
            properties or "",
            encoding="utf-8",
        )

        top = (
            top_module
            or "top"
        )

        sby_content = f"""[options]
mode {mode}
depth {depth}

[engines]
smtbmc

[script]
read -formal {rtl_file}
read -formal {property_file}
prep -top {top}

[files]
{rtl_file}
{property_file}
"""

        sby_file.write_text(
            sby_content,
            encoding="utf-8",
        )

        command = [
            self.executable,
            "-f",
            str(sby_file),
        ]

        start = time.perf_counter()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=str(run_dir),
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

            upper = output.upper()

            if (
                "PASS" in upper
                and "FAIL" not in upper
            ):

                status = "PASSED"

            elif "FAIL" in upper:

                status = "FAILED"

            else:

                status = (
                    "COMPLETED"
                    if result.returncode == 0
                    else "FAILED"
                )

            return {
                "success": (
                    result.returncode == 0
                ),
                "status": status,
                "return_code": result.returncode,
                "output": output,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "duration_seconds": round(
                    duration,
                    4,
                ),
                "work_dir": str(run_dir),
                "property_file": str(
                    property_file
                ),
                "sby_file": str(
                    sby_file
                ),
            }

        except FileNotFoundError as exc:

            return {
                "success": False,
                "status": "TOOL_NOT_FOUND",
                "return_code": -1,
                "output": str(exc),
                "error_type": "TOOL_NOT_FOUND",
                "duration_seconds": 0.0,
                "work_dir": str(run_dir),
            }

        except subprocess.TimeoutExpired:

            return {
                "success": False,
                "status": "TIMEOUT",
                "return_code": -1,
                "output": (
                    "Formal verification timed out."
                ),
                "error_type": "TIMEOUT",
                "duration_seconds": self.timeout_seconds,
                "work_dir": str(run_dir),
            }
