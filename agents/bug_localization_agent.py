"""
PragyanAI SiliconAI
Bug Localization Agent

Purpose
-------
Identify the most suspicious RTL signals / lines / constructs
associated with a verification failure.

The agent combines:

1. Simulation failure evidence
2. Failure Analyzer diagnosis
3. RTL structural information
4. Test information
5. Formal counterexamples
6. Coverage gaps
7. Optional Groq reasoning

It does NOT modify RTL.

Its output is consumed by:
    RTL Repair Agent
    Verification Judge
    Report Generator

Typical flow:

    Failure
       |
       v
    Failure Analyzer
       |
       v
    Bug Localization
       |
       +----------------------+
       |                      |
       v                      v
 suspicious RTL          confidence
 locations
       |
       v
    RTL Repair
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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
    compact_simulation_log,
    limit_text,
    load_prompt,
)


class BugLocalizationAgent:
    """
    RTL bug localization agent.

    The output is a ranked list of suspicious RTL locations.

    Example:

        [
            {
                "rank": 1,
                "line": 42,
                "signal": "count",
                "construct": "counter increment",
                "reason": "Expected count update was not observed",
                "confidence": 0.91
            }
        ]
    """

    AGENT_NAME = "Bug Localization Agent"

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
                min(1.0, number),
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
    # RTL parsing
    # ------------------------------------------------------------------

    def _index_rtl(
        self,
        rtl_code: str,
    ) -> Dict[str, Any]:

        """
        Build a lightweight RTL source index.

        This is intentionally regex-based so that it works without
        requiring a complete Verilog parser.
        """

        lines = rtl_code.splitlines()

        indexed_lines: List[Dict[str, Any]] = []

        signals: Dict[str, List[int]] = {}

        for number, line in enumerate(
            lines,
            start=1,
        ):

            stripped = line.strip()

            if not stripped:
                continue

            # ----------------------------------------------------------
            # Extract common signal names.
            # ----------------------------------------------------------

            found_signals = set()

            # signal declarations
            for match in re.finditer(
                r"\b(?:wire|reg|logic|input|output|integer)\b"
                r"(?:\s+(?:signed)\b)?"
                r"(?:\s*\[[^\]]+\])?"
                r"\s+([A-Za-z_]\w*)",
                line,
            ):

                found_signals.add(
                    match.group(1)
                )

            # Assignment LHS.
            for match in re.finditer(
                r"\b([A-Za-z_]\w*)\s*(?:<=|=)",
                line,
            ):

                found_signals.add(
                    match.group(1)
                )

            # Signal references in common RTL constructs.
            for match in re.finditer(
                r"\b(?:count|state|data|addr|address|"
                r"valid|ready|req|ack|enable|"
                r"reset|rst|full|empty|busy|done|"
                r"error|result|out|output|next_state)"
                r"(?:_[A-Za-z0-9]+)?\b",
                line,
                flags=re.IGNORECASE,
            ):

                found_signals.add(
                    match.group(0)
                )

            for signal in found_signals:

                signals.setdefault(
                    signal,
                    [],
                ).append(
                    number
                )

            indexed_lines.append(
                {
                    "line": number,
                    "text": stripped[:500],
                    "signals": sorted(
                        found_signals
                    ),
                }
            )

        return {
            "lines": indexed_lines,
            "signals": signals,
        }

    # ------------------------------------------------------------------
    # Evidence extraction
    # ------------------------------------------------------------------

    def _extract_signal_mentions(
        self,
        text: str,
        rtl_index: Dict[str, Any],
    ) -> List[str]:

        if not text:
            return []

        signals = rtl_index.get(
            "signals",
            {},
        )

        mentions: List[str] = []

        lower_text = str(
            text
        ).lower()

        for signal in signals:

            if signal.lower() in lower_text:

                mentions.append(
                    signal
                )

        # Also extract expected/actual identifiers.
        for match in re.findall(
            r"\b[A-Za-z_][A-Za-z0-9_]*\b",
            text,
        ):

            if match in signals:
                if match not in mentions:
                    mentions.append(
                        match
                    )

        return mentions[:30]

    # ------------------------------------------------------------------
    # Deterministic localization
    # ------------------------------------------------------------------

    def _deterministic_localization(
        self,
        rtl_code: str,
        simulation_output: str,
        simulation_error: str,
        failure_analysis: Dict[str, Any],
        formal_result: Dict[str, Any],
        coverage_gaps: List[Any],
    ) -> List[Dict[str, Any]]:

        rtl_index = self._index_rtl(
            rtl_code
        )

        lines = rtl_index[
            "lines"
        ]

        evidence_text = "\n".join(
            [
                str(simulation_output),
                str(simulation_error),
                json.dumps(
                    failure_analysis,
                    default=str,
                ),
                json.dumps(
                    formal_result,
                    default=str,
                ),
            ]
        )

        mentions = self._extract_signal_mentions(
            evidence_text,
            rtl_index,
        )

        candidates: List[
            Dict[str, Any]
        ] = []

        category = str(
            failure_analysis.get(
                "category",
                "",
            )
        ).upper()

        # --------------------------------------------------------------
        # Score source lines.
        # --------------------------------------------------------------

        for entry in lines:

            line_number = entry[
                "line"
            ]

            line_text = entry[
                "text"
            ]

            score = 0.0
            reasons: List[str] = []

            lower_line = line_text.lower()

            # ----------------------------------------------------------
            # Mentioned signals.
            # ----------------------------------------------------------

            line_signals = entry.get(
                "signals",
                [],
            )

            for signal in line_signals:

                if signal in mentions:

                    score += 0.35

                    reasons.append(
                        f"Failure evidence references signal '{signal}'."
                    )

            # ----------------------------------------------------------
            # Category-specific heuristics.
            # ----------------------------------------------------------

            if category in {
                "RESET_ERROR",
            }:

                if any(
                    token in lower_line
                    for token in [
                        "reset",
                        "rst",
                        "initial",
                    ]
                ):

                    score += 0.35

                    reasons.append(
                        "Line contains reset/initialization logic."
                    )

            if category in {
                "FSM_ERROR",
            }:

                if any(
                    token in lower_line
                    for token in [
                        "state",
                        "case",
                        "default",
                    ]
                ):

                    score += 0.35

                    reasons.append(
                        "Line participates in state-machine logic."
                    )

            if category in {
                "WIDTH_ERROR",
            }:

                if any(
                    token in lower_line
                    for token in [
                        "[",
                        "+",
                        "-",
                        "<<",
                        ">>",
                        "signed",
                        "unsigned",
                    ]
                ):

                    score += 0.25

                    reasons.append(
                        "Line contains width/arithmetic-related logic."
                    )

            if category in {
                "PROTOCOL_ERROR",
            }:

                if any(
                    token in lower_line
                    for token in [
                        "valid",
                        "ready",
                        "req",
                        "ack",
                        "enable",
                    ]
                ):

                    score += 0.30

                    reasons.append(
                        "Line participates in interface protocol logic."
                    )

            if category in {
                "RTL_BUG",
                "TIMING_ISSUE",
            }:

                if any(
                    token in lower_line
                    for token in [
                        "<=",
                        "posedge",
                        "negedge",
                        "always",
                        "assign",
                    ]
                ):

                    score += 0.15

                    reasons.append(
                        "Line contains executable RTL behavior."
                    )

            # ----------------------------------------------------------
            # Assertion / mismatch evidence.
            # ----------------------------------------------------------

            if any(
                token in lower_line
                for token in [
                    "assert",
                    "if",
                    "case",
                    "?",
                ]
            ):

                score += 0.08

            # ----------------------------------------------------------
            # Generate candidate.
            # ----------------------------------------------------------

            if score > 0:

                candidates.append(
                    {
                        "line": line_number,
                        "signal": (
                            line_signals[0]
                            if line_signals
                            else ""
                        ),
                        "construct": self._classify_construct(
                            line_text
                        ),
                        "score": min(
                            1.0,
                            score,
                        ),
                        "reason": (
                            " ".join(
                                reasons
                            )
                            if reasons
                            else "Potentially relevant RTL statement."
                        ),
                        "source": "deterministic",
                    }
                )

        # --------------------------------------------------------------
        # Add coverage-gap-related lines.
        # --------------------------------------------------------------

        if isinstance(
            coverage_gaps,
            list,
        ):

            gap_text = " ".join(
                str(item)
                for item in coverage_gaps
            ).lower()

            for entry in lines:

                lower_line = entry[
                    "text"
                ].lower()

                keywords = [
                    word
                    for word in re.findall(
                        r"\b[A-Za-z_]\w*\b",
                        gap_text,
                    )
                    if len(word) > 3
                ]

                matches = sum(
                    1
                    for word in keywords
                    if word in lower_line
                )

                if matches:

                    candidates.append(
                        {
                            "line": entry[
                                "line"
                            ],
                            "signal": (
                                entry[
                                    "signals"
                                ][0]
                                if entry[
                                    "signals"
                                ]
                                else ""
                            ),
                            "construct": self._classify_construct(
                                entry[
                                    "text"
                                ]
                            ),
                            "score": min(
                                1.0,
                                0.20
                                + matches * 0.08,
                            ),
                            "reason": (
                                "Line is related to a detected "
                                "coverage gap."
                            ),
                            "source": "coverage",
                        }
                    )

        # --------------------------------------------------------------
        # Deduplicate by line.
        # --------------------------------------------------------------

        best_by_line: Dict[
            int,
            Dict[str, Any]
        ] = {}

        for candidate in candidates:

            line = candidate[
                "line"
            ]

            existing = best_by_line.get(
                line
            )

            if (
                existing is None
                or candidate[
                    "score"
                ]
                > existing[
                    "score"
                ]
            ):

                best_by_line[
                    line
                ] = candidate

        ranked = sorted(
            best_by_line.values(),
            key=lambda item: item[
                "score"
            ],
            reverse=True,
        )

        return ranked[:15]

    @staticmethod
    def _classify_construct(
        line: str,
    ) -> str:

        lower = line.lower()

        if "always_ff" in lower:
            return "sequential_logic"

        if "always_comb" in lower:
            return "combinational_logic"

        if "always" in lower:
            return "procedural_logic"

        if "case" in lower:
            return "fsm_or_case"

        if "assign" in lower:
            return "continuous_assignment"

        if "<=" in lower:
            return "nonblocking_assignment"

        if "=" in lower:
            return "blocking_assignment"

        if "if" in lower:
            return "conditional_logic"

        return "rtl_statement"

    # ------------------------------------------------------------------
    # AI localization
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        rtl_code: str,
        specification: str,
        rtl_analysis: Dict[str, Any],
        simulation_output: str,
        simulation_error: str,
        failure_analysis: Dict[str, Any],
        formal_result: Dict[str, Any],
        deterministic_candidates: List[
            Dict[str, Any]
        ],
    ) -> List[Any]:

        system_prompt = load_prompt(
            "bug_localization"
        )

        if not system_prompt:

            system_prompt = """
You are an expert semiconductor RTL debugging engineer.

Locate the most likely RTL source locations responsible for the
verification failure.

Use only evidence from:
- RTL
- simulation logs
- failure diagnosis
- formal counterexamples
- coverage information

Return ONLY compact JSON:

{
  "locations": [
    {
      "line": 42,
      "signal": "count",
      "construct": "counter update",
      "reason": "...",
      "confidence": 0.91
    }
  ]
}

Maximum 8 locations.

Do not modify RTL.
Do not claim certainty without evidence.
"""

        payload = {
            "specification": limit_text(
                specification,
                1800,
            ),
            "rtl": compact_rtl(
                rtl_code,
                6000,
            ),
            "rtl_analysis": compact_rtl_analysis(
                rtl_analysis
            ),
            "simulation_output": compact_simulation_log(
                simulation_output,
                3000,
            ),
            "simulation_error": limit_text(
                simulation_error,
                1800,
            ),
            "failure_analysis": compact_json(
                failure_analysis,
                2500,
            ),
            "formal_result": compact_json(
                formal_result,
                2500,
            ),
            "deterministic_candidates": deterministic_candidates[
                :10
            ],
        }

        return [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=(
                    "Locate likely RTL bug locations.\n\n"
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
    # Merge
    # ------------------------------------------------------------------

    def _merge_locations(
        self,
        deterministic: List[
            Dict[str, Any]
        ],
        ai_result: Optional[
            Dict[str, Any]
        ],
        rtl_code: str,
    ) -> List[
        Dict[str, Any]
    ]:

        locations = list(
            deterministic
        )

        ai_locations: List[
            Dict[str, Any]
        ] = []

        if isinstance(
            ai_result,
            dict,
        ):

            raw = (
                ai_result.get(
                    "locations"
                )
                or ai_result.get(
                    "bug_locations"
                )
                or []
            )

            if isinstance(
                raw,
                list,
            ):

                ai_locations = [
                    item
                    for item in raw
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        # --------------------------------------------------------------
        # Normalize AI locations.
        # --------------------------------------------------------------

        for item in ai_locations:

            try:

                line = int(
                    item.get(
                        "line",
                        0,
                    )
                )

            except Exception:

                line = 0

            if line <= 0:
                continue

            confidence = self._safe_float(
                item.get(
                    "confidence",
                    item.get(
                        "score",
                        0.5,
                    ),
                ),
                0.5,
            )

            location = {
                "line": line,
                "signal": str(
                    item.get(
                        "signal",
                        "",
                    )
                )[:150],
                "construct": str(
                    item.get(
                        "construct",
                        "rtl_statement",
                    )
                )[:150],
                "score": confidence,
                "reason": str(
                    item.get(
                        "reason",
                        "AI identified this as a suspicious location.",
                    )
                )[:700],
                "source": "AI",
            }

            locations.append(
                location
            )

        # --------------------------------------------------------------
        # Merge same lines.
        # --------------------------------------------------------------

        merged: Dict[
            int,
            Dict[str, Any]
        ] = {}

        for location in locations:

            line = int(
                location.get(
                    "line",
                    0,
                )
            )

            if line <= 0:
                continue

            existing = merged.get(
                line
            )

            if existing is None:

                merged[line] = dict(
                    location
                )

            else:

                if (
                    float(
                        location.get(
                            "score",
                            0.0,
                        )
                    )
                    >
                    float(
                        existing.get(
                            "score",
                            0.0,
                        )
                    )
                ):

                    existing[
                        "score"
                    ] = location.get(
                        "score"
                    )

                existing[
                    "reason"
                ] = (
                    str(
                        existing.get(
                            "reason",
                            "",
                        )
                    )
                    + " "
                    + str(
                        location.get(
                            "reason",
                            "",
                        )
                    )
                )[:1000]

                existing[
                    "source"
                ] = "deterministic+AI"

        # --------------------------------------------------------------
        # Rank.
        # --------------------------------------------------------------

        ranked = sorted(
            merged.values(),
            key=lambda item: float(
                item.get(
                    "score",
                    0.0,
                )
            ),
            reverse=True,
        )

        final = []

        for rank, item in enumerate(
            ranked[:15],
            start=1,
        ):

            item[
                "rank"
            ] = rank

            item[
                "confidence"
            ] = round(
                self._safe_float(
                    item.get(
                        "score",
                        0.0,
                    )
                ),
                3,
            )

            item.pop(
                "score",
                None,
            )

            final.append(
                item
            )

        return final

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
                state.get(
                    "rtl_analysis"
                ),
                dict,
            )
            else {}
        )

        simulation_output = str(
            state.get(
                "simulation_output"
            )
            or state.get(
                "run_output"
            )
            or ""
        )

        simulation_error = str(
            state.get(
                "simulation_error"
            )
            or ""
        )

        failure_analysis = (
            state.get(
                "failure_analysis"
            )
            if isinstance(
                state.get(
                    "failure_analysis"
                ),
                dict,
            )
            else {}
        )

        formal_result = (
            state.get(
                "formal_result"
            )
            if isinstance(
                state.get(
                    "formal_result"
                ),
                dict,
            )
            else {}
        )

        coverage = (
            state.get(
                "coverage"
            )
            if isinstance(
                state.get(
                    "coverage"
                ),
                dict,
            )
            else {}
        )

        coverage_gaps = (
            coverage.get(
                "gaps",
                [],
            )
            if isinstance(
                coverage,
                dict,
            )
            else []
        )

        # --------------------------------------------------------------
        # Deterministic localization
        # --------------------------------------------------------------

        deterministic = (
            self._deterministic_localization(
                rtl_code=rtl_code,
                simulation_output=simulation_output,
                simulation_error=simulation_error,
                failure_analysis=failure_analysis,
                formal_result=formal_result,
                coverage_gaps=coverage_gaps,
            )
        )

        # --------------------------------------------------------------
        # AI localization
        # --------------------------------------------------------------

        ai_result = None

        if self.llm and rtl_code:

            messages = self._build_messages(
                rtl_code=rtl_code,
                specification=specification,
                rtl_analysis=rtl_analysis,
                simulation_output=simulation_output,
                simulation_error=simulation_error,
                failure_analysis=failure_analysis,
                formal_result=formal_result,
                deterministic_candidates=deterministic,
            )

            ai_result = self._call_llm(
                messages
            )

        locations = self._merge_locations(
            deterministic=deterministic,
            ai_result=ai_result,
            rtl_code=rtl_code,
        )

        # --------------------------------------------------------------
        # Confidence summary
        # --------------------------------------------------------------

        if locations:

            top_confidence = float(
                locations[0].get(
                    "confidence",
                    0.0,
                )
            )

        else:

            top_confidence = 0.0

        if top_confidence >= 0.80:

            assessment = (
                "A high-confidence RTL location was identified."
            )

        elif top_confidence >= 0.55:

            assessment = (
                "Potential RTL locations were identified, "
                "but additional evidence is recommended."
            )

        else:

            assessment = (
                "No high-confidence RTL location was established."
            )

        # --------------------------------------------------------------
        # Primary location
        # --------------------------------------------------------------

        primary_location = (
            locations[0]
            if locations
            else {}
        )

        # --------------------------------------------------------------
        # Result
        # --------------------------------------------------------------

        bug_location = {
            "primary": primary_location,
            "locations": locations,
            "assessment": assessment,
            "confidence": round(
                top_confidence,
                3,
            ),
            "timestamp": self._timestamp(),
        }

        elapsed = round(
            time.time() - start,
            3,
        )

        message = (
            f"Bug localization completed: "
            f"{len(locations)} candidate location(s), "
            f"top confidence={top_confidence:.2f}."
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
            "candidate_count": len(
                locations
            ),
            "top_confidence": round(
                top_confidence,
                3,
            ),
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
                "simulation_log_length": len(
                    simulation_output
                ),
                "failure_category": str(
                    failure_analysis.get(
                        "category",
                        "",
                    )
                ),
            },
            "output_summary": {
                "candidate_locations": len(
                    locations
                ),
                "top_confidence": round(
                    top_confidence,
                    3,
                ),
                "ai_used": ai_result is not None,
            },
        }

        # --------------------------------------------------------------
        # Return
        # --------------------------------------------------------------

        return {
            "bug_location": bug_location,

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

def run_bug_localization_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:

    agent = BugLocalizationAgent()

    return agent.run(state)


__all__ = [
    "BugLocalizationAgent",
    "run_bug_localization_agent",
]
