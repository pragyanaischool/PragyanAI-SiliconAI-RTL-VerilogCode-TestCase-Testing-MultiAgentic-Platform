"""
PragyanAI SiliconAI
Autonomous RTL Verification Platform

Agent Logger

Records:
- Agent execution
- Agent input summary
- Agent output summary
- Decisions
- Status
- Iteration
- Duration
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AgentLogger:
    """
    Logs AI-agent activity for a verification run.
    """

    def __init__(
        self,
        run_dir: str | Path,
    ):

        self.run_dir = Path(
            run_dir
        )

        self.agent_dir = (
            self.run_dir / "agents"
        )

        self.agent_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.trace_file = (
            self.agent_dir
            / "agent_trace.json"
        )

        if not self.trace_file.exists():

            self._write_json(
                self.trace_file,
                [],
            )

    # -----------------------------------------------------------------
    # Agent execution
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

        record = {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),

            "agent": agent,

            "status": str(
                status
            ).upper(),

            "message": message,

            "decision": decision,

            "iteration": iteration,

            "duration_seconds": round(
                float(duration_seconds),
                4,
            ),

            "input": self._compact_data(
                input_data
            ),

            "output": self._compact_data(
                output_data
            ),

            "metadata": metadata or {},
        }

        trace = self.load_trace()

        trace.append(
            record
        )

        self._write_json(
            self.trace_file,
            trace,
        )

        # Individual agent event file
        safe_name = self._safe_filename(
            agent
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        event_file = (
            self.agent_dir
            / f"{timestamp}_{safe_name}.json"
        )

        self._write_json(
            event_file,
            record,
        )

        return record

    # -----------------------------------------------------------------
    # Start / finish helpers
    # -----------------------------------------------------------------

    def start_agent(
        self,
        agent: str,
        iteration: int = 0,
        input_data: Any = None,
    ) -> Dict[str, Any]:
        """
        Record the beginning of an agent execution.

        Returns a context dictionary containing a timer.
        """

        start_time = time.perf_counter()

        record = {
            "agent": agent,
            "iteration": iteration,
            "input_data": input_data,
            "start_time": start_time,
            "started_at": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        return record

    def finish_agent(
        self,
        context: Dict[str, Any],
        status: str = "COMPLETED",
        message: str = "",
        output_data: Any = None,
        decision: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        start_time = context.get(
            "start_time"
        )

        if start_time:

            duration = (
                time.perf_counter()
                - start_time
            )

        else:

            duration = 0.0

        return self.log_agent(
            agent=context.get(
                "agent",
                "Unknown Agent",
            ),
            status=status,
            message=message,
            input_data=context.get(
                "input_data"
            ),
            output_data=output_data,
            decision=decision,
            iteration=context.get(
                "iteration",
                0,
            ),
            duration_seconds=duration,
            metadata=metadata,
        )

    # -----------------------------------------------------------------
    # Convenience methods
    # -----------------------------------------------------------------

    def log_start(
        self,
        agent: str,
        iteration: int = 0,
        message: str = "",
    ) -> Dict[str, Any]:

        return self.log_agent(
            agent=agent,
            status="STARTED",
            message=message,
            iteration=iteration,
        )

    def log_success(
        self,
        agent: str,
        message: str = "",
        output_data: Any = None,
        iteration: int = 0,
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:

        return self.log_agent(
            agent=agent,
            status="COMPLETED",
            message=message,
            output_data=output_data,
            iteration=iteration,
            duration_seconds=duration_seconds,
        )

    def log_failure(
        self,
        agent: str,
        message: str = "",
        output_data: Any = None,
        iteration: int = 0,
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:

        return self.log_agent(
            agent=agent,
            status="FAILED",
            message=message,
            output_data=output_data,
            iteration=iteration,
            duration_seconds=duration_seconds,
        )

    # -----------------------------------------------------------------
    # Load trace
    # -----------------------------------------------------------------

    def load_trace(self) -> list:

        if not self.trace_file.exists():
            return []

        try:

            with self.trace_file.open(
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
    # Agent summary
    # -----------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:

        trace = self.load_trace()

        completed = 0
        failed = 0
        running = 0

        for record in trace:

            status = str(
                record.get(
                    "status",
                    "",
                )
            ).upper()

            if status in {
                "COMPLETED",
                "PASSED",
            }:

                completed += 1

            elif status in {
                "FAILED",
                "ERROR",
            }:

                failed += 1

            elif status in {
                "RUNNING",
                "STARTED",
            }:

                running += 1

        return {
            "total": len(trace),
            "completed": completed,
            "failed": failed,
            "running": running,
        }

    # -----------------------------------------------------------------
    # Compact data
    # -----------------------------------------------------------------

    @staticmethod
    def _compact_data(
        data: Any,
        max_chars: int = 5000,
    ) -> Any:
        """
        Prevent huge LLM prompts/results from being copied
        into the agent trace.
        """

        if data is None:
            return None

        if isinstance(data, str):

            if len(data) <= max_chars:
                return data

            return (
                data[:max_chars]
                + "\n...[TRUNCATED]..."
            )

        try:

            serialized = json.dumps(
                data,
                ensure_ascii=False,
                default=str,
            )

            if len(serialized) <= max_chars:
                return data

            return (
                serialized[:max_chars]
                + "\n...[TRUNCATED]..."
            )

        except Exception:

            return str(data)[:max_chars]

    # -----------------------------------------------------------------
    # Filename helper
    # -----------------------------------------------------------------

    @staticmethod
    def _safe_filename(
        value: str,
    ) -> str:

        allowed = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789_-"
        )

        return "".join(
            c if c in allowed else "_"
            for c in str(value)
        )

    # -----------------------------------------------------------------
    # JSON helper
    # -----------------------------------------------------------------

    @staticmethod
    def _write_json(
        path: Path,
        data: Any,
    ) -> None:

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
