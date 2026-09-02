"""
PragyanAI SiliconAI

Assertion analysis utilities.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class AssertionAnalyzer:

    ASSERTION_PATTERNS = [
        r"\bassert\b",
        r"\bassert\s+property\b",
        r"\bproperty\b",
        r"\bcover\s+property\b",
        r"\bassert property\b",
    ]

    def extract_assertions(
        self,
        code: str,
    ) -> List[str]:

        if not code:
            return []

        assertions = []

        lines = code.splitlines()

        for line in lines:

            stripped = line.strip()

            if not stripped:
                continue

            for pattern in self.ASSERTION_PATTERNS:

                if re.search(
                    pattern,
                    stripped,
                    re.IGNORECASE,
                ):

                    assertions.append(
                        stripped
                    )

                    break

        return assertions

    # -----------------------------------------------------------------
    # Analyze
    # -----------------------------------------------------------------

    def analyze(
        self,
        code: str,
    ) -> Dict[str, Any]:

        assertions = (
            self.extract_assertions(
                code
            )
        )

        immediate_assertions = sum(
            1
            for assertion in assertions
            if "assert property"
            not in assertion.lower()
        )

        property_assertions = sum(
            1
            for assertion in assertions
            if "assert property"
            in assertion.lower()
        )

        cover_properties = sum(
            1
            for assertion in assertions
            if "cover property"
            in assertion.lower()
        )

        return {
            "total": len(assertions),
            "immediate_assertions": immediate_assertions,
            "property_assertions": property_assertions,
            "cover_properties": cover_properties,
            "assertions": assertions,
        }

    # -----------------------------------------------------------------
    # Generate basic assertion targets
    # -----------------------------------------------------------------

    def suggest_targets(
        self,
        rtl_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        suggestions = []

        if rtl_analysis.get(
            "reset"
        ):

            suggestions.append(
                {
                    "type": "RESET",
                    "description": (
                        "Verify reset establishes "
                        "the specified initial state."
                    ),
                }
            )

        if rtl_analysis.get(
            "fsm"
        ):

            suggestions.append(
                {
                    "type": "FSM",
                    "description": (
                        "Verify legal FSM state "
                        "transitions."
                    ),
                }
            )

        if rtl_analysis.get(
            "branches"
        ):

            suggestions.append(
                {
                    "type": "BRANCH",
                    "description": (
                        "Verify important branch "
                        "conditions."
                    ),
                }
            )

        return suggestions
