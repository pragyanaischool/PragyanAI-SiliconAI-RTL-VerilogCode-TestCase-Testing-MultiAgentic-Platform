"""
PragyanAI SiliconAI

Waveform management utilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


class WaveformManager:

    def __init__(
        self,
        base_dir: str | Path = "verification_logs/waveforms",
    ):

        self.base_dir = Path(
            base_dir
        )

        self.base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # -----------------------------------------------------------------
    # Add waveform dump
    # -----------------------------------------------------------------

    def add_vcd_dump(
        self,
        testbench_code: str,
        filename: str = "waveform.vcd",
    ) -> str:
        """
        Add a simple VCD dump block if one does not exist.
        """

        code = testbench_code or ""

        if "$dumpfile" in code:
            return code

        block = f"""
initial begin
    $dumpfile("{filename}");
    $dumpvars(0);
end
"""

        return code + "\n" + block

    # -----------------------------------------------------------------
    # Locate waveforms
    # -----------------------------------------------------------------

    def find_waveforms(
        self,
        directory: Optional[
            str | Path
        ] = None,
    ) -> List[Path]:

        search_dir = (
            Path(directory)
            if directory
            else self.base_dir
        )

        if not search_dir.exists():
            return []

        patterns = [
            "*.vcd",
            "*.fst",
            "*.wlf",
        ]

        files: List[Path] = []

        for pattern in patterns:

            files.extend(
                search_dir.rglob(pattern)
            )

        return sorted(
            files,
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    # -----------------------------------------------------------------
    # Waveform metadata
    # -----------------------------------------------------------------

    def get_waveform_info(
        self,
        path: str | Path,
    ) -> dict:

        path = Path(path)

        if not path.exists():

            return {
                "exists": False,
                "path": str(path),
            }

        return {
            "exists": True,
            "path": str(path),
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "extension": path.suffix.lower(),
        }

    # -----------------------------------------------------------------
    # Clean filename
    # -----------------------------------------------------------------

    @staticmethod
    def safe_filename(
        value: str,
    ) -> str:

        return re.sub(
            r"[^A-Za-z0-9_.-]",
            "_",
            value,
        )
