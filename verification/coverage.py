"""
PragyanAI SiliconAI

Coverage analysis utilities.
"""

from __future__ import annotations

from typing import Any, Dict, List


class CoverageAnalyzer:

    METRICS = [
        "line",
        "branch",
        "toggle",
        "fsm",
        "functional",
        "assertion",
        "mutation",
    ]

    def __init__(
        self,
        target: float = 95.0,
    ):

        self.target = float(
            target
        )

    # -----------------------------------------------------------------
    # Normalize
    # -----------------------------------------------------------------

    def normalize(
        self,
        coverage: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = {}

        for metric in self.METRICS:

            value = coverage.get(
                metric,
                0,
            )

            try:
                value = float(value)
            except Exception:
                value = 0.0

            result[metric] = max(
                0.0,
                min(
                    value,
                    100.0,
                ),
            )

        explicit_overall = coverage.get(
            "overall"
        )

        if explicit_overall is not None:

            try:

                overall = float(
                    explicit_overall
                )

                proxy = False

            except Exception:

                overall = self._calculate_overall(
                    result
                )

                proxy = True

        else:

            overall = self._calculate_overall(
                result
            )

            proxy = True

        result["overall"] = round(
            overall,
            2,
        )

        result["overall_proxy"] = proxy

        result["gaps"] = coverage.get(
            "gaps",
            [],
        ) or []

        result["recommended_tests"] = (
            coverage.get(
                "recommended_tests",
                [],
            )
            or []
        )

        return result

    # -----------------------------------------------------------------
    # Calculate overall
    # -----------------------------------------------------------------

    def _calculate_overall(
        self,
        coverage: Dict[str, float],
    ) -> float:

        values = [
            coverage.get(
                metric,
                0.0,
            )
            for metric in [
                "line",
                "branch",
                "toggle",
                "fsm",
                "functional",
                "assertion",
            ]
        ]

        valid = [
            value
            for value in values
            if value > 0
        ]

        if not valid:
            return 0.0

        return sum(valid) / len(valid)

    # -----------------------------------------------------------------
    # Find gaps
    # -----------------------------------------------------------------

    def find_gaps(
        self,
        coverage: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        normalized = self.normalize(
            coverage
        )

        gaps = []

        for metric in self.METRICS:

            if metric == "mutation":
                continue

            value = normalized.get(
                metric,
                0.0,
            )

            if value < self.target:

                gaps.append(
                    {
                        "id": (
                            f"GAP_{metric.upper()}"
                        ),
                        "type": (
                            "COVERAGE_GAP"
                        ),
                        "metric": metric,
                        "value": value,
                        "target": self.target,
                        "severity": (
                            "HIGH"
                            if value < 80
                            else "MEDIUM"
                        ),
                        "description": (
                            f"{metric.title()} coverage "
                            f"is {value:.2f}%, below the "
                            f"{self.target:.2f}% target."
                        ),
                        "recommendation": (
                            f"Generate targeted tests "
                            f"for {metric} coverage."
                        ),
                    }
                )

        # Preserve explicit AI-detected gaps.

        for gap in normalized.get(
            "gaps",
            [],
        ):

            if gap not in gaps:
                gaps.append(gap)

        return gaps

    # -----------------------------------------------------------------
    # Analyze
    # -----------------------------------------------------------------

    def analyze(
        self,
        coverage: Dict[str, Any],
    ) -> Dict[str, Any]:

        normalized = self.normalize(
            coverage
        )

        gaps = self.find_gaps(
            normalized
        )

        normalized["gaps"] = gaps

        normalized["closure_status"] = (
            "CLOSED"
            if (
                normalized["overall"]
                >= self.target
                and not gaps
            )
            else "OPEN"
        )

        return normalized
