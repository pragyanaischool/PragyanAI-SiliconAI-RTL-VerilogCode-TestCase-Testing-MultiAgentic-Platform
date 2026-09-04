"""
PragyanAI SiliconAI
===================

Central activity and artifact logger for the Agentic RTL Verification
Platform.

Every verification run gets an isolated directory containing:

    - workflow.log
    - agent_activity.jsonl
    - agent-specific directories
    - source RTL
    - generated tests
    - generated testbench
    - compiler output
    - simulator output
    - coverage
    - mutation results
    - formal results
    - repair results
    - judge results
    - final report

The logger is intentionally independent of LangGraph so that every agent
can use it without creating circular dependencies.
"""

from __future__ import annotations

import json
import logging
import re
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


# =============================================================================
# LOGGER
# =============================================================================

LOGGER = logging.getLogger("PragyanAI.activity")


# =============================================================================
# HELPERS
# =============================================================================

def _utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str, fallback: str = "artifact") -> str:
    """
    Convert arbitrary text into a filesystem-safe name.
    """

    value = str(value or "").strip()

    if not value:
        return fallback

    value = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "_",
        value,
    )

    return value[:120] or fallback


def _json_safe(value: Any) -> Any:
    """
    Convert common Python values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(k): _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _json_safe(v)
            for v in value
        ]

    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


# =============================================================================
# ACTIVITY LOGGER
# =============================================================================

class ActivityLogger:
    """
    Per-verification-run activity and artifact logger.
    """

    def __init__(
        self,
        run_dir: Path | str,
        run_id: Optional[str] = None,
    ) -> None:

        self.run_dir = Path(run_dir)
        self.run_id = run_id or self.run_dir.name

        self.run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.activity_file = (
            self.run_dir / "agent_activity.jsonl"
        )

        self.workflow_log = (
            self.run_dir / "workflow.log"
        )

        self.logger = logging.getLogger(
            f"PragyanAI.activity.{self.run_id}"
        )

        self._configure_file_logger()

        self.log_activity(
            agent="SYSTEM",
            activity="RUN_INITIALIZED",
            status="STARTED",
            message="Verification run initialized.",
        )

    # =========================================================================
    # LOGGER SETUP
    # =========================================================================

    def _configure_file_logger(self) -> None:
        """
        Configure a dedicated run-level log file.
        """

        handler_exists = False

        for handler in self.logger.handlers:

            if isinstance(
                handler,
                logging.FileHandler,
            ):
                handler_exists = True
                break

        if handler_exists:
            return

        try:

            handler = logging.FileHandler(
                self.workflow_log,
                encoding="utf-8",
            )

            formatter = logging.Formatter(
                fmt=(
                    "%(asctime)s | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "%(message)s"
                ),
                datefmt="%Y-%m-%dT%H:%M:%S",
            )

            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

            self.logger.setLevel(
                logging.INFO
            )

            self.logger.propagate = False

        except Exception:
            # Logging must never crash verification.
            pass

    # =========================================================================
    # DIRECTORY
    # =========================================================================

    def agent_dir(
        self,
        agent: str,
        step: Optional[int] = None,
    ) -> Path:
        """
        Return/create an agent-specific directory.
        """

        prefix = ""

        if step is not None:
            prefix = f"{step:02d}_"

        directory = self.run_dir / (
            prefix + _safe_name(agent)
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    # =========================================================================
    # ACTIVITY
    # =========================================================================

    def log_activity(
        self,
        agent: str,
        activity: str,
        status: str = "INFO",
        message: str = "",
        step: Optional[int] = None,
        iteration: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record one structured agent activity.
        """

        event = {
            "timestamp": _utc_timestamp(),
            "run_id": self.run_id,
            "event_id": uuid.uuid4().hex[:12],
            "agent": agent,
            "activity": activity,
            "status": status,
            "message": message,
            "step": step,
            "iteration": iteration,
            "duration_ms": duration_ms,
            "metadata": _json_safe(metadata or {}),
        }

        try:

            with self.activity_file.open(
                "a",
                encoding="utf-8",
            ) as handle:

                handle.write(
                    json.dumps(
                        event,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        except Exception as exc:

            try:
                self.logger.exception(
                    "Failed writing activity event: %s",
                    exc,
                )
            except Exception:
                pass

        try:

            self.logger.info(
                "%s | %s | %s | %s",
                agent,
                activity,
                status,
                message,
            )

        except Exception:
            pass

        return event

    # =========================================================================
    # ARTIFACT WRITING
    # =========================================================================

    def write_text(
        self,
        agent: str,
        filename: str,
        content: Any,
        step: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> Optional[Path]:
        """
        Dump text/code/log content to the agent directory.
        """

        try:

            directory = self.agent_dir(
                agent,
                step=step,
            )

            path = directory / _safe_name(
                filename,
                fallback="artifact.txt",
            )

            if content is None:
                content = ""

            if not isinstance(content, str):
                content = str(content)

            path.write_text(
                content,
                encoding=encoding,
            )

            self.log_activity(
                agent=agent,
                activity="ARTIFACT_WRITTEN",
                status="SUCCESS",
                message=f"Wrote artifact: {path.name}",
                step=step,
                metadata={
                    "artifact": str(path.relative_to(self.run_dir)),
                    "bytes": path.stat().st_size,
                },
            )

            return path

        except Exception as exc:

            self.log_activity(
                agent=agent,
                activity="ARTIFACT_WRITE_FAILED",
                status="ERROR",
                message=str(exc),
                step=step,
            )

            return None

    # =========================================================================
    # JSON ARTIFACT
    # =========================================================================

    def write_json(
        self,
        agent: str,
        filename: str,
        data: Any,
        step: Optional[int] = None,
    ) -> Optional[Path]:
        """
        Write structured JSON artifact.
        """

        try:

            serialized = json.dumps(
                _json_safe(data),
                indent=2,
                ensure_ascii=False,
                default=str,
            )

            return self.write_text(
                agent=agent,
                filename=filename,
                content=serialized,
                step=step,
            )

        except Exception as exc:

            self.log_activity(
                agent=agent,
                activity="JSON_WRITE_FAILED",
                status="ERROR",
                message=str(exc),
                step=step,
            )

            return None

    # =========================================================================
    # CODE ARTIFACT
    # =========================================================================

    def write_code(
        self,
        agent: str,
        filename: str,
        code: str,
        step: Optional[int] = None,
    ) -> Optional[Path]:
        """
        Write generated source code.

        Useful for:
            - RTL
            - Verilog
            - SystemVerilog
            - test cases
            - testbenches
            - assertions
            - mutations
        """

        return self.write_text(
            agent=agent,
            filename=filename,
            content=code,
            step=step,
        )

    # =========================================================================
    # AGENT START
    # =========================================================================

    def agent_started(
        self,
        agent: str,
        activity: str = "EXECUTION_STARTED",
        step: Optional[int] = None,
        iteration: Optional[int] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Log beginning of agent execution.
        """

        return self.log_activity(
            agent=agent,
            activity=activity,
            status="STARTED",
            message=message,
            step=step,
            iteration=iteration,
            metadata=metadata,
        )

    # =========================================================================
    # AGENT COMPLETED
    # =========================================================================

    def agent_completed(
        self,
        agent: str,
        activity: str = "EXECUTION_COMPLETED",
        step: Optional[int] = None,
        iteration: Optional[int] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Log successful agent completion.
        """

        return self.log_activity(
            agent=agent,
            activity=activity,
            status="SUCCESS",
            message=message,
            step=step,
            iteration=iteration,
            duration_ms=duration_ms,
            metadata=metadata,
        )

    # =========================================================================
    # AGENT FAILURE
    # =========================================================================

    def agent_failed(
        self,
        agent: str,
        error: Exception | str,
        step: Optional[int] = None,
        iteration: Optional[int] = None,
        activity: str = "EXECUTION_FAILED",
    ) -> Dict[str, Any]:
        """
        Log an agent exception with traceback.
        """

        if isinstance(error, Exception):
            message = str(error)

            trace = "".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            )

        else:
            message = str(error)
            trace = ""

        return self.log_activity(
            agent=agent,
            activity=activity,
            status="ERROR",
            message=message,
            step=step,
            iteration=iteration,
            metadata={
                "traceback": trace,
            },
        )

    # =========================================================================
    # RUN MANIFEST
    # =========================================================================

    def write_manifest(
        self,
        data: Dict[str, Any],
    ) -> Optional[Path]:
        """
        Write run-level manifest.
        """

        manifest = {
            "run_id": self.run_id,
            "created_at": _utc_timestamp(),
            **_json_safe(data),
        }

        path = self.run_dir / "run_manifest.json"

        try:

            path.write_text(
                json.dumps(
                    manifest,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            return path

        except Exception as exc:

            self.logger.exception(
                "Failed writing run manifest: %s",
                exc,
            )

            return None

    # =========================================================================
    # FINALIZE
    # =========================================================================

    def finalize(
        self,
        status: str,
        verdict: Optional[str] = None,
        message: str = "",
    ) -> None:
        """
        Mark verification run as complete.
        """

        self.log_activity(
            agent="SYSTEM",
            activity="RUN_COMPLETED",
            status=status,
            message=message,
            metadata={
                "verdict": verdict,
            },
        )
