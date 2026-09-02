"""
PragyanAI SiliconAI
Red Team Agent

Purpose
-------
The Red Team Agent acts as an adversarial verification engineer.

It deliberately searches for:
- Boundary-condition failures
- Illegal inputs
- Reset-related failures
- Protocol violations
- Back-to-back operations
- Overflow / underflow
- FSM illegal states
- Timing-sensitive behavior
- X/Z propagation
- Width/sign issues
- State retention problems
- Handshake failures
- Corner-case sequences

The agent does NOT modify RTL.

It produces compact, machine-readable adversarial scenarios
that can be consumed by the Test Generator / Testbench Generator.

Design goals
------------
1. Compatible with LangGraph state.
2. Compatible with existing config/settings.py and config/prompts.py.
3. Low token usage for Groq.
4. Robust JSON parsing.
5. Deterministic fallback if LLM is unavailable.
6. No false claim that a scenario has passed.
"""

from __future__ import annotations

import json
import re
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
    compact_json,
    compact_red_team,
    compact_rtl,
    compact_rtl_analysis,
    compact_simulation_log,
    compact_text if False else limit_text,
    load_prompt,
)


class RedTeamAgent:
    """
    Adversarial verification agent.

    Input state may contain:
        rtl_code
        specification
        rtl_analysis
        verification_plan
        generated_tests
        tests
        coverage
        coverage_gaps
        failure_analysis
        red_team_scenarios
        simulation_output

    Output:
        red_team_scenarios
        agent_log
        agent_trace
        messages
        warnings
    """

    AGENT_NAME = "Red Team Agent"

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
            DEFAULT_TEMPERATURE if temperature is None else temperature
        )
        self.max_tokens = (
            DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens
        )

        self.llm = None

        if self.api_key:
            try:
                self.llm = ChatGroq(
                    api_key=self.api_key,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=min(self.max_tokens, 1800),
                )
            except Exception:
                self.llm = None

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _safe_json(text: str) -> Optional[Any]:
        """
        Extract JSON from an LLM response.

        Handles:
        - Plain JSON
        - Markdown fenced JSON
        - Extra explanatory text surrounding JSON
        """

        if not text:
            return None

        text = text.strip()

        # Remove markdown fences.
        text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text)

        # First attempt: complete response.
        try:
            return json.loads(text)
        except Exception:
            pass

        # Find first JSON object.
        object_match = re.search(r"\{.*\}", text, flags=re.DOTALL)

        if object_match:
            candidate = object_match.group(0)

            try:
                return json.loads(candidate)
            except Exception:
                pass

        # Find first JSON array.
        array_match = re.search(r"\[.*\]", text, flags=re.DOTALL)

        if array_match:
            candidate = array_match.group(0)

            try:
                return json.loads(candidate)
            except Exception:
                pass

        return None

    @staticmethod
    def _normalize_severity(value: Any) -> str:
        value = str(value or "MEDIUM").upper().strip()

        allowed = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if value not in allowed:
            return "MEDIUM"

        return value

    @staticmethod
    def _normalize_category(value: Any) -> str:
        value = str(value or "CORNER_CASE").upper().strip()

        allowed = {
            "BOUNDARY",
            "RESET",
            "PROTOCOL",
            "TIMING",
            "FSM",
            "OVERFLOW",
            "UNDERFLOW",
            "HANDSHAKE",
            "WIDTH",
            "SIGN",
            "X_PROPAGATION",
            "ILLEGAL_INPUT",
            "SEQUENCE",
            "CONCURRENCY",
            "STATE",
            "CORNER_CASE",
            "FUNCTIONAL",
            "OTHER",
        }

        if value not in allowed:
            return "CORNER_CASE"

        return value

    @staticmethod
    def _normalize_scenario(
        scenario: Dict[str, Any],
        index: int,
    ) -> Dict[str, Any]:

        scenario_id = (
            scenario.get("id")
            or scenario.get("scenario_id")
            or f"RT{index:03d}"
        )

        scenario_id = str(scenario_id).strip()

        # Force consistent IDs.
        if not re.match(r"^RT\d{3,}$", scenario_id):
            scenario_id = f"RT{index:03d}"

        description = str(
            scenario.get("description")
            or scenario.get("scenario")
            or scenario.get("name")
            or "Adversarial verification scenario"
        ).strip()

        attack = str(
            scenario.get("attack")
            or scenario.get("stimulus")
            or scenario.get("action")
            or ""
        ).strip()

        expected = str(
            scenario.get("expected")
            or scenario.get("expected_behavior")
            or "Design should reject or correctly handle the adversarial condition."
        ).strip()

        rationale = str(
            scenario.get("rationale")
            or scenario.get("reason")
            or "Targets a potential corner-case weakness."
        ).strip()

        signals = scenario.get("signals")

        if isinstance(signals, list):
            signals = [
                str(item).strip()
                for item in signals
                if str(item).strip()
            ]
        elif signals:
            signals = [str(signals).strip()]
        else:
            signals = []

        return {
            "id": scenario_id,
            "description": description[:300],
            "category": RedTeamAgent._normalize_category(
                scenario.get("category")
            ),
            "severity": RedTeamAgent._normalize_severity(
                scenario.get("severity")
            ),
            "attack": attack[:500],
            "expected": expected[:400],
            "rationale": rationale[:400],
            "signals": signals[:10],
            "source": str(
                scenario.get("source") or "Red Team Agent"
            ),
        }

    # ------------------------------------------------------------------
    # Static adversarial analysis
    # ------------------------------------------------------------------

    def _static_scenarios(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        verification_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate deterministic adversarial scenarios.

        These scenarios are intentionally independent of the LLM.
        This ensures the platform remains useful even when:
        - API is unavailable
        - rate limits are reached
        - malformed JSON is returned
        """

        rtl_lower = rtl_code.lower()

        scenarios: List[Dict[str, Any]] = []

        # --------------------------------------------------------------
        # Reset attacks
        # --------------------------------------------------------------

        if (
            "reset" in rtl_lower
            or "rst" in rtl_lower
            or "rst_n" in rtl_lower
        ):
            scenarios.append(
                {
                    "id": "RT001",
                    "description": "Assert reset during an active operation",
                    "category": "RESET",
                    "severity": "HIGH",
                    "attack": (
                        "Start a normal transaction, then assert reset "
                        "before the transaction completes."
                    ),
                    "expected": (
                        "All reset-defined state returns to the specified "
                        "reset condition without corrupt residual state."
                    ),
                    "rationale": (
                        "Mid-transaction reset often exposes state-retention "
                        "and recovery defects."
                    ),
                    "signals": ["reset", "state", "valid", "ready"],
                }
            )

            scenarios.append(
                {
                    "id": "RT002",
                    "description": "Deassert reset at an unfavorable clock boundary",
                    "category": "RESET",
                    "severity": "HIGH",
                    "attack": (
                        "Toggle reset close to a clock edge and immediately "
                        "issue a transaction."
                    ),
                    "expected": (
                        "The first post-reset transaction behaves according "
                        "to the reset and synchronization specification."
                    ),
                    "rationale": (
                        "Reset release sequencing can expose initialization "
                        "and state-machine bugs."
                    ),
                    "signals": ["reset", "clk"],
                }
            )

        # --------------------------------------------------------------
        # Boundary attacks
        # --------------------------------------------------------------

        scenarios.extend(
            [
                {
                    "id": "RT003",
                    "description": "Drive minimum legal input value",
                    "category": "BOUNDARY",
                    "severity": "MEDIUM",
                    "attack": "Apply the minimum representable legal input.",
                    "expected": (
                        "Output matches the specification for the minimum "
                        "legal input."
                    ),
                    "rationale": (
                        "Minimum-value boundaries frequently expose "
                        "off-by-one conditions."
                    ),
                    "signals": [],
                },
                {
                    "id": "RT004",
                    "description": "Drive maximum representable input",
                    "category": "BOUNDARY",
                    "severity": "HIGH",
                    "attack": (
                        "Apply the maximum representable value on relevant "
                        "data inputs."
                    ),
                    "expected": (
                        "Design produces the specified result without "
                        "unexpected overflow or truncation."
                    ),
                    "rationale": (
                        "Maximum values expose width, arithmetic and "
                        "overflow defects."
                    ),
                    "signals": [],
                },
                {
                    "id": "RT005",
                    "description": "Test one-step-around-boundary values",
                    "category": "BOUNDARY",
                    "severity": "HIGH",
                    "attack": (
                        "Apply values immediately below, at, and above "
                        "important legal boundaries."
                    ),
                    "expected": (
                        "Boundary transitions follow the specification "
                        "exactly."
                    ),
                    "rationale": (
                        "Off-by-one errors are often invisible to nominal "
                        "functional tests."
                    ),
                    "signals": [],
                },
            ]
        )

        # --------------------------------------------------------------
        # Width / arithmetic
        # --------------------------------------------------------------

        if any(
            keyword in rtl_lower
            for keyword in [
                "+",
                "-",
                "*",
                "<<",
                ">>",
                "width",
            ]
        ):
            scenarios.extend(
                [
                    {
                        "id": "RT006",
                        "description": "Attempt arithmetic overflow",
                        "category": "OVERFLOW",
                        "severity": "HIGH",
                        "attack": (
                            "Drive operands near the maximum value and "
                            "perform an arithmetic operation."
                        ),
                        "expected": (
                            "Overflow behavior matches the specification."
                        ),
                        "rationale": (
                            "Arithmetic width mismatches can silently "
                            "truncate significant bits."
                        ),
                        "signals": [],
                    },
                    {
                        "id": "RT007",
                        "description": "Attempt arithmetic underflow",
                        "category": "UNDERFLOW",
                        "severity": "HIGH",
                        "attack": (
                            "Drive operands near the minimum value and "
                            "perform a subtractive operation."
                        ),
                        "expected": (
                            "Underflow behavior matches the specification."
                        ),
                        "rationale": (
                            "Signedness and width handling are common "
                            "RTL failure modes."
                        ),
                        "signals": [],
                    },
                ]
            )

        # --------------------------------------------------------------
        # FSM attacks
        # --------------------------------------------------------------

        analysis_text = json.dumps(rtl_analysis).lower()

        if "fsm" in analysis_text or "state" in analysis_text:
            scenarios.extend(
                [
                    {
                        "id": "RT008",
                        "description": "Force or reach an illegal FSM state",
                        "category": "FSM",
                        "severity": "CRITICAL",
                        "attack": (
                            "Attempt to drive the state machine toward an "
                            "undefined or illegal state."
                        ),
                        "expected": (
                            "The design recovers safely or follows the "
                            "specified illegal-state behavior."
                        ),
                        "rationale": (
                            "Illegal-state recovery is frequently "
                            "uncovered by nominal tests."
                        ),
                        "signals": ["state"],
                    },
                    {
                        "id": "RT009",
                        "description": "Apply unexpected transition sequence",
                        "category": "SEQUENCE",
                        "severity": "HIGH",
                        "attack": (
                            "Issue a control sequence that skips expected "
                            "intermediate operations."
                        ),
                        "expected": (
                            "The FSM rejects or safely handles the invalid "
                            "transition."
                        ),
                        "rationale": (
                            "Sequence-sensitive bugs may not appear in "
                            "single-operation tests."
                        ),
                        "signals": ["state"],
                    },
                ]
            )

        # --------------------------------------------------------------
        # Handshake / protocol
        # --------------------------------------------------------------

        protocol_keywords = [
            "valid",
            "ready",
            "req",
            "ack",
            "enable",
            "handshake",
        ]

        if any(keyword in rtl_lower for keyword in protocol_keywords):
            scenarios.extend(
                [
                    {
                        "id": "RT010",
                        "description": "Hold valid while ready is low",
                        "category": "HANDSHAKE",
                        "severity": "HIGH",
                        "attack": (
                            "Assert valid and keep it asserted while "
                            "ready remains low for multiple cycles."
                        ),
                        "expected": (
                            "Transaction is neither lost nor duplicated; "
                            "transfer occurs only according to the protocol."
                        ),
                        "rationale": (
                            "Handshake persistence is a common source of "
                            "data-loss bugs."
                        ),
                        "signals": ["valid", "ready"],
                    },
                    {
                        "id": "RT011",
                        "description": "Back-to-back handshake transactions",
                        "category": "PROTOCOL",
                        "severity": "HIGH",
                        "attack": (
                            "Issue transactions on consecutive cycles with "
                            "no idle gap."
                        ),
                        "expected": (
                            "Every accepted transaction is processed exactly "
                            "once and in the correct order."
                        ),
                        "rationale": (
                            "Back-to-back operation stresses pipeline and "
                            "handshake assumptions."
                        ),
                        "signals": ["valid", "ready"],
                    },
                ]
            )

        # --------------------------------------------------------------
        # Unknown / illegal input
        # --------------------------------------------------------------

        scenarios.append(
            {
                "id": "RT012",
                "description": "Inject illegal control input",
                "category": "ILLEGAL_INPUT",
                "severity": "HIGH",
                "attack": (
                    "Drive a control input combination that is outside "
                    "the documented legal operating space."
                ),
                "expected": (
                    "The design safely rejects, ignores, or handles the "
                    "illegal combination as specified."
                ),
                "rationale": (
                    "Robust hardware must not rely solely on ideal inputs."
                ),
                "signals": [],
            }
        )

        scenarios.append(
            {
                "id": "RT013",
                "description": "Check unknown-value propagation",
                "category": "X_PROPAGATION",
                "severity": "HIGH",
                "attack": (
                    "Introduce X/Z conditions where the simulator permits "
                    "them and observe dependent outputs."
                ),
                "expected": (
                    "Unknown-state behavior is consistent with the "
                    "verification assumptions and RTL intent."
                ),
                "rationale": (
                    "X propagation can hide initialization and control bugs."
                ),
                "signals": [],
            }
        )

        # --------------------------------------------------------------
        # Repeated operations
        # --------------------------------------------------------------

        scenarios.append(
            {
                "id": "RT014",
                "description": "Stress repeated identical operations",
                "category": "SEQUENCE",
                "severity": "MEDIUM",
                "attack": (
                    "Repeat the same operation many times without idle "
                    "cycles where the interface permits it."
                ),
                "expected": (
                    "State and outputs remain correct across all repetitions."
                ),
                "rationale": (
                    "Repeated operations expose counters, state retention "
                    "and resource-release problems."
                ),
                "signals": [],
            }
        )

        # --------------------------------------------------------------
        # Specification-derived scenario
        # --------------------------------------------------------------

        if specification:
            spec_lower = specification.lower()

            if "fifo" in spec_lower:
                scenarios.extend(
                    [
                        {
                            "id": "RT015",
                            "description": "Write FIFO until full",
                            "category": "BOUNDARY",
                            "severity": "CRITICAL",
                            "attack": (
                                "Fill the FIFO to capacity and attempt "
                                "one additional write."
                            ),
                            "expected": (
                                "Full behavior and overflow protection "
                                "match the specification."
                            ),
                            "rationale": (
                                "FIFO full-boundary behavior is a critical "
                                "verification point."
                            ),
                            "signals": ["full", "write", "ready"],
                        },
                        {
                            "id": "RT016",
                            "description": "Read FIFO until empty",
                            "category": "BOUNDARY",
                            "severity": "CRITICAL",
                            "attack": (
                                "Drain the FIFO completely and attempt "
                                "one additional read."
                            ),
                            "expected": (
                                "Empty behavior and underflow protection "
                                "match the specification."
                            ),
                            "rationale": (
                                "FIFO empty-boundary behavior can cause "
                                "data corruption."
                            ),
                            "signals": ["empty", "read", "valid"],
                        },
                    ]
                )

            if "counter" in spec_lower:
                scenarios.append(
                    {
                        "id": "RT017",
                        "description": "Force counter wraparound",
                        "category": "OVERFLOW",
                        "severity": "HIGH",
                        "attack": (
                            "Drive the counter to its maximum and apply "
                            "one additional increment."
                        ),
                        "expected": (
                            "Wraparound, saturation, or error behavior "
                            "matches the specification."
                        ),
                        "rationale": (
                            "Counter rollover is a classic corner case."
                        ),
                        "signals": ["count"],
                    }
                )

            if "uart" in spec_lower:
                scenarios.append(
                    {
                        "id": "RT018",
                        "description": "Exercise UART framing boundary",
                        "category": "PROTOCOL",
                        "severity": "HIGH",
                        "attack": (
                            "Transmit data with boundary timing and "
                            "back-to-back frames."
                        ),
                        "expected": (
                            "Start, data, parity and stop handling remain "
                            "protocol compliant."
                        ),
                        "rationale": (
                            "UART bugs frequently occur at frame boundaries."
                        ),
                        "signals": ["tx", "rx"],
                    }
                )

        # Limit deterministic scenarios.
        return scenarios[:20]

    # ------------------------------------------------------------------
    # LLM invocation
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        verification_plan: Dict[str, Any],
        coverage: Dict[str, Any],
        existing_tests: List[Dict[str, Any]],
        failure_analysis: Dict[str, Any],
    ) -> List[Any]:

        system_prompt = load_prompt("red_team")

        if not system_prompt:
            system_prompt = """
You are an expert semiconductor RTL verification red-team engineer.

Find adversarial verification scenarios that can expose RTL bugs.

Focus on:
- boundary conditions
- reset
- illegal inputs
- protocol violations
- timing
- FSM transitions
- overflow/underflow
- width/sign errors
- X/Z behavior
- repeated and back-to-back operations
- corner-case sequences

Return ONLY compact JSON.

Schema:
{
  "scenarios": [
    {
      "id": "RT001",
      "description": "...",
      "category": "BOUNDARY",
      "severity": "HIGH",
      "attack": "...",
      "expected": "...",
      "rationale": "...",
      "signals": ["..."]
    }
  ]
}

Maximum 10 scenarios.
"""

        user_payload = {
            "specification": limit_text(specification, 2500),
            "rtl": compact_rtl(rtl_code, 6000),
            "rtl_analysis": compact_rtl_analysis(rtl_analysis),
            "verification_plan": compact_json(
                verification_plan,
                3000,
            ),
            "coverage": compact_json(
                coverage,
                2000,
            ),
            "existing_tests": compact_red_team(
                existing_tests,
                2500,
            ),
            "failure_analysis": compact_json(
                failure_analysis,
                1800,
            ),
        }

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    "Generate adversarial RTL verification scenarios.\n\n"
                    + compact_json(user_payload, 12000)
                )
            ),
        ]

    def _call_llm(
        self,
        messages: List[Any],
    ) -> Optional[Any]:

        if not self.llm:
            return None

        try:
            response = self.llm.invoke(messages)

            content = getattr(response, "content", "")

            if isinstance(content, list):
                content = "".join(
                    str(item)
                    for item in content
                )

            return self._safe_json(str(content))

        except Exception:
            # Deliberately return None.
            #
            # The caller falls back to deterministic scenarios.
            # This prevents the verification workflow from failing
            # simply because the AI service is unavailable.
            return None

    # ------------------------------------------------------------------
    # Merge / deduplicate
    # ------------------------------------------------------------------

    def _merge_scenarios(
        self,
        static_scenarios: List[Dict[str, Any]],
        ai_scenarios: Optional[Any],
    ) -> List[Dict[str, Any]]:

        candidates: List[Dict[str, Any]] = []

        candidates.extend(static_scenarios)

        if isinstance(ai_scenarios, dict):
            ai_scenarios = (
                ai_scenarios.get("scenarios")
                or ai_scenarios.get("red_team_scenarios")
                or []
            )

        if isinstance(ai_scenarios, list):
            candidates.extend(
                item
                for item in ai_scenarios
                if isinstance(item, dict)
            )

        normalized: List[Dict[str, Any]] = []
        seen_descriptions = set()

        for index, item in enumerate(candidates, start=1):

            scenario = self._normalize_scenario(
                item,
                index,
            )

            key = re.sub(
                r"\s+",
                " ",
                scenario["description"].lower(),
            ).strip()

            if not key:
                continue

            if key in seen_descriptions:
                continue

            seen_descriptions.add(key)

            normalized.append(scenario)

        # Re-number IDs so there are no collisions between
        # deterministic and AI-generated scenarios.
        final: List[Dict[str, Any]] = []

        for index, scenario in enumerate(normalized, start=1):
            scenario["id"] = f"RT{index:03d}"
            final.append(scenario)

            if len(final) >= 20:
                break

        return final

    # ------------------------------------------------------------------
    # Public execution
    # ------------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        start_time = datetime.utcnow()

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
            if isinstance(state.get("rtl_analysis"), dict)
            else {}
        )

        verification_plan = (
            state.get("verification_plan")
            if isinstance(state.get("verification_plan"), dict)
            else {}
        )

        coverage = (
            state.get("coverage")
            if isinstance(state.get("coverage"), dict)
            else {}
        )

        existing_tests = (
            state.get("tests")
            if isinstance(state.get("tests"), list)
            else []
        )

        failure_analysis = (
            state.get("failure_analysis")
            if isinstance(state.get("failure_analysis"), dict)
            else {}
        )

        # --------------------------------------------------------------
        # Static scenarios
        # --------------------------------------------------------------

        static_scenarios = self._static_scenarios(
            rtl_code=rtl_code,
            specification=specification,
            rtl_analysis=rtl_analysis,
            verification_plan=verification_plan,
        )

        # --------------------------------------------------------------
        # AI scenarios
        # --------------------------------------------------------------

        ai_result = None

        if self.llm and rtl_code:

            messages = self._build_messages(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
                verification_plan=verification_plan,
                coverage=coverage,
                existing_tests=existing_tests,
                failure_analysis=failure_analysis,
            )

            ai_result = self._call_llm(messages)

        # --------------------------------------------------------------
        # Merge
        # --------------------------------------------------------------

        scenarios = self._merge_scenarios(
            static_scenarios,
            ai_result,
        )

        elapsed = (
            datetime.utcnow() - start_time
        ).total_seconds()

        status = "COMPLETED"

        if not scenarios:
            status = "COMPLETED_WITH_WARNING"

        message = (
            f"Generated {len(scenarios)} adversarial verification "
            f"scenarios in {elapsed:.2f}s."
        )

        if ai_result is None and self.llm:
            message += (
                " AI generation unavailable; deterministic red-team "
                "scenarios were used."
            )

        elif not self.llm:
            message += (
                " Groq is not configured; deterministic scenarios "
                "were used."
            )

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": status,
            "timestamp": self._timestamp(),
            "message": message,
            "duration_seconds": round(elapsed, 3),
            "scenario_count": len(scenarios),
        }

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "timestamp": self._timestamp(),
            "status": status,
            "input_summary": {
                "rtl_length": len(rtl_code),
                "specification_length": len(specification),
                "existing_test_count": len(existing_tests),
            },
            "output_summary": {
                "scenario_count": len(scenarios),
                "high_severity": sum(
                    1
                    for s in scenarios
                    if s["severity"] in {"HIGH", "CRITICAL"}
                ),
            },
            "duration_seconds": round(elapsed, 3),
        }

        return {
            "red_team_scenarios": scenarios,
            "agent_log": (
                list(state.get("agent_log") or [])
                + [agent_log_entry]
            ),
            "agent_trace": (
                list(state.get("agent_trace") or [])
                + [trace_entry]
            ),
            "messages": (
                list(state.get("messages") or [])
                + [message]
            ),
            "warnings": (
                list(state.get("warnings") or [])
                + (
                    [
                        "Red Team Agent used deterministic fallback "
                        "because LLM generation was unavailable."
                    ]
                    if ai_result is None
                    else []
                )
            ),
            "status": status,
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

def run_red_team_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience wrapper for LangGraph or direct execution.
    """

    agent = RedTeamAgent()

    return agent.run(state)


__all__ = [
    "RedTeamAgent",
    "run_red_team_agent",
]
