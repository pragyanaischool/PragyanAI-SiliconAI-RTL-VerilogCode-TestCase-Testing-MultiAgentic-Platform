"""
PragyanAI SiliconAI
Testbench Generator Agent

Responsibilities:
    1. Convert structured test scenarios into executable
       Verilog/SystemVerilog testbench code.
    2. Make the generated testbench Icarus-compatible.
    3. Preserve test IDs for traceability.
    4. Generate machine-readable TEST_RESULT lines.
    5. Generate machine-readable TEST_ERROR lines.
    6. Avoid unnecessary LLM context to reduce token usage.
    7. Validate basic testbench structure before returning it.
    8. Support iterative regeneration after failures.

Expected machine-readable output:

    TEST_RESULT|TC001|PASS|input=...|expected=...|actual=...

or:

    TEST_RESULT|TC001|FAIL|input=...|expected=...|actual=...

Errors:

    TEST_ERROR|TC001|message=...

The generated testbench is not considered verified merely because
it compiles. Simulation evidence must be collected by the
Simulation Agent.
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
    TESTBENCH_GENERATOR_MAX_TOKENS,
    MAX_RTL_CHARS_FOR_LLM,
    MAX_TESTBENCH_LINES,
)

from config.prompts import (
    load_prompt,
    limit_text,
    compact_json,
    compact_rtl,
    compact_plan,
    compact_rtl_analysis,
    compact_test_scenarios,
    compact_failure,
    compact_red_team,
)


class TestbenchGeneratorAgent:
    """
    Generates an executable Verilog/SystemVerilog testbench
    from structured verification scenarios.
    """

    name = "Testbench Generator"

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
            TESTBENCH_GENERATOR_MAX_TOKENS
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
        rtl_code: str,
        tests: Optional[List[Dict[str, Any]]] = None,
        specification: str = "",
        rtl_analysis: Optional[Dict[str, Any]] = None,
        verification_plan: Optional[Dict[str, Any]] = None,
        failure_analysis: Optional[Dict[str, Any]] = None,
        red_team_scenarios: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Generate executable testbench.

        Returns:

            {
                "testbench": "...",
                "test_code": "...",
                "status": "COMPLETED"
            }
        """

        tests = tests or []
        rtl_analysis = rtl_analysis or {}
        verification_plan = verification_plan or {}
        red_team_scenarios = red_team_scenarios or []

        if not rtl_code.strip():

            return {
                "testbench": "",
                "test_code": "",
                "status": "FAILED",
                "errors": [
                    "RTL code is empty."
                ],
                "messages": [
                    "Testbench Generator cannot operate without RTL."
                ],
            }

        if not tests:

            return {
                "testbench": "",
                "test_code": "",
                "status": "FAILED",
                "errors": [
                    "No test scenarios supplied."
                ],
                "messages": [
                    "Testbench Generator requires at least one test scenario."
                ],
            }

        # ----------------------------------------------------
        # If no LLM is configured, generate a conservative
        # fallback testbench.
        # ----------------------------------------------------

        if self.llm is None:

            fallback = self._fallback_testbench(
                rtl_code=rtl_code,
                tests=tests,
            )

            validation = self.validate_testbench(
                fallback
            )

            if not validation["valid"]:

                return {
                    "testbench": fallback,
                    "test_code": fallback,
                    "status": "FAILED",
                    "errors": validation["errors"],
                    "messages": [
                        "Fallback testbench generation failed validation."
                    ],
                }

            return {
                "testbench": fallback,
                "test_code": fallback,
                "status": "COMPLETED",
                "warnings": [
                    "Groq API key not configured; "
                    "fallback testbench generated."
                ],
                "messages": [
                    "Fallback testbench generated."
                ],
            }

        # ----------------------------------------------------
        # LLM generation.
        # ----------------------------------------------------

        try:

            prompt = self._build_prompt(
                rtl_code=rtl_code,
                tests=tests,
                specification=specification,
                rtl_analysis=rtl_analysis,
                verification_plan=verification_plan,
                failure_analysis=failure_analysis,
                red_team_scenarios=red_team_scenarios,
            )

            response = self.llm.invoke(
                prompt
            )

            content = self._extract_content(
                response
            )

            testbench = self._clean_testbench(
                content
            )

            validation = self.validate_testbench(
                testbench
            )

            if not validation["valid"]:

                # Attempt a deterministic repair for simple
                # formatting problems.
                repaired = self._repair_testbench_structure(
                    testbench,
                    tests,
                )

                repaired_validation = self.validate_testbench(
                    repaired
                )

                if repaired_validation["valid"]:
                    testbench = repaired
                    validation = repaired_validation

            if not validation["valid"]:

                return {
                    "testbench": testbench,
                    "test_code": testbench,
                    "status": "FAILED",
                    "errors": validation["errors"],
                    "warnings": [
                        "LLM generated testbench failed structural validation."
                    ],
                    "messages": [
                        "Testbench generation requires regeneration."
                    ],
                }

            return {
                "testbench": testbench,
                "test_code": testbench,
                "status": "COMPLETED",
                "messages": [
                    (
                        "Generated executable testbench for "
                        f"{len(tests)} test scenarios."
                    )
                ],
            }

        except Exception as exc:

            fallback = self._fallback_testbench(
                rtl_code=rtl_code,
                tests=tests,
            )

            return {
                "testbench": fallback,
                "test_code": fallback,
                "status": "COMPLETED",
                "warnings": [
                    "LLM testbench generation failed.",
                    limit_text(
                        str(exc),
                        1200,
                    ),
                    "Fallback testbench returned.",
                ],
                "messages": [
                    "Fallback testbench generated after LLM failure."
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
            rtl_code=state.get(
                "rtl_code",
                "",
            ),
            tests=state.get(
                "tests",
                state.get(
                    "generated_tests",
                    [],
                ),
            ),
            specification=state.get(
                "specification",
                state.get(
                    "prompt",
                    "",
                ),
            ),
            rtl_analysis=state.get(
                "rtl_analysis",
                {},
            ),
            verification_plan=state.get(
                "verification_plan",
                {},
            ),
            failure_analysis=state.get(
                "failure_analysis",
                {},
            ),
            red_team_scenarios=state.get(
                "red_team_scenarios",
                [],
            ),
        )

        return {
            "testbench": result.get(
                "testbench",
                "",
            ),
            "test_code": result.get(
                "test_code",
                "",
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
            "errors": result.get(
                "errors",
                [],
            ),
        }

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        rtl_code: str,
        tests: List[Dict[str, Any]],
        specification: str,
        rtl_analysis: Dict[str, Any],
        verification_plan: Dict[str, Any],
        failure_analysis: Optional[
            Dict[str, Any]
        ],
        red_team_scenarios: List[
            Dict[str, Any]
        ],
    ) -> str:
        """
        Build a compact testbench-generation prompt.

        Important:
            Do NOT send the complete LangGraph state.

        Only the information required to generate the
        testbench is included.
        """

        system_prompt = load_prompt(
            "testbench_generation"
        )

        if not system_prompt:
            system_prompt = self._default_prompt()

        rtl = compact_rtl(
            rtl_code,
            max_chars=MAX_RTL_CHARS_FOR_LLM,
        )

        test_context = compact_test_scenarios(
            tests,
            max_items=10,
            max_chars=7000,
        )

        analysis = compact_rtl_analysis(
            rtl_analysis,
            max_chars=4000,
        )

        plan = compact_plan(
            verification_plan,
            max_chars=4000,
        )

        failure = compact_failure(
            failure_analysis,
            max_chars=3500,
        )

        red_team = compact_red_team(
            red_team_scenarios,
            max_items=5,
            max_chars=3000,
        )

        spec = limit_text(
            specification,
            max_chars=5000,
            keep="both",
        )

        return f"""
{system_prompt}

============================================================
CRITICAL OUTPUT RULES
============================================================

Return ONLY executable Verilog/SystemVerilog source code.

DO NOT return:
- Markdown
- explanations
- ```verilog
- ```systemverilog
- JSON
- commentary before or after the code

The output must contain exactly one top-level testbench module.

============================================================
RTL
============================================================

{rtl}

============================================================
RTL ANALYSIS
============================================================

{analysis}

============================================================
VERIFICATION PLAN
============================================================

{plan}

============================================================
TEST SCENARIOS
============================================================

{test_context}

============================================================
SPECIFICATION
============================================================

{spec}

============================================================
PREVIOUS FAILURE ANALYSIS
============================================================

{failure}

============================================================
RED TEAM CONTEXT
============================================================

{red_team}

============================================================
MANDATORY TEST EVIDENCE FORMAT
============================================================

For every test scenario, print exactly one machine-readable
line using:

TEST_RESULT|TC001|PASS|input=...|expected=...|actual=...

or:

TEST_RESULT|TC001|FAIL|input=...|expected=...|actual=...

If a test cannot execute:

TEST_ERROR|TC001|message=...

Use the actual test ID supplied in each scenario.

Do not print PASS unless the expected behavior was actually
checked.

Do not print FAIL merely because a test is intentionally
negative. A negative test passes when the design behaves
according to the specified negative behavior.

============================================================
TESTBENCH REQUIREMENTS
============================================================

1. Instantiate the actual DUT.
2. Use the exact RTL module name and port names.
3. Declare all DUT connections.
4. Drive every required input.
5. Monitor relevant outputs.
6. Wait for appropriate clock edges where applicable.
7. Perform explicit checks.
8. Generate TEST_RESULT lines.
9. Generate TEST_ERROR lines for execution problems.
10. End simulation using $finish.
11. Do not modify the DUT.
12. Do not silently ignore mismatches.
13. Keep the testbench compatible with Icarus Verilog.
14. Avoid unsupported vendor-specific constructs.
15. Do not use UVM.
16. Do not require external packages.
17. Prefer Verilog/SystemVerilog constructs supported by:
       iverilog -g2012

============================================================
"""

    # ========================================================
    # DEFAULT PROMPT
    # ========================================================

    @staticmethod
    def _default_prompt() -> str:
        return """
You are an expert Verilog/SystemVerilog verification engineer.

Generate a simple, robust, executable testbench for the
supplied RTL.

The testbench must:
- instantiate the DUT
- drive inputs
- observe outputs
- execute all supplied scenarios
- explicitly check expected behavior
- print machine-readable TEST_RESULT lines
- print TEST_ERROR lines for execution errors
- call $finish

Use Icarus-compatible SystemVerilog.

Return only source code.
"""

    # ========================================================
    # VALIDATE TESTBENCH
    # ========================================================

    def validate_testbench(
        self,
        testbench: str,
    ) -> Dict[str, Any]:
        """
        Perform lightweight structural validation.

        This does not replace actual compilation.
        """

        errors = []
        warnings = []

        if not testbench or not testbench.strip():

            errors.append(
                "Testbench is empty."
            )

            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
            }

        code = testbench.strip()

        # ----------------------------------------------------
        # Module.
        # ----------------------------------------------------

        module_matches = re.findall(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)",
            code,
            re.IGNORECASE,
        )

        if not module_matches:

            errors.append(
                "No Verilog/SystemVerilog module found."
            )

        # ----------------------------------------------------
        # Endmodule.
        # ----------------------------------------------------

        if not re.search(
            r"\bendmodule\b",
            code,
            re.IGNORECASE,
        ):
            errors.append(
                "Missing endmodule."
            )

        # ----------------------------------------------------
        # Initial block / procedural execution.
        # ----------------------------------------------------

        if not re.search(
            r"\binitial\b|\balways\b",
            code,
            re.IGNORECASE,
        ):
            warnings.append(
                "No initial/always procedural block detected."
            )

        # ----------------------------------------------------
        # DUT instantiation.
        # ----------------------------------------------------

        if not re.search(
            r"\b[A-Za-z_][A-Za-z0-9_]*\s+"
            r"(?:#\s*\([^;]*\)\s*)?"
            r"[A-Za-z_][A-Za-z0-9_]*\s*\(",
            code,
            re.DOTALL,
        ):
            warnings.append(
                "DUT instantiation could not be confidently detected."
            )

        # ----------------------------------------------------
        # Simulation termination.
        # ----------------------------------------------------

        if not re.search(
            r"\$finish\b|\$stop\b",
            code,
            re.IGNORECASE,
        ):
            errors.append(
                "Testbench does not contain $finish or $stop."
            )

        # ----------------------------------------------------
        # Test result instrumentation.
        # ----------------------------------------------------

        if "TEST_RESULT" not in code:

            errors.append(
                "Missing TEST_RESULT instrumentation."
            )

        # ----------------------------------------------------
        # Test error instrumentation.
        # ----------------------------------------------------

        if "TEST_ERROR" not in code:

            warnings.append(
                "TEST_ERROR instrumentation not found."
            )

        # ----------------------------------------------------
        # Excessive size.
        # ----------------------------------------------------

        lines = code.splitlines()

        if len(lines) > MAX_TESTBENCH_LINES:

            warnings.append(
                (
                    f"Testbench contains {len(lines)} lines; "
                    f"configured recommendation is "
                    f"{MAX_TESTBENCH_LINES}."
                )
            )

        # ----------------------------------------------------
        # Obvious unsupported constructs.
        # ----------------------------------------------------

        unsupported = [
            "uvm_component",
            "uvm_test",
            "uvm_env",
            "`uvm_",
        ]

        for token in unsupported:

            if token.lower() in code.lower():

                errors.append(
                    f"Unsupported UVM construct detected: {token}"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ========================================================
    # CLEAN GENERATED CODE
    # ========================================================

    @staticmethod
    def _clean_testbench(
        content: str,
    ) -> str:
        """
        Remove Markdown fences and accidental explanation.
        """

        if not content:
            return ""

        text = content.strip()

        # Remove Markdown fences.
        text = re.sub(
            r"^```(?:verilog|systemverilog|sv|v)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```\s*$",
            "",
            text,
        )

        # If the model added prose before module, keep only
        # the source beginning at the first module.
        module_pos = re.search(
            r"\bmodule\s+",
            text,
            re.IGNORECASE,
        )

        if module_pos:
            text = text[
                module_pos.start():
            ]

        # If there is prose after endmodule, remove it.
        endmodule_matches = list(
            re.finditer(
                r"\bendmodule\b",
                text,
                re.IGNORECASE,
            )
        )

        if endmodule_matches:

            last = endmodule_matches[-1]

            text = text[
                :last.end()
            ]

        return text.strip()

    # ========================================================
    # STRUCTURAL REPAIR
    # ========================================================

    def _repair_testbench_structure(
        self,
        testbench: str,
        tests: List[Dict[str, Any]],
    ) -> str:
        """
        Repair simple formatting/instrumentation omissions.

        This function intentionally does not attempt to repair
        incorrect DUT logic.
        """

        code = self._clean_testbench(
            testbench
        )

        if not code:
            return code

        # Add $finish when missing.
        if not re.search(
            r"\$finish\b|\$stop\b",
            code,
            re.IGNORECASE,
        ):

            if re.search(
                r"\bend\b",
                code,
                re.IGNORECASE,
            ):
                code = re.sub(
                    r"\bend\b",
                    "    $finish;\nend",
                    code,
                    count=1,
                )
            else:
                code += "\ninitial begin\n    $finish;\nend\n"

        # If no TEST_RESULT exists, add a conservative error
        # rather than falsely reporting PASS.
        if "TEST_RESULT" not in code:

            ids = []

            for test in tests:

                test_id = test.get(
                    "test_id",
                    "",
                )

                if test_id:
                    ids.append(
                        str(test_id)
                    )

            if ids:

                code = re.sub(
                    r"\bend\b",
                    (
                        "    $display("
                        '"TEST_ERROR|GENERATION|message=Missing test result checks"'
                        ");\n"
                        "    $finish;\n"
                        "end"
                    ),
                    code,
                    count=1,
                )

        return code

    # ========================================================
    # FALLBACK TESTBENCH
    # ========================================================

    def _fallback_testbench(
        self,
        rtl_code: str,
        tests: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a generic fallback testbench.

        Important:
            This is intentionally conservative.

        It attempts to infer the DUT interface from RTL.
        It does NOT claim functional PASS without explicit
        expected-value knowledge.
        """

        module_name = self._extract_module_name(
            rtl_code
        )

        ports = self._extract_module_ports(
            rtl_code
        )

        if not module_name:

            return """
module generated_testbench;

    initial begin
        $display("TEST_ERROR|GENERATION|message=Unable to identify DUT module");
        $finish;
    end

endmodule
""".strip()

        declarations = []
        connections = []

        for port in ports:

            name = port["name"]
            direction = port["direction"]

            width = port.get(
                "width",
                "",
            )

            if direction == "input":

                declaration = "reg"

                if width:
                    declarations.append(
                        f"{declaration} {width} {name};"
                    )
                else:
                    declarations.append(
                        f"{declaration} {name};"
                    )

            else:

                declaration = "wire"

                if width:
                    declarations.append(
                        f"{declaration} {width} {name};"
                    )
                else:
                    declarations.append(
                        f"{declaration} {name};"
                    )

            connections.append(
                f".{name}({name})"
            )

        dut_instance = (
            f"{module_name} dut (\n        "
            + ",\n        ".join(
                connections
            )
            + "\n    );"
        )

        input_initialization = []

        for port in ports:

            if port["direction"] != "input":
                continue

            name = port["name"]

            input_initialization.append(
                f"        {name} = '0;"
            )

        test_lines = []

        for test in tests:

            test_id = test.get(
                "test_id",
                "",
            )

            if not test_id:
                continue

            description = self._escape_verilog_string(
                test.get(
                    "description",
                    "Generated test",
                )
            )

            test_lines.append(
                f'        $display("TEST_ERROR|{test_id}|message=Fallback testbench cannot determine functional expected values for: {description}");'
            )

        return f"""
`timescale 1ns/1ps

module generated_testbench;

    // --------------------------------------------------------
    // DUT SIGNALS
    // --------------------------------------------------------

    {chr(10).join("    " + x for x in declarations)}

    // --------------------------------------------------------
    // DUT
    // --------------------------------------------------------

    {dut_instance}

    // --------------------------------------------------------
    // TEST EXECUTION
    // --------------------------------------------------------

    initial begin

{chr(10).join(input_initialization)}

        #10;

{chr(10).join(test_lines)}

        $display("TEST_ERROR|SUMMARY|message=Fallback testbench requires AI-generated functional checks");
        $finish;

    end

endmodule
""".strip()

    # ========================================================
    # MODULE NAME
    # ========================================================

    @staticmethod
    def _extract_module_name(
        rtl_code: str,
    ) -> str:

        match = re.search(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)",
            rtl_code,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return ""

    # ========================================================
    # PORT PARSER
    # ========================================================

    @staticmethod
    def _extract_module_ports(
        rtl_code: str,
    ) -> List[Dict[str, Any]]:
        """
        Lightweight module-port parser.

        Handles common declarations such as:

            input clk
            input rst
            input [7:0] data
            output [7:0] result
            output reg done
            output logic valid
        """

        ports = []

        # ----------------------------------------------------
        # ANSI-style ports.
        # ----------------------------------------------------

        pattern = re.compile(
            r"\b(input|output|inout)\b"
            r"\s*"
            r"(?:(?:wire|reg|logic|signed|unsigned)\s*)*"
            r"(\[[^\]]+\])?"
            r"\s*"
            r"([A-Za-z_][A-Za-z0-9_]*)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(
            rtl_code
        ):

            direction = match.group(
                1
            ).lower()

            width = (
                match.group(2)
                or ""
            )

            name = match.group(
                3
            )

            ports.append(
                {
                    "name": name,
                    "direction": direction,
                    "width": width,
                }
            )

        # ----------------------------------------------------
        # Remove duplicates.
        # ----------------------------------------------------

        unique = {}

        for port in ports:

            unique[
                port["name"]
            ] = port

        return list(
            unique.values()
        )

    # ========================================================
    # VERILOG STRING ESCAPING
    # ========================================================

    @staticmethod
    def _escape_verilog_string(
        value: Any,
    ) -> str:

        text = str(
            value
        )

        text = text.replace(
            "\\",
            "\\\\",
        )

        text = text.replace(
            '"',
            '\\"',
        )

        text = text.replace(
            "\n",
            " ",
        )

        return limit_text(
            text,
            max_chars=300,
        )

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

def generate_testbench(
    rtl_code: str,
    tests: Optional[List[Dict[str, Any]]] = None,
    specification: str = "",
    rtl_analysis: Optional[Dict[str, Any]] = None,
    verification_plan: Optional[Dict[str, Any]] = None,
    failure_analysis: Optional[
        Dict[str, Any]
    ] = None,
    red_team_scenarios: Optional[
        List[Dict[str, Any]]
    ] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper.
    """

    agent = TestbenchGeneratorAgent(
        api_key=api_key,
    )

    return agent.generate(
        rtl_code=rtl_code,
        tests=tests,
        specification=specification,
        rtl_analysis=rtl_analysis,
        verification_plan=verification_plan,
        failure_analysis=failure_analysis,
        red_team_scenarios=red_team_scenarios,
    )


# ============================================================
# FACTORY
# ============================================================

def get_testbench_generator(
    api_key: Optional[str] = None,
) -> TestbenchGeneratorAgent:
    """
    Return configured Testbench Generator agent.
    """

    return TestbenchGeneratorAgent(
        api_key=api_key,
    )
