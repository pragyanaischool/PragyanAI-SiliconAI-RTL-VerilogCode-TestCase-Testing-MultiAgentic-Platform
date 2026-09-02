"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

Verification Logger

High-level evidence/logging facade combining:

- RunManager
- AgentLogger
- TestLogger

Also manages:
- RTL
- Coverage
- Failure analysis
- Reports
- Verification summary
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .run_manager import RunManager
from .agent_logger import AgentLogger
from .test_logger import TestLogger


class VerificationLogger:
    """
    High-level logging API for the complete verification workflow.
    """

    def __init__(
        self,
        base_dir: str | Path = "verification_logs/runs",
    ):

        self.run_manager = RunManager(
            base_dir=base_dir
        )

        self.agent_logger: Optional[
            AgentLogger
        ] = None

        self.test_logger: Optional[
            TestLogger
        ] = None

        self.run_id: Optional[
            str
        ] = None

        self.run_dir: Optional[
            Path
        ] = None

    # -----------------------------------------------------------------
    # Run lifecycle
    # -----------------------------------------------------------------

    def create_run(
        self,
        specification: str = "",
        rtl_version: str = "v1",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a verification run and initialize all loggers.
        """

        self.run_id = (
            self.run_manager.create_run(
                specification=specification,
                rtl_version=rtl_version,
                metadata=metadata,
            )
        )

        self.run_dir = (
            self.run_manager.get_run_dir()
        )

        self.agent_logger = AgentLogger(
            self.run_dir
        )

        self.test_logger = TestLogger(
            self.run_dir
        )

        self.run_manager.add_event(
            event_type="RUN_CREATED",
            message="Verification run created.",
        )

        return self.run_id

    # -----------------------------------------------------------------
    # Require active run
    # -----------------------------------------------------------------

    def _require_run(self) -> None:

        if self.run_dir is None:

            raise RuntimeError(
                "No active verification run. "
                "Call create_run() first."
            )

    # -----------------------------------------------------------------
    # RTL
    # -----------------------------------------------------------------

    def save_rtl(
        self,
        rtl_code: str,
        version: Optional[str] = None,
    ) -> Path:

        self._require_run()

        path = self.run_manager.save_rtl(
            rtl_code=rtl_code,
            version=version,
        )

        self.run_manager.add_event(
            event_type="RTL_SAVED",
            message=f"RTL saved: {path.name}",
            data={
                "version": version,
                "path": str(
                    path.relative_to(
                        self.run_dir
                    )
                ),
            },
        )

        return path

    # -----------------------------------------------------------------
    # Testbench
    # -----------------------------------------------------------------

    def save_testbench(
        self,
        testbench_code: str,
        filename: str = "testbench.v",
    ) -> Path:

        self._require_run()

        path = self.run_manager.save_testbench(
            testbench_code,
            filename,
        )

        self.run_manager.add_event(
            event_type="TESTBENCH_SAVED",
            message=(
                f"Testbench saved: {filename}"
            ),
        )

        return path

    # -----------------------------------------------------------------
    # Agent
    # -----------------------------------------------------------------

    def log_agent(
        self,
        agent: str,
        status: str,
        message: str = "",
        input_data: Any = None,
        output_data: Any = None,
        decision: str = "",
        iteration: int = 0,
        duration_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        self._require_run()

        if self.agent_logger is None:

            raise RuntimeError(
                "AgentLogger is not initialized."
            )

        record = (
            self.agent_logger.log_agent(
                agent=agent,
                status=status,
                message=message,
                input_data=input_data,
                output_data=output_data,
                decision=decision,
                iteration=iteration,
                duration_seconds=duration_seconds,
                metadata=metadata,
            )
        )

        self.run_manager.add_event(
            event_type="AGENT_EXECUTION",
            message=(
                f"{agent}: {status}"
            ),
            data={
                "agent": agent,
                "status": status,
                "iteration": iteration,
            },
        )

        return record

    # -----------------------------------------------------------------
    # Agent context
    # -----------------------------------------------------------------

    def start_agent(
        self,
        agent: str,
        iteration: int = 0,
        input_data: Any = None,
    ) -> Dict[str, Any]:

        self._require_run()

        if self.agent_logger is None:

            raise RuntimeError(
                "AgentLogger is not initialized."
            )

        return self.agent_logger.start_agent(
            agent=agent,
            iteration=iteration,
            input_data=input_data,
        )

    def finish_agent(
        self,
        context: Dict[str, Any],
        status: str = "COMPLETED",
        message: str = "",
        output_data: Any = None,
        decision: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        self._require_run()

        if self.agent_logger is None:

            raise RuntimeError(
                "AgentLogger is not initialized."
            )

        return self.agent_logger.finish_agent(
            context=context,
            status=status,
            message=message,
            output_data=output_data,
            decision=decision,
            metadata=metadata,
        )

    # -----------------------------------------------------------------
    # Test
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

        self._require_run()

        if self.test_logger is None:

            raise RuntimeError(
                "TestLogger is not initialized."
            )

        record = (
            self.test_logger.log_test(
                test_id=test_id,
                description=description,
                status=status,
                inputs=inputs,
                expected=expected,
                actual=actual,
                rtl_version=rtl_version,
                iteration=iteration,
                agent=agent,
                duration_seconds=duration_seconds,
                testbench_code=testbench_code,
                simulation_output=simulation_output,
                error_message=error_message,
                metadata=metadata,
            )
        )

        self.run_manager.add_event(
            event_type="TEST_EXECUTED",
            message=(
                f"{test_id}: "
                f"{record['status']}"
            ),
            data={
                "test_id": test_id,
                "status": record[
                    "status"
                ],
                "iteration": iteration,
            },
        )

        return record

    # -----------------------------------------------------------------
    # Coverage
    # -----------------------------------------------------------------

    def save_coverage(
        self,
        coverage: Dict[str, Any],
    ) -> Path:

        self._require_run()

        path = self.run_manager.save_json(
            "coverage/coverage.json",
            coverage,
        )

        self.run_manager.update_metadata(
            coverage=coverage
        )

        self.run_manager.add_event(
            event_type="COVERAGE_UPDATED",
            message="Coverage evidence updated.",
            data={
                "coverage": coverage
            },
        )

        return path

    # -----------------------------------------------------------------
    # Failure
    # -----------------------------------------------------------------

    def save_failure_analysis(
        self,
        test_id: str,
        failure_data: Dict[str, Any],
    ) -> Path:

        self._require_run()

        path = self.run_manager.save_json(
            f"failures/{test_id}_analysis.json",
            failure_data,
        )

        self.run_manager.add_event(
            event_type="FAILURE_ANALYSIS",
            message=(
                f"Failure analysis recorded for {test_id}."
            ),
            data={
                "test_id": test_id
            },
        )

        return path

    # -----------------------------------------------------------------
    # Generic artifact
    # -----------------------------------------------------------------

    def save_text(
        self,
        relative_path: str,
        content: str,
    ) -> Path:

        self._require_run()

        return self.run_manager.save_text(
            relative_path,
            content,
        )

    def save_json(
        self,
        relative_path: str,
        data: Any,
    ) -> Path:

        self._require_run()

        return self.run_manager.save_json(
            relative_path,
            data,
        )

    # -----------------------------------------------------------------
    # Iteration
    # -----------------------------------------------------------------

    def set_iteration(
        self,
        iteration: int,
    ) -> None:

        self._require_run()

        self.run_manager.set_iteration(
            iteration
        )

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    def set_status(
        self,
        status: str,
    ) -> None:

        self._require_run()

        self.run_manager.set_status(
            status
        )

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:

        self._require_run()

        test_summary = (
            self.test_logger.get_summary()
            if self.test_logger
            else {}
        )

        agent_summary = (
            self.agent_logger.get_summary()
            if self.agent_logger
            else {}
        )

        metadata = (
            self.run_manager.load_metadata()
        )

        coverage = metadata.get(
            "coverage",
            {},
        )

        return {
            "run_id": self.run_id,

            "status": metadata.get(
                "status",
                "UNKNOWN",
            ),

            "rtl_version": metadata.get(
                "rtl_version",
                "v1",
            ),

            "iteration": metadata.get(
                "iteration",
                0,
            ),

            "tests": test_summary,

            "agents": agent_summary,

            "coverage": coverage,

            "run_dir": str(
                self.run_dir
            ),
        }

    # -----------------------------------------------------------------
    # Generate final summary
    # -----------------------------------------------------------------

    def save_summary(
        self,
        summary: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Path:

        self._require_run()

        if summary is None:

            summary = self.get_summary()

        summary["generated_at"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        path = self.run_manager.save_json(
            "reports/summary.json",
            summary,
        )

        return path

    # -----------------------------------------------------------------
    # Finish
    # -----------------------------------------------------------------

    def finish(
        self,
        status: str = "COMPLETED",
    ) -> Dict[str, Any]:

        self._require_run()

        self.run_manager.finish_run(
            status
        )

        summary = self.get_summary()

        summary["status"] = (
            str(status).upper()
        )

        self.save_summary(
            summary
        )

        return summary

    # -----------------------------------------------------------------
    # Paths
    # -----------------------------------------------------------------

    def get_run_dir(self) -> Path:

        self._require_run()

        return self.run_dir

    def get_report_dir(self) -> Path:

        self._require_run()

        return self.run_manager.get_report_dir()

    def get_coverage_dir(self) -> Path:

        self._require_run()

        return self.run_manager.get_coverage_dir()
