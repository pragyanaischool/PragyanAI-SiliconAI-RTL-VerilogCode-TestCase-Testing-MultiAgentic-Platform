"""
PragyanAI SiliconAI
Test Result Parser Unit Tests

Tests:
    verification/test_parser.py

The parser converts simulator/testbench output such as:

    TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0

and:

    TEST_RESULT|TC002|FAIL|input=1|expected=2|actual=1

into structured Python dictionaries.

It also handles:

    TEST_ERROR|TC003|FAIL|message=timeout

The parser must be robust because simulator output is the bridge
between Verilog/SystemVerilog execution and the AI verification graph.
"""

from __future__ import annotations

import os
import sys

import pytest


# ---------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

from verification.test_parser import (
    parse_test_results,
)


# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def parse(output: str):
    """
    Small wrapper so all tests use the same parser entry point.
    """

    result = parse_test_results(
        output
    )

    assert isinstance(
        result,
        list,
    )

    return result


def find_test(
    results,
    test_id,
):
    for item in results:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if str(
            item.get(
                "test_id",
                "",
            )
        ) == test_id:
            return item

    return None


# =====================================================================
# BASIC PASS
# =====================================================================

def test_parse_single_pass_result():
    output = (
        "TEST_RESULT|TC001|PASS|"
        "input=0|expected=0|actual=0"
    )

    results = parse(
        output
    )

    assert len(results) == 1

    test = find_test(
        results,
        "TC001",
    )

    assert test is not None

    assert str(
        test.get(
            "status",
            "",
        )
    ).upper() in {
        "PASS",
        "PASSED",
    }


# =====================================================================
# BASIC FAIL
# =====================================================================

def test_parse_single_fail_result():
    output = (
        "TEST_RESULT|TC002|FAIL|"
        "input=1|expected=2|actual=1"
    )

    results = parse(
        output
    )

    assert len(results) == 1

    test = find_test(
        results,
        "TC002",
    )

    assert test is not None

    assert str(
        test.get(
            "status",
            "",
        )
    ).upper() in {
        "FAIL",
        "FAILED",
    }


# =====================================================================
# MULTIPLE TESTS
# =====================================================================

def test_parse_multiple_test_results():
    output = """
TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0
TEST_RESULT|TC002|PASS|input=1|expected=1|actual=1
TEST_RESULT|TC003|FAIL|input=2|expected=3|actual=2
"""

    results = parse(
        output
    )

    assert len(results) == 3

    assert find_test(
        results,
        "TC001",
    ) is not None

    assert find_test(
        results,
        "TC002",
    ) is not None

    assert find_test(
        results,
        "TC003",
    ) is not None


# =====================================================================
# KEY/VALUE FIELDS
# =====================================================================

def test_parse_key_value_fields():
    output = (
        "TEST_RESULT|TC001|PASS|"
        "input=5|expected=10|actual=10"
    )

    results = parse(
        output
    )

    test = find_test(
        results,
        "TC001",
    )

    assert test is not None

    # Different parser implementations may expose these fields
    # directly or through an evidence/metadata structure.
    combined = str(
        test
    ).lower()

    assert "5" in combined
    assert "10" in combined


# =====================================================================
# ERROR RESULT
# =====================================================================

def test_parse_test_error():
    output = (
        "TEST_ERROR|TC004|FAIL|"
        "message=Expected response was not observed"
    )

    results = parse(
        output
    )

    assert len(results) >= 1

    test = find_test(
        results,
        "TC004",
    )

    assert test is not None

    text = str(
        test
    ).lower()

    assert (
        "fail" in text
        or "error" in text
    )


# =====================================================================
# ERROR WITH SPACES
# =====================================================================

def test_parse_error_message_with_spaces():
    output = (
        "TEST_ERROR|TC005|FAIL|"
        "message=Counter did not reset correctly"
    )

    results = parse(
        output
    )

    assert len(results) >= 1

    test = find_test(
        results,
        "TC005",
    )

    assert test is not None

    assert (
        "counter" in str(
            test
        ).lower()
    )


# =====================================================================
# WHITESPACE
# =====================================================================

def test_parser_handles_leading_and_trailing_whitespace():
    output = """
    
      TEST_RESULT|TC006|PASS|input=0|expected=0|actual=0
    
    """

    results = parse(
        output
    )

    assert len(results) == 1

    assert find_test(
        results,
        "TC006",
    ) is not None


# =====================================================================
# BLANK LINES
# =====================================================================

def test_parser_ignores_blank_lines():
    output = """

TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0


TEST_RESULT|TC002|PASS|input=1|expected=1|actual=1


"""

    results = parse(
        output
    )

    assert len(results) == 2


# =====================================================================
# NORMAL SIMULATOR NOISE
# =====================================================================

def test_parser_ignores_simulator_noise():
    output = """
VCD info: dumpfile waveform.vcd opened for output.
Time: 0 ns
Reset asserted
Time: 10 ns
Reset released

TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0

simulation completed.
"""

    results = parse(
        output
    )

    assert len(results) == 1

    assert find_test(
        results,
        "TC001",
    ) is not None


# =====================================================================
# MIXED PASS AND ERROR
# =====================================================================

def test_parser_handles_mixed_results():
    output = """
TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0
TEST_ERROR|TC002|FAIL|message=timeout
TEST_RESULT|TC003|PASS|input=1|expected=1|actual=1
"""

    results = parse(
        output
    )

    assert len(results) == 3

    tc001 = find_test(
        results,
        "TC001",
    )

    tc002 = find_test(
        results,
        "TC002",
    )

    tc003 = find_test(
        results,
        "TC003",
    )

    assert tc001 is not None
    assert tc002 is not None
    assert tc003 is not None


# =====================================================================
# DUPLICATE TEST IDS
# =====================================================================

def test_parser_handles_duplicate_test_ids():
    """
    Duplicate IDs can happen if a testbench retries a test.

    The parser should not crash.
    """

    output = """
TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0
TEST_RESULT|TC001|FAIL|input=1|expected=1|actual=0
"""

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )

    assert len(results) >= 1


# =====================================================================
# MALFORMED RECORD
# =====================================================================

def test_parser_handles_malformed_record():
    output = """
TEST_RESULT
TEST_RESULT|TC001
TEST_RESULT|TC002|PASS
"""

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )


# =====================================================================
# UNKNOWN STATUS
# =====================================================================

def test_parser_handles_unknown_status():
    output = (
        "TEST_RESULT|TC007|UNKNOWN|"
        "input=1|expected=2|actual=1"
    )

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )

    if results:
        test = find_test(
            results,
            "TC007",
        )

        if test is not None:
            assert isinstance(
                test,
                dict,
            )


# =====================================================================
# SPECIAL CHARACTERS IN VALUES
# =====================================================================

def test_parser_handles_special_characters():
    output = (
        "TEST_RESULT|TC008|FAIL|"
        "input=data[3:0]=1010|"
        "expected=count=10|"
        "actual=count=9"
    )

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )

    test = find_test(
        results,
        "TC008",
    )

    assert test is not None


# =====================================================================
# PIPE INSIDE VALUE
# =====================================================================

def test_parser_does_not_crash_on_extra_pipe():
    output = (
        "TEST_RESULT|TC009|FAIL|"
        "input=a|b|expected=1|actual=0"
    )

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )


# =====================================================================
# EMPTY OUTPUT
# =====================================================================

def test_parser_empty_output():
    results = parse(
        ""
    )

    assert results == []


# =====================================================================
# NONE-LIKE INPUT
# =====================================================================

def test_parser_none_input_does_not_crash():
    """
    Some callers may accidentally pass None.

    If the implementation chooses to raise TypeError instead,
    this test accepts that explicit behavior rather than an
    arbitrary exception.
    """

    try:
        results = parse_test_results(
            None
        )

        assert isinstance(
            results,
            list,
        )

    except (TypeError, AttributeError):
        # Explicitly unsupported input type is acceptable.
        pass


# =====================================================================
# CASE SENSITIVITY
# =====================================================================

def test_parser_handles_lowercase_result_marker():
    output = (
        "test_result|TC010|PASS|"
        "input=0|expected=0|actual=0"
    )

    results = parse(
        output
    )

    assert isinstance(
        results,
        list,
    )


# =====================================================================
# LONG SIMULATOR OUTPUT
# =====================================================================

def test_parser_handles_large_simulator_output():
    noise = "\n".join(
        [
            f"simulation message {i}"
            for i in range(500)
        ]
    )

    output = (
        noise
        + "\n"
        + "TEST_RESULT|TC011|PASS|"
          "input=7|expected=7|actual=7"
        + "\n"
        + noise
    )

    results = parse(
        output
    )

    assert find_test(
        results,
        "TC011",
    ) is not None


# =====================================================================
# PASS/FAIL COUNT
# =====================================================================

def test_parser_results_can_be_counted():
    output = """
TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0
TEST_RESULT|TC002|PASS|input=1|expected=1|actual=1
TEST_RESULT|TC003|FAIL|input=2|expected=3|actual=2
TEST_ERROR|TC004|FAIL|message=timeout
"""

    results = parse(
        output
    )

    statuses = [
        str(
            item.get(
                "status",
                "",
            )
        ).upper()
        for item in results
        if isinstance(item, dict)
    ]

    passed = sum(
        status in {
            "PASS",
            "PASSED",
        }
        for status in statuses
    )

    failed = sum(
        status in {
            "FAIL",
            "FAILED",
            "ERROR",
        }
        for status in statuses
    )

    assert passed >= 2
    assert failed >= 1


# =====================================================================
# SERIALIZATION
# =====================================================================

def test_parser_output_is_json_serializable():
    import json

    output = """
TEST_RESULT|TC001|PASS|input=0|expected=0|actual=0
TEST_ERROR|TC002|FAIL|message=timeout
"""

    results = parse(
        output
    )

    try:
        json.dumps(
            results
        )
    except TypeError as exc:
        pytest.fail(
            f"Parser output is not JSON serializable: {exc}"
        )


# =====================================================================
# EXPECTED MACHINE-READABLE CONTRACT
# =====================================================================

def test_parser_preserves_test_id():
    output = (
        "TEST_RESULT|TC123|PASS|"
        "input=15|expected=15|actual=15"
    )

    results = parse(
        output
    )

    test = find_test(
        results,
        "TC123",
    )

    assert test is not None


def test_parser_handles_multiple_key_value_pairs():
    output = (
        "TEST_RESULT|TC124|PASS|"
        "clk=10|rst_n=1|en=1|"
        "expected=5|actual=5"
    )

    results = parse(
        output
    )

    test = find_test(
        results,
        "TC124",
    )

    assert test is not None


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    pytest.main(
        [
            "-v",
            __file__,
        ]
    )
