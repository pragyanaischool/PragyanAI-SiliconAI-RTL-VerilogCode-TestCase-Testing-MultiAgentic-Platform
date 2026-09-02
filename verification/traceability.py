"""
PragyanAI SiliconAI

Verification traceability manager.

Creates a requirement-to-evidence relationship.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TraceabilityManager:

    def __init__(
        self,
        run_dir: str | Path,
    ):

        self.run_dir = Path(
            run_dir
        )

        self.file = (
            self.run_dir
            / "reports"
            / "traceability.json"
        )

        self.file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file.exists():

            self._write(
                {
                    "requirements": [],
                    "links": [],
                    "updated_at": datetime.now().isoformat(),
                }
            )

    # -----------------------------------------------------------------
    # Add requirement
    # -----------------------------------------------------------------

    def add_requirement(
        self,
        requirement_id: str,
        description: str,
        source: str = "specification",
    ) -> Dict[str, Any]:

        data = self.load()

        requirement = {
            "requirement_id": requirement_id,
            "description": description,
            "source": source,
            "created_at": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        requirements = data.get(
            "requirements",
            [],
        )

        requirements.append(
            requirement
        )

        data["requirements"] = (
            requirements
        )

        self._save(
            data
        )

        return requirement

    # -----------------------------------------------------------------
    # Link evidence
    # -----------------------------------------------------------------

    def link(
        self,
        requirement_id: str,
        artifact_type: str,
        artifact_id: str,
        status: str = "COVERED",
        evidence: str = "",
    ) -> Dict[str, Any]:

        data = self.load()

        link = {
            "requirement_id": requirement_id,
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "status": status,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        links = data.get(
            "links",
            [],
        )

        links.append(
            link
        )

        data["links"] = links

        self._save(
            data
        )

        return link

    # -----------------------------------------------------------------
    # Load
    # -----------------------------------------------------------------

    def load(self) -> Dict[str, Any]:

        if not self.file.exists():

            return {
                "requirements": [],
                "links": [],
            }

        try:

            with self.file.open(
                "r",
                encoding="utf-8",
            ) as f:

                return json.load(f)

        except Exception:

            return {
                "requirements": [],
                "links": [],
            }

    # -----------------------------------------------------------------
    # Requirement status
    # -----------------------------------------------------------------

    def requirement_status(
        self,
        requirement_id: str,
    ) -> Dict[str, Any]:

        data = self.load()

        requirement = next(
            (
                item
                for item in data.get(
                    "requirements",
                    [],
                )
                if item.get(
                    "requirement_id"
                )
                == requirement_id
            ),
            None,
        )

        links = [
            link
            for link in data.get(
                "links",
                [],
            )
            if link.get(
                "requirement_id"
            )
            == requirement_id
        ]

        covered = any(
            str(
                link.get(
                    "status",
                    "",
                )
            ).upper()
            == "COVERED"
            for link in links
        )

        return {
            "requirement": requirement,
            "links": links,
            "covered": covered,
        }

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:

        data = self.load()

        requirements = data.get(
            "requirements",
            [],
        )

        covered = 0

        for requirement in requirements:

            requirement_id = requirement.get(
                "requirement_id"
            )

            status = self.requirement_status(
                requirement_id
            )

            if status["covered"]:
                covered += 1

        total = len(
            requirements
        )

        coverage = (
            covered
            / total
            * 100
            if total
            else 0
        )

        return {
            "total_requirements": total,
            "covered_requirements": covered,
            "uncovered_requirements": (
                total - covered
            ),
            "traceability_coverage": round(
                coverage,
                2,
            ),
        }

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------

    def _save(
        self,
        data: Dict[str, Any],
    ) -> None:

        data["updated_at"] = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        self._write(
            data
        )

    def _write(
        self,
        data: Dict[str, Any],
    ) -> None:

        with self.file.open(
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
