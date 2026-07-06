"""
Declarative mission grader.

grading_spec (missions.grading_spec, version 1):
{
  "version": 1,
  "pass_policy": "all",
  "checks": [
    {"id": "q",    "type": "num_qubits", "equals": 2},            # or "min"/"max"
    {"id": "used", "type": "blocks_used",
     "opcodes": [{"opcode": "quantum_gateH", "min_count": 1}]},
    {"id": "no_x", "type": "blocks_forbidden", "opcodes": ["quantum_gateX"]},
    {"id": "dist", "type": "counts_distribution", "shots": 2048,
     "expected": {"00": 0.5, "11": 0.5}, "tolerance": 0.1, "other_max": 0.02}
  ]
}
Each check may carry "feedback_fail" (shown to the student on failure).

Counts are never taken from the client: counts_distribution re-executes
the submitted blocks with QuantumExecutor. Unknown check types fail
closed so an out-of-date grader rejects loudly instead of passing.
"""

from typing import Any, Dict, List

from executor import QuantumExecutor

DEFAULT_SHOTS = 2048
DEFAULT_OTHER_MAX = 0.02


def _count_opcodes(blocks: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for block in blocks:
        opcode = block.get("opcode", "")
        counts[opcode] = counts.get(opcode, 0) + 1
    return counts


def _get_num_qubits(blocks: List[Dict]) -> int:
    for block in blocks:
        if block.get("opcode") == "quantum_createCircuit":
            try:
                return int(block.get("args", {}).get("NUM_QUBITS", 0))
            except (TypeError, ValueError):
                return 0
    return 0


def _check_num_qubits(blocks: List[Dict], check: Dict, _ctx: Dict) -> bool:
    num = _get_num_qubits(blocks)
    if "equals" in check and num != int(check["equals"]):
        return False
    if "min" in check and num < int(check["min"]):
        return False
    if "max" in check and num > int(check["max"]):
        return False
    return num > 0


def _check_blocks_used(blocks: List[Dict], check: Dict, _ctx: Dict) -> bool:
    opcode_counts = _count_opcodes(blocks)
    for requirement in check.get("opcodes", []):
        opcode = requirement.get("opcode", "")
        min_count = int(requirement.get("min_count", 1))
        if opcode_counts.get(opcode, 0) < min_count:
            return False
    return True


def _check_blocks_forbidden(blocks: List[Dict], check: Dict, _ctx: Dict) -> bool:
    opcode_counts = _count_opcodes(blocks)
    return not any(opcode_counts.get(opcode, 0) > 0 for opcode in check.get("opcodes", []))


def _check_counts_distribution(blocks: List[Dict], check: Dict, ctx: Dict) -> bool:
    opcode_counts = _count_opcodes(blocks)
    if opcode_counts.get("quantum_measureAll", 0) == 0:
        return False

    shots = int(check.get("shots", DEFAULT_SHOTS))
    result = QuantumExecutor().execute(blocks, shots)
    if not result.get("success"):
        ctx["error"] = result.get("error")
        return False

    counts = result.get("counts") or {}
    ctx["counts"] = counts
    total = sum(counts.values())
    if total == 0:
        return False

    expected: Dict[str, float] = check.get("expected", {})
    tolerance = float(check.get("tolerance", 0.05))
    other_max = float(check.get("other_max", DEFAULT_OTHER_MAX))

    for state, probability in expected.items():
        observed = counts.get(state, 0) / total
        if abs(observed - float(probability)) > tolerance:
            return False

    for state, count in counts.items():
        if state not in expected and count / total > other_max:
            return False

    return True


CHECKERS = {
    "num_qubits": _check_num_qubits,
    "blocks_used": _check_blocks_used,
    "blocks_forbidden": _check_blocks_forbidden,
    "counts_distribution": _check_counts_distribution,
}


def grade(blocks: List[Dict], spec: Dict) -> Dict[str, Any]:
    """Grade submitted blocks against a grading_spec.

    Returns {"passed": bool, "checks": [{id, type, passed, feedback}], "counts": dict|None}.
    """
    check_results = []
    counts: Any = None

    for check in spec.get("checks", []):
        check_type = check.get("type", "")
        checker = CHECKERS.get(check_type)
        ctx: Dict[str, Any] = {}

        if checker is None:
            # Fail closed: an unknown check type means grader and seed are
            # out of sync — reject loudly instead of silently passing.
            passed = False
            feedback = f"지원하지 않는 채점 규칙입니다: {check_type}"
        else:
            try:
                passed = checker(blocks, check, ctx)
            except Exception as e:  # malformed spec or circuit
                passed = False
                ctx["error"] = str(e)
            feedback = "" if passed else check.get("feedback_fail", "조건을 만족하지 못했어요.")
            if not passed and ctx.get("error"):
                feedback = f"{feedback} ({ctx['error']})"

        if ctx.get("counts") is not None:
            counts = ctx["counts"]

        check_results.append({
            "id": check.get("id", check_type),
            "type": check_type,
            "passed": passed,
            "feedback": feedback,
        })

    return {
        "passed": all(r["passed"] for r in check_results) and bool(check_results),
        "checks": check_results,
        "counts": counts,
    }
