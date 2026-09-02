"""
PragyanAI SiliconAI
RTL Analyzer Agent

Responsibilities:
    1. Understand RTL structure.
    2. Identify inputs, outputs, clocks and resets.
    3. Identify sequential/combinational logic.
    4. Detect state machines and state elements.
    5. Identify interfaces and protocols.
    6. Identify corner cases and verification risks.
    7. Produce compact structured analysis.

The agent does NOT modify RTL.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from langchain_groq import ChatGroq

from config.settings import (
    GROQ_API_KEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    RTL_ANALYZER_MAX_TOKENS,
    MAX_RTL_CHARS_FOR_LLM,
)

from config.prompts import (
    load_prompt,
    limit_text,
    compact_json,
    compact_rtl,
)


class RTLAnalyzerAgent:
    """
    AI agent responsible for understanding RTL and extracting
    verification-relevant structural information.
    """

    name = "RTL Analyzer"

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
            RTL_ANALYZER_MAX_TOKENS
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

    def analyze(
        self,
        rtl_code: str,
        specification: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze RTL.

        Returns a dictionary compatible with graph state:

            {
                "rtl_analysis": {...},
                "status": "...",
                "messages": [...]
            }
        """

        if not rtl_code or not rtl_code.strip():
            return {
                "rtl_analysis": {
                    "module_name": "",
                    "language": "unknown",
                    "summary": "No RTL code supplied.",
                    "potential_risks": [
                        "RTL input is empty."
                    ],
                },
                "status": "FAILED",
                "messages": [
                    "RTL Analyzer: No RTL code supplied."
                ],
            }

        # First perform deterministic extraction.
        structural = self._static_analysis(rtl_code)

        # If LLM is unavailable, static analysis is still useful.
        if self.llm is None:
            structural["summary"] = (
                "Static RTL analysis completed. "
                "Groq API key is not configured, so "
                "AI semantic analysis was skipped."
            )

            return {
                "rtl_analysis": structural,
                "status": "COMPLETED",
                "messages": [
                    "RTL Analyzer completed using static analysis."
                ],
            }

        try:
            prompt = self._build_prompt(
                rtl_code=rtl_code,
                specification=specification,
                structural_analysis=structural,
            )

            response = self.llm.invoke(prompt)

            content = self._extract_content(response)

            ai_analysis = self._parse_json(content)

            if not isinstance(ai_analysis, dict):
                ai_analysis = {}

            result = self._merge_analysis(
                structural,
                ai_analysis,
            )

            return {
                "rtl_analysis": result,
                "status": "COMPLETED",
                "messages": [
                    "RTL Analyzer completed successfully."
                ],
            }

        except Exception as exc:

            # Do not fail the entire verification pipeline
            # merely because AI analysis failed.
            structural["summary"] = (
                "Static RTL analysis completed. "
                f"AI analysis failed: {limit_text(str(exc), 1000)}"
            )

            structural["potential_risks"] = (
                structural.get("potential_risks", [])
                + [
                    "AI semantic analysis unavailable."
                ]
            )

            return {
                "rtl_analysis": structural,
                "status": "COMPLETED",
                "warnings": [
                    (
                        "RTL Analyzer LLM call failed: "
                        f"{limit_text(str(exc), 1000)}"
                    )
                ],
                "messages": [
                    "RTL Analyzer fell back to static analysis."
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

        rtl_code = (
            state.get("rtl_code")
            or state.get("prompt")
            or ""
        )

        specification = (
            state.get("specification")
            or state.get("prompt")
            or ""
        )

        result = self.analyze(
            rtl_code=rtl_code,
            specification=specification,
        )

        return {
            "rtl_analysis": result.get(
                "rtl_analysis",
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
        rtl_code: str,
        specification: str,
        structural_analysis: Dict[str, Any],
    ) -> str:
        """
        Build compact LLM prompt.

        The static analysis is supplied to the LLM so that
        the model spends tokens on semantic reasoning rather
        than rediscovering obvious syntax.
        """

        system_prompt = load_prompt(
            "rtl_analysis"
        )

        if not system_prompt:
            system_prompt = self._default_prompt()

        rtl = compact_rtl(
            rtl_code,
            max_chars=MAX_RTL_CHARS_FOR_LLM,
        )

        spec = limit_text(
            specification,
            max_chars=8000,
            keep="both",
        )

        structural = compact_json(
            structural_analysis,
            max_chars=5000,
        )

        return f"""
{system_prompt}

IMPORTANT OUTPUT RULES:
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not use ```json.
- Do not explain the JSON outside the JSON object.
- Do not invent ports, signals or behavior.
- Clearly distinguish observed facts from inferred risks.

SPECIFICATION:
{spec}

STATIC RTL ANALYSIS:
{structural}

RTL CODE:
{rtl}
"""

    # ========================================================
    # DEFAULT PROMPT
    # ========================================================

    @staticmethod
    def _default_prompt() -> str:
        return """
You are an expert semiconductor RTL verification engineer.

Analyze the supplied Verilog/SystemVerilog design.

Identify:
- module
- inputs
- outputs
- clocks
- resets
- registers
- state
- FSMs
- combinational logic
- sequential logic
- interfaces
- protocols
- memories
- arithmetic
- corner cases
- verification risks
- verification points

Return compact JSON only.
"""

    # ========================================================
    # STATIC ANALYSIS
    # ========================================================

    def _static_analysis(
        self,
        rtl_code: str,
    ) -> Dict[str, Any]:
        """
        Lightweight deterministic RTL parser.

        This is intentionally regex-based so that the platform
        can operate without requiring a full HDL parser.
        """

        code = rtl_code

        module_match = re.search(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)",
            code,
            re.IGNORECASE,
        )

        module_name = (
            module_match.group(1)
            if module_match
            else ""
        )

        language = (
            "SystemVerilog"
            if (
                "logic " in code
                or "always_ff" in code
                or "always_comb" in code
                or "typedef enum" in code
                or "interface " in code
            )
            else "Verilog"
        )

        inputs = self._extract_ports(
            code,
            "input",
        )

        outputs = self._extract_ports(
            code,
            "output",
        )

        clocks = self._find_clock_signals(code)

        resets = self._find_reset_signals(code)

        registers = self._find_registers(code)

        state_elements = self._find_state_elements(
            code
        )

        state_machine = self._detect_fsm(code)

        states = self._find_states(code)

        combinational = self._find_combinational_blocks(
            code
        )

        sequential = self._find_sequential_blocks(
            code
        )

        protocols = self._detect_protocols(
            code
        )

        memories = self._detect_memory(code)

        arithmetic = self._detect_arithmetic(code)

        corner_cases = self._detect_corner_cases(
            code
        )

        risks = self._detect_risks(
            code,
            clocks=clocks,
            resets=resets,
            state_machine=state_machine,
        )

        verification_points = self._build_verification_points(
            inputs=inputs,
            outputs=outputs,
            clocks=clocks,
            resets=resets,
            state_elements=state_elements,
            protocols=protocols,
            corner_cases=corner_cases,
        )

        return {
            "module_name": module_name,
            "language": language,
            "inputs": inputs,
            "outputs": outputs,
            "parameters": self._find_parameters(code),
            "clocks": clocks,
            "resets": resets,
            "registers": registers,
            "wires": self._find_wires(code),
            "state_elements": state_elements,
            "state_machine": state_machine,
            "states": states,
            "combinational_logic": combinational,
            "sequential_logic": sequential,
            "interfaces": [],
            "protocols": protocols,
            "arithmetic_operations": arithmetic,
            "memory_elements": memories,
            "critical_paths": [],
            "corner_cases": corner_cases,
            "potential_risks": risks,
            "assumptions": [],
            "verification_points": verification_points,
            "complexity": self._estimate_complexity(code),
            "summary": "",
        }

    # ========================================================
    # PORT EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_ports(
        code: str,
        direction: str,
    ):
        results = []

        pattern = (
            rf"\b{direction}\b"
            r"(?:\s+(?:wire|reg|logic|signed|unsigned))*"
            r"(?:\s*\[[^\]]+\])?"
            r"\s+([^;,\)]+)"
        )

        for match in re.finditer(
            pattern,
            code,
            re.IGNORECASE,
        ):
            raw = match.group(1)

            names = re.split(
                r",|\s*,\s*",
                raw,
            )

            for name in names:

                name = re.sub(
                    r"\s*=.*$",
                    "",
                    name,
                ).strip()

                name = re.sub(
                    r"\[[^\]]+\]",
                    "",
                    name,
                ).strip()

                if re.match(
                    r"^[A-Za-z_][A-Za-z0-9_]*$",
                    name,
                ):
                    results.append(
                        {
                            "name": name,
                            "direction": direction,
                        }
                    )

        # Remove duplicates.
        unique = {}

        for item in results:
            unique[item["name"]] = item

        return list(unique.values())

    # ========================================================
    # CLOCKS
    # ========================================================

    @staticmethod
    def _find_clock_signals(
        code: str,
    ):
        signals = set()

        patterns = [
            r"posedge\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"negedge\s+([A-Za-z_][A-Za-z0-9_]*)",
        ]

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                code,
                re.IGNORECASE,
            ):
                signals.add(
                    match.group(1)
                )

        for match in re.finditer(
            r"\b(?:clk|clock|i_clk|sys_clk)\b",
            code,
            re.IGNORECASE,
        ):
            signals.add(
                match.group(0)
            )

        return sorted(signals)

    # ========================================================
    # RESETS
    # ========================================================

    @staticmethod
    def _find_reset_signals(
        code: str,
    ):
        signals = set()

        pattern = (
            r"\b([A-Za-z_][A-Za-z0-9_]*)\b"
        )

        reset_keywords = [
            "rst",
            "reset",
            "rst_n",
            "reset_n",
            "areset",
            "areset_n",
            "sreset",
            "sreset_n",
        ]

        for match in re.finditer(
            pattern,
            code,
            re.IGNORECASE,
        ):

            name = match.group(1).lower()

            if any(
                keyword in name
                for keyword in reset_keywords
            ):
                signals.add(
                    match.group(1)
                )

        return sorted(signals)

    # ========================================================
    # REGISTERS
    # ========================================================

    @staticmethod
    def _find_registers(
        code: str,
    ):
        registers = set()

        patterns = [
            r"\breg\s+(?:\[[^\]]+\]\s*)?([A-Za-z_][A-Za-z0-9_]*)",
            r"\blogic\s+(?:\[[^\]]+\]\s*)?([A-Za-z_][A-Za-z0-9_]*)",
        ]

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                code,
                re.IGNORECASE,
            ):
                registers.add(
                    match.group(1)
                )

        return sorted(registers)

    # ========================================================
    # STATE
    # ========================================================

    @staticmethod
    def _find_state_elements(
        code: str,
    ):
        states = set()

        patterns = [
            r"\bstate\b",
            r"\bcurrent_state\b",
            r"\bnext_state\b",
            r"\bstate_reg\b",
        ]

        for pattern in patterns:

            if re.search(
                pattern,
                code,
                re.IGNORECASE,
            ):
                matches = re.findall(
                    r"\b[A-Za-z_][A-Za-z0-9_]*state[A-Za-z0-9_]*\b",
                    code,
                    re.IGNORECASE,
                )

                states.update(matches)

        return sorted(states)

    # ========================================================
    # FSM
    # ========================================================

    @staticmethod
    def _detect_fsm(
        code: str,
    ) -> bool:

        patterns = [
            r"\bcase\s*\(",
            r"\bunique\s+case",
            r"\btypedef\s+enum",
            r"\bcurrent_state\b",
            r"\bnext_state\b",
        ]

        score = 0

        for pattern in patterns:

            if re.search(
                pattern,
                code,
                re.IGNORECASE,
            ):
                score += 1

        return score >= 2

    # ========================================================
    # STATES
    # ========================================================

    @staticmethod
    def _find_states(
        code: str,
    ):
        states = set()

        patterns = [
            r"\bSTATE_[A-Za-z0-9_]+\b",
            r"\bS_[A-Za-z0-9_]+\b",
            r"\bIDLE\b",
            r"\bREADY\b",
            r"\bBUSY\b",
            r"\bWAIT\b",
            r"\bDONE\b",
        ]

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                code,
                re.IGNORECASE,
            ):
                states.add(
                    match.group(0)
                )

        return sorted(states)

    # ========================================================
    # COMBINATIONAL
    # ========================================================

    @staticmethod
    def _find_combinational_blocks(
        code: str,
    ):

        result = []

        if re.search(
            r"\balways_comb\b",
            code,
            re.IGNORECASE,
        ):
            result.append(
                "always_comb"
            )

        if re.search(
            r"\balways\s*@\s*\(\s*\*\s*\)",
            code,
            re.IGNORECASE,
        ):
            result.append(
                "always @*"
            )

        return result

    # ========================================================
    # SEQUENTIAL
    # ========================================================

    @staticmethod
    def _find_sequential_blocks(
        code: str,
    ):

        result = []

        if re.search(
            r"\balways_ff\b",
            code,
            re.IGNORECASE,
        ):
            result.append(
                "always_ff"
            )

        if re.search(
            r"\balways\s*@.*posedge",
            code,
            re.IGNORECASE,
        ):
            result.append(
                "posedge always block"
            )

        if re.search(
            r"\balways\s*@.*negedge",
            code,
            re.IGNORECASE,
        ):
            result.append(
                "negedge always block"
            )

        return result

    # ========================================================
    # PROTOCOL DETECTION
    # ========================================================

    @staticmethod
    def _detect_protocols(
        code: str,
    ):

        protocols = []

        protocol_patterns = {
            "valid-ready": [
                r"\bvalid\b",
                r"\bready\b",
            ],
            "request-acknowledge": [
                r"\breq\b",
                r"\back\b",
            ],
            "FIFO": [
                r"\bfifo\b",
                r"\bfull\b",
                r"\bempty\b",
            ],
            "AXI": [
                r"\baxi\b",
                r"\bawvalid\b",
                r"\bawready\b",
            ],
            "APB": [
                r"\bpsel\b",
                r"\bpenable\b",
            ],
            "UART": [
                r"\brx\b",
                r"\btx\b",
            ],
            "SPI": [
                r"\bsclk\b",
                r"\bmosi\b",
                r"\bmiso\b",
            ],
            "I2C": [
                r"\bsda\b",
                r"\bscl\b",
            ],
        }

        for name, patterns in protocol_patterns.items():

            matches = 0

            for pattern in patterns:

                if re.search(
                    pattern,
                    code,
                    re.IGNORECASE,
                ):
                    matches += 1

            if matches >= 2:
                protocols.append(name)

        return protocols

    # ========================================================
    # MEMORY
    # ========================================================

    @staticmethod
    def _detect_memory(
        code: str,
    ):

        memories = []

        if re.search(
            r"\[[^\]]+\]\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:;|=)",
            code,
        ):
            memories.append(
                "array/register memory"
            )

        if re.search(
            r"\bmem\b|\bram\b|\bsram\b",
            code,
            re.IGNORECASE,
        ):
            memories.append(
                "memory/RAM"
            )

        return memories

    # ========================================================
    # ARITHMETIC
    # ========================================================

    @staticmethod
    def _detect_arithmetic(
        code: str,
    ):

        operations = []

        operators = {
            "addition": r"\+",
            "subtraction": r"-",
            "multiplication": r"\*",
            "division": r"/",
            "modulo": r"%",
            "shift": r"<<|>>",
            "comparison": r"==|!=|<=|>=|<|>",
        }

        for name, pattern in operators.items():

            if re.search(
                pattern,
                code,
            ):
                operations.append(name)

        return operations

    # ========================================================
    # CORNER CASES
    # ========================================================

    @staticmethod
    def _detect_corner_cases(
        code: str,
    ):

        cases = []

        checks = [
            (
                r"\bfull\b",
                "Full condition"
            ),
            (
                r"\bempty\b",
                "Empty condition"
            ),
            (
                r"\boverflow\b",
                "Overflow"
            ),
            (
                r"\bunderflow\b",
                "Underflow"
            ),
            (
                r"\bdefault\b",
                "Default case"
            ),
            (
                r"\breset\b",
                "Reset behavior"
            ),
            (
                r"\bvalid\b",
                "Valid/invalid behavior"
            ),
            (
                r"\bread\b",
                "Read boundary"
            ),
            (
                r"\bwrite\b",
                "Write boundary"
            ),
        ]

        for pattern, description in checks:

            if re.search(
                pattern,
                code,
                re.IGNORECASE,
            ):
                cases.append(
                    description
                )

        return cases

    # ========================================================
    # RISKS
    # ========================================================

    @staticmethod
    def _detect_risks(
        code: str,
        clocks,
        resets,
        state_machine,
    ):

        risks = []

        if not clocks:
            risks.append(
                "Clock signal could not be identified."
            )

        if not resets:
            risks.append(
                "Reset signal could not be identified."
            )

        if state_machine:
            risks.append(
                "FSM requires state transition and illegal-state testing."
            )

        if re.search(
            r"\bcase\s*\(",
            code,
            re.IGNORECASE,
        ) and not re.search(
            r"\bdefault\s*:",
            code,
            re.IGNORECASE,
        ):
            risks.append(
                "Case statement may lack a default branch."
            )

        if re.search(
            r"\b\d+'[sb]?[01]+\b",
            code,
            re.IGNORECASE,
        ):
            risks.append(
                "Fixed-width constants detected; "
                "width boundary testing recommended."
            )

        if re.search(
            r"<<|>>",
            code,
        ):
            risks.append(
                "Shift operations detected; "
                "boundary shift testing recommended."
            )

        return risks

    # ========================================================
    # VERIFICATION POINTS
    # ========================================================

    @staticmethod
    def _build_verification_points(
        inputs,
        outputs,
        clocks,
        resets,
        state_elements,
        protocols,
        corner_cases,
    ):

        points = []

        for item in inputs[:20]:
            points.append(
                f"Input behavior: {item.get('name', '')}"
            )

        for item in outputs[:20]:
            points.append(
                f"Output behavior: {item.get('name', '')}"
            )

        for clock in clocks:
            points.append(
                f"Clock behavior: {clock}"
            )

        for reset in resets:
            points.append(
                f"Reset behavior: {reset}"
            )

        for state in state_elements:
            points.append(
                f"State behavior: {state}"
            )

        for protocol in protocols:
            points.append(
                f"Protocol behavior: {protocol}"
            )

        for corner in corner_cases:
            points.append(
                f"Corner case: {corner}"
            )

        return points

    # ========================================================
    # PARAMETERS
    # ========================================================

    @staticmethod
    def _find_parameters(
        code: str,
    ):

        result = []

        pattern = (
            r"\bparameter\b"
            r"(?:\s+\w+)?"
            r"\s+([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*=\s*([^,\);]+)"
        )

        for match in re.finditer(
            pattern,
            code,
            re.IGNORECASE,
        ):

            result.append(
                {
                    "name": match.group(1),
                    "value": match.group(2).strip(),
                }
            )

        return result

    # ========================================================
    # WIRES
    # ========================================================

    @staticmethod
    def _find_wires(
        code: str,
    ):

        wires = set()

        pattern = (
            r"\bwire\s+"
            r"(?:\[[^\]]+\]\s*)?"
            r"([A-Za-z_][A-Za-z0-9_]*)"
        )

        for match in re.finditer(
            pattern,
            code,
            re.IGNORECASE,
        ):
            wires.add(
                match.group(1)
            )

        return sorted(wires)

    # ========================================================
    # COMPLEXITY
    # ========================================================

    @staticmethod
    def _estimate_complexity(
        code: str,
    ):

        score = 0

        score += len(
            re.findall(
                r"\balways\b",
                code,
                re.IGNORECASE,
            )
        )

        score += 2 * len(
            re.findall(
                r"\bcase\b",
                code,
                re.IGNORECASE,
            )
        )

        score += len(
            re.findall(
                r"\bif\b",
                code,
                re.IGNORECASE,
            )
        )

        score += len(
            re.findall(
                r"\bfor\b|\bwhile\b",
                code,
                re.IGNORECASE,
            )
        )

        if score < 5:
            return "LOW"

        if score < 15:
            return "MEDIUM"

        if score < 30:
            return "HIGH"

        return "VERY_HIGH"

    # ========================================================
    # JSON PARSER
    # ========================================================

    @staticmethod
    def _parse_json(
        content: str,
    ) -> Dict[str, Any]:

        if not content:
            return {}

        content = content.strip()

        # Remove Markdown code fences if the LLM ignored
        # the instruction.
        content = re.sub(
            r"^```(?:json)?",
            "",
            content,
            flags=re.IGNORECASE,
        )

        content = re.sub(
            r"```$",
            "",
            content,
        )

        content = content.strip()

        try:
            parsed = json.loads(
                content
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

        # Try to recover the first JSON object.
        start = content.find("{")
        end = content.rfind("}")

        if start >= 0 and end > start:

            candidate = content[
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
                    return parsed

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
    # MERGE
    # ========================================================

    @staticmethod
    def _merge_analysis(
        structural: Dict[str, Any],
        ai_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge AI analysis over deterministic analysis.

        Static facts are retained if the LLM omits them.
        """

        result = dict(structural)

        for key, value in ai_analysis.items():

            if value is None:
                continue

            if (
                isinstance(value, list)
                and not value
                and result.get(key)
            ):
                continue

            result[key] = value

        # Guarantee critical fields exist.
        defaults = {
            "module_name": "",
            "language": "unknown",
            "inputs": [],
            "outputs": [],
            "parameters": [],
            "clocks": [],
            "resets": [],
            "registers": [],
            "wires": [],
            "state_elements": [],
            "state_machine": False,
            "states": [],
            "combinational_logic": [],
            "sequential_logic": [],
            "interfaces": [],
            "protocols": [],
            "arithmetic_operations": [],
            "memory_elements": [],
            "critical_paths": [],
            "corner_cases": [],
            "potential_risks": [],
            "assumptions": [],
            "verification_points": [],
            "complexity": "UNKNOWN",
            "summary": "",
        }

        for key, value in defaults.items():

            if key not in result:
                result[key] = value

        return result


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_rtl(
    rtl_code: str,
    specification: str = "",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Functional convenience wrapper.
    """

    agent = RTLAnalyzerAgent(
        api_key=api_key,
    )

    return agent.analyze(
        rtl_code=rtl_code,
        specification=specification,
    )


# ============================================================
# FACTORY
# ============================================================

def get_rtl_analyzer(
    api_key: Optional[str] = None,
) -> RTLAnalyzerAgent:
    """
    Return configured RTL Analyzer agent.
    """

    return RTLAnalyzerAgent(
        api_key=api_key,
    )
