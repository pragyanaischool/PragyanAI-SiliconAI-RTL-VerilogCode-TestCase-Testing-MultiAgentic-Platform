"""
PragyanAI SiliconAI
Coverage Agent

Purpose
-------
Analyze verification coverage after successful simulation.

The agent combines:
1. Available deterministic coverage information
2. Test execution evidence
3. RTL analysis
4. Verification plan
5. Coverage gaps
6. Optional LLM reasoning

Important
---------
This implementation is intentionally simulator-agnostic.

If a real coverage database is available later from:
    - Verilator
    - Questa
    - VCS
    - Xcelium
    - Verilog-XL
    - custom instrumentation

the database can be passed through state["coverage"].

For the current Icarus-based platform, this agent calculates
verification/proxy coverage from available evidence and identifies
likely coverage gaps.

It does NOT falsely claim that Icarus has generated native
industry-grade line/branch/toggle/FSM coverage.

Typical flow:

    Simulation
        |
        v
    Coverage Agent
        |
        +---- Coverage adequate ----> Red Team
        |
        +---- Coverage gaps --------> Test Generator
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config.settings import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    GROQ_API_KEY,
    VERIFICATION_TARGET,
)
from config.prompts import (
    compact_json,
    compact_rtl,
    compact_rtl_analysis,
    limit_text,
    load_prompt,
)


class CoverageAgent:
    """
    Coverage analysis and gap-detection agent.

    The agent focuses on verification evidence rather than
    pretending that proxy metrics are equivalent to commercial
    simulator coverage databases.
    """

    AGENT_NAME = "Coverage Agent"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        target: Optional[float] = None,
    ) -> None:

        self.api_key = api_key or GROQ_API_KEY
        self.model = model or DEFAULT_MODEL

        self.temperature = (
            DEFAULT_TEMPERATURE
            if temperature is None
            else temperature
        )

        self.max_tokens = (
            DEFAULT_MAX_TOKENS
            if max_tokens is None
            else max_tokens
        )

        self.target = (
            float(target)
            if target is not None
            else float(VERIFICATION_TARGET)
        )

        self.llm = None

        if self.api_key:
            try:
                self.llm = ChatGroq(
                    api_key=self.api_key,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=min(
                        self.max_tokens,
                        1800,
                    ),
                )
            except Exception:
                self.llm = None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            number = float(value)

            if number != number:
                return default

            return max(
                0.0,
                min(100.0, number),
            )

        except Exception:
            return default

    @staticmethod
    def _safe_json(
        text: str,
    ) -> Optional[Any]:

        if not text:
            return None

        text = str(text).strip()

        text = re.sub(
            r"```json\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```\s*",
            "",
            text,
        )

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if match:

            try:
                return json.loads(
                    match.group(0)
                )
            except Exception:
                pass

        return None

    @staticmethod
    def _compact(
        value: Any,
        limit: int = 4000,
    ) -> str:

        text = str(value or "")

        if len(text) <= limit:
            return text

        return (
            text[: limit // 2]
            + "\n...[TRUNCATED]...\n"
            + text[-limit // 2 :]
        )

    # ------------------------------------------------------------------
    # Test evidence
    # ------------------------------------------------------------------

    @staticmethod
    def _test_statistics(
        tests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        total = len(tests)

        passed = sum(
            1
            for test in tests
            if str(
                test.get("status", "")
            ).upper()
            in {"PASS", "PASSED", "SUCCESS"}
        )

        failed = sum(
            1
            for test in tests
            if str(
                test.get("status", "")
            ).upper()
            in {"FAIL", "FAILED", "ERROR"}
        )

        unknown = max(
            0,
            total - passed - failed,
        )

        pass_rate = (
            (passed / total) * 100.0
            if total
            else 0.0
        )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "unknown": unknown,
            "pass_rate": round(
                pass_rate,
                2,
            ),
        }

    # ------------------------------------------------------------------
    # RTL structural analysis
    # ------------------------------------------------------------------

    def _estimate_rtl_complexity(
        self,
        rtl_code: str,
    ) -> Dict[str, Any]:

        code = rtl_code or ""

        lines = [
            line
            for line in code.splitlines()
            if line.strip()
        ]

        always_blocks = len(
            re.findall(
                r"\balways(?:_ff|_comb)?\b",
                code,
                flags=re.IGNORECASE,
            )
        )

        if_blocks = len(
            re.findall(
                r"\bif\s*\(",
                code,
                flags=re.IGNORECASE,
            )
        )

        case_blocks = len(
            re.findall(
                r"\bcase\s*\(",
                code,
                flags=re.IGNORECASE,
            )
        )

        case_items = len(
            re.findall(
                r"^\s*[^/\s].*:",
                code,
                flags=re.MULTILINE,
            )
        )

        loops = len(
            re.findall(
                r"\b(for|while|repeat|forever)\b",
                code,
                flags=re.IGNORECASE,
            )
        )

        modules = len(
            re.findall(
                r"\bmodule\s+\w+",
                code,
                flags=re.IGNORECASE,
            )
        )

        inputs = len(
            re.findall(
                r"\binput\b",
                code,
                flags=re.IGNORECASE,
            )
        )

        outputs = len(
            re.findall(
                r"\boutput\b",
                code,
                flags=re.IGNORECASE,
            )
        )

        sequential = bool(
            re.search(
                r"posedge|negedge",
                code,
                flags=re.IGNORECASE,
            )
        )

        complexity = (
            len(lines)
            + always_blocks * 4
            + if_blocks * 3
            + case_blocks * 5
            + loops * 8
        )

        return {
            "non_empty_lines": len(lines),
            "modules": modules,
            "always_blocks": always_blocks,
            "if_conditions": if_blocks,
            "case_blocks": case_blocks,
            "case_items_estimate": case_items,
            "loops": loops,
            "input_count": inputs,
            "output_count": outputs,
            "sequential": sequential,
            "complexity_score": min(
                100,
                round(
                    complexity / 10.0,
                    2,
                ),
            ),
        }

    # ------------------------------------------------------------------
    # Deterministic coverage
    # ------------------------------------------------------------------

    def _calculate_proxy_coverage(
        self,
        rtl_code: str,
        tests: List[Dict[str, Any]],
        existing_coverage: Dict[str, Any],
        verification_plan: Dict[str, Any],
        rtl_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate evidence-based proxy metrics.

        If real coverage metrics already exist, preserve them.

        Otherwise derive conservative metrics from:
            - test pass rate
            - test diversity
            - structural RTL complexity
            - plan completeness
            - reset/corner/negative testing
            - assertion evidence
        """

        test_stats = self._test_statistics(
            tests
        )

        complexity = self._estimate_rtl_complexity(
            rtl_code
        )

        # --------------------------------------------------------------
        # Preserve real metrics when supplied.
        # --------------------------------------------------------------

        real_metrics = {}

        for key in [
            "line",
            "branch",
            "toggle",
            "fsm",
            "functional",
            "assertion",
            "mutation",
            "overall",
        ]:

            if key in existing_coverage:

                real_metrics[key] = self._safe_float(
                    existing_coverage.get(key)
                )

        # --------------------------------------------------------------
        # Test diversity
        # --------------------------------------------------------------

        descriptions = " ".join(
            str(
                test.get("description", "")
            ).lower()
            for test in tests
        )

        categories = {
            "reset": "reset" in descriptions,
            "boundary": (
                "boundary" in descriptions
                or "minimum" in descriptions
                or "maximum" in descriptions
            ),
            "corner": (
                "corner" in descriptions
                or "edge" in descriptions
            ),
            "negative": (
                "invalid" in descriptions
                or "illegal" in descriptions
                or "negative" in descriptions
            ),
            "sequence": (
                "sequence" in descriptions
                or "back-to-back" in descriptions
                or "back to back" in descriptions
            ),
            "protocol": (
                "protocol" in descriptions
                or "handshake" in descriptions
                or "valid" in descriptions
            ),
        }

        diversity_score = (
            sum(categories.values())
            / len(categories)
            * 100.0
        )

        # --------------------------------------------------------------
        # Functional proxy
        # --------------------------------------------------------------

        if test_stats["total"]:

            functional = (
                test_stats["pass_rate"] * 0.65
                + diversity_score * 0.35
            )

        else:
            functional = 0.0

        # --------------------------------------------------------------
        # Branch proxy
        # --------------------------------------------------------------

        if complexity["if_conditions"] > 0:

            branch = min(
                100.0,
                test_stats["pass_rate"] * 0.60
                + diversity_score * 0.40,
            )

        else:
            branch = (
                test_stats["pass_rate"]
                if test_stats["total"]
                else 0.0
            )

        # --------------------------------------------------------------
        # Line proxy
        # --------------------------------------------------------------

        if complexity["non_empty_lines"] > 0:

            line = min(
                100.0,
                test_stats["pass_rate"] * 0.70
                + diversity_score * 0.30,
            )

        else:
            line = 0.0

        # --------------------------------------------------------------
        # Toggle proxy
        # --------------------------------------------------------------

        toggle = min(
            100.0,
            test_stats["pass_rate"] * 0.55
            + diversity_score * 0.45,
        )

        # --------------------------------------------------------------
        # FSM proxy
        # --------------------------------------------------------------

        if (
            complexity["case_blocks"] > 0
            or "fsm" in str(rtl_analysis).lower()
        ):
            fsm = min(
                100.0,
                test_stats["pass_rate"] * 0.60
                + diversity_score * 0.40,
            )
        else:
            fsm = 100.0

        # --------------------------------------------------------------
        # Assertion proxy
        # --------------------------------------------------------------

        assertion_count = len(
            re.findall(
                r"\bassert(?:ion)?\b",
                rtl_code,
                flags=re.IGNORECASE,
            )
        )

        if assertion_count > 0:
            assertion = min(
                100.0,
                60.0
                + test_stats["pass_rate"] * 0.40,
            )
        else:
            assertion = 0.0

        # --------------------------------------------------------------
        # Mutation
        # --------------------------------------------------------------

        mutation = self._safe_float(
            existing_coverage.get(
                "mutation",
                0.0,
            )
        )

        # --------------------------------------------------------------
        # Merge real metrics over proxies.
        # --------------------------------------------------------------

        metrics = {
            "line": real_metrics.get(
                "line",
                round(line, 2),
            ),
            "branch": real_metrics.get(
                "branch",
                round(branch, 2),
            ),
            "toggle": real_metrics.get(
                "toggle",
                round(toggle, 2),
            ),
            "fsm": real_metrics.get(
                "fsm",
                round(fsm, 2),
            ),
            "functional": real_metrics.get(
                "functional",
                round(functional, 2),
            ),
            "assertion": real_metrics.get(
                "assertion",
                round(assertion, 2),
            ),
            "mutation": real_metrics.get(
                "mutation",
                round(mutation, 2),
            ),
        }

        # --------------------------------------------------------------
        # Overall score.
        # --------------------------------------------------------------

        if "overall" in real_metrics:

            overall = real_metrics["overall"]

        else:

            overall = (
                metrics["line"] * 0.15
                + metrics["branch"] * 0.15
                + metrics["toggle"] * 0.10
                + metrics["fsm"] * 0.10
                + metrics["functional"] * 0.25
                + metrics["assertion"] * 0.10
                + metrics["mutation"] * 0.15
            )

        metrics["overall"] = round(
            overall,
            2,
        )

        return metrics

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def _find_gaps(
        self,
        metrics: Dict[str, Any],
        tests: List[Dict[str, Any]],
        rtl_code: str,
        specification: str,
        verification_plan: Dict[str, Any],
        existing_gaps: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:

        gaps: List[Dict[str, Any]] = []

        # --------------------------------------------------------------
        # Metric gaps
        # --------------------------------------------------------------

        metric_names = [
            (
                "line",
                "Structural execution evidence is below target.",
                "Generate tests targeting unexecuted RTL paths.",
            ),
            (
                "branch",
                "Conditional behavior may not be sufficiently exercised.",
                "Generate branch-directed tests for each decision outcome.",
            ),
            (
                "functional",
                "Functional scenario coverage is below target.",
                "Generate additional requirement-driven functional tests.",
            ),
            (
                "assertion",
                "Assertion evidence is insufficient.",
                "Add assertions for important protocol and state invariants.",
            ),
            (
                "mutation",
                "Mutation resilience has not been sufficiently demonstrated.",
                "Run mutation testing and add tests that kill surviving mutants.",
            ),
        ]

        for metric, description, recommendation in metric_names:

            value = self._safe_float(
                metrics.get(metric)
            )

            # Mutation is special: zero may mean mutation testing
            # has not yet been executed.
            if (
                metric == "mutation"
                and value == 0
            ):
                gaps.append(
                    {
                        "id": f"GAP{len(gaps)+1:03d}",
                        "type": "MUTATION_GAP",
                        "metric": metric,
                        "description": (
                            "Mutation effectiveness has not yet been "
                            "established."
                        ),
                        "recommendation": recommendation,
                        "priority": "HIGH",
                    }
                )

                continue

            if value < self.target:

                priority = (
                    "CRITICAL"
                    if value < self.target - 20
                    else "HIGH"
                    if value < self.target - 10
                    else "MEDIUM"
                )

                gaps.append(
                    {
                        "id": f"GAP{len(gaps)+1:03d}",
                        "type": "COVERAGE_GAP",
                        "metric": metric,
                        "description": description,
                        "current": round(
                            value,
                            2,
                        ),
                        "target": self.target,
                        "recommendation": recommendation,
                        "priority": priority,
                    }
                )

        # --------------------------------------------------------------
        # Test diversity gaps
        # --------------------------------------------------------------

        test_text = " ".join(
            str(
                test.get("description", "")
            ).lower()
            for test in tests
        )

        if "reset" in rtl_code.lower():

            if "reset" not in test_text:

                gaps.append(
                    {
                        "id": f"GAP{len(gaps)+1:03d}",
                        "type": "RESET_GAP",
                        "metric": "functional",
                        "description": (
                            "RTL contains reset logic but no explicit "
                            "reset-focused test was detected."
                        ),
                        "recommendation": (
                            "Generate reset assertion, reset recovery "
                            "and mid-operation reset tests."
                        ),
                        "priority": "HIGH",
                    }
                )

        if (
            "if" in rtl_code.lower()
            and not any(
                word in test_text
                for word in [
                    "boundary",
                    "corner",
                    "minimum",
                    "maximum",
                    "edge",
                ]
            )
        ):

            gaps.append(
                {
                    "id": f"GAP{len(gaps)+1:03d}",
                    "type": "BOUNDARY_GAP",
                    "metric": "branch",
                    "description": (
                        "Conditional RTL was detected without clear "
                        "boundary-oriented tests."
                    ),
                    "recommendation": (
                        "Generate minimum, maximum and one-step-around-"
                        "boundary scenarios."
                    ),
                    "priority": "MEDIUM",
                }
            )

        # --------------------------------------------------------------
        # Negative testing
        # --------------------------------------------------------------

        if not any(
            word in test_text
            for word in [
                "invalid",
                "illegal",
                "negative",
                "error",
            ]
        ):

            gaps.append(
                {
                    "id": f"GAP{len(gaps)+1:03d}",
                    "type": "NEGATIVE_TEST_GAP",
                    "metric": "functional",
                    "description": (
                        "No explicit negative or illegal-input test "
                        "was detected."
                    ),
                    "recommendation": (
                        "Generate adversarial invalid-input and protocol "
                        "violation tests."
                    ),
                    "priority": "MEDIUM",
                }
            )

        # --------------------------------------------------------------
        # Existing gaps
        # --------------------------------------------------------------

        if isinstance(
            existing_gaps,
            list,
        ):

            for item in existing_gaps:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                description = str(
                    item.get("description")
                    or ""
                ).strip()

                if not description:
                    continue

                duplicate = any(
                    description.lower()
                    == str(
                        gap.get("description", "")
                    ).lower()
                    for gap in gaps
                )

                if not duplicate:

                    copied = dict(item)

                    copied.setdefault(
                        "id",
                        f"GAP{len(gaps)+1:03d}",
                    )

                    copied.setdefault(
                        "priority",
                        "MEDIUM",
                    )

                    gaps.append(
                        copied
                    )

        return gaps[:20]

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        verification_plan: Dict[str, Any],
        tests: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        gaps: List[Dict[str, Any]],
    ) -> List[Any]:

        system_prompt = load_prompt(
            "coverage_analysis"
        )

        if not system_prompt:

            system_prompt = """
You are an expert semiconductor RTL verification engineer.

Analyze the supplied verification evidence.

Identify:
- important coverage gaps
- missing scenarios
- branch/functional weaknesses
- reset gaps
- protocol gaps
- assertion gaps
- mutation gaps

Do not invent simulator coverage numbers.

Return ONLY compact JSON:

{
  "overall_assessment": "...",
  "gaps": [
    {
      "id": "GAP001",
      "type": "COVERAGE_GAP",
      "description": "...",
      "recommendation": "...",
      "priority": "HIGH"
    }
  ],
  "recommended_tests": [
    "..."
  ]
}

Maximum 10 gaps and 10 recommended tests.
"""

        payload = {
            "specification": limit_text(
                specification,
                2000,
            ),
            "rtl": compact_rtl(
                rtl_code,
                5000,
            ),
            "rtl_analysis": compact_rtl_analysis(
                rtl_analysis
            ),
            "verification_plan": compact_json(
                verification_plan,
                2500,
            ),
            "tests": compact_json(
                tests,
                3500,
            ),
            "metrics": metrics,
            "deterministic_gaps": gaps[:12],
        }

        return [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=(
                    "Analyze RTL verification coverage.\n\n"
                    + compact_json(
                        payload,
                        11000,
                    )
                ),
            ),
        ]

    def _call_llm(
        self,
        messages: List[Any],
    ) -> Optional[Dict[str, Any]]:

        if not self.llm:
            return None

        try:

            response = self.llm.invoke(
                messages
            )

            content = getattr(
                response,
                "content",
                "",
            )

            if isinstance(
                content,
                list,
            ):

                content = "".join(
                    str(item)
                    for item in content
                )

            parsed = self._safe_json(
                str(content)
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except Exception:
            return None

        return None

    # ------------------------------------------------------------------
    # Merge AI output
    # ------------------------------------------------------------------

    def _merge_ai_gaps(
        self,
        deterministic_gaps: List[Dict[str, Any]],
        ai_result: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        gaps = list(
            deterministic_gaps
        )

        if not isinstance(
            ai_result,
            dict,
        ):
            return gaps[:20]

        ai_gaps = (
            ai_result.get("gaps")
            or ai_result.get("coverage_gaps")
            or []
        )

        if not isinstance(
            ai_gaps,
            list,
        ):
            return gaps[:20]

        for item in ai_gaps:

            if not isinstance(
                item,
                dict,
            ):
                continue

            description = str(
                item.get("description")
                or item.get("gap")
                or ""
            ).strip()

            if not description:
                continue

            duplicate = any(
                description.lower()
                in str(
                    gap.get("description", "")
                ).lower()
                or str(
                    gap.get("description", "")
                ).lower()
                in description.lower()
                for gap in gaps
            )

            if duplicate:
                continue

            gap = {
                "id": f"GAP{len(gaps)+1:03d}",
                "type": str(
                    item.get("type")
                    or "AI_IDENTIFIED_GAP"
                ).upper(),
                "metric": str(
                    item.get("metric")
                    or "functional"
                ),
                "description": description[:500],
                "recommendation": str(
                    item.get("recommendation")
                    or item.get("recommended_action")
                    or "Generate targeted verification tests."
                )[:600],
                "priority": str(
                    item.get("priority")
                    or "MEDIUM"
                ).upper(),
                "source": "Coverage Agent",
            }

            gaps.append(
                gap
            )

            if len(gaps) >= 20:
                break

        return gaps[:20]

    # ------------------------------------------------------------------
    # Public execution
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.time()

        rtl_code = str(
            state.get("rtl_code")
            or ""
        )

        specification = str(
            state.get("specification")
            or state.get("prompt")
            or ""
        )

        rtl_analysis = (
            state.get("rtl_analysis")
            if isinstance(
                state.get("rtl_analysis"),
                dict,
            )
            else {}
        )

        verification_plan = (
            state.get("verification_plan")
            if isinstance(
                state.get("verification_plan"),
                dict,
            )
            else {}
        )

        tests = (
            state.get("tests")
            if isinstance(
                state.get("tests"),
                list,
            )
            else []
        )

        existing_coverage = (
            state.get("coverage")
            if isinstance(
                state.get("coverage"),
                dict,
            )
            else {}
        )

        existing_gaps = (
            existing_coverage.get(
                "gaps",
                [],
            )
            if isinstance(
                existing_coverage,
                dict,
            )
            else []
        )

        # --------------------------------------------------------------
        # Calculate metrics
        # --------------------------------------------------------------

        metrics = self._calculate_proxy_coverage(
            rtl_code=rtl_code,
            tests=tests,
            existing_coverage=existing_coverage,
            verification_plan=verification_plan,
            rtl_analysis=rtl_analysis,
        )

        # --------------------------------------------------------------
        # Detect deterministic gaps
        # --------------------------------------------------------------

        gaps = self._find_gaps(
            metrics=metrics,
            tests=tests,
            rtl_code=rtl_code,
            specification=specification,
            verification_plan=verification_plan,
            existing_gaps=existing_gaps,
        )

        # --------------------------------------------------------------
        # LLM analysis
        # --------------------------------------------------------------

        ai_result = None

        if self.llm and rtl_code:

            messages = self._build_messages(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
                verification_plan=verification_plan,
                tests=tests,
                metrics=metrics,
                gaps=gaps,
            )

            ai_result = self._call_llm(
                messages
            )

        # --------------------------------------------------------------
        # Merge AI gaps
        # --------------------------------------------------------------

        final_gaps = self._merge_ai_gaps(
            deterministic_gaps=gaps,
            ai_result=ai_result,
        )

        # --------------------------------------------------------------
        # Recommended tests
        # --------------------------------------------------------------

        recommended_tests: List[str] = []

        for gap in final_gaps:

            recommendation = str(
                gap.get(
                    "recommendation",
                    "",
                )
            ).strip()

            if recommendation:
                recommended_tests.append(
                    recommendation
                )

        if isinstance(
            ai_result,
            dict,
        ):

            ai_recommendations = (
                ai_result.get(
                    "recommended_tests"
                )
                or []
            )

            if isinstance(
                ai_recommendations,
                list,
            ):

                recommended_tests.extend(
                    str(item)
                    for item in ai_recommendations
                    if str(item).strip()
                )

        # Deduplicate.
        unique_recommendations = []

        seen = set()

        for item in recommended_tests:

            normalized = re.sub(
                r"\s+",
                " ",
                str(item).strip(),
            )

            key = normalized.lower()

            if key in seen:
                continue

            seen.add(key)

            unique_recommendations.append(
                normalized[:600]
            )

            if len(unique_recommendations) >= 10:
                break

        # --------------------------------------------------------------
        # Assessment
        # --------------------------------------------------------------

        overall = metrics["overall"]

        if overall >= self.target:

            assessment = (
                "Coverage evidence meets the configured verification "
                "target."
            )

        elif overall >= self.target - 10:

            assessment = (
                "Coverage is approaching the target but additional "
                "targeted verification is recommended."
            )

        else:

            assessment = (
                "Coverage is below target and significant verification "
                "gaps remain."
            )

        if isinstance(
            ai_result,
            dict,
        ):

            ai_assessment = str(
                ai_result.get(
                    "overall_assessment",
                    "",
                )
            ).strip()

            if ai_assessment:
                assessment = ai_assessment[:1000]

        # --------------------------------------------------------------
        # Evidence quality
        # --------------------------------------------------------------

        evidence_type = (
            "REAL_COVERAGE"
            if any(
                key in existing_coverage
                for key in [
                    "line",
                    "branch",
                    "toggle",
                    "fsm",
                ]
            )
            else "PROXY_COVERAGE"
        )

        # --------------------------------------------------------------
        # Result
        # --------------------------------------------------------------

        coverage_result = {
            "line": metrics["line"],
            "branch": metrics["branch"],
            "toggle": metrics["toggle"],
            "fsm": metrics["fsm"],
            "functional": metrics["functional"],
            "assertion": metrics["assertion"],
            "mutation": metrics["mutation"],
            "overall": metrics["overall"],
            "target": self.target,
            "target_met": overall >= self.target,
            "evidence_type": evidence_type,
            "assessment": assessment,
            "gaps": final_gaps,
            "recommended_tests": unique_recommendations,
            "timestamp": self._timestamp(),
        }

        elapsed = round(
            time.time() - start,
            3,
        )

        # --------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------

        status = "COMPLETED"

        message = (
            f"Coverage analysis completed: "
            f"overall={overall:.2f}%, "
            f"target={self.target:.2f}%, "
            f"gaps={len(final_gaps)}."
        )

        if evidence_type == "PROXY_COVERAGE":

            message += (
                " Metrics are verification proxies because "
                "native simulator coverage data was not supplied."
            )

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": status,
            "timestamp": self._timestamp(),
            "message": message,
            "duration_seconds": elapsed,
            "overall": overall,
            "target": self.target,
            "gaps": len(final_gaps),
            "evidence_type": evidence_type,
        }

        # --------------------------------------------------------------
        # Agent log
        # --------------------------------------------------------------

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "timestamp": self._timestamp(),
            "status": status,
            "duration_seconds": elapsed,
            "input_summary": {
                "rtl_length": len(rtl_code),
                "test_count": len(tests),
                "existing_coverage": bool(
                    existing_coverage
                ),
            },
            "output_summary": {
                "overall": overall,
                "target": self.target,
                "target_met": (
                    overall >= self.target
                ),
                "gap_count": len(final_gaps),
                "recommended_test_count": len(
                    unique_recommendations
                ),
                "evidence_type": evidence_type,
                "ai_used": ai_result is not None,
            },
        }

        return {
            "coverage": coverage_result,
            "coverage_gaps": final_gaps,
            "agent_log": (
                list(
                    state.get(
                        "agent_log"
                    )
                    or []
                )
                + [agent_log_entry]
            ),
            "agent_trace": (
                list(
                    state.get(
                        "agent_trace"
                    )
                    or []
                )
                + [trace_entry]
            ),
            "messages": (
                list(
                    state.get(
                        "messages"
                    )
                    or []
                )
                + [message]
            ),
            "status": status,
        }

    # ------------------------------------------------------------------
    # LangGraph interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.run(state)


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def run_coverage_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience wrapper for LangGraph.
    """

    agent = CoverageAgent()

    return agent.run(state)


__all__ = [
    "CoverageAgent",
    "run_coverage_agent",
]
