"""
PragyanAI SiliconAI
Formal Verification Agent

Purpose
-------
Generate and execute lightweight formal verification properties for RTL.

The Formal Agent is responsible for:
    1. Identifying important formal properties.
    2. Generating simple SystemVerilog Assertions.
    3. Preparing a SymbiYosys job.
    4. Executing the formal runner when available.
    5. Capturing counterexamples / failures.
    6. Returning structured formal evidence.

Important
---------
This agent is deliberately conservative.

It does NOT claim formal proof unless the formal backend reports
success.

For arbitrary generated RTL, formal verification may fail because:
    - the design is not formally suitable
    - assumptions are missing
    - unsupported constructs are present
    - clock/reset information is unclear
    - properties cannot be bound correctly
    - SymbiYosys/Yosys is unavailable

In those situations the result is reported as:
    NOT_PROVEN
    FAILED
    UNSUPPORTED
    UNAVAILABLE

Typical flow:

    Mutation Agent
          |
          v
     Formal Agent
          |
     +----+----------------+
     |                     |
     v                     v
   PROVEN              COUNTEREXAMPLE
     |                     |
     v                     v
 Verification Judge   Bug Localization
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
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
    compact_json,
    compact_rtl,
    compact_rtl_analysis,
    limit_text,
    load_prompt,
)
from eda.formal_runner import FormalRunner


class FormalAgent:
    """
    AI-assisted formal-property generation and deterministic
    formal execution agent.
    """

    AGENT_NAME = "Formal Agent"

    VALID_STATUS = {
        "PROVEN",
        "FAILED",
        "NOT_PROVEN",
        "UNSUPPORTED",
        "UNAVAILABLE",
        "SKIPPED",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        runner: Optional[FormalRunner] = None,
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

        self.runner = runner or FormalRunner()

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
    def _save_text(
        path: Path,
        content: str,
    ) -> Optional[str]:

        try:

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                content or "",
                encoding="utf-8",
            )

            return str(path)

        except Exception:

            return None

    @staticmethod
    def _save_json(
        path: Path,
        data: Any,
    ) -> Optional[str]:

        try:

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            return str(path)

        except Exception:

            return None

    # ------------------------------------------------------------------
    # RTL structural inspection
    # ------------------------------------------------------------------

    def _inspect_rtl(
        self,
        rtl_code: str,
    ) -> Dict[str, Any]:

        code = rtl_code or ""

        clocks = re.findall(
            r"\b(?:posedge|negedge)\s+([A-Za-z_]\w*)",
            code,
            flags=re.IGNORECASE,
        )

        resets = re.findall(
            r"\b(?:rst|reset|rst_n|reset_n)\w*",
            code,
            flags=re.IGNORECASE,
        )

        registers = re.findall(
            r"\breg\s+(?:\[[^\]]+\]\s*)?([A-Za-z_]\w*)",
            code,
            flags=re.IGNORECASE,
        )

        always_blocks = re.findall(
            r"\balways(?:_ff|_comb)?\b",
            code,
            flags=re.IGNORECASE,
        )

        case_blocks = re.findall(
            r"\bcase\s*\(",
            code,
            flags=re.IGNORECASE,
        )

        assertions = re.findall(
            r"\bassert(?:ion)?\b",
            code,
            flags=re.IGNORECASE,
        )

        return {
            "clocks": list(
                dict.fromkeys(clocks)
            )[:10],
            "resets": list(
                dict.fromkeys(resets)
            )[:10],
            "registers": list(
                dict.fromkeys(registers)
            )[:20],
            "always_blocks": len(
                always_blocks
            ),
            "case_blocks": len(
                case_blocks
            ),
            "existing_assertions": len(
                assertions
            ),
        }

    # ------------------------------------------------------------------
    # Deterministic formal properties
    # ------------------------------------------------------------------

    def _generate_baseline_properties(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        inspection = self._inspect_rtl(
            rtl_code
        )

        properties: List[Dict[str, Any]] = []

        clocks = inspection["clocks"]
        resets = inspection["resets"]

        # --------------------------------------------------------------
        # Reset property
        # --------------------------------------------------------------

        if clocks and resets:

            clock = clocks[0]
            reset = resets[0]

            properties.append(
                {
                    "id": "FP001",
                    "name": "Reset State Stability",
                    "category": "RESET",
                    "severity": "HIGH",
                    "clock": clock,
                    "assertion": (
                        f"assert property "
                        f"(@(posedge {clock}) "
                        f"{reset} |-> $stable({reset}));"
                    ),
                    "intent": (
                        "Check reset-related stability assumptions."
                    ),
                }
            )

        # --------------------------------------------------------------
        # Valid/ready handshake
        # --------------------------------------------------------------

        code_lower = rtl_code.lower()

        if (
            "valid" in code_lower
            and "ready" in code_lower
            and clocks
        ):

            clock = clocks[0]

            properties.append(
                {
                    "id": "FP002",
                    "name": "Valid Persistence",
                    "category": "PROTOCOL",
                    "severity": "HIGH",
                    "clock": clock,
                    "assertion": (
                        f"assert property "
                        f"(@(posedge {clock}) "
                        f"valid && !ready |=> valid);"
                    ),
                    "intent": (
                        "A valid transaction should remain asserted "
                        "until accepted, when required by the protocol."
                    ),
                }
            )

        # --------------------------------------------------------------
        # FIFO properties
        # --------------------------------------------------------------

        if "fifo" in (
            specification
            + rtl_code
        ).lower():

            if clocks:

                clock = clocks[0]

                if "full" in code_lower:

                    properties.append(
                        {
                            "id": "FP003",
                            "name": "FIFO Full Protection",
                            "category": "FIFO",
                            "severity": "CRITICAL",
                            "clock": clock,
                            "assertion": (
                                f"assert property "
                                f"(@(posedge {clock}) "
                                f"full |-> !write);"
                            ),
                            "intent": (
                                "Prevent writes while FIFO is full."
                            ),
                        }
                    )

                if "empty" in code_lower:

                    properties.append(
                        {
                            "id": "FP004",
                            "name": "FIFO Empty Protection",
                            "category": "FIFO",
                            "severity": "CRITICAL",
                            "clock": clock,
                            "assertion": (
                                f"assert property "
                                f"(@(posedge {clock}) "
                                f"empty |-> !read);"
                            ),
                            "intent": (
                                "Prevent reads while FIFO is empty."
                            ),
                        }
                    )

        # --------------------------------------------------------------
        # Counter properties
        # --------------------------------------------------------------

        if (
            "counter" in specification.lower()
            or "count" in code_lower
        ):

            if clocks:

                clock = clocks[0]

                properties.append(
                    {
                        "id": "FP005",
                        "name": "Counter Stability",
                        "category": "COUNTER",
                        "severity": "MEDIUM",
                        "clock": clock,
                        "assertion": (
                            f"assert property "
                            f"(@(posedge {clock}) "
                            f"$isunknown(count) == 0);"
                        ),
                        "intent": (
                            "Detect unknown counter values."
                        ),
                    }
                )

        # --------------------------------------------------------------
        # Unknown-state detection
        # --------------------------------------------------------------

        if clocks:

            clock = clocks[0]

            for signal in inspection["registers"][:3]:

                properties.append(
                    {
                        "id": f"FP{len(properties)+1:03d}",
                        "name": (
                            f"Unknown Check: {signal}"
                        ),
                        "category": "X_PROPAGATION",
                        "severity": "MEDIUM",
                        "clock": clock,
                        "assertion": (
                            f"assert property "
                            f"(@(posedge {clock}) "
                            f"!$isunknown({signal}));"
                        ),
                        "intent": (
                            f"Check that register {signal} "
                            "does not become unknown."
                        ),
                    }
                )

        # --------------------------------------------------------------
        # Limit
        # --------------------------------------------------------------

        return properties[:10]

    # ------------------------------------------------------------------
    # AI property generation
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        baseline: List[Dict[str, Any]],
    ) -> List[Any]:

        system_prompt = load_prompt(
            "formal_verification"
        )

        if not system_prompt:

            system_prompt = """
You are an expert formal RTL verification engineer.

Generate a small number of conservative SystemVerilog Assertions
from the supplied RTL and specification.

Only generate properties that are strongly supported by the
available signals and behavior.

Return ONLY JSON:

{
  "properties": [
    {
      "id": "FP001",
      "name": "...",
      "category": "...",
      "severity": "HIGH",
      "clock": "clk",
      "assertion": "assert property (...);",
      "intent": "..."
    }
  ]
}

Maximum 6 properties.

Never claim that a property has been formally proven.
"""

        payload = {
            "specification": limit_text(
                specification,
                2200,
            ),
            "rtl": compact_rtl(
                rtl_code,
                5500,
            ),
            "rtl_analysis": compact_rtl_analysis(
                rtl_analysis
            ),
            "baseline_properties": baseline[:8],
        }

        return [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=(
                    "Generate conservative formal properties "
                    "for this RTL.\n\n"
                    + compact_json(
                        payload,
                        11000,
                    )
                )
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
    # Merge properties
    # ------------------------------------------------------------------

    def _merge_properties(
        self,
        baseline: List[Dict[str, Any]],
        ai_result: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        properties = list(
            baseline
        )

        if not isinstance(
            ai_result,
            dict,
        ):
            return properties[:12]

        ai_properties = (
            ai_result.get(
                "properties"
            )
            or ai_result.get(
                "formal_properties"
            )
            or []
        )

        if not isinstance(
            ai_properties,
            list,
        ):
            return properties[:12]

        for item in ai_properties:

            if not isinstance(
                item,
                dict,
            ):
                continue

            assertion = str(
                item.get(
                    "assertion",
                    "",
                )
            ).strip()

            if not assertion:
                continue

            # Basic sanity check.
            if "assert" not in assertion.lower():
                continue

            name = str(
                item.get(
                    "name",
                    f"AI Formal Property {len(properties)+1}",
                )
            ).strip()

            duplicate = any(
                assertion == str(
                    existing.get(
                        "assertion",
                        "",
                    )
                ).strip()
                for existing in properties
            )

            if duplicate:
                continue

            properties.append(
                {
                    "id": f"FP{len(properties)+1:03d}",
                    "name": name[:200],
                    "category": str(
                        item.get(
                            "category",
                            "GENERAL",
                        )
                    ).upper()[:50],
                    "severity": str(
                        item.get(
                            "severity",
                            "MEDIUM",
                        )
                    ).upper()[:20],
                    "clock": str(
                        item.get(
                            "clock",
                            "",
                        )
                    )[:100],
                    "assertion": assertion[:1000],
                    "intent": str(
                        item.get(
                            "intent",
                            "",
                        )
                    )[:500],
                    "source": "Formal Agent",
                }
            )

            if len(properties) >= 12:
                break

        return properties[:12]

    # ------------------------------------------------------------------
    # Formal file preparation
    # ------------------------------------------------------------------

    def _prepare_formal_files(
        self,
        state: Dict[str, Any],
        rtl_code: str,
        properties: List[Dict[str, Any]],
    ) -> Dict[str, str]:

        run_dir = state.get(
            "run_dir"
        )

        if run_dir:

            formal_dir = (
                Path(run_dir)
                / "formal"
            )

        else:

            formal_dir = (
                Path("verification_logs")
                / "formal"
            )

        formal_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        design_path = formal_dir / "design.sv"
        properties_path = formal_dir / "properties.sv"

        property_text = "\n\n".join(
            str(
                prop.get(
                    "assertion",
                    "",
                )
            )
            for prop in properties
            if prop.get(
                "assertion"
            )
        )

        self._save_text(
            design_path,
            rtl_code,
        )

        self._save_text(
            properties_path,
            property_text,
        )

        return {
            "formal_dir": str(
                formal_dir
            ),
            "design": str(
                design_path
            ),
            "properties": str(
                properties_path
            ),
        }

    # ------------------------------------------------------------------
    # Formal runner compatibility
    # ------------------------------------------------------------------

    def _execute_formal(
        self,
        rtl_code: str,
        properties: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Execute FormalRunner while supporting small API variations
        between runner implementations.
        """

        try:

            result = self.runner.run(
                rtl_code=rtl_code,
                properties=properties,
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except TypeError:

            pass

        except Exception as exc:

            return {
                "status": "UNAVAILABLE",
                "success": False,
                "error": str(exc),
                "output": "",
            }

        # Compatibility fallback.
        try:

            result = self.runner.run(
                rtl_code,
                properties,
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except Exception as exc:

            return {
                "status": "UNAVAILABLE",
                "success": False,
                "error": str(exc),
                "output": "",
            }

        return {
            "status": "UNAVAILABLE",
            "success": False,
            "error": (
                "FormalRunner returned no structured result."
            ),
            "output": "",
        }

    # ------------------------------------------------------------------
    # Interpret result
    # ------------------------------------------------------------------

    def _interpret_formal_result(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:

        raw_status = str(
            result.get(
                "status",
                "",
            )
        ).upper()

        success = bool(
            result.get(
                "success",
                result.get(
                    "passed",
                    False,
                ),
            )
        )

        output = str(
            result.get(
                "output",
                result.get(
                    "stdout",
                    "",
                ),
            )
        )

        error = str(
            result.get(
                "error",
                result.get(
                    "stderr",
                    "",
                ),
            )
        )

        combined = (
            output
            + "\n"
            + error
        ).upper()

        if (
            raw_status in self.VALID_STATUS
        ):

            status = raw_status

        elif success:

            status = "PROVEN"

        elif any(
            marker in combined
            for marker in [
                "COUNTEREXAMPLE",
                "ASSERTION FAILED",
                "FAILED",
                "FAIL",
                "VIOLATED",
            ]
        ):

            status = "FAILED"

        elif any(
            marker in combined
            for marker in [
                "NOT FOUND",
                "UNSUPPORTED",
                "UNKNOWN OPTION",
            ]
        ):

            status = "UNSUPPORTED"

        else:

            status = "NOT_PROVEN"

        counterexample = ""

        for marker in [
            "counterexample",
            "trace",
            "assertion failed",
            "failed",
        ]:

            index = combined.lower().find(
                marker.lower()
            )

            if index >= 0:

                counterexample = self._compact(
                    (
                        output
                        + "\n"
                        + error
                    )[max(0, index - 200):],
                    3000,
                )

                break

        return {
            "status": status,
            "success": status == "PROVEN",
            "output": self._compact(
                output,
                5000,
            ),
            "error": self._compact(
                error,
                3000,
            ),
            "counterexample": counterexample,
        }

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.time()

        rtl_code = str(
            state.get("rtl_code")
            or ""
        ).strip()

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

        # --------------------------------------------------------------
        # Validate
        # --------------------------------------------------------------

        if not rtl_code:

            message = (
                "Formal verification skipped: RTL code is empty."
            )

            trace = {
                "agent": self.AGENT_NAME,
                "status": "FAILED",
                "timestamp": self._timestamp(),
                "message": message,
            }

            return {
                "formal_result": {
                    "status": "SKIPPED",
                    "success": False,
                    "reason": message,
                },
                "agent_trace": (
                    list(
                        state.get(
                            "agent_trace"
                        )
                        or []
                    )
                    + [trace]
                ),
                "status": "FAILED",
            }

        # --------------------------------------------------------------
        # Generate baseline properties
        # --------------------------------------------------------------

        baseline = self._generate_baseline_properties(
            rtl_code=rtl_code,
            specification=specification,
            rtl_analysis=rtl_analysis,
        )

        # --------------------------------------------------------------
        # AI properties
        # --------------------------------------------------------------

        ai_result = None

        if self.llm:

            messages = self._build_messages(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
                baseline=baseline,
            )

            ai_result = self._call_llm(
                messages
            )

        properties = self._merge_properties(
            baseline=baseline,
            ai_result=ai_result,
        )

        # --------------------------------------------------------------
        # No properties
        # --------------------------------------------------------------

        if not properties:

            message = (
                "No suitable formal properties could be generated."
            )

            elapsed = round(
                time.time() - start,
                3,
            )

            trace = {
                "agent": self.AGENT_NAME,
                "status": "COMPLETED",
                "timestamp": self._timestamp(),
                "message": message,
                "duration_seconds": elapsed,
            }

            return {
                "formal_result": {
                    "status": "SKIPPED",
                    "success": False,
                    "properties": [],
                    "reason": message,
                },
                "formal_properties": [],
                "agent_trace": (
                    list(
                        state.get(
                            "agent_trace"
                        )
                        or []
                    )
                    + [trace]
                ),
                "status": "COMPLETED",
            }

        # --------------------------------------------------------------
        # Prepare files
        # --------------------------------------------------------------

        artifacts = self._prepare_formal_files(
            state=state,
            rtl_code=rtl_code,
            properties=properties,
        )

        property_text = "\n\n".join(
            prop["assertion"]
            for prop in properties
        )

        # --------------------------------------------------------------
        # Execute formal backend
        # --------------------------------------------------------------

        runner_result = self._execute_formal(
            rtl_code=rtl_code,
            properties=property_text,
            state=state,
        )

        interpreted = (
            self._interpret_formal_result(
                runner_result
            )
        )

        # --------------------------------------------------------------
        # Save result
        # --------------------------------------------------------------

        formal_dir = Path(
            artifacts["formal_dir"]
        )

        result_payload = {
            "timestamp": self._timestamp(),
            "status": interpreted["status"],
            "success": interpreted["success"],
            "properties": properties,
            "output": interpreted["output"],
            "error": interpreted["error"],
            "counterexample": interpreted[
                "counterexample"
            ],
            "artifacts": artifacts,
        }

        result_path = self._save_json(
            formal_dir / "formal_result.json",
            result_payload,
        )

        # --------------------------------------------------------------
        # Formal score
        # --------------------------------------------------------------

        proven = (
            interpreted["status"]
            == "PROVEN"
        )

        failed = (
            interpreted["status"]
            == "FAILED"
        )

        if proven:

            formal_score = 100.0

        elif failed:

            formal_score = 0.0

        else:

            formal_score = 0.0

        # --------------------------------------------------------------
        # Message
        # --------------------------------------------------------------

        elapsed = round(
            time.time() - start,
            3,
        )

        status = interpreted[
            "status"
        ]

        message = (
            f"Formal verification completed with status "
            f"{status}. "
            f"Generated {len(properties)} property/properties."
        )

        if status == "PROVEN":

            message += (
                " Formal backend reported all checked properties "
                "as proven."
            )

        elif status == "FAILED":

            message += (
                " One or more formal properties were violated "
                "or a counterexample was reported."
            )

        elif status in {
            "UNAVAILABLE",
            "UNSUPPORTED",
        }:

            message += (
                " Formal proof could not be established with "
                "the available backend."
            )

        # --------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": "COMPLETED",
            "timestamp": self._timestamp(),
            "message": message,
            "duration_seconds": elapsed,
            "formal_status": status,
            "property_count": len(
                properties
            ),
            "formal_score": formal_score,
        }

        # --------------------------------------------------------------
        # Agent log
        # --------------------------------------------------------------

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "status": "COMPLETED",
            "timestamp": self._timestamp(),
            "duration_seconds": elapsed,
            "input_summary": {
                "rtl_length": len(
                    rtl_code
                ),
                "specification_length": len(
                    specification
                ),
            },
            "output_summary": {
                "property_count": len(
                    properties
                ),
                "formal_status": status,
                "formal_score": formal_score,
                "counterexample": bool(
                    interpreted[
                        "counterexample"
                    ]
                ),
            },
            "artifacts": artifacts,
            "result_file": result_path or "",
            "ai_used": ai_result is not None,
        }

        # --------------------------------------------------------------
        # Return
        # --------------------------------------------------------------

        return {
            "formal_properties": properties,

            "formal_result": result_payload,

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

            "status": "COMPLETED",
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

def run_formal_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:

    agent = FormalAgent()

    return agent.run(state)


__all__ = [
    "FormalAgent",
    "run_formal_agent",
]
