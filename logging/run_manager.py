"""
Verification run manager.

Creates isolated directories for every verification execution.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import RUNS_DIR

from .activity_logger import ActivityLogger


def create_run_id() -> str:
    """
    Create a human-readable unique run ID.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    suffix = uuid.uuid4().hex[:8]

    return f"{timestamp}_{suffix}"


def create_verification_run(
    metadata: Optional[Dict[str, Any]] = None,
) -> tuple[str, Path, ActivityLogger]:
    """
    Create a new verification run.
    """

    run_id = create_run_id()

    run_dir = (
        Path(RUNS_DIR)
        / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = ActivityLogger(
        run_dir=run_dir,
        run_id=run_id,
    )

    logger.write_manifest(
        {
            "metadata": metadata or {},
            "status": "initialized",
        }
    )

    return (
        run_id,
        run_dir,
        logger,
    )
