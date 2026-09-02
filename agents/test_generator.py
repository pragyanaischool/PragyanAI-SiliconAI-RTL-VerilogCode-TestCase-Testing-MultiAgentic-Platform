"""
PragyanAI SiliconAI
Test Generator Agent

Responsibilities:
    1. Convert verification plan into executable test scenarios.
    2. Generate directed tests.
    3. Generate boundary/corner tests.
    4. Generate negative/adversarial tests.
    5. Generate reset and protocol tests.
    6. Maintain requirement-to-test traceability.
    7. Assign priority and verification category.
    8. Produce compact structured test specifications.

The agent does NOT generate Verilog/SystemVerilog code.
That responsibility belongs to TestbenchGeneratorAgent.
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
    TEST_GENERATOR_MAX_TOKENS,
    MAX_TEST_SCENARIOS,
)

from config.prompts import (
    load_prompt,
    limit_text,
    compact_json,
    compact_rtl_analysis,
    compact_plan,
    compact_red_team,
    compact_coverage,
)


class TestGeneratorAgent:
    """
    Generates structured verification test scenarios.

    Example output:

        {
            "test_id": "TC001",
            "name": "Reset Initialization",
            "category": "RESET",
            "priority": "CRITICAL",
            "description": "...",
            "preconditions": [...],
            "inputs": {...},
            "sequence": [...],
            "expected_behavior": "...",
            "requirement_ids": ["REQ001"]
        }
    """

    name = "Test Generator"

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
            TEST_GENERATOR_MAX_TOKENS
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

    def generate(
        self,
        verification_plan: Optional[Dict[str, Any]] = None,
        rtl_analysis: Optional[Dict[str, Any]] = None,
        specification: str = "",
        existing_tests: Optional[List[Dict[str, Any]]] = None,
        coverage: Optional[Dict[str, Any]] = None,
        red_team_scenarios: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate verification scenarios.

        Returns:

            {
                "tests": [...],
                "generated_tests": [...],
                "status": "COMPLETED"
            }
        """

        verification_plan = verification_plan or {}
        rtl_analysis = rtl_analysis or {}
        existing_tests = existing_tests or []
        coverage = coverage or {}
        red_team_scenarios = red_team_scenarios or []

        baseline = self._build_baseline_tests(
            verification_plan=verification_plan,
            rtl_analysis=rtl_analysis,
            existing_tests=existing_tests,
            coverage=coverage,
            red_team_scenarios=red_team_scenarios,
        )

        if self.llm is None:

            return {
                "tests": baseline,
                "generated_tests": baseline,
                "status": "COMPLETED",
                "warnings": [
                    "Groq API key not configured; "
                    "baseline test generation used."
                ],
                "messages": [
                    f"Generated {len(baseline)} baseline test scenarios."
                ],
            }

        try:

            prompt = self._build_prompt(
                verification_plan=verification_plan,
                rtl_analysis=rtl_analysis,
                specification=specification,
                existing_tests=existing_tests,
                coverage=coverage,
                red_team_scenarios=red_team_scenarios,
                baseline=baseline,
            )

            response = self.llm.invoke(
                prompt
            )

            content = self._extract_content(
                response
            )

            ai_tests = self._parse_tests(
                content
            )

            if not ai_tests:
                ai_tests = baseline

            merged = self._normalize_tests(
                ai_tests,
                baseline=baseline,
                existing_tests=existing_tests,
            )

            return {
                "tests": merged,
                "generated_tests": merged,
                "status": "COMPLETED",
                "messages": [
                    f"Generated {len(merged)} verification scenarios."
                ],
            }

        except Exception as exc:

            return {
                "tests": baseline,
                "generated_tests": baseline,
                "status": "COMPLETED",
                "warnings": [
                    "AI test generation failed; "
                    "baseline scenarios retained.",
                    limit_text(
                        str(exc),
                        1200,
                    ),
                ],
                "messages": [
                    f"Generated {len(baseline)} fallback test scenarios."
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

        result = self.generate(
            verification_plan=state.get(
                "verification_plan",
                {},
            ),
            rtl_analysis=state.get(
                "rtl_analysis",
                {},
            ),
            specification=state.get(
                "specification",
                state.get("prompt", ""),
            ),
            existing_tests=state.get(
                "tests",
                [],
            ),
            coverage=state.get(
                "coverage",
                {},
            ),
            red_team_scenarios=state.get(
                "red_team_scenarios",
                [],
            ),
        )

        return {
            "tests": result.get(
                "tests",
                [],
            ),
            "generated_tests": result.get(
                "generated_tests",
                [],
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
        verification_plan: Dict[str, Any],
        rtl_analysis: Dict[str, Any],
        specification: str,
        existing_tests: List[Dict[str, Any]],
        coverage: Dict[str, Any],
        red_team_scenarios: List[Dict[str, Any]],
        baseline: List[Dict[str, Any]],
    ) -> str:

        system_prompt = load_prompt(
            "test_generation"
        )

        if not system_prompt:
            system_prompt = self._default_prompt()

        spec = limit_text(
            specification,
            max_chars=7000,
            keep="both",
        )

        analysis = compact_rtl_analysis(
            rtl_analysis,
            max_chars=5000,
        )

        plan = compact_plan(
            verification_plan,
            max_chars=6000,
        )

        coverage_text = compact_coverage(
            coverage,
            max_chars=4000,
        )

        red_team_text = compact_red_team(
            red_team_scenarios,
            max_items=8,
            max_chars=4000,
        )

        existing_text = compact_json(
            self._compact_existing_tests(
                existing_tests
            ),
            max_chars=4000,
        )

        baseline_text = compact_json(
            baseline,
            max_chars=5000,
        )

        return f"""
{system_prompt}

IMPORTANT OUTPUT REQUIREMENTS:

Return ONLY valid JSON.

The JSON must contain:

{{
  "tests": [
    {{
      "test_id": "TC001",
      "name": "...",
      "description": "...",
      "category": "...",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "objective": "...",
      "preconditions": [],
      "inputs": {{}},
      "sequence": [],
      "expected_behavior": "...",
      "expected_outputs": {{}},
      "corner_case": false,
      "negative_test": false,
      "reset_required": false,
      "coverage_target": "...",
      "requirement_ids": [],
      "rationale": "..."
    }}
  ]
}}

Rules:
- Generate at most {MAX_TEST_SCENARIOS} tests.
- Do not generate Verilog.
- Do not invent ports or signals.
- Every test must have a unique test_id.
- Prefer high-value tests over repetitive tests.
- Include reset testing where applicable.
- Include boundary testing.
- Include negative testing where applicable.
- Include back-to-back/consecutive operations where applicable.
- Include protocol testing where applicable.
- Include requirement IDs when requirements exist.
- If coverage gaps are supplied, target them.
- If red-team scenarios are supplied, convert the most important ones
  into executable test scenarios.
- Keep sequences concise.

SPECIFICATION:
{spec}

RTL ANALYSIS:
{analysis}

VERIFICATION PLAN:
{plan}

CURRENT COVERAGE:
{coverage_text}

RED TEAM SCENARIOS:
{red_team_text}

EXISTING TESTS:
{existing_text}

BASELINE TESTS:
{baseline_text}
"""

    # ========================================================
    # DEFAULT PROMPT
    # ========================================================

    @staticmethod
    def _default_prompt() -> str:
        return """
You are a senior RTL verification engineer.

Generate a compact set of high-value verification scenarios.

The tests should cover:
- normal operation
- reset
- boundaries
- corner cases
- invalid inputs
- state transitions
- protocol behavior
- back-to-back transactions
- error handling
- coverage gaps
- adversarial scenarios

Each test must be independently understandable by a
testbench-generation agent.

Return JSON only.
"""

    # ========================================================
    # BASELINE TEST GENERATION
    # ========================================================

    def _build_baseline_tests(
        self,
        verification_plan: Dict[str, Any],
        rtl_analysis: Dict[str, Any],
        existing_tests: List[Dict[str, Any]],
        coverage: Dict[str, Any],
        red_team_scenarios: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        tests: List[Dict[str, Any]] = []

        # ----------------------------------------------------
        # Existing tests are considered first.
        # ----------------------------------------------------

        existing_ids = set()

        for test in existing_tests:

            if not isinstance(
                test,
                dict,
            ):
                continue

            test_id = test.get(
                "test_id"
            )

            if test_id:
                existing_ids.add(
                    str(test_id)
                )

        # ----------------------------------------------------
        # Requirements
        # ----------------------------------------------------

        requirements = verification_plan.get(
            "requirements",
            [],
        )

        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        reset_strategy = verification_plan.get(
            "reset_strategy",
            [],
        )

        if reset_strategy:

            tests.append(
                self._make_test(
                    name="Reset Initialization",
                    description=(
                        "Verify that the design reaches the "
                        "specified initial state after reset."
                    ),
                    category="RESET",
                    priority="CRITICAL",
                    objective=(
                        "Verify deterministic initialization."
                    ),
                    sequence=[
                        {
                            "step": 1,
                            "action": "Apply reset",
                        },
                        {
                            "step": 2,
                            "action": "Hold reset for required cycles",
                        },
                        {
                            "step": 3,
                            "action": "Release reset",
                        },
                        {
                            "step": 4,
                            "action": "Check outputs and state",
                        },
                    ],
                    expected_behavior=(
                        "All reset-defined outputs and state elements "
                        "reach their specified initial values."
                    ),
                    reset_required=True,
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=(
                        "Reset behavior is foundational to sequential "
                        "RTL correctness."
                    ),
                )
            )

        # ----------------------------------------------------
        # Basic operation
        # ----------------------------------------------------

        tests.append(
            self._make_test(
                name="Basic Functional Operation",
                description=(
                    "Verify normal legal operation using "
                    "representative input values."
                ),
                category="FUNCTIONAL",
                priority="CRITICAL",
                objective=(
                    "Establish that the core function operates correctly."
                ),
                sequence=[
                    {
                        "step": 1,
                        "action": "Apply legal input values",
                    },
                    {
                        "step": 2,
                        "action": "Allow design to process inputs",
                    },
                    {
                        "step": 3,
                        "action": "Check outputs",
                    },
                ],
                expected_behavior=(
                    "Outputs match the specified functional behavior."
                ),
                requirement_ids=self._requirement_ids(
                    requirements
                ),
                rationale=(
                    "Baseline functional correctness test."
                ),
            )
        )

        # ----------------------------------------------------
        # Minimum boundary
        # ----------------------------------------------------

        tests.append(
            self._make_test(
                name="Minimum Boundary Values",
                description=(
                    "Exercise minimum legal values on relevant "
                    "data/control inputs."
                ),
                category="BOUNDARY",
                priority="HIGH",
                objective=(
                    "Verify lower-bound behavior."
                ),
                sequence=[
                    {
                        "step": 1,
                        "action": "Drive minimum legal values",
                    },
                    {
                        "step": 2,
                        "action": "Execute normal operation",
                    },
                    {
                        "step": 3,
                        "action": "Check outputs",
                    },
                ],
                expected_behavior=(
                    "Design handles minimum legal values correctly "
                    "without unexpected behavior."
                ),
                corner_case=True,
                requirement_ids=self._requirement_ids(
                    requirements
                ),
                rationale=(
                    "Boundary conditions frequently expose "
                    "width and comparison defects."
                ),
            )
        )

        # ----------------------------------------------------
        # Maximum boundary
        # ----------------------------------------------------

        tests.append(
            self._make_test(
                name="Maximum Boundary Values",
                description=(
                    "Exercise maximum legal values on relevant "
                    "data/control inputs."
                ),
                category="BOUNDARY",
                priority="HIGH",
                objective=(
                    "Verify upper-bound behavior."
                ),
                sequence=[
                    {
                        "step": 1,
                        "action": "Drive maximum legal values",
                    },
                    {
                        "step": 2,
                        "action": "Execute normal operation",
                    },
                    {
                        "step": 3,
                        "action": "Check outputs",
                    },
                ],
                expected_behavior=(
                    "Design handles maximum legal values correctly."
                ),
                corner_case=True,
                requirement_ids=self._requirement_ids(
                    requirements
                ),
                rationale=(
                    "Upper boundaries can reveal overflow and "
                    "off-by-one errors."
                ),
            )
        )

        # ----------------------------------------------------
        # Back-to-back
        # ----------------------------------------------------

        tests.append(
            self._make_test(
                name="Back-to-Back Transactions",
                description=(
                    "Verify consecutive legal operations without "
                    "unnecessary idle cycles."
                ),
                category="SEQUENCE",
                priority="HIGH",
                objective=(
                    "Verify transaction sequencing and state updates."
                ),
                sequence=[
                    {
                        "step": 1,
                        "action": "Apply transaction A",
                    },
                    {
                        "step": 2,
                        "action": "Apply transaction B immediately",
                    },
                    {
                        "step": 3,
                        "action": "Check each result",
                    },
                ],
                expected_behavior=(
                    "Each transaction produces the correct result "
                    "and no transaction is lost or corrupted."
                ),
                requirement_ids=self._requirement_ids(
                    requirements
                ),
                rationale=(
                    "Sequential designs often fail under consecutive "
                    "operations even when isolated tests pass."
                ),
            )
        )

        # ----------------------------------------------------
        # Negative test
        # ----------------------------------------------------

        negative_tests = verification_plan.get(
            "negative_tests",
            [],
        )

        if negative_tests:

            tests.append(
                self._make_test(
                    name="Invalid Input Handling",
                    description=(
                        "Apply an invalid or unsupported input "
                        "combination and observe design behavior."
                    ),
                    category="NEGATIVE",
                    priority="HIGH",
                    objective=(
                        "Verify safe and specified behavior for "
                        "invalid inputs."
                    ),
                    sequence=[
                        {
                            "step": 1,
                            "action": "Enter valid operating state",
                        },
                        {
                            "step": 2,
                            "action": "Apply invalid input combination",
                        },
                        {
                            "step": 3,
                            "action": "Observe outputs and state",
                        },
                    ],
                    expected_behavior=(
                        "The design follows its specified behavior "
                        "for invalid input conditions."
                    ),
                    negative_test=True,
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=(
                        "Negative testing identifies unsafe assumptions "
                        "and missing defensive logic."
                    ),
                )
            )

        # ----------------------------------------------------
        # FSM test
        # ----------------------------------------------------

        if rtl_analysis.get(
            "state_machine",
            False,
        ):

            tests.append(
                self._make_test(
                    name="FSM State Transition",
                    description=(
                        "Exercise valid state transitions and verify "
                        "state-dependent outputs."
                    ),
                    category="FSM",
                    priority="CRITICAL",
                    objective=(
                        "Verify legal FSM transitions."
                    ),
                    sequence=[
                        {
                            "step": 1,
                            "action": "Initialize FSM",
                        },
                        {
                            "step": 2,
                            "action": "Apply transition-triggering inputs",
                        },
                        {
                            "step": 3,
                            "action": "Check resulting state/output",
                        },
                        {
                            "step": 4,
                            "action": "Repeat for important transitions",
                        },
                    ],
                    expected_behavior=(
                        "FSM follows all specified legal state transitions."
                    ),
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=(
                        "FSM transition errors are high-impact RTL defects."
                    ),
                )
            )

            tests.append(
                self._make_test(
                    name="FSM Illegal State Recovery",
                    description=(
                        "Exercise behavior associated with an illegal "
                        "or unexpected FSM state where applicable."
                    ),
                    category="FSM_NEGATIVE",
                    priority="HIGH",
                    objective=(
                        "Verify safe behavior from illegal state conditions."
                    ),
                    sequence=[
                        {
                            "step": 1,
                            "action": "Reach a legal FSM state",
                        },
                        {
                            "step": 2,
                            "action": "Create or model illegal state condition",
                        },
                        {
                            "step": 3,
                            "action": "Observe recovery behavior",
                        },
                    ],
                    expected_behavior=(
                        "The design either prevents illegal states or "
                        "recovers according to the specification."
                    ),
                    negative_test=True,
                    corner_case=True,
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=(
                        "Illegal-state handling is important for robust FSMs."
                    ),
                )
            )

        # ----------------------------------------------------
        # Protocol tests
        # ----------------------------------------------------

        protocols = rtl_analysis.get(
            "protocols",
            [],
        )

        for protocol in protocols[:3]:

            tests.append(
                self._make_test(
                    name=f"{protocol} Protocol Compliance",
                    description=(
                        f"Verify legal {protocol} transaction sequencing."
                    ),
                    category="PROTOCOL",
                    priority="HIGH",
                    objective=(
                        f"Verify {protocol} protocol behavior."
                    ),
                    sequence=[
                        {
                            "step": 1,
                            "action": f"Initiate legal {protocol} transaction",
                        },
                        {
                            "step": 2,
                            "action": "Complete handshake/transaction",
                        },
                        {
                            "step": 3,
                            "action": "Check outputs and completion",
                        },
                    ],
                    expected_behavior=(
                        f"The design complies with the detected "
                        f"{protocol} transaction behavior."
                    ),
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=(
                        f"Protocol compliance is required for {protocol} interfaces."
                    ),
                )
            )

        # ----------------------------------------------------
        # Coverage-driven tests
        # ----------------------------------------------------

        gaps = coverage.get(
            "gaps",
            [],
        )

        for gap in gaps[:4]:

            if isinstance(
                gap,
                dict,
            ):

                description = gap.get(
                    "description",
                    "Coverage gap",
                )

                recommendation = gap.get(
                    "recommendation",
                    "",
                )

                metric = gap.get(
                    "metric",
                    "functional",
                )

                tests.append(
                    self._make_test(
                        name=f"Coverage Gap - {metric}",
                        description=description,
                        category="COVERAGE",
                        priority="HIGH",
                        objective=(
                            "Close an identified verification coverage gap."
                        ),
                        sequence=[
                            {
                                "step": 1,
                                "action": recommendation
                                or "Generate targeted stimulus",
                            },
                            {
                                "step": 2,
                                "action": "Execute the scenario",
                            },
                            {
                                "step": 3,
                                "action": "Measure resulting coverage",
                            },
                        ],
                        expected_behavior=(
                            "The targeted coverage point is exercised "
                            "without introducing functional failures."
                        ),
                        coverage_target=metric,
                        requirement_ids=self._requirement_ids(
                            requirements
                        ),
                        rationale=(
                            "Targeted test generated from measured coverage evidence."
                        ),
                    )
                )

        # ----------------------------------------------------
        # Red-team scenarios
        # ----------------------------------------------------

        for scenario in red_team_scenarios[:3]:

            if not isinstance(
                scenario,
                dict,
            ):
                continue

            name = scenario.get(
                "name",
                "Adversarial Scenario",
            )

            tests.append(
                self._make_test(
                    name=f"Red Team - {name}",
                    description=scenario.get(
                        "description",
                        "Adversarial verification scenario.",
                    ),
                    category="RED_TEAM",
                    priority=scenario.get(
                        "priority",
                        "HIGH",
                    ),
                    objective=(
                        "Stress the design using an adversarial scenario."
                    ),
                    sequence=scenario.get(
                        "sequence",
                        [
                            {
                                "step": 1,
                                "action": "Apply adversarial stimulus",
                            },
                            {
                                "step": 2,
                                "action": "Observe design response",
                            },
                        ],
                    ),
                    expected_behavior=scenario.get(
                        "expected_failure",
                        "Design remains within specified safe behavior.",
                    ),
                    negative_test=True,
                    corner_case=True,
                    coverage_target="adversarial",
                    requirement_ids=self._requirement_ids(
                        requirements
                    ),
                    rationale=scenario.get(
                        "rationale",
                        "Adversarial verification scenario.",
                    ),
                )
            )

        # ----------------------------------------------------
        # Deduplicate and limit.
        # ----------------------------------------------------

        tests = self._deduplicate_tests(
            tests
        )

        return tests[
            :MAX_TEST_SCENARIOS
        ]

    # ========================================================
    # TEST FACTORY
    # ========================================================

    @staticmethod
    def _make_test(
        name: str,
        description: str,
        category: str,
        priority: str,
        objective: str,
        sequence: Optional[List[Dict[str, Any]]] = None,
        expected_behavior: str = "",
        inputs: Optional[Dict[str, Any]] = None,
        expected_outputs: Optional[Dict[str, Any]] = None,
        preconditions: Optional[List[str]] = None,
        corner_case: bool = False,
        negative_test: bool = False,
        reset_required: bool = False,
        coverage_target: str = "",
        requirement_ids: Optional[List[str]] = None,
        rationale: str = "",
    ) -> Dict[str, Any]:

        return {
            "test_id": "",
            "name": name,
            "description": description,
            "category": category,
            "priority": priority,
            "objective": objective,
            "preconditions": preconditions or [],
            "inputs": inputs or {},
            "sequence": sequence or [],
            "expected_behavior": expected_behavior,
            "expected_outputs": expected_outputs or {},
            "corner_case": corner_case,
            "negative_test": negative_test,
            "reset_required": reset_required,
            "coverage_target": coverage_target,
            "requirement_ids": requirement_ids or [],
            "rationale": rationale,
        }

    # ========================================================
    # NORMALIZATION
    # ========================================================

    def _normalize_tests(
        self,
        tests: List[Dict[str, Any]],
        baseline: List[Dict[str, Any]],
        existing_tests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        normalized = []

        # Existing IDs prevent duplicate scenarios where possible.
        used_ids = set()

        for existing in existing_tests:

            if isinstance(
                existing,
                dict,
            ):

                test_id = existing.get(
                    "test_id"
                )

                if test_id:
                    used_ids.add(
                        str(test_id)
                    )

        counter = 1

        # Prefer AI-generated tests.
        for test in tests:

            if not isinstance(
                test,
                dict,
            ):
                continue

            normalized_test = self._normalize_single_test(
                test
            )

            test_id = normalized_test.get(
                "test_id"
            )

            if not test_id or test_id in used_ids:

                while (
                    f"TC{counter:03d}"
                    in used_ids
                ):
                    counter += 1

                test_id = f"TC{counter:03d}"
                counter += 1

            normalized_test[
                "test_id"
            ] = test_id

            used_ids.add(
                test_id
            )

            normalized.append(
                normalized_test
            )

            if len(normalized) >= MAX_TEST_SCENARIOS:
                break

        # If AI generated too few tests, supplement from baseline.
        if len(normalized) < min(
            MAX_TEST_SCENARIOS,
            5,
        ):

            for test in baseline:

                normalized_test = self._normalize_single_test(
                    test
                )

                if not normalized_test:
                    continue

                if self._is_duplicate_test(
                    normalized_test,
                    normalized,
                ):
                    continue

                while (
                    f"TC{counter:03d}"
                    in used_ids
                ):
                    counter += 1

                normalized_test[
                    "test_id"
                ] = f"TC{counter:03d}"

                counter += 1

                normalized.append(
                    normalized_test
                )

                if len(normalized) >= MAX_TEST_SCENARIOS:
                    break

        return normalized

    # ========================================================
    # SINGLE TEST NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_single_test(
        test: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = {
            "test_id": str(
                test.get(
                    "test_id",
                    "",
                )
            ).strip(),

            "name": str(
                test.get(
                    "name",
                    "Unnamed Test",
                )
            ).strip(),

            "description": str(
                test.get(
                    "description",
                    "",
                )
            ).strip(),

            "category": str(
                test.get(
                    "category",
                    "FUNCTIONAL",
                )
            ).upper(),

            "priority": str(
                test.get(
                    "priority",
                    "MEDIUM",
                )
            ).upper(),

            "objective": str(
                test.get(
                    "objective",
                    "",
                )
            ).strip(),

            "preconditions": (
                test.get(
                    "preconditions",
                    [],
                )
                if isinstance(
                    test.get(
                        "preconditions",
                        [],
                    ),
                    list,
                )
                else []
            ),

            "inputs": (
                test.get(
                    "inputs",
                    {},
                )
                if isinstance(
                    test.get(
                        "inputs",
                        {},
                    ),
                    dict,
                )
                else {}
            ),

            "sequence": (
                test.get(
                    "sequence",
                    [],
                )
                if isinstance(
                    test.get(
                        "sequence",
                        [],
                    ),
                    list,
                )
                else []
            ),

            "expected_behavior": str(
                test.get(
                    "expected_behavior",
                    "",
                )
            ).strip(),

            "expected_outputs": (
                test.get(
                    "expected_outputs",
                    {},
                )
                if isinstance(
                    test.get(
                        "expected_outputs",
                        {},
                    ),
                    dict,
                )
                else {}
            ),

            "corner_case": bool(
                test.get(
                    "corner_case",
                    False,
                )
            ),

            "negative_test": bool(
                test.get(
                    "negative_test",
                    False,
                )
            ),

            "reset_required": bool(
                test.get(
                    "reset_required",
                    False,
                )
            ),

            "coverage_target": str(
                test.get(
                    "coverage_target",
                    "",
                )
            ).strip(),

            "requirement_ids": (
                test.get(
                    "requirement_ids",
                    [],
                )
                if isinstance(
                    test.get(
                        "requirement_ids",
                        [],
                    ),
                    list,
                )
                else []
            ),

            "rationale": str(
                test.get(
                    "rationale",
                    "",
                )
            ).strip(),
        }

        # Normalize priority.
        valid_priorities = {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
        }

        if result["priority"] not in valid_priorities:
            result["priority"] = "MEDIUM"

        return result

    # ========================================================
    # EXISTING TEST COMPRESSION
    # ========================================================

    @staticmethod
    def _compact_existing_tests(
        tests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        result = []

        for test in tests[-MAX_TEST_SCENARIOS:]:

            if not isinstance(
                test,
                dict,
            ):
                continue

            result.append(
                {
                    "test_id": test.get(
                        "test_id",
                        "",
                    ),
                    "name": test.get(
                        "name",
                        "",
                    ),
                    "category": test.get(
                        "category",
                        "",
                    ),
                    "status": test.get(
                        "status",
                        "",
                    ),
                }
            )

        return result

    # ========================================================
    # REQUIREMENT IDS
    # ========================================================

    @staticmethod
    def _requirement_ids(
        requirements: List[Any],
    ) -> List[str]:

        ids = []

        for requirement in requirements:

            if isinstance(
                requirement,
                dict,
            ):

                req_id = requirement.get(
                    "requirement_id"
                )

                if req_id:
                    ids.append(
                        str(req_id)
                    )

        return ids[:10]

    # ========================================================
    # DUPLICATE TESTS
    # ========================================================

    @staticmethod
    def _is_duplicate_test(
        test: Dict[str, Any],
        existing: List[Dict[str, Any]],
    ) -> bool:

        name = (
            test.get(
                "name",
                "",
            )
            .strip()
            .lower()
        )

        category = (
            test.get(
                "category",
                "",
            )
            .strip()
            .lower()
        )

        for item in existing:

            item_name = (
                item.get(
                    "name",
                    "",
                )
                .strip()
                .lower()
            )

            item_category = (
                item.get(
                    "category",
                    "",
                )
                .strip()
                .lower()
            )

            if (
                name == item_name
                and category == item_category
            ):
                return True

        return False

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    def _deduplicate_tests(
        self,
        tests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        result = []

        seen = set()

        for test in tests:

            key = (
                str(
                    test.get(
                        "name",
                        "",
                    )
                )
                .strip()
                .lower()
                + "|"
                + str(
                    test.get(
                        "category",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                test
            )

        # Assign deterministic IDs.
        for index, test in enumerate(
            result,
            start=1,
        ):
            test["test_id"] = (
                f"TC{index:03d}"
            )

        return result

    # ========================================================
    # PARSE LLM TESTS
    # ========================================================

    def _parse_tests(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:

        if not content:
            return []

        text = content.strip()

        # Remove markdown fences.
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

        # Case 1: JSON object containing tests.
        try:

            parsed = json.loads(
                text
            )

            if isinstance(
                parsed,
                dict,
            ):

                tests = parsed.get(
                    "tests",
                    [],
                )

                if isinstance(
                    tests,
                    list,
                ):
                    return [
                        item
                        for item in tests
                        if isinstance(
                            item,
                            dict,
                        )
                    ]

            if isinstance(
                parsed,
                list,
            ):

                return [
                    item
                    for item in parsed
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        except json.JSONDecodeError:
            pass

        # Case 2: Recover JSON object.
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:

            candidate = text[
                start:end + 1
            ]

            try:

                parsed = json.loads(
                    candidate
                )

                if isinstance(
                    parsed,
                    dict,
                ):

                    tests = parsed.get(
                        "tests",
                        [],
                    )

                    if isinstance(
                        tests,
                        list,
                    ):
                        return [
                            item
                            for item in tests
                            if isinstance(
                                item,
                                dict,
                            )
                        ]

            except json.JSONDecodeError:
                pass

        # Case 3: Recover JSON array.
        start = text.find("[")
        end = text.rfind("]")

        if start >= 0 and end > start:

            candidate = text[
                start:end + 1
            ]

            try:

                parsed = json.loads(
                    candidate
                )

                if isinstance(
                    parsed,
                    list,
                ):
                    return [
                        item
                        for item in parsed
                        if isinstance(
                            item,
                            dict,
                        )
                    ]

            except json.JSONDecodeError:
                pass

        return []

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


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def generate_tests(
    verification_plan: Optional[Dict[str, Any]] = None,
    rtl_analysis: Optional[Dict[str, Any]] = None,
    specification: str = "",
    existing_tests: Optional[List[Dict[str, Any]]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    red_team_scenarios: Optional[
        List[Dict[str, Any]]
    ] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper.
    """

    agent = TestGeneratorAgent(
        api_key=api_key,
    )

    return agent.generate(
        verification_plan=verification_plan,
        rtl_analysis=rtl_analysis,
        specification=specification,
        existing_tests=existing_tests,
        coverage=coverage,
        red_team_scenarios=red_team_scenarios,
    )


# ============================================================
# FACTORY
# ============================================================

def get_test_generator(
    api_key: Optional[str] = None,
) -> TestGeneratorAgent:
    """
    Return configured Test Generator agent.
    """

    return TestGeneratorAgent(
        api_key=api_key,
    )
