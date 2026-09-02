"""
PragyanAI SiliconAI
Verification Judge Agent

Purpose
-------
Acts as an independent verification/signoff judge.

The judge does NOT generate RTL or tests.
It evaluates the evidence produced by the verification pipeline and
decides whether the current RTL has sufficient evidence for signoff.

Decision model
--------------
PASS / VERIFIED / SIGNOFF
    Strong evidence supports verification signoff.

FAIL
    Significant verification evidence indicates a real failure.

NEED_MORE_VERIFICATION
    Evidence is incomplete, contradictory, or insufficient.

Important
---------
A high proxy coverage number alone is NEVER sufficient for signoff.
The judge considers:
    - simulation
    - test results
    - coverage
    - mutation testing
    - formal verification
    - failure analysis
    - repair status
    - regression quality

The judge never claims formal proof unless the formal backend actually
reported a proven result.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_groq import ChatGroq

from config.settings import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    GROQ_API_KEY,
    VERIFICATION_TARGET,
    AGENT_TOKEN_LIMITS,
)
from config.prompts import (
    compact_failure,
    compact_json,
    compact_rtl_analysis,
    compact_simulation_log,
    limit_text,
    load_prompt,
)


class VerificationJudgeAgent:
    """
    Independent evidence-based verification judge.

    The judge is deliberately conservative.

    It should be possible for the judge to say:

        NEED_MORE_VERIFICATION

    rather than forcing a PASS/FAIL decision when evidence is incomplete.
    """

    name = "Verification Judge"

    PASS_VERDICTS = {
        "PASS",
        "PASSED",
        "VERIFIED",
        "SIGNOFF",
        "SIGN_OFF",
    }

    FAIL_VERDICTS = {
        "FAIL",
        "FAILED",
        "REJECT",
        "REJECTED",
    }

    REVIEW_VERDICTS = {
        "NEED_MORE_VERIFICATION",
        "NEEDS_MORE_VERIFICATION",
        "REVIEW",
        "INCONCLUSIVE",
        "NOT_PROVEN",
        "UNKNOWN",
    }

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: Optional[int] = None,
    ):
        self.model = model
        self.temperature = temperature

        configured_limit = AGENT_TOKEN_LIMITS.get(
            "verification_judge",
            DEFAULT_MAX_TOKENS,
        )

        self.max_tokens = max_tokens or min(
            configured_limit,
            DEFAULT_MAX_TOKENS,
        )

        self.prompt_template = self._load_prompt()

        self.llm = None

        if GROQ_API_KEY:
            try:
                self.llm = ChatGroq(
                    api_key=GROQ_API_KEY,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception:
                self.llm = None

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _load_prompt(self) -> str:
        try:
            prompt = load_prompt("verification_judge")

            if prompt and prompt.strip():
                return prompt

        except Exception:
            pass

        return """
You are an independent semiconductor verification signoff judge.

Evaluate the supplied verification evidence.

You are NOT the RTL designer.
You are NOT the test generator.
You must independently judge whether the evidence supports signoff.

Consider:
1. Simulation results
2. Failed tests
3. Coverage
4. Mutation score
5. Formal results
6. Failure analysis
7. Repair status
8. Regression completeness
9. Evidence quality

Critical rules:
- Proxy coverage is not equivalent to real EDA coverage.
- A high coverage score alone is not sufficient.
- Compilation success is not verification.
- Never claim formal proof unless formal evidence says PROVEN.
- Never claim equivalence unless equivalence evidence exists.
- Missing evidence should result in NEED_MORE_VERIFICATION.
- Contradictory evidence should result in NEED_MORE_VERIFICATION.
- Any unresolved critical failure should prevent signoff.
- Do not invent results.

Return ONLY compact JSON.

Schema:

{
  "verdict": "PASS|FAIL|NEED_MORE_VERIFICATION",
  "score": 0,
  "confidence": 0.0,
  "summary": "short decision summary",
  "reasons": [
    "reason 1",
    "reason 2"
  ],
  "blocking_issues": [
    "issue 1"
  ],
  "required_actions": [
    "action 1"
  ]
}

Do not claim that the RTL is verified unless the supplied evidence
actually supports that conclusion.
"""

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        if not text:
            return {}

        text = text.strip()

        try:
            result = json.loads(text)

            if isinstance(result, dict):
                return result

        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            try:
                result = json.loads(
                    text[start : end + 1]
                )

                if isinstance(result, dict):
                    return result

            except Exception:
                pass

        return {}

    @staticmethod
    def _normalize_verdict(value: Any) -> str:
        text = str(value or "").strip().upper()

        text = text.replace("-", "_")
        text = text.replace(" ", "_")

        if text in VerificationJudgeAgent.PASS_VERDICTS:
            return "PASS"

        if text in VerificationJudgeAgent.FAIL_VERDICTS:
            return "FAIL"

        if text in VerificationJudgeAgent.REVIEW_VERDICTS:
            return "NEED_MORE_VERIFICATION"

        return "NEED_MORE_VERIFICATION"

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _normalize_list(
        value: Any,
        limit: int = 10,
    ) -> List[str]:
        if not isinstance(value, list):
            return []

        result: List[str] = []

        for item in value[:limit]:
            text = str(item).strip()

            if text:
                result.append(
                    limit_text(
                        text,
                        500,
                    )
                )

        return result

    # ------------------------------------------------------------------
    # Evidence extraction
    # ------------------------------------------------------------------

    def _test_evidence(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        tests = state.get("tests", []) or []

        passed = 0
        failed = 0
        executed = 0
        unknown = 0

        for test in tests:
            if not isinstance(test, dict):
                continue

            status = str(
                test.get(
                    "status",
                    "",
                )
            ).upper()

            if status:
                executed += 1

            if status in {
                "PASS",
                "PASSED",
                "SUCCESS",
            }:
                passed += 1

            elif status in {
                "FAIL",
                "FAILED",
                "ERROR",
            }:
                failed += 1

            else:
                unknown += 1

        pass_rate = (
            passed / executed * 100.0
            if executed
            else 0.0
        )

        return {
            "tests_total": len(tests),
            "tests_executed": executed,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_unknown": unknown,
            "test_pass_rate": round(
                pass_rate,
                2,
            ),
        }

    def _coverage_evidence(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        coverage = state.get(
            "coverage",
            {},
        ) or {}

        if not isinstance(coverage, dict):
            coverage = {}

        overall = self._safe_float(
            coverage.get(
                "overall",
                0,
            )
        )

        evidence_type = str(
            coverage.get(
                "evidence_type",
                "UNKNOWN",
            )
        ).upper()

        gaps = coverage.get(
            "gaps",
            state.get(
                "coverage_gaps",
                [],
            ),
        )

        if not isinstance(gaps, list):
            gaps = []

        return {
            "overall": round(
                overall,
                2,
            ),
            "line": self._safe_float(
                coverage.get("line", 0)
            ),
            "branch": self._safe_float(
                coverage.get("branch", 0)
            ),
            "toggle": self._safe_float(
                coverage.get("toggle", 0)
            ),
            "fsm": self._safe_float(
                coverage.get("fsm", 0)
            ),
            "functional": self._safe_float(
                coverage.get("functional", 0)
            ),
            "assertion": self._safe_float(
                coverage.get("assertion", 0)
            ),
            "mutation": self._safe_float(
                coverage.get("mutation", 0)
            ),
            "gap_count": len(gaps),
            "evidence_type": evidence_type,
        }

    def _mutation_evidence(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        mutations = state.get(
            "mutations",
            [],
        ) or []

        mutation_score = self._safe_float(
            state.get(
                "mutation_score",
                0,
            )
        )

        executed = 0
        killed = 0
        survived = 0

        for mutation in mutations:
            if not isinstance(mutation, dict):
                continue

            status = str(
                mutation.get(
                    "status",
                    mutation.get(
                        "result",
                        "",
                    ),
                )
            ).upper()

            if status in {
                "KILLED",
                "SURVIVED",
            }:
                executed += 1

            if status == "KILLED":
                killed += 1

            elif status == "SURVIVED":
                survived += 1

        return {
            "executed": executed,
            "killed": killed,
            "survived": survived,
            "mutation_score": round(
                mutation_score,
                2,
            ),
        }

    def _formal_evidence(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        formal = state.get(
            "formal_result",
            {},
        ) or {}

        if not isinstance(formal, dict):
            formal = {}

        status = str(
            formal.get(
                "status",
                "",
            )
        ).upper()

        properties = formal.get(
            "properties",
            formal.get(
                "formal_properties",
                [],
            ),
        )

        if not isinstance(properties, list):
            properties = []

        proven = 0
        failed = 0
        not_proven = 0

        for prop in properties:
            if not isinstance(prop, dict):
                continue

            pstatus = str(
                prop.get(
                    "status",
                    "",
                )
            ).upper()

            if pstatus == "PROVEN":
                proven += 1

            elif pstatus in {
                "FAILED",
                "FAIL",
            }:
                failed += 1

            elif pstatus in {
                "NOT_PROVEN",
                "UNSUPPORTED",
                "UNAVAILABLE",
                "SKIPPED",
            }:
                not_proven += 1

        return {
            "status": status,
            "properties_total": len(properties),
            "proven": proven,
            "failed": failed,
            "not_proven": not_proven,
        }

    # ------------------------------------------------------------------
    # Deterministic judge
    # ------------------------------------------------------------------

    def _deterministic_evidence(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        tests = self._test_evidence(state)
        coverage = self._coverage_evidence(state)
        mutation = self._mutation_evidence(state)
        formal = self._formal_evidence(state)

        simulation_passed = state.get(
            "simulation_passed",
            None,
        )

        failure_analysis = state.get(
            "failure_analysis",
            {},
        ) or {}

        if not isinstance(failure_analysis, dict):
            failure_analysis = {}

        failure_category = str(
            failure_analysis.get(
                "category",
                "",
            )
        ).upper()

        retry_required = bool(
            state.get(
                "retry_required",
                False,
            )
        )

        repair = state.get(
            "repair_proposal",
            {},
        ) or {}

        if not isinstance(repair, dict):
            repair = {}

        repair_status = str(
            repair.get(
                "validation_status",
                "",
            )
        ).upper()

        blocking: List[str] = []
        reasons: List[str] = []
        actions: List[str] = []

        # --------------------------------------------------------------
        # Simulation
        # --------------------------------------------------------------

        if simulation_passed is False:
            blocking.append(
                "Simulation did not pass."
            )

        elif simulation_passed is None:
            actions.append(
                "Execute the simulation/regression and collect explicit results."
            )

        else:
            reasons.append(
                "Top-level simulation reports PASS."
            )

        # --------------------------------------------------------------
        # Tests
        # --------------------------------------------------------------

        if tests["tests_failed"] > 0:
            blocking.append(
                f'{tests["tests_failed"]} test(s) failed.'
            )

        if tests["tests_unknown"] > 0:
            actions.append(
                f'{tests["tests_unknown"]} test(s) have no definitive result.'
            )

        if tests["tests_executed"] == 0:
            actions.append(
                "No structured test execution evidence is available."
            )

        elif tests["test_pass_rate"] >= 99.9:
            reasons.append(
                "All executed structured tests passed."
            )

        # --------------------------------------------------------------
        # Failure analysis
        # --------------------------------------------------------------

        if failure_category in {
            "RTL_BUG",
            "RESET_ERROR",
            "FSM_ERROR",
            "WIDTH_ERROR",
            "PROTOCOL_ERROR",
            "TIMING_ISSUE",
        }:
            blocking.append(
                f"Verification evidence indicates unresolved failure category: "
                f"{failure_category}."
            )

        if retry_required:
            actions.append(
                "Resolve the retry-required condition before signoff."
            )

        # --------------------------------------------------------------
        # Coverage
        # --------------------------------------------------------------

        coverage_overall = coverage["overall"]

        if coverage_overall < VERIFICATION_TARGET:
            actions.append(
                f"Increase coverage from {coverage_overall:.1f}% "
                f"toward the {VERIFICATION_TARGET}% target."
            )

        else:
            reasons.append(
                f"Coverage meets the configured {VERIFICATION_TARGET}% target."
            )

        if coverage["gap_count"] > 0:
            actions.append(
                f"Close or justify {coverage['gap_count']} remaining coverage gap(s)."
            )

        if coverage["evidence_type"] == "PROXY_COVERAGE":
            actions.append(
                "Replace proxy coverage with real EDA coverage before production signoff."
            )

        # --------------------------------------------------------------
        # Mutation
        # --------------------------------------------------------------

        if mutation["executed"] == 0:
            actions.append(
                "Execute mutation testing or explicitly justify why it is unavailable."
            )

        elif mutation["survived"] > 0:
            actions.append(
                f'{mutation["survived"]} mutant(s) survived.'
            )

        elif mutation["mutation_score"] >= 90:
            reasons.append(
                "Mutation testing provides strong evidence."
            )

        # --------------------------------------------------------------
        # Formal
        # --------------------------------------------------------------

        if formal["failed"] > 0:
            blocking.append(
                f'{formal["failed"]} formal property/properties failed.'
            )

        if formal["properties_total"] > 0:
            if formal["proven"] > 0:
                reasons.append(
                    f'{formal["proven"]} formal property/properties proven.'
                )

            if formal["not_proven"] > 0:
                actions.append(
                    f'{formal["not_proven"]} formal property/properties are not proven.'
                )

        # --------------------------------------------------------------
        # Repair
        # --------------------------------------------------------------

        if repair_status in {
            "LOW_CONFIDENCE_REVIEW_REQUIRED",
            "PROPOSED_DOWNSTREAM_VERIFICATION_REQUIRED",
        }:
            actions.append(
                "Re-run downstream verification after the proposed RTL repair."
            )

        # --------------------------------------------------------------
        # Determine preliminary verdict
        # --------------------------------------------------------------

        if blocking:
            preliminary = "FAIL"

        elif actions:
            preliminary = "NEED_MORE_VERIFICATION"

        else:
            preliminary = "PASS"

        # --------------------------------------------------------------
        # Confidence
        # --------------------------------------------------------------

        evidence_score = 0.0

        if simulation_passed is True:
            evidence_score += 20.0

        if (
            tests["tests_executed"] > 0
            and tests["tests_failed"] == 0
        ):
            evidence_score += 20.0

        if coverage_overall >= VERIFICATION_TARGET:
            evidence_score += 20.0

        if mutation["executed"] > 0:
            evidence_score += min(
                15.0,
                mutation["mutation_score"] * 0.15,
            )

        if formal["proven"] > 0:
            evidence_score += 15.0

        if coverage["evidence_type"] == "REAL_COVERAGE":
            evidence_score += 10.0

        score = min(
            100.0,
            evidence_score,
        )

        return {
            "preliminary_verdict": preliminary,
            "score": round(score, 2),
            "tests": tests,
            "coverage": coverage,
            "mutation": mutation,
            "formal": formal,
            "blocking_issues": blocking,
            "reasons": reasons,
            "required_actions": actions,
        }

    # ------------------------------------------------------------------
    # LLM judge
    # ------------------------------------------------------------------

    def _build_llm_context(
        self,
        state: Dict[str, Any],
        deterministic: Dict[str, Any],
    ) -> str:
        rtl_analysis = state.get(
            "rtl_analysis",
            {},
        ) or {}

        failure_analysis = state.get(
            "failure_analysis",
            {},
        ) or {}

        bug_location = state.get(
            "bug_location",
            {},
        ) or {}

        simulation_output = state.get(
            "simulation_output",
            state.get(
                "run_output",
                "",
            ),
        )

        simulation_error = state.get(
            "simulation_error",
            state.get(
                "error_log",
                "",
            ),
        )

        context = f"""
SPECIFICATION:
{limit_text(
    str(
        state.get(
            "specification",
            state.get(
                "prompt",
                "",
            ),
        )
        or ""
    ),
    2200,
)}

RTL STRUCTURAL ANALYSIS:
{compact_rtl_analysis(
    rtl_analysis,
    max_chars=1400,
)}

FAILURE ANALYSIS:
{compact_failure(
    failure_analysis,
    max_chars=1800,
)}

BUG LOCATION:
{compact_json(
    bug_location,
    max_chars=1200,
)}

SIMULATION OUTPUT:
{compact_simulation_log(
    simulation_output,
    max_chars=1400,
)}

SIMULATION ERROR:
{compact_simulation_log(
    simulation_error,
    max_chars=1200,
)}

DETERMINISTIC EVIDENCE:
{compact_json(
    deterministic,
    max_chars=4000,
)}
"""

        return limit_text(
            context,
            12500,
        )

    def _call_llm(
        self,
        state: Dict[str, Any],
        deterministic: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.llm is None:
            return {}

        context = self._build_llm_context(
            state,
            deterministic,
        )

        prompt = f"""
{self.prompt_template}

CURRENT EVIDENCE
================

{context}

IMPORTANT:
The deterministic evidence is advisory input.
Check it critically against the supplied evidence.

Return ONLY JSON.
"""

        prompt = limit_text(
            prompt,
            15000,
        )

        try:
            response = self.llm.invoke(
                prompt
            )

            content = getattr(
                response,
                "content",
                "",
            )

            if isinstance(content, list):
                content = "".join(
                    str(item)
                    for item in content
                )

            return self._extract_json(
                str(content)
            )

        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Merge AI and deterministic evidence
    # ------------------------------------------------------------------

    def _merge_decision(
        self,
        deterministic: Dict[str, Any],
        ai_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        deterministic_verdict = (
            deterministic["preliminary_verdict"]
        )

        ai_verdict = self._normalize_verdict(
            ai_result.get(
                "verdict",
                "",
            )
        )

        # --------------------------------------------------------------
        # Conservative decision policy
        #
        # If deterministic evidence says FAIL, AI cannot override it
        # without explicit evidence.
        # --------------------------------------------------------------

        if deterministic_verdict == "FAIL":
            verdict = "FAIL"

        elif deterministic_verdict == "NEED_MORE_VERIFICATION":
            verdict = "NEED_MORE_VERIFICATION"

        elif ai_verdict == "FAIL":
            verdict = "FAIL"

        elif ai_verdict == "NEED_MORE_VERIFICATION":
            verdict = "NEED_MORE_VERIFICATION"

        elif ai_verdict == "PASS":
            verdict = "PASS"

        else:
            verdict = deterministic_verdict

        deterministic_score = self._safe_float(
            deterministic.get(
                "score",
                0,
            )
        )

        ai_score = self._safe_float(
            ai_result.get(
                "score",
                deterministic_score,
            )
        )

        # Do not allow AI to manufacture a high score.
        score = min(
            deterministic_score,
            ai_score
            if ai_result
            else deterministic_score,
        )

        if not ai_result:
            score = deterministic_score

        confidence = self._safe_float(
            ai_result.get(
                "confidence",
                0.65
                if verdict != "PASS"
                else 0.75,
            ),
            0.65,
        )

        reasons = list(
            deterministic.get(
                "reasons",
                [],
            )
        )

        blocking = list(
            deterministic.get(
                "blocking_issues",
                [],
            )
        )

        actions = list(
            deterministic.get(
                "required_actions",
                [],
            )
        )

        if ai_result:
            reasons.extend(
                self._normalize_list(
                    ai_result.get(
                        "reasons",
                        [],
                    ),
                    6,
                )
            )

            blocking.extend(
                self._normalize_list(
                    ai_result.get(
                        "blocking_issues",
                        [],
                    ),
                    6,
                )
            )

            actions.extend(
                self._normalize_list(
                    ai_result.get(
                        "required_actions",
                        [],
                    ),
                    6,
                )
            )

        # De-duplicate while preserving order.
        reasons = list(
            dict.fromkeys(
                reasons
            )
        )[:12]

        blocking = list(
            dict.fromkeys(
                blocking
            )
        )[:12]

        actions = list(
            dict.fromkeys(
                actions
            )
        )[:12]

        summary = str(
            ai_result.get(
                "summary",
                "",
            )
            or ""
        ).strip()

        if not summary:
            if verdict == "PASS":
                summary = (
                    "Verification evidence meets the current signoff criteria."
                )
            elif verdict == "FAIL":
                summary = (
                    "Verification evidence contains unresolved blocking failures."
                )
            else:
                summary = (
                    "Verification evidence is incomplete and requires additional evidence."
                )

        return {
            "verdict": verdict,
            "score": round(
                max(
                    0.0,
                    min(
                        100.0,
                        score,
                    ),
                ),
                2,
            ),
            "confidence": round(
                max(
                    0.0,
                    min(
                        1.0,
                        confidence,
                    ),
                ),
                3,
            ),
            "summary": limit_text(
                summary,
                1000,
            ),
            "reasons": reasons,
            "blocking_issues": blocking,
            "required_actions": actions,
            "deterministic_verdict": deterministic_verdict,
            "ai_verdict": (
                ai_verdict
                if ai_result
                else None
            ),
            "judge_policy": "CONSERVATIVE_EVIDENCE_BASED",
        }

    # ------------------------------------------------------------------
    # Artifact
    # ------------------------------------------------------------------

    def _save_result(
        self,
        state: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Optional[str]:
        run_dir = state.get(
            "run_dir"
        )

        if not run_dir:
            return None

        reports_dir = os.path.join(
            run_dir,
            "reports",
        )

        os.makedirs(
            reports_dir,
            exist_ok=True,
        )

        path = os.path.join(
            reports_dir,
            "verification_judge.json",
        )

        try:
            with open(
                path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    result,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            return path

        except Exception:
            return None

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        started = datetime.utcnow()

        logs: List[str] = []
        trace: List[Dict[str, Any]] = []
        warnings: List[str] = []
        errors: List[str] = []

        logs.append(
            f"[{self.name}] Starting independent verification judgment."
        )

        trace.append(
            {
                "agent": self.name,
                "status": "STARTED",
                "timestamp": self._timestamp(),
                "message": (
                    "Evaluating simulation, tests, coverage, mutation, "
                    "formal, failure, and repair evidence."
                ),
            }
        )

        deterministic = self._deterministic_evidence(
            state
        )

        logs.append(
            f"[{self.name}] Deterministic evidence score: "
            f'{deterministic["score"]:.2f}.'
        )

        ai_result = self._call_llm(
            state,
            deterministic,
        )

        if ai_result:
            logs.append(
                f"[{self.name}] Independent AI judgment received."
            )
        else:
            warnings.append(
                "AI judge unavailable; deterministic evidence policy used."
            )

        result = self._merge_decision(
            deterministic,
            ai_result,
        )

        # --------------------------------------------------------------
        # Final hard safety rules
        # --------------------------------------------------------------

        # Never PASS when tests explicitly failed.
        if (
            deterministic["tests"]["tests_failed"] > 0
            and result["verdict"] == "PASS"
        ):
            result["verdict"] = "FAIL"

            result["blocking_issues"].append(
                "Explicit failed test prevents signoff."
            )

        # Never PASS when simulation explicitly failed.
        if (
            state.get("simulation_passed") is False
            and result["verdict"] == "PASS"
        ):
            result["verdict"] = "FAIL"

            result["blocking_issues"].append(
                "Explicit simulation failure prevents signoff."
            )

        # Never PASS with failed formal properties.
        if (
            deterministic["formal"]["failed"] > 0
            and result["verdict"] == "PASS"
        ):
            result["verdict"] = "FAIL"

            result["blocking_issues"].append(
                "Failed formal property prevents signoff."
            )

        # Proxy coverage means production signoff should remain cautious.
        if (
            deterministic["coverage"]["evidence_type"]
            == "PROXY_COVERAGE"
            and result["verdict"] == "PASS"
        ):
            result["verdict"] = (
                "NEED_MORE_VERIFICATION"
            )

            result["required_actions"].append(
                "Collect real EDA coverage before production signoff."
            )

        result["blocking_issues"] = list(
            dict.fromkeys(
                result["blocking_issues"]
            )
        )

        result["required_actions"] = list(
            dict.fromkeys(
                result["required_actions"]
            )
        )

        result["reasons"] = list(
            dict.fromkeys(
                result["reasons"]
            )
        )

        result["timestamp"] = self._timestamp()

        artifact_path = self._save_result(
            state,
            result,
        )

        if artifact_path:
            result["artifact"] = artifact_path

        # --------------------------------------------------------------
        # Status
        # --------------------------------------------------------------

        verdict = result["verdict"]

        if verdict == "PASS":
            status = "VERIFIED"

            message = (
                "Verification judge reached PASS based on available evidence."
            )

        elif verdict == "FAIL":
            status = "FAILED"

            message = (
                "Verification judge rejected signoff because "
                "blocking verification evidence remains."
            )

        else:
            status = "NEEDS_MORE_VERIFICATION"

            message = (
                "Verification judge requires additional evidence before signoff."
            )

        logs.append(
            f"[{self.name}] Verdict={verdict}, "
            f'Score={result["score"]:.2f}, '
            f'Confidence={result["confidence"]:.2f}.'
        )

        elapsed = (
            datetime.utcnow() - started
        ).total_seconds()

        trace.append(
            {
                "agent": self.name,
                "status": status,
                "timestamp": self._timestamp(),
                "message": message,
                "duration_seconds": round(
                    elapsed,
                    4,
                ),
            }
        )

        return {
            "judge_result": result,
            "verification_score": result["score"],
            "status": status,
            "next_action": (
                "END"
                if verdict == "PASS"
                else "REVERIFY"
            ),
            "retry_required": (
                verdict != "PASS"
            ),
            "agent_log": logs,
            "agent_trace": trace,
            "warnings": warnings,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # LangGraph interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.run(state)


__all__ = [
    "VerificationJudgeAgent",
]
