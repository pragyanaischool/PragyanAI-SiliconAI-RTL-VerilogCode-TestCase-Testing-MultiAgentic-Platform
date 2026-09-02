"""
PragyanAI SiliconAI

Mutation testing analysis.

The module provides:
- Mutation definitions
- Mutation result tracking
- Mutation score calculation

Actual RTL mutation execution can be connected to
Icarus/Verilator later.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MutationAnalyzer:

    MUTATION_TYPES = [
        "COMPARISON_OPERATOR",
        "EQUALITY_OPERATOR",
        "CONDITION_INVERSION",
        "ARITHMETIC_OPERATOR",
        "RESET_VALUE",
        "ENABLE_REMOVAL",
        "STATE_TRANSITION",
        "CONSTANT_CHANGE",
        "BIT_INDEX",
        "PRIORITY_CHANGE",
        "ASSIGNMENT_REMOVAL",
    ]

    def generate_candidates(
        self,
        rtl_code: str,
        rtl_analysis: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate mutation candidates.

        This method does not modify RTL.
        """

        candidates = []

        analysis = rtl_analysis or {}

        branches = analysis.get(
            "branches",
            [],
        )

        corner_cases = analysis.get(
            "corner_cases",
            [],
        )

        candidate_types = []

        if branches:

            candidate_types.extend(
                [
                    "COMPARISON_OPERATOR",
                    "CONDITION_INVERSION",
                ]
            )

        if corner_cases:

            candidate_types.extend(
                [
                    "CONSTANT_CHANGE",
                    "RESET_VALUE",
                ]
            )

        candidate_types.extend(
            [
                "ARITHMETIC_OPERATOR",
                "ENABLE_REMOVAL",
                "STATE_TRANSITION",
            ]
        )

        candidate_types = list(
            dict.fromkeys(
                candidate_types
            )
        )

        for index, mutation_type in enumerate(
            candidate_types[:10],
            start=1,
        ):

            candidates.append(
                {
                    "mutation_id": (
                        f"M{index:03d}"
                    ),
                    "type": mutation_type,
                    "description": (
                        f"Candidate {mutation_type} "
                        f"mutation."
                    ),
                    "status": "CANDIDATE",
                    "safe_to_apply": False,
                }
            )

        return candidates

    # -----------------------------------------------------------------
    # Record result
    # -----------------------------------------------------------------

    def record_result(
        self,
        mutation: Dict[str, Any],
        killed: bool,
        detector_test: str = "",
        evidence: str = "",
    ) -> Dict[str, Any]:

        result = dict(
            mutation
        )

        result["status"] = (
            "KILLED"
            if killed
            else "SURVIVED"
        )

        result["detector_test"] = (
            detector_test
        )

        result["evidence"] = evidence

        return result

    # -----------------------------------------------------------------
    # Score
    # -----------------------------------------------------------------

    def calculate_score(
        self,
        mutations: List[Dict[str, Any]],
    ) -> float:

        if not mutations:
            return 0.0

        applicable = [
            mutation
            for mutation in mutations
            if str(
                mutation.get(
                    "status",
                    ""
                )
            ).upper()
            in {
                "KILLED",
                "SURVIVED",
            }
        ]

        if not applicable:
            return 0.0

        killed = sum(
            1
            for mutation in applicable
            if str(
                mutation.get(
                    "status",
                    ""
                )
            ).upper()
            == "KILLED"
        )

        return round(
            killed
            / len(applicable)
            * 100,
            2,
        )

    # -----------------------------------------------------------------
    # Surviving mutations
    # -----------------------------------------------------------------

    def surviving_mutations(
        self,
        mutations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        return [
            mutation
            for mutation in mutations
            if str(
                mutation.get(
                    "status",
                    ""
                )
            ).upper()
            == "SURVIVED"
        ]
