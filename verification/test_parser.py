"""
PragyanAI SiliconAI

Machine-readable simulation/test result parser.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


TEST_RESULT_PATTERN = re.compile(
    r"TEST_RESULT\|([^|]+)\|([^|]+)(.*)"
)

TEST_ERROR_PATTERN = re.compile(
    r"TEST_ERROR\|([^|]+)\|(.*)"
)


def _parse_fields(
    text: str,
) -> Dict[str, str]:

    fields: Dict[str, str] = {}

    text = text.strip()

    if not text:
        return fields

    parts = text.split("|")

    for part in parts:

        if "=" not in part:
            continue

        key, value = part.split(
            "=",
            1,
        )

        fields[
            key.strip()
        ] = value.strip()

    return fields


def parse_test_results(
    simulation_output: str,
) -> List[Dict[str, Any]]:
    """
    Parse all TEST_RESULT lines.
    """

    results: List[Dict[str, Any]] = []

    if not simulation_output:
        return results

    for line in simulation_output.splitlines():

        line = line.strip()

        match = TEST_RESULT_PATTERN.search(
            line
        )

        if not match:
            continue

        test_id = match.group(1).strip()

        status = (
            match.group(2)
            .strip()
            .upper()
        )

        fields = _parse_fields(
            match.group(3)
        )

        if status == "PASS":
            status = "PASSED"

        elif status == "FAIL":
            status = "FAILED"

        results.append(
            {
                "test_id": test_id,
                "status": status,
                "inputs": fields.get(
                    "input",
                    fields.get(
                        "inputs",
                        "",
                    ),
                ),
                "expected": fields.get(
                    "expected",
                    "",
                ),
                "actual": fields.get(
                    "actual",
                    "",
                ),
                "fields": fields,
                "raw_line": line,
            }
        )

    return results


def parse_simulation_output(
    simulation_output: str,
) -> Dict[str, Any]:
    """
    Parse simulation output into a structured result.
    """

    tests = parse_test_results(
        simulation_output
    )

    errors = []

    if simulation_output:

        for line in simulation_output.splitlines():

            match = TEST_ERROR_PATTERN.search(
                line.strip()
            )

            if match:

                errors.append(
                    {
                        "test_id": match.group(
                            1
                        ).strip(),

                        "message": match.group(
                            2
                        ).strip(),

                        "raw_line": line,
                    }
                )

    passed = sum(
        1
        for test in tests
        if test["status"] == "PASSED"
    )

    failed = sum(
        1
        for test in tests
        if test["status"] == "FAILED"
    )

    total = len(tests)

    pass_rate = (
        passed / total * 100
        if total
        else 0.0
    )

    return {
        "tests": tests,
        "errors": errors,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(
            pass_rate,
            2,
        ),
        "simulation_passed": (
            failed == 0
            and len(errors) == 0
        ),
    }


def merge_test_metadata(
    parsed_results: List[Dict[str, Any]],
    metadata: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge parser results with generated test metadata.
    """

    metadata_map = {
        str(item.get("test_id")): item
        for item in metadata
        if isinstance(item, dict)
    }

    merged = []

    for result in parsed_results:

        test_id = str(
            result.get(
                "test_id",
                "",
            )
        )

        combined = dict(
            metadata_map.get(
                test_id,
                {}
            )
        )

        combined.update(
            result
        )

        merged.append(
            combined
        )

    return merged
