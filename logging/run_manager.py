"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

Run Manager

Responsible for:
- Creating verification runs
- Creating evidence directories
- Maintaining run metadata
- Managing RTL versions
- Managing run status
- Providing paths for logs and artifacts
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class RunManager:
    """
    Manages the lifecycle and filesystem structure of a
    verification run.
    """

    def __init__(
        self,
        base_dir: str | Path = "verification_logs/runs",
    ):
        self.base_dir = Path(base_dir)

        self.base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.run_id: Optional[str] = None
        self.run_dir: Optional[Path] = None

    # -----------------------------------------------------------------
    # Create Run
    # -----------------------------------------------------------------

    def create_run(
        self,
        specification: str = "",
        rtl_version: str = "v1",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new verification run.
        """

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        unique_id = uuid.uuid4().hex[:6].upper()

        self.run_id = (
            f"RUN_{timestamp}_{unique_id}"
        )

        self.run_dir = (
            self.base_dir / self.run_id
        )

        # -------------------------------------------------------------
        # Create directory tree
        # -------------------------------------------------------------

        directories = [
            "rtl",
            "testcases",
            "simulation",
            "failures",
            "coverage",
            "agents",
            "reports",
            "waveforms",
        ]

        for directory in directories:

            (
                self.run_dir / directory
            ).mkdir(
                parents=True,
                exist_ok=True,
            )

        # -------------------------------------------------------------
        # Specification
        # -------------------------------------------------------------

        specification_file = (
            self.run_dir
            / "specification.txt"
        )

        specification_file.write_text(
            specification or "",
            encoding="utf-8",
        )

        # -------------------------------------------------------------
        # Metadata
        # -------------------------------------------------------------

        run_metadata = {
            "run_id": self.run_id,
            "created_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "updated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "status": "CREATED",
            "rtl_version": rtl_version,
            "iteration": 0,
            "specification": specification,
            "tests": [],
            "coverage": {},
            "agent_trace": [],
            "events": [],
        }

        if metadata:
            run_metadata.update(metadata)

        self._write_json(
            self.run_dir / "run.json",
            run_metadata,
        )

        return self.run_id

    # -----------------------------------------------------------------
    # Require active run
    # -----------------------------------------------------------------

    def _require_run(self) -> Path:
        """
        Return current run directory or raise an error.
        """

        if self.run_dir is None:

            raise RuntimeError(
                "No active verification run. "
                "Call create_run() first."
            )

        return self.run_dir

    # -----------------------------------------------------------------
    # Path helpers
    # -----------------------------------------------------------------

    def get_run_dir(self) -> Path:
        """Return active run directory."""

        return self._require_run()

    def get_path(
        self,
        *parts: str,
    ) -> Path:
        """
        Return a path inside the active run.
        """

        return self._require_run().joinpath(
            *parts
        )

    def get_rtl_dir(self) -> Path:
        return self.get_path("rtl")

    def get_testcase_dir(self) -> Path:
        return self.get_path("testcases")

    def get_simulation_dir(self) -> Path:
        return self.get_path("simulation")

    def get_failure_dir(self) -> Path:
        return self.get_path("failures")

    def get_coverage_dir(self) -> Path:
        return self.get_path("coverage")

    def get_agent_dir(self) -> Path:
        return self.get_path("agents")

    def get_report_dir(self) -> Path:
        return self.get_path("reports")

    def get_waveform_dir(self) -> Path:
        return self.get_path("waveforms")

    # -----------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------

    def load_metadata(self) -> Dict[str, Any]:
        """Load run.json."""

        run_dir = self._require_run()

        path = run_dir / "run.json"

        if not path.exists():
            return {}

        return self._read_json(
            path,
            {},
        )

    def save_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> None:
        """Overwrite run metadata."""

        run_dir = self._require_run()

        metadata["updated_at"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        self._write_json(
            run_dir / "run.json",
            metadata,
        )

    def update_metadata(
        self,
        **updates: Any,
    ) -> Dict[str, Any]:
        """
        Update selected metadata fields.
        """

        metadata = self.load_metadata()

        metadata.update(updates)

        self.save_metadata(
            metadata
        )

        return metadata

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    def set_status(
        self,
        status: str,
    ) -> None:
        """
        Set verification run status.
        """

        metadata = self.load_metadata()

        metadata["status"] = str(
            status
        ).upper()

        self.save_metadata(
            metadata
        )

    def get_status(self) -> str:
        """
        Get current verification status.
        """

        metadata = self.load_metadata()

        return str(
            metadata.get(
                "status",
                "UNKNOWN",
            )
        )

    # -----------------------------------------------------------------
    # Iteration
    # -----------------------------------------------------------------

    def set_iteration(
        self,
        iteration: int,
    ) -> None:

        self.update_metadata(
            iteration=int(iteration)
        )

    def get_iteration(self) -> int:

        metadata = self.load_metadata()

        try:
            return int(
                metadata.get(
                    "iteration",
                    0,
                )
            )
        except Exception:
            return 0

    # -----------------------------------------------------------------
    # RTL version
    # -----------------------------------------------------------------

    def save_rtl(
        self,
        rtl_code: str,
        version: Optional[str] = None,
    ) -> Path:
        """
        Save RTL with version information.
        """

        run_dir = self._require_run()

        if version is None:

            current_iteration = (
                self.get_iteration()
            )

            version = (
                f"v{max(current_iteration, 1)}"
            )

        rtl_dir = (
            run_dir / "rtl"
        )

        rtl_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"design_{version}.v"
        )

        path = rtl_dir / filename

        path.write_text(
            rtl_code or "",
            encoding="utf-8",
        )

        self.update_metadata(
            rtl_version=version
        )

        # Maintain a convenient final/latest copy.
        latest = (
            rtl_dir / "design_latest.v"
        )

        latest.write_text(
            rtl_code or "",
            encoding="utf-8",
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

        path = (
            self._require_run()
            / filename
        )

        path.write_text(
            testbench_code or "",
            encoding="utf-8",
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
        """
        Save arbitrary text evidence.
        """

        path = (
            self._require_run()
            / relative_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            content or "",
            encoding="utf-8",
        )

        return path

    def save_json(
        self,
        relative_path: str,
        data: Any,
    ) -> Path:
        """
        Save arbitrary JSON evidence.
        """

        path = (
            self._require_run()
            / relative_path
        )

        self._write_json(
            path,
            data,
        )

        return path

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------

    def add_event(
        self,
        event_type: str,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add an event to run.json.
        """

        metadata = self.load_metadata()

        event = {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "type": event_type,
            "message": message,
            "data": data or {},
        }

        events = metadata.get(
            "events",
            [],
        )

        if not isinstance(events, list):
            events = []

        events.append(event)

        metadata["events"] = events

        self.save_metadata(
            metadata
        )

        return event

    # -----------------------------------------------------------------
    # Finish run
    # -----------------------------------------------------------------

    def finish_run(
        self,
        status: str = "COMPLETED",
    ) -> None:

        self.set_status(
            status
        )

        self.add_event(
            event_type="RUN_FINISHED",
            message=(
                f"Verification run finished "
                f"with status {status}"
            ),
        )

    # -----------------------------------------------------------------
    # JSON helpers
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

    @staticmethod
    def _read_json(
        path: Path,
        default: Any,
    ) -> Any:

        try:

            with path.open(
                "r",
                encoding="utf-8",
            ) as f:

                return json.load(f)

        except Exception:

            return default
