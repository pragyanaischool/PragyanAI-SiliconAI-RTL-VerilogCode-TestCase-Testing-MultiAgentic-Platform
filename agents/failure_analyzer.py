"""
PragyanAI SiliconAI
Failure Analyzer Agent

Purpose
-------
Analyze failed RTL simulations and determine the most likely cause.

The agent distinguishes between:

    TESTBENCH_BUG
    RTL_BUG
    SPEC_AMBIGUITY
    ENVIRONMENT
    COMPILATION_ERROR
    TIMING_ISSUE
    UNKNOWN

It produces a compact, structured diagnosis that can be consumed by
the LangGraph router.

Important:
-----------
The Failure Analyzer does NOT repair RTL.

It only diagnoses the failure and recommends the next action.

Typical flow:

    Simulation Failure
           |
           v
    Failure Analyzer
           |
       +---+-------------------+
       |                       |
       v                       v
   Testbench issue          RTL issue
       |                       |
       v                       v
  Generate tests          RTL Repair Agent
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
)
from config.prompts import (
    compact_failure,
    compact_json,
    compact_rtl,
    compact_rtl_analysis,
    compact_simulation_log,
    limit_text,
    load_prompt,
)


class FailureAnalyzerAgent:
    """
    AI-assisted failure diagnosis agent.

    The agent combines:
        1. Deterministic failure classification
        2. Simulation evidence
        3. RTL context
        4. Verification/test context
        5. Optional Groq reasoning

    The deterministic layer is always executed first.
    """

    AGENT_NAME = "Failure Analyzer"

    VALID_CATEGORIES = {
        "TESTBENCH_BUG",
        "RTL_BUG",
        "SPEC_AMBIGUITY",
        "ENVIRONMENT",
        "COMPILATION_ERROR",
        "TIMING_ISSUE",
        "PROTOCOL_ERROR",
        "WIDTH_ERROR",
        "RESET_ERROR",
        "FSM_ERROR",
        "UNKNOWN",
    }

    VALID_ACTIONS = {
        "TEST_GENERATION",
        "RTL_REPAIR",
        "SPEC_REVIEW",
        "ENVIRONMENT_FIX",
        "TIMING_ANALYSIS",
        "PROTOCOL_ANALYSIS",
        "STOP",
        "RETRY",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
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
    def _safe_json(text: str) -> Optional[Any]:
        """
        Robust JSON extraction from an LLM response.
        """

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

        # Object extraction.
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
    def _normalize_text(
        value: Any,
        default: str = "",
        limit: int = 800,
    ) -> str:

        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        return text[:limit]

    @classmethod
    def _normalize_category(
        cls,
        value: Any,
    ) -> str:

        category = str(
            value or "UNKNOWN"
        ).upper().strip()

        if category not in cls.VALID_CATEGORIES:
            return "UNKNOWN"

        return category

    @classmethod
    def _normalize_action(
        cls,
        value: Any,
    ) -> str:

        action = str(
            value or "RETRY"
        ).upper().strip()

        if action not in cls.VALID_ACTIONS:
            return "RETRY"

        return action

    # ------------------------------------------------------------------
    # Deterministic classification
    # ------------------------------------------------------------------

    def _classify_failure(
        self,
        compile_error: str,
        simulation_error: str,
        simulation_output: str,
        run_output: str,
    ) -> Dict[str, Any]:
        """
        Classify the failure using deterministic evidence.

        This provides a stable fallback when:
        - Groq is unavailable
        - Groq rate limit is reached
        - LLM response is malformed
        """

        compile_text = (
            f"{compile_error}\n{run_output}"
        ).lower()

        sim_text = (
            f"{simulation_error}\n"
            f"{simulation_output}\n"
            f"{run_output}"
        ).lower()

        # --------------------------------------------------------------
        # Compilation errors
        # --------------------------------------------------------------

        compilation_patterns = [
            "syntax error",
            "parse error",
            "syntax error in",
            "unknown module",
            "unknown module type",
            "port",
            "not found",
            "undeclared",
            "undefined",
            "invalid module item",
            "malformed",
            "iverilog",
        ]

        if compile_error and any(
            pattern in compile_text
            for pattern in compilation_patterns
        ):
            return {
                "category": "COMPILATION_ERROR",
                "confidence": 0.97,
                "reason": (
                    "The simulator reported a compile-time "
                    "failure before normal execution."
                ),
                "evidence": self._extract_evidence(
                    compile_error
                ),
                "recommended_action": "RTL_REPAIR",
            }

        # --------------------------------------------------------------
        # Timing
        # --------------------------------------------------------------

        timing_patterns = [
            "timeout",
            "timed out",
            "time limit",
            "simulation did not finish",
            "watchdog",
            "deadlock",
        ]

        if any(
            pattern in sim_text
            for pattern in timing_patterns
        ):
            return {
                "category": "TIMING_ISSUE",
                "confidence": 0.90,
                "reason": (
                    "Simulation appears to have stalled, timed out, "
                    "or failed to reach completion."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "TIMING_ANALYSIS",
            }

        # --------------------------------------------------------------
        # Testbench errors
        # --------------------------------------------------------------

        testbench_patterns = [
            "test_error",
            "testbench error",
            "tb error",
            "test bench error",
            "expected=",
            "actual=",
        ]

        if "test_error" in sim_text:
            return {
                "category": "TESTBENCH_BUG",
                "confidence": 0.82,
                "reason": (
                    "The testbench emitted an explicit TEST_ERROR "
                    "record."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "TEST_GENERATION",
            }

        # --------------------------------------------------------------
        # Width / signedness
        # --------------------------------------------------------------

        width_patterns = [
            "width",
            "truncat",
            "signed",
            "unsigned",
            "overflow",
            "underflow",
            "out of range",
        ]

        if any(
            pattern in sim_text
            for pattern in width_patterns
        ):
            return {
                "category": "WIDTH_ERROR",
                "confidence": 0.72,
                "reason": (
                    "Failure evidence contains indicators of a "
                    "data-width or signedness problem."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "RTL_REPAIR",
            }

        # --------------------------------------------------------------
        # Reset
        # --------------------------------------------------------------

        reset_patterns = [
            "reset",
            "rst",
            "rst_n",
            "initialization",
            "initial state",
        ]

        if any(
            pattern in sim_text
            for pattern in reset_patterns
        ):
            return {
                "category": "RESET_ERROR",
                "confidence": 0.68,
                "reason": (
                    "Failure evidence references reset or initialization "
                    "behavior."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "RTL_REPAIR",
            }

        # --------------------------------------------------------------
        # Protocol
        # --------------------------------------------------------------

        protocol_patterns = [
            "valid",
            "ready",
            "handshake",
            "protocol",
            "ack",
            "request",
            "response",
        ]

        if any(
            pattern in sim_text
            for pattern in protocol_patterns
        ):
            return {
                "category": "PROTOCOL_ERROR",
                "confidence": 0.65,
                "reason": (
                    "Failure evidence suggests an interface or "
                    "handshake protocol violation."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "PROTOCOL_ANALYSIS",
            }

        # --------------------------------------------------------------
        # FSM
        # --------------------------------------------------------------

        fsm_patterns = [
            "state",
            "fsm",
            "illegal state",
            "unexpected state",
            "transition",
        ]

        if any(
            pattern in sim_text
            for pattern in fsm_patterns
        ):
            return {
                "category": "FSM_ERROR",
                "confidence": 0.64,
                "reason": (
                    "Failure evidence suggests a state-machine "
                    "transition or state-retention problem."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "RTL_REPAIR",
            }

        # --------------------------------------------------------------
        # Generic RTL failure
        # --------------------------------------------------------------

        if any(
            marker in sim_text
            for marker in [
                "failed",
                "mismatch",
                "assertion",
                "incorrect",
                "unexpected",
            ]
        ):
            return {
                "category": "RTL_BUG",
                "confidence": 0.58,
                "reason": (
                    "Simulation completed far enough to expose "
                    "behavior inconsistent with the expected result."
                ),
                "evidence": self._extract_evidence(
                    simulation_output
                ),
                "recommended_action": "RTL_REPAIR",
            }

        # --------------------------------------------------------------
        # Unknown
        # --------------------------------------------------------------

        return {
            "category": "UNKNOWN",
            "confidence": 0.30,
            "reason": (
                "The available simulation evidence is insufficient "
                "to confidently classify the failure."
            ),
            "evidence": self._extract_evidence(
                run_output
            ),
            "recommended_action": "RETRY",
        }

    @staticmethod
    def _extract_evidence(
        text: str,
        max_lines: int = 12,
    ) -> List[str]:
        """
        Extract useful error/failure lines without returning
        the complete simulator log.
        """

        if not text:
            return []

        lines = str(text).splitlines()

        important: List[str] = []

        keywords = [
            "error",
            "fail",
            "mismatch",
            "expected",
            "actual",
            "assert",
            "timeout",
            "warning",
            "reset",
            "state",
            "protocol",
        ]

        for line in lines:

            stripped = line.strip()

            if not stripped:
                continue

            lower = stripped.lower()

            if any(
                keyword in lower
                for keyword in keywords
            ):
                important.append(
                    stripped[:500]
                )

            if len(important) >= max_lines:
                break

        if not important:
            important = [
                line.strip()[:500]
                for line in lines[-max_lines:]
                if line.strip()
            ]

        return important[:max_lines]

    # ------------------------------------------------------------------
    # LLM prompt
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        simulation_output: str,
        simulation_error: str,
        compile_error: str,
        tests: List[Dict[str, Any]],
        deterministic: Dict[str, Any],
    ) -> List[Any]:

        system_prompt = load_prompt(
            "failure_analysis"
        )

        if not system_prompt:
            system_prompt = """
You are an expert RTL verification failure-analysis engineer.

Analyze the supplied simulation failure.

Determine:
- failure category
- likely root cause
- evidence
- confidence
- recommended next action

Possible categories:
TESTBENCH_BUG
RTL_BUG
SPEC_AMBIGUITY
ENVIRONMENT
COMPILATION_ERROR
TIMING_ISSUE
PROTOCOL_ERROR
WIDTH_ERROR
RESET_ERROR
FSM_ERROR
UNKNOWN

Return ONLY compact JSON:

{
  "category": "RTL_BUG",
  "root_cause": "...",
  "evidence": ["..."],
  "confidence": 0.0,
  "recommended_action": "RTL_REPAIR",
  "explanation": "..."
}

Do not claim certainty without evidence.
Do not repair RTL.
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
            "compile_error": limit_text(
                compile_error,
                1800,
            ),
            "simulation_error": limit_text(
                simulation_error,
                1800,
            ),
            "simulation_output": compact_simulation_log(
                simulation_output,
                3500,
            ),
            "tests": compact_json(
                tests,
                2500,
            ),
            "deterministic_classification": compact_failure(
                deterministic
            ),
        }

        return [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=(
                    "Analyze this RTL verification failure.\n\n"
                    + compact_json(
                        payload,
                        11000,
                    )
                )
            ),
        ]

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

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

            if isinstance(content, list):
                content = "".join(
                    str(item)
                    for item in content
                )

            parsed = self._safe_json(
                str(content)
            )

            if isinstance(parsed, dict):
                return parsed

        except Exception:
            return None

        return None

    # ------------------------------------------------------------------
    # Diagnosis normalization
    # ------------------------------------------------------------------

    def _normalize_diagnosis(
        self,
        deterministic: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        result = dict(deterministic)

        if isinstance(ai_result, dict):

            ai_category = self._normalize_category(
                ai_result.get("category")
            )

            if ai_category != "UNKNOWN":
                result["category"] = ai_category

            if ai_result.get("root_cause"):
                result["root_cause"] = self._normalize_text(
                    ai_result.get("root_cause"),
                    limit=1000,
                )

            if ai_result.get("reason"):
                result["reason"] = self._normalize_text(
                    ai_result.get("reason"),
                    limit=1000,
                )

            if ai_result.get("explanation"):
                result["explanation"] = self._normalize_text(
                    ai_result.get("explanation"),
                    limit=1000,
                )

            evidence = ai_result.get(
                "evidence"
            )

            if isinstance(evidence, list):
                result["evidence"] = [
                    str(item)[:500]
                    for item in evidence[:12]
                ]

            confidence = ai_result.get(
                "confidence"
            )

            try:
                confidence = float(
                    confidence
                )
            except Exception:
                confidence = result.get(
                    "confidence",
                    0.5,
                )

            result["confidence"] = max(
                0.0,
                min(1.0, confidence),
            )

            result[
                "recommended_action"
            ] = self._normalize_action(
                ai_result.get(
                    "recommended_action"
                )
            )

        # Make sure root cause always exists.
        if not result.get("root_cause"):
            result["root_cause"] = result.get(
                "reason",
                "Root cause could not be determined.",
            )

        result.setdefault(
            "evidence",
            [],
        )

        result.setdefault(
            "confidence",
            0.3,
        )

        result.setdefault(
            "recommended_action",
            "RETRY",
        )

        return result

    # ------------------------------------------------------------------
    # Public run
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

        simulation_output = str(
            state.get("simulation_output")
            or state.get("run_output")
            or ""
        )

        simulation_error = str(
            state.get("simulation_error")
            or ""
        )

        compile_error = str(
            state.get("compile_error")
            or ""
        )

        tests = (
            state.get("tests")
            if isinstance(
                state.get("tests"),
                list,
            )
            else []
        )

        # --------------------------------------------------------------
        # Deterministic diagnosis
        # --------------------------------------------------------------

        deterministic = self._classify_failure(
            compile_error=compile_error,
            simulation_error=simulation_error,
            simulation_output=simulation_output,
            run_output=str(
                state.get("run_output")
                or ""
            ),
        )

        # --------------------------------------------------------------
        # AI diagnosis
        # --------------------------------------------------------------

        ai_result = None

        if self.llm and rtl_code:

            messages = self._build_messages(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
                simulation_output=simulation_output,
                simulation_error=simulation_error,
                compile_error=compile_error,
                tests=tests,
                deterministic=deterministic,
            )

            ai_result = self._call_llm(
                messages
            )

        diagnosis = self._normalize_diagnosis(
            deterministic=deterministic,
            ai_result=ai_result,
        )

        elapsed = round(
            time.time() - start,
            3,
        )

        category = diagnosis.get(
            "category",
            "UNKNOWN",
        )

        action = diagnosis.get(
            "recommended_action",
            "RETRY",
        )

        confidence = float(
            diagnosis.get(
                "confidence",
                0.3,
            )
        )

        root_cause = str(
            diagnosis.get(
                "root_cause",
                diagnosis.get(
                    "reason",
                    "Unknown failure",
                ),
            )
        )

        evidence = diagnosis.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence,
            list,
        ):
            evidence = [
                str(evidence)
            ]

        # --------------------------------------------------------------
        # Router-compatible fields
        # --------------------------------------------------------------

        retry_required = action in {
            "RETRY",
            "TEST_GENERATION",
            "TIMING_ANALYSIS",
            "PROTOCOL_ANALYSIS",
        }

        # RTL repair should be selected for RTL-oriented failures.
        if category in {
            "RTL_BUG",
            "COMPILATION_ERROR",
            "WIDTH_ERROR",
            "RESET_ERROR",
            "FSM_ERROR",
        }:
            retry_required = True

        # --------------------------------------------------------------
        # Human-readable summary
        # --------------------------------------------------------------

        summary = (
            f"Failure classified as {category} "
            f"with confidence {confidence:.2f}. "
            f"Recommended action: {action}."
        )

        # --------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": "COMPLETED",
            "timestamp": self._timestamp(),
            "message": summary,
            "duration_seconds": elapsed,
            "category": category,
            "confidence": round(
                confidence,
                3,
            ),
            "recommended_action": action,
        }

        # --------------------------------------------------------------
        # Agent log
        # --------------------------------------------------------------

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "timestamp": self._timestamp(),
            "status": "COMPLETED",
            "duration_seconds": elapsed,
            "category": category,
            "confidence": round(
                confidence,
                3,
            ),
            "recommended_action": action,
            "root_cause": root_cause[:1000],
            "evidence_count": len(
                evidence
            ),
            "ai_used": ai_result is not None,
        }

        # --------------------------------------------------------------
        # Return state
        # --------------------------------------------------------------

        return {
            "failure_analysis": {
                "category": category,
                "root_cause": root_cause[:1200],
                "reason": str(
                    diagnosis.get(
                        "reason",
                        "",
                    )
                )[:1000],
                "explanation": str(
                    diagnosis.get(
                        "explanation",
                        "",
                    )
                )[:1000],
                "evidence": [
                    str(item)[:500]
                    for item in evidence[:12]
                ],
                "confidence": round(
                    confidence,
                    3,
                ),
                "recommended_action": action,
                "timestamp": self._timestamp(),
            },

            "root_cause": root_cause[:1200],

            "next_action": action,

            "retry_required": retry_required,

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
                + [summary]
            ),

            "status": "COMPLETED",
        }

    # ------------------------------------------------------------------
    # LangGraph node interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.run(state)


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def run_failure_analyzer(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience function for LangGraph.
    """

    agent = FailureAnalyzerAgent()

    return agent.run(state)


__all__ = [
    "FailureAnalyzerAgent",
    "run_failure_analyzer",
]
