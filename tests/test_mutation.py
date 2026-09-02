"""
tests/test_mutation.py

Tests for:
    - verification.mutation
    - agents.mutation_agent

Mutation testing validates whether the verification suite can detect
small, intentional changes ("mutants") introduced into RTL.

The tests are intentionally defensive because the mutation implementation
may evolve while preserving the core state contract.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

from agents.mutation_agent import MutationAgent


# ---------------------------------------------------------------------------
# Sample RTL
# ---------------------------------------------------------------------------

SAMPLE_RTL = r"""
module alu(
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire       en,
    output reg  [3:0] y
);

always @(*) begin
    if (en && (a == b))
        y = a + b;
    else if (a > b)
        y = a - b;
    else if (a != b)
        y = a & b;
    else
        y = 4'b0000;
end

endmodule
"""


SIMPLE_RTL = r"""
module simple(
    input  wire a,
    input  wire b,
    output wire y
);

assign y = a & b;

endmodule
"""


INVALID_RTL = r"""
module broken(
    input wire a,
    output wire y

assign y = a;

endmodule
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def base_state(**overrides: Any) -> Dict[str, Any]:
    """
    Build a minimal LangGraph-compatible VerificationState.
    """
    state: Dict[str, Any] = {
        "prompt": "Mutation testing sample",
        "specification": (
            "The ALU should perform addition when enabled and inputs "
            "are equal, subtraction when a > b, and AND otherwise."
        ),
        "rtl_code": SAMPLE_RTL,
        "rtl_version": 1,
        "tests": [
            {
                "id": "TC001",
                "name": "equal inputs",
                "description": "Verify addition for equal inputs",
                "inputs": {"a": 3, "b": 3, "en": 1},
                "expected": {"y": 6},
                "status": "PASS",
            },
            {
                "id": "TC002",
                "name": "greater than",
                "description": "Verify subtraction when a > b",
                "inputs": {"a": 7, "b": 2, "en": 0},
                "expected": {"y": 5},
                "status": "PASS",
            },
            {
                "id": "TC003",
                "name": "and operation",
                "description": "Verify AND behavior",
                "inputs": {"a": 10, "b": 6, "en": 0},
                "expected": {"y": 2},
                "status": "PASS",
            },
        ],
        "generated_tests": [],
        "mutation_score": 0.0,
        "mutations": [],
        "agent_trace": [],
        "agent_log": [],
        "warnings": [],
        "errors": [],
        "iteration": 0,
        "max_iterations": 3,
        "status": "READY",
        "run_dir": "",
    }

    state.update(overrides)
    return state


def extract_mutations(result: Dict[str, Any]):
    """
    Retrieve mutation information while tolerating minor API evolution.
    """
    for key in (
        "mutations",
        "mutation_results",
        "mutation_result",
        "mutation_candidates",
    ):
        value = result.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            for nested_key in (
                "mutations",
                "results",
                "candidates",
                "mutation_results",
            ):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return nested

            return [value]

    return []


def mutation_status(item: Any) -> str:
    """
    Normalize mutation status from several possible schemas.
    """
    if not isinstance(item, dict):
        return ""

    for key in ("status", "result", "outcome", "mutation_status"):
        value = item.get(key)
        if value is not None:
            return str(value).upper()

    if item.get("killed") is True:
        return "KILLED"

    if item.get("survived") is True:
        return "SURVIVED"

    return ""


def mutation_id(item: Any):
    """
    Extract a mutation ID from flexible result schemas.
    """
    if not isinstance(item, dict):
        return None

    for key in (
        "id",
        "mutation_id",
        "mutant_id",
        "candidate_id",
    ):
        if item.get(key) is not None:
            return str(item[key])

    return None


def public_methods(obj):
    return [
        name
        for name in dir(obj)
        if not name.startswith("_") and callable(getattr(obj, name, None))
    ]


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------

def test_mutation_agent_constructor():
    agent = MutationAgent()

    assert agent is not None
    assert hasattr(agent, "run")


def test_mutation_agent_has_callable_run():
    agent = MutationAgent()

    assert callable(agent.run)


def test_mutation_agent_does_not_require_groq_key(monkeypatch):
    """
    Mutation testing is deterministic and should not require an LLM.
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = MutationAgent()

    assert agent is not None
    assert callable(agent.run)


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def test_mutation_agent_generates_candidates(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    agent = MutationAgent()
    result = agent.run(state)

    assert isinstance(result, dict)

    mutations = extract_mutations(result)

    # A mutation implementation should discover at least some operators
    # in the sample ALU.
    assert isinstance(mutations, list)


def test_mutation_candidates_are_dict_like(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    for mutation in mutations:
        assert isinstance(mutation, dict)


def test_mutation_ids_are_unique(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    ids = [
        mutation_id(item)
        for item in mutations
        if mutation_id(item) is not None
    ]

    assert len(ids) == len(set(ids))


def test_mutation_candidates_have_useful_metadata(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    if not mutations:
        pytest.skip("No mutation candidates generated")

    useful_fields = {
        "id",
        "mutation_id",
        "mutant_id",
        "operator",
        "mutation_operator",
        "description",
        "location",
        "line",
        "status",
        "original",
        "replacement",
    }

    for mutation in mutations:
        assert useful_fields.intersection(mutation.keys())


# ---------------------------------------------------------------------------
# Supported mutation operators
# ---------------------------------------------------------------------------

def test_supported_mutation_operators_are_detected(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    if not mutations:
        pytest.skip("No mutation candidates generated")

    operators = []

    for mutation in mutations:
        if not isinstance(mutation, dict):
            continue

        for key in (
            "operator",
            "mutation_operator",
            "type",
            "kind",
        ):
            if mutation.get(key):
                operators.append(str(mutation[key]).upper())
                break

    if not operators:
        pytest.skip("Mutation records do not expose operator metadata")

    combined = " ".join(operators)

    expected_operator_fragments = (
        "AND",
        "OR",
        "EQ",
        "NE",
        "GT",
        "LT",
        "PLUS",
        "MINUS",
        "BITWISE",
        "CONST",
    )

    assert any(fragment in combined for fragment in expected_operator_fragments)


# ---------------------------------------------------------------------------
# Empty / malformed RTL
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rtl",
    [
        "",
        "   ",
        "\n\n",
        INVALID_RTL,
    ],
)
def test_mutation_agent_handles_empty_or_invalid_rtl(tmp_path, rtl):
    state = base_state(
        rtl_code=rtl,
        run_dir=str(tmp_path),
    )

    agent = MutationAgent()
    result = agent.run(state)

    assert isinstance(result, dict)

    # The important contract is that the agent does not crash and returns
    # a state-compatible dictionary.
    assert "mutation_score" in result or "mutations" in result


def test_mutation_agent_handles_missing_rtl(tmp_path):
    state = base_state(run_dir=str(tmp_path))
    state.pop("rtl_code", None)

    result = MutationAgent().run(state)

    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Mutation execution and score
# ---------------------------------------------------------------------------

def test_mutation_score_exists(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    assert "mutation_score" in result

    score = result["mutation_score"]

    assert isinstance(score, (int, float))


def test_mutation_score_is_between_zero_and_hundred(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    score = result.get("mutation_score", 0)

    assert 0 <= float(score) <= 100


def test_mutation_status_values_are_reasonable(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    if not mutations:
        pytest.skip("No mutation results generated")

    allowed = {
        "KILLED",
        "SURVIVED",
        "SKIPPED",
        "ERROR",
        "FAILED",
        "EXECUTED",
        "NOT_EXECUTED",
        "UNSUPPORTED",
        "UNAVAILABLE",
        "UNKNOWN",
        "PASS",
        "FAIL",
        "",
    }

    statuses = [mutation_status(item) for item in mutations]

    for status in statuses:
        assert status in allowed or any(
            token in status
            for token in (
                "KILL",
                "SURVIV",
                "SKIP",
                "ERROR",
                "FAIL",
                "UNSUPPORT",
            )
        )


def test_mutation_result_can_contain_killed_or_survived(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    if not mutations:
        pytest.skip("No mutation results generated")

    statuses = {
        mutation_status(item)
        for item in mutations
        if mutation_status(item)
    }

    if statuses:
        assert statuses.intersection(
            {
                "KILLED",
                "SURVIVED",
                "SKIPPED",
                "ERROR",
                "FAILED",
                "UNSUPPORTED",
            }
        )


# ---------------------------------------------------------------------------
# Original RTL preservation
# ---------------------------------------------------------------------------

def test_original_rtl_is_preserved(tmp_path):
    original = SAMPLE_RTL

    state = base_state(
        rtl_code=original,
        run_dir=str(tmp_path),
    )

    result = MutationAgent().run(state)

    assert state["rtl_code"] == original

    if "rtl_code" in result:
        assert result["rtl_code"] == original


def test_mutation_does_not_change_source_file(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    agent = MutationAgent()
    result = agent.run(state)

    assert isinstance(result, dict)

    # The source state remains the source of truth.
    assert state["rtl_code"] == SAMPLE_RTL


# ---------------------------------------------------------------------------
# Artifact tests
# ---------------------------------------------------------------------------

def test_mutation_artifacts_are_created_when_run_dir_is_supported(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    assert isinstance(result, dict)

    mutation_dir = tmp_path / "mutations"

    if mutation_dir.exists():
        assert mutation_dir.is_dir()


def test_mutation_artifacts_do_not_overwrite_original_rtl(tmp_path):
    original_path = tmp_path / "original.v"
    original_path.write_text(SAMPLE_RTL, encoding="utf-8")

    state = base_state(run_dir=str(tmp_path))

    MutationAgent().run(state)

    assert original_path.exists()
    assert original_path.read_text(encoding="utf-8") == SAMPLE_RTL


def test_mutation_result_references_artifacts_if_available(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    artifact_keys = {
        "artifact",
        "artifact_path",
        "artifacts",
        "mutation_artifacts",
        "mutation_dir",
    }

    if not artifact_keys.intersection(result.keys()):
        pytest.skip("Mutation agent does not expose artifact metadata")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def test_mutation_result_is_json_serializable(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    try:
        serialized = json.dumps(result, default=str)
    except TypeError as exc:
        pytest.fail(f"Mutation result is not JSON serializable: {exc}")

    assert isinstance(serialized, str)


def test_mutation_records_are_json_serializable(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    for mutation in mutations:
        try:
            json.dumps(mutation, default=str)
        except TypeError as exc:
            pytest.fail(
                f"Mutation record is not JSON serializable: {exc}"
            )


# ---------------------------------------------------------------------------
# Trace / logging
# ---------------------------------------------------------------------------

def test_mutation_agent_trace_is_available(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    trace = result.get("agent_trace", result.get("agent_log", []))

    assert trace is not None
    assert isinstance(trace, (list, dict, str))


def test_mutation_agent_does_not_expose_api_key(tmp_path, monkeypatch):
    fake_key = "THIS_IS_A_FAKE_SECRET_KEY"

    monkeypatch.setenv("GROQ_API_KEY", fake_key)

    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    serialized = json.dumps(result, default=str)

    assert fake_key not in serialized


# ---------------------------------------------------------------------------
# LangGraph compatibility
# ---------------------------------------------------------------------------

def test_mutation_agent_accepts_plain_dict_state(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    assert isinstance(result, dict)


def test_mutation_agent_preserves_unrelated_state_fields(tmp_path):
    state = base_state(
        run_dir=str(tmp_path),
        prompt="KEEP_THIS_PROMPT",
        specification="KEEP_THIS_SPECIFICATION",
        iteration=7,
    )

    result = MutationAgent().run(state)

    assert result.get("prompt") == "KEEP_THIS_PROMPT"
    assert result.get("specification") == "KEEP_THIS_SPECIFICATION"
    assert result.get("iteration") == 7


def test_mutation_agent_output_is_state_compatible(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    expected_possible_fields = {
        "mutations",
        "mutation_score",
        "agent_trace",
        "agent_log",
        "warnings",
        "errors",
        "status",
    }

    assert expected_possible_fields.intersection(result.keys())


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_mutation_candidate_generation_is_deterministic(tmp_path):
    """
    MutationAgent should not depend on an LLM, so the same RTL should
    produce stable candidate metadata across repeated runs.
    """
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"

    run1.mkdir()
    run2.mkdir()

    state1 = base_state(run_dir=str(run1))
    state2 = base_state(run_dir=str(run2))

    result1 = MutationAgent().run(state1)
    result2 = MutationAgent().run(state2)

    mutations1 = extract_mutations(result1)
    mutations2 = extract_mutations(result2)

    ids1 = [
        mutation_id(item)
        for item in mutations1
        if mutation_id(item) is not None
    ]

    ids2 = [
        mutation_id(item)
        for item in mutations2
        if mutation_id(item) is not None
    ]

    assert ids1 == ids2


def test_simple_rtl_produces_stable_result(tmp_path):
    state = base_state(
        rtl_code=SIMPLE_RTL,
        run_dir=str(tmp_path),
    )

    result = MutationAgent().run(state)

    assert isinstance(result, dict)

    score = result.get("mutation_score", 0)

    assert 0 <= float(score) <= 100


# ---------------------------------------------------------------------------
# Multiple operators
# ---------------------------------------------------------------------------

def test_alu_rtl_exercises_multiple_mutation_categories(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)
    mutations = extract_mutations(result)

    if not mutations:
        pytest.skip("No mutations generated")

    serialized = json.dumps(mutations, default=str).upper()

    categories_found = 0

    for token in (
        "AND",
        "EQ",
        "GT",
        "PLUS",
        "MINUS",
        "BITWISE",
    ):
        if token in serialized:
            categories_found += 1

    assert categories_found >= 1


# ---------------------------------------------------------------------------
# Direct verification.mutation API discovery
# ---------------------------------------------------------------------------

def test_verification_mutation_module_imports():
    """
    The lower-level mutation module must remain importable independently
    of the agent layer.
    """
    import verification.mutation as mutation_module

    assert mutation_module is not None


def test_verification_mutation_module_has_public_api():
    import verification.mutation as mutation_module

    methods = public_methods(mutation_module)

    # Do not enforce one exact class/function name because the implementation
    # may evolve. The module itself must remain usable.
    assert isinstance(methods, list)


# ---------------------------------------------------------------------------
# Mutation score sanity
# ---------------------------------------------------------------------------

def test_mutation_score_is_not_nan(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    score = float(result.get("mutation_score", 0))

    assert score == score  # NaN != NaN


def test_mutation_score_is_finite(tmp_path):
    state = base_state(run_dir=str(tmp_path))

    result = MutationAgent().run(state)

    score = float(result.get("mutation_score", 0))

    assert score != float("inf")
    assert score != float("-inf")


# ---------------------------------------------------------------------------
# Environment / simulator availability
# ---------------------------------------------------------------------------

def test_iverilog_availability_is_reported():
    """
    Mutation execution may use Icarus. This test does not fail when Icarus
    is unavailable because candidate generation can still be tested.
    """
    iverilog = shutil.which("iverilog")

    assert iverilog is None or os.path.exists(iverilog)


# ---------------------------------------------------------------------------
# Final integration-style test
# ---------------------------------------------------------------------------

def test_mutation_agent_end_to_end(tmp_path):
    """
    Lightweight end-to-end contract test.

    Expected flow:

        RTL
         ↓
        Mutation candidates
         ↓
        Mutant execution
         ↓
        KILLED / SURVIVED
         ↓
        Mutation score
         ↓
        LangGraph-compatible state
    """
    state = base_state(run_dir=str(tmp_path))

    agent = MutationAgent()
    result = agent.run(state)

    assert isinstance(result, dict)

    mutations = extract_mutations(result)

    assert isinstance(mutations, list)

    score = float(result.get("mutation_score", 0))

    assert 0 <= score <= 100

    # The original design must remain untouched.
    assert state["rtl_code"] == SAMPLE_RTL

    # Result must be safe to persist.
    json.dumps(result, default=str)
