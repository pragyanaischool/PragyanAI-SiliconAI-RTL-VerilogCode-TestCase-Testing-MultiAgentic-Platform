"""
PragyanAI SiliconAI
RTL Repair Agent

Purpose
-------
Proposes conservative RTL repairs based on verification evidence.

Design principle
----------------
AI proposes the smallest plausible repair.
Deterministic checks validate the proposal structurally.
The repair is NOT considered verified until downstream simulation,
coverage, mutation, formal/equivalence, and judge stages accept it.

Inputs from VerificationState
-----------------------------
- specification
- rtl_code
- rtl_analysis
- failure_analysis
- bug_location
- simulation_output
- simulation_error
- tests
- coverage
- formal_result
- run_dir
- iteration

Outputs
-------
- repair_proposal
- repaired_rtl
- rtl_version
- logs
- agent_trace
- warnings
- errors
- status

Artifacts
---------
verification_logs/runs/<RUN_ID>/rtl/
    repair_iteration_<N>.v
    repair_iteration_<N>_proposal.json
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from langchain_groq import ChatGroq

from config.settings import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    GROQ_API_KEY,
    AGENT_TOKEN_LIMITS,
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


class RTLRepairAgent:
    """
    Conservative AI-assisted RTL repair agent.

    Important:
        This agent proposes and structurally validates a repair.
        It does not declare the RTL verified.
    """

    name = "RTL Repair Agent"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: Optional[int] = None,
    ):
        self.model = model
        self.temperature = temperature

        configured_limit = AGENT_TOKEN_LIMITS.get(
            "rtl_repair",
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
        """
        Load the external repair prompt.

        Falls back to a compact built-in prompt if the file is missing.
        """

        try:
            prompt = load_prompt("rtl_repair")
            if prompt and prompt.strip():
                return prompt
        except Exception:
            pass

        return """
You are an expert semiconductor RTL repair engineer.

Your task is to propose the SMALLEST plausible RTL repair based only on
the supplied verification evidence.

Rules:
1. Preserve the existing module interface.
2. Preserve unrelated RTL.
3. Make the minimum necessary behavioral change.
4. Do not redesign the module.
5. Do not invent signals unless absolutely necessary.
6. Do not change clock/reset architecture without strong evidence.
7. Do not change testbench behavior.
8. Do not claim the repair is verified.
9. Return ONLY compact JSON.
10. Include the complete repaired RTL.

Schema:

{
  "root_cause": "concise explanation",
  "repair_strategy": "minimal repair description",
  "changed_lines": [
    {
      "line": 42,
      "before": "...",
      "after": "...",
      "reason": "..."
    }
  ],
  "repaired_rtl": "complete RTL source",
  "confidence": 0.0,
  "reason": "why this repair is justified"
}

If evidence is insufficient, return the original RTL unchanged and set
confidence below 0.40.

Never claim that the repair has been verified.
"""

    # ------------------------------------------------------------------
    # Utility functions
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _clean_code(text: str) -> str:
        """
        Remove Markdown fences accidentally returned by an LLM.
        """

        if not text:
            return ""

        text = text.strip()

        text = re.sub(
            r"^```(?:verilog|systemverilog|sv|v)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        return text.strip()

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        Safely extract a JSON object from an LLM response.
        """

        if not text:
            return {}

        text = text.strip()

        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else {}
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            candidate = text[start : end + 1]

            try:
                value = json.loads(candidate)
                return value if isinstance(value, dict) else {}
            except Exception:
                return {}

        return {}

    @staticmethod
    def _module_names(rtl: str) -> List[str]:
        """
        Extract module names so that an AI repair cannot silently replace
        the design with a different module/interface.
        """

        if not rtl:
            return []

        return re.findall(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)",
            rtl,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _endmodule_count(rtl: str) -> int:
        return len(
            re.findall(
                r"\bendmodule\b",
                rtl or "",
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _has_basic_rtl_structure(rtl: str) -> bool:
        if not rtl:
            return False

        if "module" not in rtl.lower():
            return False

        if "endmodule" not in rtl.lower():
            return False

        if RTLRepairAgent._endmodule_count(rtl) == 0:
            return False

        return True

    @staticmethod
    def _normalize_changed_lines(
        changed_lines: Any,
    ) -> List[Dict[str, Any]]:
        """
        Normalize AI-generated changed line metadata.
        """

        if not isinstance(changed_lines, list):
            return []

        result: List[Dict[str, Any]] = []

        for item in changed_lines[:12]:
            if not isinstance(item, dict):
                continue

            result.append(
                {
                    "line": item.get("line"),
                    "before": limit_text(
                        str(item.get("before", "")),
                        250,
                    ),
                    "after": limit_text(
                        str(item.get("after", "")),
                        250,
                    ),
                    "reason": limit_text(
                        str(item.get("reason", "")),
                        300,
                    ),
                }
            )

        return result

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------

    def _build_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        rtl = state.get("rtl_code", "") or ""

        failure = state.get("failure_analysis", {}) or {}
        bug_location = state.get("bug_location", {}) or {}
        rtl_analysis = state.get("rtl_analysis", {}) or {}
        coverage = state.get("coverage", {}) or {}
        formal_result = state.get("formal_result", {}) or {}

        simulation_output = state.get(
            "simulation_output",
            state.get("run_output", ""),
        )

        simulation_error = state.get(
            "simulation_error",
            state.get("error_log", ""),
        )

        tests = state.get("tests", []) or []

        return {
            "specification": limit_text(
                str(
                    state.get(
                        "specification",
                        state.get("prompt", ""),
                    )
                    or ""
                ),
                3000,
            ),
            "rtl": compact_rtl(
                rtl,
                max_chars=9000,
            ),
            "rtl_analysis": compact_rtl_analysis(
                rtl_analysis,
                max_chars=1800,
            ),
            "failure_analysis": compact_failure(
                failure,
                max_chars=2200,
            ),
            "bug_location": compact_json(
                bug_location,
                max_chars=1800,
            ),
            "simulation_output": compact_simulation_log(
                simulation_output,
                max_chars=1800,
            ),
            "simulation_error": compact_simulation_log(
                simulation_error,
                max_chars=1800,
            ),
            "coverage": compact_json(
                coverage,
                max_chars=1600,
            ),
            "formal_result": compact_json(
                formal_result,
                max_chars=1600,
            ),
            "tests": compact_json(
                tests[:8],
                max_chars=1800,
            ),
        }

    # ------------------------------------------------------------------
    # Deterministic repair assessment
    # ------------------------------------------------------------------

    def _assess_repair(
        self,
        original_rtl: str,
        repaired_rtl: str,
    ) -> Tuple[bool, List[str]]:
        """
        Structural safety checks.

        These checks intentionally do NOT prove functional correctness.
        """

        warnings: List[str] = []

        if not repaired_rtl:
            return False, ["Repair output is empty."]

        if not self._has_basic_rtl_structure(repaired_rtl):
            return False, [
                "Repair does not contain a valid basic module/endmodule structure."
            ]

        original_modules = self._module_names(original_rtl)
        repaired_modules = self._module_names(repaired_rtl)

        if original_modules != repaired_modules:
            return False, [
                "Repair changed the module name/interface structure."
            ]

        original_endmodules = self._endmodule_count(original_rtl)
        repaired_endmodules = self._endmodule_count(repaired_rtl)

        if original_endmodules != repaired_endmodules:
            return False, [
                "Repair changed the number of endmodule declarations."
            ]

        original_len = len(original_rtl)
        repaired_len = len(repaired_rtl)

        if original_len > 0:
            ratio = repaired_len / original_len

            if ratio < 0.50:
                return False, [
                    "Repair is substantially smaller than the original RTL."
                ]

            if ratio > 2.00:
                return False, [
                    "Repair is substantially larger than the original RTL."
                ]

            if ratio > 1.50:
                warnings.append(
                    "Repair is significantly larger than the original RTL."
                )

        if repaired_rtl == original_rtl:
            warnings.append(
                "No RTL change was proposed."
            )

        return True, warnings

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.llm is None:
            return {}

        user_prompt = f"""
{self.prompt_template}

VERIFICATION CONTEXT
====================

SPECIFICATION:
{context["specification"]}

RTL:
{context["rtl"]}

RTL ANALYSIS:
{context["rtl_analysis"]}

FAILURE ANALYSIS:
{context["failure_analysis"]}

BUG LOCATION:
{context["bug_location"]}

SIMULATION OUTPUT:
{context["simulation_output"]}

SIMULATION ERROR:
{context["simulation_error"]}

COVERAGE:
{context["coverage"]}

FORMAL RESULT:
{context["formal_result"]}

RECENT TESTS:
{context["tests"]}

Return ONLY JSON.
"""

        # Keep the request compact to reduce Groq TPM usage.
        user_prompt = limit_text(
            user_prompt,
            17500,
        )

        try:
            response = self.llm.invoke(user_prompt)

            content = getattr(response, "content", "")

            if isinstance(content, list):
                content = "".join(
                    str(item)
                    for item in content
                )

            return self._extract_json(str(content))

        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_proposal(
        self,
        rtl: str,
        failure_analysis: Dict[str, Any],
        bug_location: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Safe fallback.

        We deliberately do not perform blind regex-based RTL modifications.
        A false repair is substantially worse than asking downstream agents
        to generate better evidence.
        """

        category = str(
            failure_analysis.get("category", "UNKNOWN")
        )

        root_cause = str(
            failure_analysis.get(
                "root_cause",
                failure_analysis.get(
                    "summary",
                    "Insufficient evidence for a safe automatic repair.",
                ),
            )
        )

        primary = bug_location.get("primary", {})
        if not isinstance(primary, dict):
            primary = {}

        return {
            "root_cause": root_cause,
            "repair_strategy": (
                "No automatic RTL modification made because "
                "sufficient evidence for a conservative repair was unavailable."
            ),
            "changed_lines": [],
            "repaired_rtl": rtl,
            "confidence": 0.20,
            "reason": (
                f"Failure category={category}. "
                f"Primary suspected location="
                f"{primary.get('line', 'unknown')}. "
                "A safe repair requires stronger evidence."
            ),
            "fallback": True,
        }

    # ------------------------------------------------------------------
    # Artifact handling
    # ------------------------------------------------------------------

    def _save_artifacts(
        self,
        state: Dict[str, Any],
        proposal: Dict[str, Any],
        repaired_rtl: str,
    ) -> Dict[str, str]:
        run_dir = state.get("run_dir")

        if not run_dir:
            return {}

        rtl_dir = os.path.join(
            run_dir,
            "rtl",
        )

        os.makedirs(
            rtl_dir,
            exist_ok=True,
        )

        iteration = int(
            state.get("iteration", 1) or 1
        )

        rtl_path = os.path.join(
            rtl_dir,
            f"repair_iteration_{iteration}.v",
        )

        proposal_path = os.path.join(
            rtl_dir,
            f"repair_iteration_{iteration}_proposal.json",
        )

        try:
            with open(
                rtl_path,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(repaired_rtl)

            with open(
                proposal_path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    proposal,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            return {
                "rtl_file": rtl_path,
                "proposal_file": proposal_path,
            }

        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        started = datetime.utcnow()

        rtl = state.get("rtl_code", "") or ""

        logs: List[str] = []
        trace: List[Dict[str, Any]] = []
        warnings: List[str] = []
        errors: List[str] = []

        logs.append(
            f"[{self.name}] Starting RTL repair analysis."
        )

        trace.append(
            {
                "agent": self.name,
                "status": "STARTED",
                "timestamp": self._timestamp(),
                "message": "Analyzing verification evidence for a conservative RTL repair.",
            }
        )

        if not rtl.strip():
            error = "No RTL code supplied to RTL Repair Agent."

            errors.append(error)

            trace.append(
                {
                    "agent": self.name,
                    "status": "FAILED",
                    "timestamp": self._timestamp(),
                    "message": error,
                }
            )

            return {
                "repair_proposal": {},
                "repaired_rtl": "",
                "rtl_version": state.get(
                    "rtl_version",
                    "v1",
                ),
                "agent_log": logs,
                "agent_trace": trace,
                "warnings": warnings,
                "errors": errors,
                "status": "FAILED",
            }

        context = self._build_context(state)

        failure_analysis = state.get(
            "failure_analysis",
            {},
        ) or {}

        bug_location = state.get(
            "bug_location",
            {},
        ) or {}

        # --------------------------------------------------------------
        # Ask AI for repair
        # --------------------------------------------------------------

        ai_proposal = self._call_llm(context)

        if ai_proposal:
            logs.append(
                f"[{self.name}] AI repair proposal received."
            )
        else:
            logs.append(
                f"[{self.name}] AI repair unavailable; using conservative fallback."
            )

        if not ai_proposal:
            proposal = self._fallback_proposal(
                rtl,
                failure_analysis,
                bug_location,
            )
        else:
            proposal = {
                "root_cause": limit_text(
                    str(
                        ai_proposal.get(
                            "root_cause",
                            "",
                        )
                    ),
                    800,
                ),
                "repair_strategy": limit_text(
                    str(
                        ai_proposal.get(
                            "repair_strategy",
                            "",
                        )
                    ),
                    1200,
                ),
                "changed_lines": self._normalize_changed_lines(
                    ai_proposal.get(
                        "changed_lines",
                        [],
                    )
                ),
                "repaired_rtl": self._clean_code(
                    str(
                        ai_proposal.get(
                            "repaired_rtl",
                            "",
                        )
                    )
                ),
                "confidence": float(
                    ai_proposal.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                ),
                "reason": limit_text(
                    str(
                        ai_proposal.get(
                            "reason",
                            "",
                        )
                    ),
                    1200,
                ),
                "fallback": False,
            }

        # --------------------------------------------------------------
        # Clamp confidence
        # --------------------------------------------------------------

        proposal["confidence"] = max(
            0.0,
            min(
                1.0,
                float(
                    proposal.get(
                        "confidence",
                        0.0,
                    )
                ),
            ),
        )

        repaired_rtl = self._clean_code(
            str(
                proposal.get(
                    "repaired_rtl",
                    "",
                )
            )
        )

        # --------------------------------------------------------------
        # Structural validation
        # --------------------------------------------------------------

        valid, structural_warnings = self._assess_repair(
            rtl,
            repaired_rtl,
        )

        warnings.extend(
            structural_warnings
        )

        if not valid:
            logs.append(
                f"[{self.name}] Proposed repair rejected by structural validation."
            )

            repaired_rtl = rtl

            proposal["repair_accepted"] = False
            proposal["validation_status"] = "REJECTED"
            proposal["validation_reason"] = (
                "; ".join(structural_warnings)
                if structural_warnings
                else "Structural validation failed."
            )

            proposal["repaired_rtl"] = rtl

        else:
            proposal["repair_accepted"] = (
                repaired_rtl != rtl
            )

            proposal["validation_status"] = (
                "STRUCTURALLY_VALID"
                if repaired_rtl != rtl
                else "NO_CHANGE"
            )

        # --------------------------------------------------------------
        # Never accept low-confidence repair automatically
        # --------------------------------------------------------------

        confidence = float(
            proposal.get(
                "confidence",
                0.0,
            )
        )

        if (
            repaired_rtl != rtl
            and confidence < 0.45
        ):
            warnings.append(
                "Repair confidence is below the automatic-acceptance threshold."
            )

            proposal["automatic_acceptance"] = False
            proposal["validation_status"] = (
                "LOW_CONFIDENCE_REVIEW_REQUIRED"
            )

        elif repaired_rtl != rtl:
            proposal["automatic_acceptance"] = False
            proposal["validation_status"] = (
                "PROPOSED_DOWNSTREAM_VERIFICATION_REQUIRED"
            )
        else:
            proposal["automatic_acceptance"] = False

        # --------------------------------------------------------------
        # Version
        # --------------------------------------------------------------

        current_version = str(
            state.get(
                "rtl_version",
                "v1",
            )
            or "v1"
        )

        match = re.search(
            r"(\d+)$",
            current_version,
        )

        if match:
            next_number = int(
                match.group(1)
            ) + (
                1
                if repaired_rtl != rtl
                else 0
            )

            rtl_version = (
                f"{current_version[:match.start()]}"
                f"{next_number}"
            )
        else:
            rtl_version = (
                f"{current_version}_repair"
                if repaired_rtl != rtl
                else current_version
            )

        proposal["rtl_version"] = rtl_version
        proposal["timestamp"] = self._timestamp()

        # --------------------------------------------------------------
        # Save artifacts
        # --------------------------------------------------------------

        artifacts = self._save_artifacts(
            state,
            proposal,
            repaired_rtl,
        )

        if artifacts:
            proposal["artifacts"] = artifacts

            logs.append(
                f"[{self.name}] Repair artifacts saved."
            )

        # --------------------------------------------------------------
        # Final trace
        # --------------------------------------------------------------

        elapsed = (
            datetime.utcnow() - started
        ).total_seconds()

        if repaired_rtl != rtl:
            status = "REPAIR_PROPOSED"

            message = (
                f"Proposed conservative RTL repair "
                f"(confidence={confidence:.2f}). "
                "Downstream verification is required."
            )
        else:
            status = "NO_REPAIR"

            message = (
                "No RTL modification accepted; additional verification "
                "evidence is required."
            )

        logs.append(
            f"[{self.name}] {message}"
        )

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
            "repair_proposal": proposal,
            "repaired_rtl": repaired_rtl,
            "rtl_version": rtl_version,
            "agent_log": logs,
            "agent_trace": trace,
            "warnings": warnings,
            "errors": errors,
            "status": status,
            "next_action": (
                "VERIFY_REPAIR"
                if repaired_rtl != rtl
                else "GENERATE_MORE_EVIDENCE"
            ),
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
    "RTLRepairAgent",
]
