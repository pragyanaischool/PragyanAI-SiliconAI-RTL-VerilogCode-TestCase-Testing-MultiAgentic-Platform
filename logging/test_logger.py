"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

Test Logger

Records individual verification test evidence.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestLogger:
    """
    Stores and manages individual test execution evidence.
    """

    def __init__(
        self,
        run_dir: str | Path,
    ):

        self.run_dir = Path(
            run_dir
        )

        self.test_dir = (
            self.run_dir
            / "testcases"
        )

        self.simulation_dir = (
            self.run_dir
            / "simulation"
        )

        self.failure_dir = (
            self.run_dir
            / "failures"
        )

        self.reports_dir = (
            self.run_dir
            / "reports"
        )

        for directory in [
            self.test_dir,
            self.simulation_dir,
            self.failure_dir,
            self.reports_dir,
        ]:

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        self.results_file = (
            self.reports_dir
            / "test_results.json"
        )

        self.csv_file = (
            self.reports_dir
            / "test_results.csv"
        )

        if not self.results_file.exists():

            self._write_json(
                self.results_file,
                [],
            )

    # -----------------------------------------------------------------
    # Log test
    # -----------------------------------------------------------------

    def log_test(
        self,
        test_id: str,
        description: str = "",
        status: str = "UNKNOWN",
        inputs: Any = "",
        expected: Any = "",
        actual: Any = "",
        rtl_version: str = "v1",
        iteration: int = 0,
        agent: str = "Testbench Generator",
        duration_seconds: float = 0.0,
        testbench_code: str = "",
        simulation_output: str = "",
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a single test.
        """

        normalized_status = (
            self.normalize_status(status)
        )

        timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

        # -------------------------------------------------------------
        # Test code
        # -------------------------------------------------------------

        test_code_file = ""

        if testbench_code:

            filename = (
                f"{test_id}.v"
            )

            path = (
                self.test_dir
                / filename
            )

            path.write_text(
                testbench_code,
                encoding="utf-8",
            )

            test_code_file = str(
                path.relative_to(
                    self.run_dir
                )
            )

        # -------------------------------------------------------------
        # Simulation log
        # -------------------------------------------------------------

        simulation_log = ""

        if simulation_output:

            log_path = (
                self.simulation_dir
                / f"{test_id}.log"
            )

            log_path.write_text(
                simulation_output,
                encoding="utf-8",
            )

            simulation_log = str(
                log_path.relative_to(
                    self.run_dir
                )
            )

        # -------------------------------------------------------------
        # Test record
        # -------------------------------------------------------------

        record = {
            "test_id": test_id,

            "description": description,

            "status": normalized_status,

            "inputs": self._stringify(
                inputs
            ),

            "expected": self._stringify(
                expected
            ),

            "actual": self._stringify(
                actual
            ),

            "error_message": error_message,

            "rtl_version": rtl_version,

            "iteration": int(
                iteration
            ),

            "agent": agent,

            "duration_seconds": round(
                float(duration_seconds),
                4,
            ),

            "test_code_file": test_code_file,

            "simulation_log": simulation_log,

            "timestamp": timestamp,

            "metadata": metadata or {},
        }

        # -------------------------------------------------------------
        # Save JSON
        # -------------------------------------------------------------

        results = self.load_results()

        results.append(
            record
        )

        self._write_json(
            self.results_file,
            results,
        )

        # -------------------------------------------------------------
        # Save failure evidence
        # -------------------------------------------------------------

        if normalized_status == "FAILED":

            failure_file = (
                self.failure_dir
                / f"{test_id}.json"
            )

            self._write_json(
                failure_file,
                record,
            )

        # -------------------------------------------------------------
        # Update CSV
        # -------------------------------------------------------------

        self.export_csv(
            results
        )

        return record

    # -----------------------------------------------------------------
    # Status helpers
    # -----------------------------------------------------------------

    @staticmethod
    def normalize_status(
        status: Any,
    ) -> str:

        value = str(
            status or "UNKNOWN"
        ).strip().upper()

        aliases = {
            "PASS": "PASSED",
            "SUCCESS": "PASSED",
            "OK": "PASSED",
            "FAIL": "FAILED",
            "ERROR": "FAILED",
            "SKIP": "SKIPPED",
        }

        return aliases.get(
            value,
            value,
        )

    # -----------------------------------------------------------------
    # Load results
    # -----------------------------------------------------------------

    def load_results(self) -> List[Dict[str, Any]]:

        if not self.results_file.exists():
            return []

        try:

            with self.results_file.open(
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            if isinstance(data, list):
                return data

        except Exception:
            pass

        return []

    # -----------------------------------------------------------------
    # Find test
    # -----------------------------------------------------------------

    def get_test(
        self,
        test_id: str,
    ) -> Optional[Dict[str, Any]]:

        for test in self.load_results():

            if test.get(
                "test_id"
            ) == test_id:

                return test

        return None

    # -----------------------------------------------------------------
    # Test summary
    # -----------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:

        results = self.load_results()

        total = len(results)

        passed = sum(
            1
            for test in results
            if self.normalize_status(
                test.get("status")
            ) == "PASSED"
        )

        failed = sum(
            1
            for test in results
            if self.normalize_status(
                test.get("status")
            ) == "FAILED"
        )

        skipped = sum(
            1
            for test in results
            if self.normalize_status(
                test.get("status")
            ) == "SKIPPED"
        )

        pass_rate = (
            (passed / total) * 100
            if total
            else 0.0
        )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(
                pass_rate,
                2,
            ),
        }

    # -----------------------------------------------------------------
    # Failed tests
    # -----------------------------------------------------------------

    def get_failed_tests(
        self,
    ) -> List[Dict[str, Any]]:

        return [
            test
            for test in self.load_results()
            if self.normalize_status(
                test.get("status")
            ) == "FAILED"
        ]

    # -----------------------------------------------------------------
    # Export CSV
    # -----------------------------------------------------------------

    def export_csv(
        self,
        results: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> Path:

        if results is None:
            results = self.load_results()

        fields = [
            "test_id",
            "description",
            "status",
            "inputs",
            "expected",
            "actual",
            "error_message",
            "rtl_version",
            "iteration",
            "agent",
            "duration_seconds",
            "test_code_file",
            "simulation_log",
            "timestamp",
        ]

        with self.csv_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()

            for record in results:

                writer.writerow(
                    {
                        field: record.get(
                            field,
                            "",
                        )
                        for field in fields
                    }
                )

        return self.csv_file

    # -----------------------------------------------------------------
    # Save testbench separately
    # -----------------------------------------------------------------

    def save_testbench(
        self,
        test_id: str,
        code: str,
    ) -> Path:

        path = (
            self.test_dir
            / f"{test_id}.v"
        )

        path.write_text(
            code or "",
            encoding="utf-8",
        )

        return path

    # -----------------------------------------------------------------
    # Save simulation
    # -----------------------------------------------------------------

    def save_simulation_output(
        self,
        test_id: str,
        output: str,
    ) -> Path:

        path = (
            self.simulation_dir
            / f"{test_id}.log"
        )

        path.write_text(
            output or "",
            encoding="utf-8",
        )

        return path

    # -----------------------------------------------------------------
    # Save failure
    # -----------------------------------------------------------------

    def save_failure(
        self,
        test_id: str,
        failure_data: Dict[str, Any],
    ) -> Path:

        path = (
            self.failure_dir
            / f"{test_id}.json"
        )

        self._write_json(
            path,
            failure_data,
        )

        return path

    # -----------------------------------------------------------------
    # String conversion
    # -----------------------------------------------------------------

    @staticmethod
    def _stringify(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            str,
        ):
            return value

        try:

            return json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

        except Exception:

            return str(value)

    # -----------------------------------------------------------------
    # JSON helper
    # -----------------------------------------------------------------

    @staticmethod
    def _write_json(
        path: Path,
        data: Any,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
