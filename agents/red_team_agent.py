"""
PragyanAI SiliconAI
Red-Team Verification Agent

Generates adversarial verification scenarios designed to expose
corner-case RTL bugs.

The agent has:
- deterministic scenario generation
- optional Groq/LLM enhancement
- no dependency on SymbiYosys
- compact prompts to avoid excessive API-token usage
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

try:
    from config.prompts import (
        compact_json,
        compact_red_team,
        compact_rtl,
        compact_rtl_analysis,
        load_prompt,
        limit_text,
    )
except Exception:

    def limit_text(
        text: Any,
        max_chars: int = 6000,
    ) -> str:
        value = str(text or "")
        return value[:max_chars]

    def compact_rtl(
        rtl: Any,
        max_chars: int = 6000,
    ) -> str:
        return limit_text(rtl, max_chars)

    def compact_rtl_analysis(
        analysis: Any,
        max_chars: int = 4000,
    ) -> str:
        return limit_text(analysis, max_chars)

    def compact_json(
        value: Any,
        max_chars: int = 4000,
    ) -> str:
        try:
            text = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except Exception:
            text = str(value)

        return limit_text(text, max_chars)

    def compact_red_team(
        value: Any,
        max_chars: int = 5000,
    ) -> str:
        return limit_text(value, max_chars)

    def load_prompt(
        name: str,
        default: str = "",
    ) -> str:
        return default


# =====================================================================
# OPTIONAL GROQ
# =====================================================================

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


# =====================================================================
# CONSTANTS
# =====================================================================

DEFAULT_MODEL = "openai/gpt-oss-120b"

SCENARIO_CATEGORIES = [
    "RESET",
    "BOUNDARY",
    "OVERFLOW",
    "UNDERFLOW",
    "FSM",
    "PROTOCOL",
    "BACK_TO_BACK",
    "ILLEGAL_INPUT",
    "X_Z_STATE",
    "FIFO",
    "UART",
    "HANDSHAKE",
    "TIMING",
    "CORNER_CASE",
]


# =====================================================================
# HELPERS
# =====================================================================

def _safe_state(
    state: Any,
) -> Dict[str, Any]:
    """Convert state into a dictionary."""

    if state is None:
        return {}

    if isinstance(state, dict):
        return dict(state)

    try:
        return dict(state)
    except Exception:
        return {}


def _clean_text(
    value: Any,
) -> str:
    """Normalize arbitrary value to text."""

    if value is None:
        return ""

    return str(value).strip()


def _extract_json(
    text: str,
) -> Any:
    """
    Extract JSON from an LLM response.

    Supports:
    - plain JSON
    - JSON fenced in ```json
    - JSON embedded in surrounding text
    """

    if not text:
        return None

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Markdown code block
    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        candidate = match.group(1).strip()

        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Array
    start = text.find("[")
    end = text.rfind("]")

    if start >= 0 and end > start:

        candidate = text[start : end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Object
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[start : end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


def _normalize_scenarios(
    scenarios: Any,
) -> List[Dict[str, Any]]:
    """
    Normalize generated scenarios into a stable schema.
    """

    if scenarios is None:
        return []

    if isinstance(scenarios, dict):

        if isinstance(
            scenarios.get("scenarios"),
            list,
        ):
            scenarios = scenarios["scenarios"]
        else:
            scenarios = [scenarios]

    if not isinstance(
        scenarios,
        list,
    ):
        return []

    output: List[Dict[str, Any]] = []

    for index, item in enumerate(
        scenarios,
        start=1,
    ):

        if isinstance(
            item,
            str,
        ):

            text = item.strip()

            if not text:
                continue

            output.append(
                {
                    "id": f"RT{index:03d}",
                    "category": "CORNER_CASE",
                    "title": text[:120],
                    "scenario": text,
                    "stimulus": text,
                    "expected": "",
                    "risk": "MEDIUM",
                    "source": "LLM",
                }
            )

            continue

        if not isinstance(
            item,
            dict,
        ):
            continue

        scenario_id = (
            item.get("id")
            or item.get("scenario_id")
            or f"RT{index:03d}"
        )

        category = (
            item.get("category")
            or "CORNER_CASE"
        )

        category = str(
            category
        ).upper().replace(
            " ",
            "_",
        )

        if category not in SCENARIO_CATEGORIES:
            category = "CORNER_CASE"

        title = (
            item.get("title")
            or item.get("name")
            or f"Red-team scenario {index}"
        )

        scenario = (
            item.get("scenario")
            or item.get("description")
            or item.get("stimulus")
            or title
        )

        stimulus = (
            item.get("stimulus")
            or scenario
        )

        expected = (
            item.get("expected")
            or item.get("expected_behavior")
            or ""
        )

        risk = (
            item.get("risk")
            or item.get("severity")
            or "MEDIUM"
        )

        normalized = {
            "id": str(scenario_id),
            "category": category,
            "title": str(title),
            "scenario": str(scenario),
            "stimulus": str(stimulus),
            "expected": str(expected),
            "risk": str(risk).upper(),
            "source": item.get(
                "source",
                "LLM",
            ),
        }

        # Preserve useful extra fields.
        for key in (
            "signals",
            "inputs",
            "steps",
            "rationale",
            "bug_class",
            "requirement",
        ):

            if key in item:
                normalized[key] = item[key]

        output.append(
            normalized
        )

    # Reassign deterministic IDs if missing/duplicated.
    seen = set()

    for index, item in enumerate(
        output,
        start=1,
    ):

        current_id = str(
            item.get(
                "id",
                "",
            )
        )

        if (
            not current_id
            or current_id in seen
        ):

            current_id = f"RT{index:03d}"

        seen.add(current_id)
        item["id"] = current_id

    return output


# =====================================================================
# DETERMINISTIC RED TEAM GENERATOR
# =====================================================================

def _contains(
    text: str,
    *terms: str,
) -> bool:
    """Case-insensitive keyword detection."""

    value = text.lower()

    return any(
        term.lower() in value
        for term in terms
    )


def generate_deterministic_scenarios(
    rtl_code: str,
    specification: str = "",
    rtl_analysis: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Generate deterministic adversarial scenarios.

    This guarantees useful output even when:
    - Groq is unavailable
    - API key is absent
    - LLM call fails
    """

    rtl = _clean_text(rtl_code)
    spec = _clean_text(specification)

    analysis_text = ""

    if rtl_analysis:
        analysis_text = compact_rtl_analysis(
            rtl_analysis,
            3000,
        )

    combined = (
        rtl
        + "\n"
        + spec
        + "\n"
        + analysis_text
    )

    scenarios: List[Dict[str, Any]] = []

    def add(
        category: str,
        title: str,
        scenario: str,
        stimulus: str,
        expected: str,
        risk: str = "HIGH",
    ) -> None:

        scenarios.append(
            {
                "id": f"RT{len(scenarios) + 1:03d}",
                "category": category,
                "title": title,
                "scenario": scenario,
                "stimulus": stimulus,
                "expected": expected,
                "risk": risk,
                "source": "DETERMINISTIC",
            }
        )

    # -------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------

    if _contains(
        combined,
        "reset",
        "rst",
        "reset_n",
    ):

        add(
            "RESET",
            "Reset during active operation",
            (
                "Assert reset while the design is processing "
                "an active transaction."
            ),
            (
                "Start a transaction, assert reset before completion, "
                "then release reset."
            ),
            (
                "All state-dependent outputs should return to the "
                "specified reset state without stale transaction data."
            ),
        )

        add(
            "RESET",
            "Reset release boundary",
            (
                "Release reset immediately before or after a clock "
                "edge and verify deterministic behavior."
            ),
            (
                "Toggle reset around consecutive clock edges."
            ),
            (
                "The first post-reset behavior must comply with the "
                "specified synchronous/asynchronous reset semantics."
            ),
            "MEDIUM",
        )

    # -------------------------------------------------------------
    # Boundary values
    # -------------------------------------------------------------

    add(
        "BOUNDARY",
        "Minimum input value",
        "Drive the minimum legal input values.",
        "Apply all-zero or minimum-width values.",
        "Outputs and state must match the specification.",
        "MEDIUM",
    )

    add(
        "BOUNDARY",
        "Maximum input value",
        "Drive the maximum representable legal values.",
        "Apply all-one values for relevant input widths.",
        "No unintended truncation or incorrect behavior.",
        "HIGH",
    )

    # -------------------------------------------------------------
    # Overflow / underflow
    # -------------------------------------------------------------

    if _contains(
        combined,
        "+",
        "add",
        "increment",
        "counter",
        "overflow",
    ):

        add(
            "OVERFLOW",
            "Arithmetic overflow boundary",
            (
                "Exercise the largest representable value followed "
                "by another increment."
            ),
            (
                "Drive maximum value and perform increment/add operation."
            ),
            (
                "Overflow behavior must exactly match the specification."
            ),
        )

    if _contains(
        combined,
        "-",
        "sub",
        "subtract",
        "decrement",
        "underflow",
    ):

        add(
            "UNDERFLOW",
            "Arithmetic underflow boundary",
            (
                "Exercise the smallest representable value followed "
                "by decrement/subtraction."
            ),
            (
                "Drive minimum value and perform decrement/subtraction."
            ),
            (
                "Underflow behavior must exactly match the specification."
            ),
        )

    # -------------------------------------------------------------
    # Back-to-back operations
    # -------------------------------------------------------------

    add(
        "BACK_TO_BACK",
        "Back-to-back transactions",
        (
            "Perform transactions on consecutive cycles without "
            "idle gaps."
        ),
        (
            "Issue valid transactions on adjacent clock cycles."
        ),
        (
            "Every transaction should be accepted and produce the "
            "correct result."
        ),
    )

    # -------------------------------------------------------------
    # Idle behavior
    # -------------------------------------------------------------

    add(
        "CORNER_CASE",
        "Idle stability",
        (
            "Hold inputs idle for multiple cycles and verify that "
            "outputs/state do not change unexpectedly."
        ),
        (
            "Drive stable idle inputs for 5-10 clock cycles."
        ),
        (
            "State and outputs remain stable unless the specification "
            "explicitly permits changes."
        ),
        "MEDIUM",
    )

    # -------------------------------------------------------------
    # FSM
    # -------------------------------------------------------------

    if _contains(
        combined,
        "state",
        "fsm",
        "case",
        "always_ff",
        "always @(posedge",
    ):

        add(
            "FSM",
            "Unexpected FSM transition",
            (
                "Exercise every legal transition and attempt boundary "
                "conditions around state changes."
            ),
            (
                "Drive inputs immediately before and after expected "
                "state transitions."
            ),
            (
                "FSM remains within legal states and transitions."
            ),
        )

        add(
            "FSM",
            "Illegal state recovery",
            (
                "Evaluate behavior if the FSM enters an unsupported "
                "or default state."
            ),
            (
                "Use reset/recovery conditions or simulation force "
                "where practical."
            ),
            (
                "Design reaches a safe deterministic state."
            ),
            "MEDIUM",
        )

    # -------------------------------------------------------------
    # Protocol
    # -------------------------------------------------------------

    if _contains(
        combined,
        "valid",
        "ready",
        "handshake",
        "req",
        "ack",
    ):

        add(
            "HANDSHAKE",
            "Valid held while not ready",
            (
                "Keep a request or valid indication asserted while "
                "the receiver is unavailable."
            ),
            (
                "Assert valid/request and delay ready/ack."
            ),
            (
                "The transaction must not be lost or duplicated."
            ),
        )

        add(
            "HANDSHAKE",
            "Back-to-back handshake",
            (
                "Complete multiple handshakes on consecutive cycles."
            ),
            (
                "Assert valid for consecutive transfers."
            ),
            (
                "Each accepted transfer produces exactly one result."
            ),
        )

    # -------------------------------------------------------------
    # FIFO
    # -------------------------------------------------------------

    if _contains(
        combined,
        "fifo",
        "full",
        "empty",
        "wr_ptr",
        "rd_ptr",
    ):

        add(
            "FIFO",
            "Write when full",
            (
                "Attempt a write when FIFO occupancy reaches capacity."
            ),
            (
                "Fill FIFO completely, then assert write enable."
            ),
            (
                "No illegal overwrite occurs and full behavior "
                "matches the specification."
            ),
        )

        add(
            "FIFO",
            "Read when empty",
            (
                "Attempt a read while FIFO contains no valid data."
            ),
            (
                "Reset/drain FIFO, then assert read enable."
            ),
            (
                "No invalid data is consumed and empty behavior "
                "matches the specification."
            ),
        )

        add(
            "FIFO",
            "Full-to-read boundary",
            (
                "Read immediately after FIFO reaches full capacity."
            ),
            (
                "Fill FIFO, then read one item."
            ),
            (
                "Full flag and occupancy update correctly."
            ),
        )

    # -------------------------------------------------------------
    # UART
    # -------------------------------------------------------------

    if _contains(
        combined,
        "uart",
        "baud",
        "tx",
        "serial",
        "start bit",
        "stop bit",
    ):

        add(
            "UART",
            "UART framing boundary",
            (
                "Verify exact start, data and stop bit sequencing."
            ),
            (
                "Transmit alternating and all-zero/all-one data patterns."
            ),
            (
                "Frame contains exactly one start bit, eight data bits "
                "and the specified stop bit."
            ),
        )

        add(
            "UART",
            "UART back-to-back transmission",
            (
                "Start a second transmission immediately after "
                "completion of the first."
            ),
            (
                "Transmit two different bytes with minimal idle time."
            ),
            (
                "Both frames are complete and correctly separated."
            ),
        )

        add(
            "TIMING",
            "UART bit timing boundary",
            (
                "Check output transitions exactly at the configured "
                "bit-period boundaries."
            ),
            (
                "Sample TX at every clock within a bit period."
            ),
            (
                "TX remains stable within each bit period and changes "
                "only at valid boundaries."
            ),
        )

    # -------------------------------------------------------------
    # X/Z
    # -------------------------------------------------------------

    add(
        "X_Z_STATE",
        "Unknown input robustness",
        (
            "Where simulator semantics permit, evaluate behavior "
            "with unknown or high-impedance control signals."
        ),
        (
            "Drive X/Z on non-critical inputs during simulation."
        ),
        (
            "No unintended optimistic behavior or unsafe state "
            "transition occurs."
        ),
        "MEDIUM",
    )

    # -------------------------------------------------------------
    # Width / signedness
    # -------------------------------------------------------------

    if _contains(
        combined,
        "[",
        "width",
        "parameter",
        "logic",
        "reg",
        "wire",
    ):

        add(
            "BOUNDARY",
            "Width truncation boundary",
            (
                "Exercise values where arithmetic results require "
                "more bits than the destination."
            ),
            (
                "Apply maximum-width operands and inspect every "
                "destination bit."
            ),
            (
                "Any truncation must be intentional and specified."
            ),
        )

    # -------------------------------------------------------------
    # Illegal inputs
    # -------------------------------------------------------------

    add(
        "ILLEGAL_INPUT",
        "Illegal control combination",
        (
            "Drive combinations of control signals that are normally "
            "discouraged or unsupported."
        ),
        (
            "Assert multiple mutually exclusive controls together."
        ),
        (
            "Design follows specified priority/default behavior and "
            "does not enter an unsafe state."
        ),
        "MEDIUM",
    )

    # -------------------------------------------------------------
    # Ensure minimum diversity
    # -------------------------------------------------------------

    required_categories = {
        "RESET",
        "BOUNDARY",
        "BACK_TO_BACK",
        "CORNER_CASE",
    }

    existing = {
        str(
            item.get(
                "category",
                "",
            )
        ).upper()
        for item in scenarios
    }

    # These are normally already present, but guarantee them.
    if "RESET" not in existing:

        add(
            "RESET",
            "Basic reset robustness",
            "Apply and release reset while observing all outputs.",
            "Assert reset, hold for several cycles, then release.",
            "Outputs return to defined reset state.",
            "HIGH",
        )

    # -------------------------------------------------------------
    # Deduplicate
    # -------------------------------------------------------------

    unique: List[Dict[str, Any]] = []
    fingerprints = set()

    for item in scenarios:

        fingerprint = (
            str(
                item.get(
                    "category",
                    "",
                )
            ).lower(),
            str(
                item.get(
                    "title",
                    "",
                )
            ).lower(),
        )

        if fingerprint in fingerprints:
            continue

        fingerprints.add(
            fingerprint
        )

        unique.append(item)

    # Re-number
    for index, item in enumerate(
        unique,
        start=1,
    ):
        item["id"] = f"RT{index:03d}"

    return unique


# =====================================================================
# AGENT
# =====================================================================

class RedTeamAgent:
    """
    Adversarial verification scenario generator.
    """

    name = "red_team_agent"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.1,
        max_tokens: int = 1800,
    ) -> None:

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.llm = None

        # -------------------------------------------------------------
        # Optional Groq initialization
        # -------------------------------------------------------------

        if ChatGroq is not None:

            try:

                import os

                api_key = os.getenv(
                    "GROQ_API_KEY"
                )

                if api_key:

                    self.llm = ChatGroq(
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )

            except Exception:

                self.llm = None

    # -----------------------------------------------------------------
    # LLM GENERATION
    # -----------------------------------------------------------------

    def _generate_with_llm(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        baseline: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        if self.llm is None:
            return []

        system_prompt = load_prompt(
            "red_team",
            default=(
                "You are an expert RTL verification engineer. "
                "Generate concise adversarial verification scenarios."
            ),
        )

        prompt = f"""
Generate adversarial RTL verification scenarios.

Return ONLY valid JSON.

Required format:

[
  {{
    "id": "RT001",
    "category": "RESET",
    "title": "Short title",
    "scenario": "What adversarial condition is tested",
    "stimulus": "How the test should stimulate the DUT",
    "expected": "Expected correct behavior",
    "risk": "HIGH"
  }}
]

Rules:
- Generate 5 to 10 high-value scenarios.
- Focus on corner cases and failure modes.
- Avoid duplicating obvious baseline tests.
- Include reset/boundary/protocol/FSM cases when relevant.
- Do not invent ports that are clearly absent.
- Keep each scenario concise.
- Do not include markdown.

Specification:
{limit_text(specification, 3500)}

RTL:
{compact_rtl(rtl_code, 5000)}

RTL Analysis:
{compact_rtl_analysis(rtl_analysis, 2500)}

Existing deterministic scenarios:
{compact_json(baseline, 2500)}
"""

        try:

            response = self.llm.invoke(
                [
                    (
                        "system",
                        system_prompt,
                    ),
                    (
                        "human",
                        prompt,
                    ),
                ]
            )

            text = getattr(
                response,
                "content",
                str(response),
            )

            parsed = _extract_json(
                str(text)
            )

            return _normalize_scenarios(
                parsed
            )

        except Exception:

            return []

    # -----------------------------------------------------------------
    # MAIN RUN
    # -----------------------------------------------------------------

    def run(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        data = _safe_state(
            state
        )

        rtl_code = _clean_text(
            data.get(
                "rtl_code",
                "",
            )
        )

        specification = _clean_text(
            data.get(
                "specification",
                data.get(
                    "prompt",
                    "",
                ),
            )
        )

        rtl_analysis = data.get(
            "rtl_analysis",
            {},
        )

        if not isinstance(
            rtl_analysis,
            dict,
        ):
            rtl_analysis = {}

        # -------------------------------------------------------------
        # Deterministic baseline
        # -------------------------------------------------------------

        deterministic = (
            generate_deterministic_scenarios(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
            )
        )

        # -------------------------------------------------------------
        # Optional LLM enhancement
        # -------------------------------------------------------------

        llm_scenarios = self._generate_with_llm(
            rtl_code=rtl_code,
            specification=specification,
            rtl_analysis=rtl_analysis,
            baseline=deterministic,
        )

        # -------------------------------------------------------------
        # Merge
        # -------------------------------------------------------------

        merged: List[Dict[str, Any]] = []

        fingerprints = set()

        for item in (
            deterministic
            + llm_scenarios
        ):

            category = str(
                item.get(
                    "category",
                    "",
                )
            ).upper()

            title = str(
                item.get(
                    "title",
                    "",
                )
            ).strip().lower()

            fingerprint = (
                category,
                title,
            )

            if fingerprint in fingerprints:
                continue

            fingerprints.add(
                fingerprint
            )

            merged.append(
                dict(item)
            )

        # Limit excessive output.
        merged = merged[:40]

        # Reassign IDs.
        for index, item in enumerate(
            merged,
            start=1,
        ):

            item["id"] = f"RT{index:03d}"

        # -------------------------------------------------------------
        # Trace
        # -------------------------------------------------------------

        trace = list(
            data.get(
                "agent_trace",
                [],
            )
            or []
        )

        trace.append(
            {
                "agent": self.name,
                "status": "completed",
                "scenario_count": len(
                    merged
                ),
                "deterministic_count": len(
                    deterministic
                ),
                "llm_count": len(
                    llm_scenarios
                ),
            }
        )

        # -------------------------------------------------------------
        # Agent log
        # -------------------------------------------------------------

        agent_log = list(
            data.get(
                "agent_log",
                [],
            )
            or []
        )

        agent_log.append(
            {
                "agent": self.name,
                "event": "red_team_generation",
                "scenario_count": len(
                    merged
                ),
                "llm_used": bool(
                    llm_scenarios
                ),
            }
        )

        # -------------------------------------------------------------
        # Return state update
        # -------------------------------------------------------------

        return {
            "red_team_scenarios": merged,
            "agent_trace": trace,
            "agent_log": agent_log,
            "status": "RED_TEAM_COMPLETE",
            "next_action": "mutation",
        }


# =====================================================================
# COMPATIBILITY HELPERS
# =====================================================================

def run_red_team(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Functional helper for callers that don't instantiate the agent.
    """

    return RedTeamAgent().run(
        state
    )


__all__ = [
    "RedTeamAgent",
    "run_red_team",
    "generate_deterministic_scenarios",
    "SCENARIO_CATEGORIES",
]

