"""
PragyanAI SiliconAI

Verification scoring engine.

This is a platform heuristic and should not be represented
as an industry certification metric.
"""

from __future__ import annotations

from typing import Any, Dict, List


class VerificationScorer:

    def __init__(
        self,
        test_weight: float = 0.35,
        coverage_weight: float = 0.35,
        mutation_weight: float = 0.15,
        assertion_weight: float = 0.15,
    ):

        self.test_weight = test_weight
        self.coverage_weight = coverage_weight
        self.mutation_weight = mutation_weight
        self.assertion_weight = assertion_weight

    # -----------------------------------------------------------------
    # Test score
    # -----------------------------------------------------------------

    def test_score(
        self,
        tests: List[Dict[str, Any]],
    ) -> float:

        if not tests:
            return 0.0

        passed = sum(
            1
            for test in tests
            if str(
                test.get(
                    "status",
                    "",
                )
            ).upper()
            in {
                "PASS",
                "PASSED",
            }
        )

        return (
            passed
            / len(tests)
            * 100
        )

    # -----------------------------------------------------------------
    # Coverage score
    # -----------------------------------------------------------------

    def coverage_score(
        self,
        coverage: Dict[str, Any],
    ) -> float:

        try:

            return float(
                coverage.get(
                    "overall",
                    0,
                )
            )

        except Exception:

            return 0.0

    # -----------------------------------------------------------------
    # Mutation score
    # -----------------------------------------------------------------

    def mutation_score(
        self,
        coverage: Dict[str, Any],
        mutations: List[Dict[str, Any]] | None = None,
    ) -> float:

        if mutations:

            killed = sum(
                1
                for mutation in mutations
                if str(
                    mutation.get(
                        "status",
                        "",
                    )
                ).upper()
                == "KILLED"
            )

            applicable = sum(
                1
                for mutation in mutations
                if str(
                    mutation.get(
                        "status",
                        "",
                    )
                ).upper()
                in {
                    "KILLED",
                    "SURVIVED",
                }
            )

            if applicable:

                return (
                    killed
                    / applicable
                    * 100
                )

        try:

            return float(
                coverage.get(
                    "mutation",
                    0,
                )
            )

        except Exception:

            return 0.0

    # -----------------------------------------------------------------
    # Assertion score
    # -----------------------------------------------------------------

    def assertion_score(
        self,
        coverage: Dict[str, Any],
    ) -> float:

        try:

            return float(
                coverage.get(
                    "assertion",
                    0,
                )
            )

        except Exception:

            return 0.0

    # -----------------------------------------------------------------
    # Calculate
    # -----------------------------------------------------------------

    def calculate(
        self,
        tests: List[Dict[str, Any]],
        coverage: Dict[str, Any],
        mutations: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:

        test_score = self.test_score(
            tests
        )

        coverage_score = self.coverage_score(
            coverage
        )

        mutation_score = self.mutation_score(
            coverage,
            mutations,
        )

        assertion_score = self.assertion_score(
            coverage
        )

        total = (
            test_score
            * self.test_weight
            + coverage_score
            * self.coverage_weight
            + mutation_score
            * self.mutation_weight
            + assertion_score
            * self.assertion_weight
        )

        return {
            "test_score": round(
                test_score,
                2,
            ),
            "coverage_score": round(
                coverage_score,
                2,
            ),
            "mutation_score": round(
                mutation_score,
                2,
            ),
            "assertion_score": round(
                assertion_score,
                2,
            ),
            "verification_score": round(
                max(
                    0,
                    min(
                        total,
                        100,
                    ),
                ),
                2,
            ),
        }
