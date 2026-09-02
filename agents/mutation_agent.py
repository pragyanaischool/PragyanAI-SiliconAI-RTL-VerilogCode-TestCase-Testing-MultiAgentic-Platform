"""
PragyanAI SiliconAI
Mutation Testing Agent

Purpose
-------
Measure the effectiveness of a verification test suite by creating
controlled RTL mutations and checking whether existing tests detect
them.

Core idea
---------
Good verification should not only make the original RTL pass.

It should also FAIL when realistic bugs are intentionally introduced.

Example:

Original RTL:
    assign y = a & b;

Mutation:
    assign y = a | b;

If the test suite detects the mutation:
    MUTANT KILLED

If the mutant still passes:
    MUTANT SURVIVED

Mutation Score:
    killed_mutants / executed_mutants * 100

This gives PragyanAI a stronger verification metric than simply
counting passing tests.

Important
---------
This implementation is deliberately conservative.

It only applies mutations to recognizable RTL constructs and creates
a mutated copy of the RTL.

The actual compilation/simulation is performed by IcarusRunner.

The agent itself does not claim a mutant is killed unless the
simulation evidence supports that conclusion.

Typical flow:

        Coverage
           |
           v
    Mutation Agent
           |
     Generate mutants
           |
           v
      Icarus Runner
           |
      +----+-----+
      |          |
      v          v
   KILLED     SURVIVED
      |          |
      +-----+----+
            |
            v
       Mutation Score
            |
            v
       Formal Agent
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eda.iverilog_runner import IcarusRunner


class MutationAgent:
    """
    Deterministic RTL mutation-testing agent.

    Mutation operators currently supported:

        1. AND -> OR
        2. OR -> AND
        3. == -> !=
        4. != -> ==
        5. > -> >=
        6. < -> <=
        7. >= -> >
        8. <= -> <
        9. + -> -
       10. - -> +
       11. & -> |
       12. | -> &
       13. Bitwise inversion of simple conditions
       14. Literal 0 -> 1
       15. Literal 1 -> 0

    The agent limits the number of mutations to keep execution time
    manageable.
    """

    AGENT_NAME = "Mutation Agent"

    DEFAULT_MAX_MUTANTS = 10

    def __init__(
        self,
        runner: Optional[IcarusRunner] = None,
        max_mutants: int = DEFAULT_MAX_MUTANTS,
        timeout: Optional[int] = None,
    ) -> None:

        self.runner = runner or IcarusRunner()

        self.max_mutants = max(
            1,
            int(max_mutants),
        )

        self.timeout = timeout

        if timeout is not None:
            try:
                self.runner.timeout = timeout
            except Exception:
                pass

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
    # Mutation operators
    # ------------------------------------------------------------------

    def _generate_mutations(
        self,
        rtl_code: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate candidate mutations.

        Each mutation contains:
            id
            operator
            description
            original
            mutated
            line
            rtl_code
        """

        mutations: List[Dict[str, Any]] = []

        if not rtl_code:
            return mutations

        lines = rtl_code.splitlines()

        # --------------------------------------------------------------
        # Helper
        # --------------------------------------------------------------

        def add_mutation(
            operator: str,
            description: str,
            original: str,
            mutated: str,
            line_number: int,
            mutated_code: str,
        ) -> None:

            if len(mutations) >= self.max_mutants:
                return

            mutations.append(
                {
                    "id": f"MUT{len(mutations)+1:03d}",
                    "operator": operator,
                    "description": description,
                    "original": original,
                    "mutated": mutated,
                    "line": line_number,
                    "rtl_code": mutated_code,
                    "status": "NOT_EXECUTED",
                }
            )

        # --------------------------------------------------------------
        # Operators
        # --------------------------------------------------------------

        operators = [
            (
                "AND_TO_OR",
                r"(?<![&])&&(?![&])",
                "&&",
                "||",
                "Logical AND converted to logical OR",
            ),
            (
                "OR_TO_AND",
                r"(?<![|])\|\|(?![|])",
                "||",
                "&&",
                "Logical OR converted to logical AND",
            ),
            (
                "EQ_TO_NE",
                r"(?<![=!])==(?![=])",
                "==",
                "!=",
                "Equality comparison inverted",
            ),
            (
                "NE_TO_EQ",
                r"!=",
                "!=",
                "==",
                "Inequality comparison inverted",
            ),
            (
                "GE_TO_GT",
                r">=",
                ">=",
                ">",
                "Greater-than-or-equal boundary changed to greater-than",
            ),
            (
                "LE_TO_LT",
                r"<=",
                "<=",
                "<",
                "Less-than-or-equal boundary changed to less-than",
            ),
            (
                "GT_TO_GE",
                r"(?<![>])>(?!=)",
                ">",
                ">=",
                "Greater-than boundary changed to greater-than-or-equal",
            ),
            (
                "LT_TO_LE",
                r"(?<![<])<(?!=)",
                "<",
                "<=",
                "Less-than boundary changed to less-than-or-equal",
            ),
            (
                "PLUS_TO_MINUS",
                r"\+",
                "+",
                "-",
                "Addition changed to subtraction",
            ),
            (
                "MINUS_TO_PLUS",
                r"(?<![>-])-",
                "-",
                "+",
                "Subtraction changed to addition",
            ),
            (
                "BITWISE_AND_TO_OR",
                r"(?<![&])&(?![&])",
                "&",
                "|",
                "Bitwise AND changed to OR",
            ),
            (
                "BITWISE_OR_TO_AND",
                r"(?<![|])\|(?![|])",
                "|",
                "&",
                "Bitwise OR changed to AND",
            ),
        ]

        # --------------------------------------------------------------
        # Scan source lines.
        # --------------------------------------------------------------

        for line_number, line in enumerate(
            lines,
            start=1,
        ):

            stripped = line.strip()

            # Skip comments.
            if (
                not stripped
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
            ):
                continue

            # Avoid modifying module/interface declarations.
            if re.search(
                r"\bmodule\b|\bendmodule\b",
                stripped,
                flags=re.IGNORECASE,
            ):
                continue

            for (
                operator,
                pattern,
                original,
                replacement,
                description,
            ) in operators:

                if len(mutations) >= self.max_mutants:
                    break

                match = re.search(
                    pattern,
                    line,
                )

                if not match:
                    continue

                # Create only the first mutation for a source line/operator.
                mutated_line = (
                    line[:match.start()]
                    + replacement
                    + line[match.end():]
                )

                mutated_lines = list(
                    lines
                )

                mutated_lines[
                    line_number - 1
                ] = mutated_line

                mutated_code = "\n".join(
                    mutated_lines
                )

                add_mutation(
                    operator=operator,
                    description=description,
                    original=original,
                    mutated=replacement,
                    line_number=line_number,
                    mutated_code=mutated_code,
                )

            if len(mutations) >= self.max_mutants:
                break

        # --------------------------------------------------------------
        # Literal mutations
        # --------------------------------------------------------------

        if len(mutations) < self.max_mutants:

            for line_number, line in enumerate(
                lines,
                start=1,
            ):

                if len(mutations) >= self.max_mutants:
                    break

                stripped = line.strip()

                if (
                    not stripped
                    or stripped.startswith("//")
                ):
                    continue

                # 0 -> 1
                match = re.search(
                    r"(?<![\w'])0(?![\w'])",
                    line,
                )

                if match:

                    mutated_line = (
                        line[:match.start()]
                        + "1"
                        + line[match.end():]
                    )

                    mutated_lines = list(
                        lines
                    )

                    mutated_lines[
                        line_number - 1
                    ] = mutated_line

                    add_mutation(
                        operator="CONST_0_TO_1",
                        description=(
                            "Constant zero changed to one"
                        ),
                        original="0",
                        mutated="1",
                        line_number=line_number,
                        mutated_code="\n".join(
                            mutated_lines
                        ),
                    )

                if len(mutations) >= self.max_mutants:
                    break

                # 1 -> 0
                match = re.search(
                    r"(?<![\w'])1(?![\w'])",
                    line,
                )

                if match:

                    mutated_line = (
                        line[:match.start()]
                        + "0"
                        + line[match.end():]
                    )

                    mutated_lines = list(
                        lines
                    )

                    mutated_lines[
                        line_number - 1
                    ] = mutated_line

                    add_mutation(
                        operator="CONST_1_TO_0",
                        description=(
                            "Constant one changed to zero"
                        ),
                        original="1",
                        mutated="0",
                        line_number=line_number,
                        mutated_code="\n".join(
                            mutated_lines
                        ),
                    )

        return mutations[: self.max_mutants]

    # ------------------------------------------------------------------
    # Testbench execution
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_testbench(
        state: Dict[str, Any],
    ) -> str:

        testbench = (
            state.get("testbench")
            or state.get("test_code")
            or ""
        )

        return str(
            testbench
        ).strip()

    # ------------------------------------------------------------------
    # Result interpretation
    # ------------------------------------------------------------------

    @staticmethod
    def _is_simulation_failure(
        result: Dict[str, Any],
    ) -> bool:

        compile_success = bool(
            result.get(
                "compile_success"
            )
            or result.get(
                "compile_passed"
            )
        )

        simulation_success = bool(
            result.get(
                "simulation_success"
            )
            or result.get(
                "simulation_passed"
            )
        )

        compile_error = str(
            result.get(
                "compile_error",
                "",
            )
        )

        simulation_error = str(
            result.get(
                "simulation_error",
                "",
            )
        )

        simulation_output = str(
            result.get(
                "simulation_output",
                result.get(
                    "output",
                    "",
                ),
            )
        )

        combined = (
            compile_error
            + "\n"
            + simulation_error
            + "\n"
            + simulation_output
        ).upper()

        explicit_failure = any(
            token in combined
            for token in [
                "TEST_ERROR",
                "FAILED",
                "FAILURE",
                "ASSERTION FAILED",
                "MISMATCH",
                "FATAL",
            ]
        )

        return (
            not compile_success
            or not simulation_success
            or explicit_failure
        )

    # ------------------------------------------------------------------
    # Single mutant execution
    # ------------------------------------------------------------------

    def _execute_mutant(
        self,
        mutant: Dict[str, Any],
        testbench: str,
    ) -> Dict[str, Any]:

        start = time.time()

        rtl_code = str(
            mutant.get(
                "rtl_code",
                "",
            )
        )

        try:

            result = self.runner.run(
                rtl_code=rtl_code,
                testbench_code=testbench,
                filename_prefix=(
                    mutant.get(
                        "id",
                        "mutant",
                    )
                ),
            )

        except TypeError:

            try:

                result = self.runner.run(
                    rtl_code,
                    testbench,
                )

            except Exception as exc:

                result = {
                    "compile_success": False,
                    "simulation_success": False,
                    "compile_error": str(exc),
                    "simulation_error": str(exc),
                    "simulation_output": "",
                }

        except Exception as exc:

            result = {
                "compile_success": False,
                "simulation_success": False,
                "compile_error": str(exc),
                "simulation_error": str(exc),
                "simulation_output": "",
            }

        if not isinstance(
            result,
            dict,
        ):

            result = {
                "compile_success": False,
                "simulation_success": False,
                "compile_error": (
                    "Invalid simulator result."
                ),
                "simulation_error": "",
                "simulation_output": "",
            }

        killed = self._is_simulation_failure(
            result
        )

        elapsed = round(
            time.time() - start,
            3,
        )

        return {
            "status": (
                "KILLED"
                if killed
                else "SURVIVED"
            ),
            "compile_success": bool(
                result.get(
                    "compile_success"
                    )
                    or result.get(
                        "compile_passed"
                    )
            ),
            "simulation_success": bool(
                result.get(
                    "simulation_success"
                )
                or result.get(
                    "simulation_passed"
                )
            ),
            "simulation_output": self._compact(
                result.get(
                    "simulation_output",
                    result.get(
                        "output",
                        "",
                    ),
                ),
                3500,
            ),
            "compile_error": self._compact(
                result.get(
                    "compile_error",
                    "",
                ),
                2500,
            ),
            "simulation_error": self._compact(
                result.get(
                    "simulation_error",
                    "",
                ),
                2500,
            ),
            "duration_seconds": elapsed,
        }

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
        ).strip()

        testbench = self._extract_testbench(
            state
        )

        iteration = int(
            state.get("iteration")
            or 1
        )

        run_dir = state.get(
            "run_dir"
        )

        if run_dir:

            mutation_dir = (
                Path(run_dir)
                / "mutations"
            )

        else:

            mutation_dir = (
                Path("verification_logs")
                / "mutations"
            )

        # --------------------------------------------------------------
        # Validate
        # --------------------------------------------------------------

        if not rtl_code:

            message = (
                "Mutation testing skipped: RTL code is empty."
            )

            trace = {
                "agent": self.AGENT_NAME,
                "status": "FAILED",
                "timestamp": self._timestamp(),
                "message": message,
            }

            return {
                "mutations": [],
                "mutation_score": 0.0,
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
                "errors": (
                    list(
                        state.get(
                            "errors"
                        )
                        or []
                    )
                    + [message]
                ),
            }

        if not testbench:

            message = (
                "Mutation testing skipped: testbench is empty."
            )

            trace = {
                "agent": self.AGENT_NAME,
                "status": "FAILED",
                "timestamp": self._timestamp(),
                "message": message,
            }

            return {
                "mutations": [],
                "mutation_score": 0.0,
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
                "errors": (
                    list(
                        state.get(
                            "errors"
                        )
                        or []
                    )
                    + [message]
                ),
            }

        # --------------------------------------------------------------
        # Generate mutants
        # --------------------------------------------------------------

        mutants = self._generate_mutations(
            rtl_code
        )

        if not mutants:

            message = (
                "No suitable mutation points were detected in the RTL."
            )

            trace = {
                "agent": self.AGENT_NAME,
                "status": "COMPLETED",
                "timestamp": self._timestamp(),
                "message": message,
                "mutation_count": 0,
            }

            return {
                "mutations": [],
                "mutation_score": 0.0,
                "mutation_count": 0,
                "mutants_killed": 0,
                "mutants_survived": 0,
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
        # Save original RTL
        # --------------------------------------------------------------

        self._save_text(
            mutation_dir
            / "original_rtl.v",
            rtl_code,
        )

        # --------------------------------------------------------------
        # Execute mutants
        # --------------------------------------------------------------

        results: List[Dict[str, Any]] = []

        killed = 0
        survived = 0
        compile_failed = 0

        for mutant in mutants:

            mutant_id = mutant["id"]

            mutant_path = self._save_text(
                mutation_dir
                / f"{mutant_id}.v",
                mutant["rtl_code"],
            )

            execution = self._execute_mutant(
                mutant=mutant,
                testbench=testbench,
            )

            status = execution["status"]

            if status == "KILLED":
                killed += 1

            else:
                survived += 1

            if not execution[
                "compile_success"
            ]:
                compile_failed += 1

            result = {
                "id": mutant_id,
                "operator": mutant[
                    "operator"
                ],
                "description": mutant[
                    "description"
                ],
                "original": mutant[
                    "original"
                ],
                "mutated": mutant[
                    "mutated"
                ],
                "line": mutant[
                    "line"
                ],
                "status": status,
                "compile_success": execution[
                    "compile_success"
                ],
                "simulation_success": execution[
                    "simulation_success"
                ],
                "simulation_output": execution[
                    "simulation_output"
                ],
                "compile_error": execution[
                    "compile_error"
                ],
                "simulation_error": execution[
                    "simulation_error"
                ],
                "duration_seconds": execution[
                    "duration_seconds"
                ],
                "rtl_file": mutant_path or "",
                "iteration": iteration,
                "timestamp": self._timestamp(),
            }

            results.append(
                result
            )

            # Save per-mutant result.
            self._save_json(
                mutation_dir
                / f"{mutant_id}.json",
                result,
            )

        # --------------------------------------------------------------
        # Mutation score
        # --------------------------------------------------------------

        executed = (
            killed + survived
        )

        if executed:

            mutation_score = (
                killed
                / executed
                * 100.0
            )

        else:

            mutation_score = 0.0

        mutation_score = round(
            mutation_score,
            2,
        )

        # --------------------------------------------------------------
        # Surviving mutant analysis
        # --------------------------------------------------------------

        surviving_mutants = [
            result
            for result in results
            if result["status"]
            == "SURVIVED"
        ]

        recommended_tests: List[str] = []

        for mutant in surviving_mutants:

            operator = mutant.get(
                "operator",
                "UNKNOWN",
            )

            line = mutant.get(
                "line",
                "?",
            )

            description = mutant.get(
                "description",
                "",
            )

            recommended_tests.append(
                (
                    f"Add a targeted test for mutation "
                    f"{operator} at RTL line {line}: "
                    f"{description}."
                )
            )

        # --------------------------------------------------------------
        # Summary
        # --------------------------------------------------------------

        if mutation_score >= 90:

            assessment = (
                "Strong mutation effectiveness. "
                "Most injected faults were detected by the test suite."
            )

        elif mutation_score >= 75:

            assessment = (
                "Good mutation effectiveness, but surviving mutants "
                "indicate additional targeted tests are required."
            )

        elif mutation_score >= 50:

            assessment = (
                "Moderate mutation effectiveness. "
                "Several realistic RTL faults escaped detection."
            )

        else:

            assessment = (
                "Weak mutation effectiveness. "
                "The current test suite does not detect many "
                "realistic injected RTL faults."
            )

        # --------------------------------------------------------------
        # Structured mutation result
        # --------------------------------------------------------------

        mutation_result = {
            "score": mutation_score,
            "mutation_score": mutation_score,
            "total_mutants": len(results),
            "executed_mutants": executed,
            "killed_mutants": killed,
            "survived_mutants": survived,
            "compile_failed_mutants": compile_failed,
            "assessment": assessment,
            "surviving_mutants": surviving_mutants,
            "recommended_tests": recommended_tests[:15],
            "iteration": iteration,
            "timestamp": self._timestamp(),
            "method": "RTL mutation + Icarus simulation",
        }

        # --------------------------------------------------------------
        # Save summary
        # --------------------------------------------------------------

        summary_path = self._save_json(
            mutation_dir
            / "mutation_summary.json",
            mutation_result,
        )

        # --------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------

        elapsed = round(
            time.time() - start,
            3,
        )

        message = (
            f"Mutation testing completed: "
            f"{killed}/{executed} mutants killed, "
            f"mutation score={mutation_score:.2f}%."
        )

        if survived:
            message += (
                f" {survived} mutant(s) survived."
            )

        trace_entry = {
            "agent": self.AGENT_NAME,
            "status": "COMPLETED",
            "timestamp": self._timestamp(),
            "message": message,
            "duration_seconds": elapsed,
            "mutation_score": mutation_score,
            "mutants": len(results),
            "killed": killed,
            "survived": survived,
        }

        # --------------------------------------------------------------
        # Agent log
        # --------------------------------------------------------------

        agent_log_entry = {
            "agent": self.AGENT_NAME,
            "status": "COMPLETED",
            "timestamp": self._timestamp(),
            "duration_seconds": elapsed,
            "iteration": iteration,
            "input_summary": {
                "rtl_length": len(rtl_code),
                "testbench_length": len(testbench),
            },
            "output_summary": {
                "total_mutants": len(results),
                "killed": killed,
                "survived": survived,
                "mutation_score": mutation_score,
            },
            "summary_file": summary_path or "",
        }

        # --------------------------------------------------------------
        # Return state
        # --------------------------------------------------------------

        return {
            "mutations": results,

            "mutation_score": mutation_score,

            "mutation_result": mutation_result,

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

            "warnings": (
                list(
                    state.get(
                        "warnings"
                    )
                    or []
                )
                + (
                    [
                        (
                            f"{survived} surviving mutant(s) "
                            "require targeted tests."
                        )
                    ]
                    if survived
                    else []
                )
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

def run_mutation_agent(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience wrapper for LangGraph.
    """

    agent = MutationAgent()

    return agent.run(state)


__all__ = [
    "MutationAgent",
    "run_mutation_agent",
]
