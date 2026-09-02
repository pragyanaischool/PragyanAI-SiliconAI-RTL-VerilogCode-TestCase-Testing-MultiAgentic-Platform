"""
PragyanAI SiliconAI
Verification Planner Agent

Responsibilities:
    1. Convert specification + RTL analysis into a verification plan.
    2. Identify functional verification areas.
    3. Define directed, corner, negative and random tests.
    4. Define reset and clock verification strategy.
    5. Define assertion, coverage, mutation and formal targets.
    6. Prioritize high-risk verification scenarios.
    7. Produce compact structured JSON.

The planner does NOT generate executable testbench code.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_groq import ChatGroq

from config.settings import (
    GROQ_API_KEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    PLANNER_MAX_TOKENS,
    VERIFICATION_TARGET,
    MAX_TEST_SCENARIOS,
)

from config.prompts import (
    load_prompt,
    limit_text,
    compact_json,
    compact_rtl_analysis,
)


class VerificationPlannerAgent:
    """
    AI agent responsible for creating the verification strategy.
    """

    name = "Verification Planner"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or DEFAULT_MODEL

        self.temperature = (
            DEFAULT_TEMPERATURE
            if temperature is None
            else temperature
        )

        self.max_tokens = (
            PLANNER_MAX_TOKENS
            if max_tokens is None
            else max_tokens
        )

        self.llm = None

        if self.api_key:
            self.llm = ChatGroq(
                api_key=self.api_key,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def plan(
        self,
        rtl_analysis: Optional[Dict[str, Any]] = None,
        specification: str = "",
        rtl_code: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a verification plan.

        Returns:

            {
                "verification_plan": {...},
                "status": "COMPLETED"
            }
        """

        rtl_analysis = rtl_analysis or {}

        # Always create a deterministic baseline plan.
        baseline = self._build_baseline_plan(
            rtl_analysis=rtl_analysis,
            specification=specification,
        )

        # LLM unavailable -> baseline plan.
        if self.llm is None:
            baseline["completion_criteria"] = (
                self._build_completion_criteria()
            )

            return {
                "verification_plan": baseline,
                "status": "COMPLETED",
                "warnings": [
                    "Groq API key not configured; "
                    "baseline verification plan generated."
                ],
                "messages": [
                    "Verification Planner completed using baseline analysis."
                ],
            }

        try:

            prompt = self._build_prompt(
                rtl_analysis=rtl_analysis,
                specification=specification,
                rtl_code=rtl_code,
                baseline=baseline,
            )

            response = self.llm.invoke(
                prompt
            )

            content = self._extract_content(
                response
            )

            ai_plan = self._parse_json(
                content
            )

            if not isinstance(
                ai_plan,
                dict,
            ):
                ai_plan = {}

            result = self._merge_plan(
                baseline,
                ai_plan,
            )

            return {
                "verification_plan": result,
                "status": "COMPLETED",
                "messages": [
                    "Verification Planner completed successfully."
                ],
            }

        except Exception as exc:

            return {
                "verification_plan": baseline,
                "status": "COMPLETED",
                "warnings": [
                    "AI verification planning failed; "
                    "baseline plan retained.",
                    limit_text(
                        str(exc),
                        1200,
                    ),
                ],
                "messages": [
                    "Verification Planner used fallback planning."
                ],
            }

    # ========================================================
    # LANGGRAPH NODE
    # ========================================================

    def __call__(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        LangGraph-compatible node.
        """

        result = self.plan(
            rtl_analysis=state.get(
                "rtl_analysis",
                {},
            ),
            specification=state.get(
                "specification",
                state.get("prompt", ""),
            ),
            rtl_code=state.get(
                "rtl_code",
                "",
            ),
        )

        return {
            "verification_plan": result.get(
                "verification_plan",
                {},
            ),
            "status": result.get(
                "status",
                "COMPLETED",
            ),
            "messages": result.get(
                "messages",
                [],
            ),
            "warnings": result.get(
                "warnings",
                [],
            ),
        }

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        rtl_analysis: Dict[str, Any],
        specification: str,
        rtl_code: str,
        baseline: Dict[str, Any],
    ) -> str:
        """
        Build compact planner prompt.

        Full RTL is deliberately not sent unless needed.
        The RTL Analyzer's structured representation is the
        primary planning context.
        """

        system_prompt = load_prompt(
            "verification_planning"
        )

        if not system_prompt:
            system_prompt = self._default_prompt()

        spec = limit_text(
            specification,
            max_chars=8000,
            keep="both",
        )

        analysis = compact_rtl_analysis(
            rtl_analysis,
            max_chars=6000,
        )

        baseline_text = compact_json(
            baseline,
            max_chars=5000,
        )

        # Only provide a limited RTL excerpt.
        rtl_excerpt = limit_text(
            rtl_code,
            max_chars=12000,
            keep="both",
        )

        return f"""
{system_prompt}

IMPORTANT:
Return ONLY valid JSON.
Do not return Markdown.
Do not use ```json.
Do not invent functionality that is not supported by the RTL
or specification.

The verification plan must be:
- practical
- prioritized
- executable by downstream test-generation agents
- compact
- specification-aware
- risk-driven

SPECIFICATION:
{spec}

RTL ANALYSIS:
{analysis}

BASELINE PLAN:
{baseline_text}

RTL EXCERPT:
{rtl_excerpt}
"""

    # ========================================================
    # DEFAULT PROMPT
    # ========================================================

    @staticmethod
    def _default_prompt() -> str:
        return """
You are a senior semiconductor verification architect.

Create a verification plan for the supplied RTL.

Consider:
- functional behavior
- interfaces
- reset
- clocking
- state transitions
- boundary conditions
- error conditions
- illegal inputs
- protocol violations
- timing-sensitive behavior
- assertions
- coverage
- mutation testing
- formal verification
- adversarial testing

Prioritize tests according to verification risk.

Return JSON only.
"""

    # ========================================================
    # BASELINE PLAN
    # ========================================================

    def _build_baseline_plan(
        self,
        rtl_analysis: Dict[str, Any],
        specification: str,
    ) -> Dict[str, Any]:
        """
        Build a deterministic verification plan.

        This provides useful behavior even when the LLM is
        unavailable or rate-limited.
        """

        inputs = self._names(
            rtl_analysis.get(
                "inputs",
                [],
            )
        )

        outputs = self._names(
            rtl_analysis.get(
                "outputs",
                [],
            )
        )

        clocks = rtl_analysis.get(
            "clocks",
            [],
        )

        resets = rtl_analysis.get(
            "resets",
            [],
        )

        protocols = rtl_analysis.get(
            "protocols",
            [],
        )

        corner_cases = rtl_analysis.get(
            "corner_cases",
            [],
        )

        risks = rtl_analysis.get(
            "potential_risks",
            [],
        )

        state_machine = bool(
            rtl_analysis.get(
                "state_machine",
                False,
            )
        )

        state_elements = rtl_analysis.get(
            "state_elements",
            [],
        )

        functional_areas = []

        # Basic interface verification.
        if inputs:
            functional_areas.append(
                "Input behavior and legal input combinations"
            )

        if outputs:
            functional_areas.append(
                "Output correctness and response behavior"
            )

        if clocks:
            functional_areas.append(
                "Clocked sequential behavior"
            )

        if resets:
            functional_areas.append(
                "Reset assertion, reset release and reset recovery"
            )

        if state_machine:
            functional_areas.append(
                "FSM state transition and illegal-state behavior"
            )

        if state_elements:
            functional_areas.append(
                "Register/state retention and update behavior"
            )

        for protocol in protocols:
            functional_areas.append(
                f"{protocol} protocol compliance"
            )

        if not functional_areas:
            functional_areas.append(
                "Basic functional behavior derived from RTL"
            )

        # Directed tests.
        directed_tests = [
            "Basic legal operation",
            "Reset initialization",
            "Normal input/output operation",
        ]

        if clocks:
            directed_tests.append(
                "Clock-by-clock sequential behavior"
            )

        if state_machine:
            directed_tests.append(
                "State transition verification"
            )

        for protocol in protocols[:4]:
            directed_tests.append(
                f"{protocol} legal transaction sequence"
            )

        # Corner tests.
        corner_tests = [
            "Minimum input value",
            "Maximum input value",
            "Zero/idle condition",
            "Back-to-back transactions",
        ]

        corner_tests.extend(
            corner_cases[:6]
        )

        # Negative tests.
        negative_tests = [
            "Invalid input combination",
            "Protocol violation",
            "Operation while inactive",
        ]

        if resets:
            negative_tests.append(
                "Reset during active operation"
            )

        if state_machine:
            negative_tests.append(
                "Illegal or unexpected state transition"
            )

        # Random testing.
        random_tests = [
            "Constrained random legal inputs",
            "Random boundary-value combinations",
            "Random transaction sequences",
        ]

        if protocols:
            random_tests.append(
                "Random protocol transaction sequences"
            )

        # Reset strategy.
        reset_strategy = []

        if resets:

            for reset in resets[:5]:
                reset_strategy.extend(
                    [
                        f"Assert {reset} before operation",
                        f"Deassert {reset} and verify initialization",
                        f"Assert {reset} during normal operation",
                    ]
                )

        else:
            reset_strategy.append(
                "No explicit reset detected; verify initial behavior."
            )

        # Clock strategy.
        clock_strategy = []

        if clocks:

            for clock in clocks[:5]:
                clock_strategy.extend(
                    [
                        f"Verify behavior on {clock} active edge",
                        f"Verify setup of inputs before {clock} edge",
                        f"Verify outputs/state after {clock} edge",
                    ]
                )

        else:
            clock_strategy.append(
                "No explicit clock detected; treat design as combinational "
                "unless RTL semantics indicate otherwise."
            )

        # Assertion targets.
        assertion_targets = []

        for output in outputs[:10]:
            assertion_targets.append(
                f"Output correctness: {output}"
            )

        for reset in resets[:5]:
            assertion_targets.append(
                f"Reset invariant: {reset}"
            )

        if state_machine:
            assertion_targets.extend(
                [
                    "FSM remains in a legal state",
                    "Valid state transitions occur",
                    "No unexpected state transition",
                ]
            )

        for risk in risks[:5]:
            assertion_targets.append(
                f"Risk condition: {risk}"
            )

        # Mutation strategy.
        mutation_strategy = [
            "Flip conditional operators",
            "Modify comparison boundaries",
            "Change arithmetic operators",
            "Alter reset behavior",
            "Modify state transition logic",
        ]

        # Formal strategy.
        formal_strategy = [
            "Check reset invariant",
            "Check output safety properties",
            "Check state legality",
            "Check protocol invariants",
            "Search for counterexamples on critical behavior",
        ]

        # Red team.
        red_team_strategy = [
            "Stress boundary values",
            "Inject illegal input combinations",
            "Interrupt transactions with reset",
            "Exercise back-to-back operations",
            "Attempt protocol violations",
        ]

        # Priority tests.
        priority_tests = []

        priority_tests.extend(
            directed_tests[:5]
        )

        priority_tests.extend(
            corner_tests[:5]
        )

        priority_tests.extend(
            negative_tests[:4]
        )

        # Deduplicate.
        priority_tests = self._deduplicate(
            priority_tests
        )

        plan = {
            "objective": (
                "Demonstrate that the RTL satisfies the supplied "
                "functional intent across normal, boundary, "
                "negative and adversarial scenarios."
            ),

            "requirements": self._extract_requirements(
                specification
            ),

            "functional_areas": self._deduplicate(
                functional_areas
            ),

            "directed_tests": self._deduplicate(
                directed_tests
            ),

            "random_tests": self._deduplicate(
                random_tests
            ),

            "corner_tests": self._deduplicate(
                corner_tests
            ),

            "negative_tests": self._deduplicate(
                negative_tests
            ),

            "reset_strategy": self._deduplicate(
                reset_strategy
            ),

            "clock_strategy": self._deduplicate(
                clock_strategy
            ),

            "assertion_targets": self._deduplicate(
                assertion_targets
            ),

            "coverage_targets": {
                "line": VERIFICATION_TARGET,
                "branch": VERIFICATION_TARGET,
                "toggle": VERIFICATION_TARGET,
                "fsm": VERIFICATION_TARGET,
                "functional": VERIFICATION_TARGET,
                "assertion": 80.0,
                "mutation": 80.0,
            },

            "mutation_strategy": mutation_strategy,

            "formal_strategy": formal_strategy,

            "red_team_strategy": red_team_strategy,

            "priority_tests": priority_tests[
                :MAX_TEST_SCENARIOS
            ],

            "expected_test_count": min(
                max(
                    len(priority_tests),
                    5,
                ),
                MAX_TEST_SCENARIOS,
            ),

            "completion_criteria": (
                self._build_completion_criteria()
            ),

            "risks": risks[:10],
        }

        return plan

    # ========================================================
    # REQUIREMENT EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_requirements(
        specification: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract simple numbered/bulleted requirements from
        specification text.

        AI planning can refine these later.
        """

        if not specification:
            return []

        lines = specification.splitlines()

        requirements = []

        counter = 1

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # Match:
            # 1. ...
            # 1) ...
            # - ...
            # * ...
            match = re.match(
                r"^(?:\d+[\.\)]|[-*])\s*(.+)$",
                line,
            )

            if match:
                description = match.group(1).strip()

                if description:
                    requirements.append(
                        {
                            "requirement_id": (
                                f"REQ{counter:03d}"
                            ),
                            "description": description,
                            "priority": "MEDIUM",
                            "verification_status": "PLANNED",
                        }
                    )

                    counter += 1

        # If no explicit list exists, use first useful
        # specification paragraph as a requirement.
        if not requirements:

            paragraphs = [
                p.strip()
                for p in specification.split("\n\n")
                if p.strip()
            ]

            for paragraph in paragraphs[:5]:

                requirements.append(
                    {
                        "requirement_id": (
                            f"REQ{counter:03d}"
                        ),
                        "description": limit_text(
                            paragraph,
                            600,
                        ),
                        "priority": "MEDIUM",
                        "verification_status": "PLANNED",
                    }
                )

                counter += 1

        return requirements

    # ========================================================
    # COMPLETION CRITERIA
    # ========================================================

    @staticmethod
    def _build_completion_criteria():
        return [
            "All critical functional scenarios execute.",
            "No blocking test failures remain.",
            "Coverage reaches the configured verification target.",
            "Important coverage gaps have a documented disposition.",
            "Critical assertions pass.",
            "Mutation testing demonstrates meaningful test strength.",
            "Formal checks pass where applicable.",
            "Specification requirements have traceable evidence.",
            "Verification Judge independently approves sign-off.",
        ]

    # ========================================================
    # MERGE AI PLAN
    # ========================================================

    def _merge_plan(
        self,
        baseline: Dict[str, Any],
        ai_plan: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = dict(baseline)

        for key, value in ai_plan.items():

            if value is None:
                continue

            if isinstance(
                value,
                list,
            ):

                if not value:
                    continue

                result[key] = value

            elif isinstance(
                value,
                dict,
            ):

                existing = result.get(
                    key,
                    {},
                )

                if isinstance(
                    existing,
                    dict,
                ):
                    merged = dict(existing)
                    merged.update(value)
                    result[key] = merged
                else:
                    result[key] = value

            else:
                result[key] = value

        # Safety normalization.
        list_fields = [
            "functional_areas",
            "directed_tests",
            "random_tests",
            "corner_tests",
            "negative_tests",
            "reset_strategy",
            "clock_strategy",
            "assertion_targets",
            "mutation_strategy",
            "formal_strategy",
            "red_team_strategy",
            "priority_tests",
            "risks",
            "completion_criteria",
        ]

        for field in list_fields:

            value = result.get(
                field,
                [],
            )

            if not isinstance(
                value,
                list,
            ):
                value = [str(value)]

            result[field] = self._deduplicate(
                value
            )

        # Limit downstream context.
        result["priority_tests"] = result[
            "priority_tests"
        ][:MAX_TEST_SCENARIOS]

        result["directed_tests"] = result[
            "directed_tests"
        ][:MAX_TEST_SCENARIOS]

        result["corner_tests"] = result[
            "corner_tests"
        ][:MAX_TEST_SCENARIOS]

        result["negative_tests"] = result[
            "negative_tests"
        ][:MAX_TEST_SCENARIOS]

        return result

    # ========================================================
    # JSON PARSER
    # ========================================================

    @staticmethod
    def _parse_json(
        content: str,
    ) -> Dict[str, Any]:

        if not content:
            return {}

        text = content.strip()

        text = re.sub(
            r"^```(?:json)?",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```$",
            "",
            text,
        )

        text = text.strip()

        try:

            result = json.loads(
                text
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except json.JSONDecodeError:
            pass

        # Attempt JSON object recovery.
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:

            candidate = text[
                start:end + 1
            ]

            try:

                result = json.loads(
                    candidate
                )

                if isinstance(
                    result,
                    dict,
                ):
                    return result

            except json.JSONDecodeError:
                pass

        return {}

    # ========================================================
    # RESPONSE CONTENT
    # ========================================================

    @staticmethod
    def _extract_content(
        response: Any,
    ) -> str:

        if response is None:
            return ""

        content = getattr(
            response,
            "content",
            response,
        )

        if isinstance(
            content,
            str,
        ):
            return content

        if isinstance(
            content,
            list,
        ):

            parts = []

            for item in content:

                if isinstance(
                    item,
                    dict,
                ):
                    parts.append(
                        str(
                            item.get(
                                "text",
                                "",
                            )
                        )
                    )
                else:
                    parts.append(
                        str(item)
                    )

            return "".join(parts)

        return str(content)

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _names(
        items: List[Any],
    ) -> List[str]:

        names = []

        for item in items or []:

            if isinstance(
                item,
                dict,
            ):
                name = item.get(
                    "name",
                    "",
                )
            else:
                name = str(item)

            if name:
                names.append(
                    str(name)
                )

        return names

    @staticmethod
    def _deduplicate(
        values: List[Any],
    ) -> List[Any]:

        result = []
        seen = set()

        for value in values:

            key = str(
                value
            ).strip().lower()

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            result.append(value)

        return result


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def create_verification_plan(
    rtl_analysis: Optional[Dict[str, Any]] = None,
    specification: str = "",
    rtl_code: str = "",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function for direct use.
    """

    agent = VerificationPlannerAgent(
        api_key=api_key,
    )

    return agent.plan(
        rtl_analysis=rtl_analysis,
        specification=specification,
        rtl_code=rtl_code,
    )


# ============================================================
# FACTORY
# ============================================================

def get_verification_planner(
    api_key: Optional[str] = None,
) -> VerificationPlannerAgent:
    """
    Return a configured Verification Planner agent.
    """

    return VerificationPlannerAgent(
        api_key=api_key,
    )
