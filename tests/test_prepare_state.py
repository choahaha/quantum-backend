"""
Tests for the quantum_prepareState block (state preparation at circuit start).

Run from the quantum-backend directory:
    venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

from qiskit.quantum_info import Statevector

from executor import QuantumExecutor, create_circuit_diagram

SHOTS = 200


def create(num_qubits):
    return {"opcode": "quantum_createCircuit", "args": {"NUM_QUBITS": num_qubits}}


def prepare(qubit, state):
    return {"opcode": "quantum_prepareState", "args": {"QUBIT": qubit, "STATE": state}}


def gate(name, qubit):
    return {"opcode": f"quantum_gate{name}", "args": {"QUBIT": qubit}}


MEASURE = {"opcode": "quantum_measureAll", "args": {}}


def run(blocks, shots=SHOTS, locale="en"):
    return QuantumExecutor(locale).execute(blocks, shots)


class PrepareStateResultsTest(unittest.TestCase):
    def assert_always(self, blocks, outcome):
        result = run(blocks)
        self.assertTrue(result["success"], result["error"])
        self.assertEqual(result["counts"], {outcome: SHOTS})

    def test_prepare_0_measures_0(self):
        self.assert_always([create(1), prepare(0, 0), MEASURE], "0")

    def test_prepare_1_measures_1(self):
        self.assert_always([create(1), prepare(0, 1), MEASURE], "1")

    def test_prepare_1_then_x_measures_0(self):
        self.assert_always([create(1), prepare(0, 1), gate("X", 0), MEASURE], "0")

    def test_two_qubits_q0_1_q1_0_reads_01(self):
        # Qiskit bit strings put qubit 0 on the right
        self.assert_always([create(2), prepare(0, 1), prepare(1, 0), MEASURE], "01")

    def test_string_values_from_the_vm_are_accepted(self):
        self.assert_always([create(1), prepare("0", "1"), MEASURE], "1")

    def test_prepare_0_then_h_is_an_even_superposition(self):
        # Check the ideal probabilities instead of finite-shot counts (no flaky 50:50).
        executor = QuantumExecutor()
        executor._build_circuit([create(1), prepare(0, 0), gate("H", 0)])
        probabilities = Statevector(executor.circuit).probabilities_dict()
        self.assertAlmostEqual(probabilities["0"], 0.5)
        self.assertAlmostEqual(probabilities["1"], 0.5)

        result = run([create(1), prepare(0, 0), gate("H", 0), MEASURE], shots=1000)
        self.assertTrue(result["success"], result["error"])
        self.assertEqual(set(result["counts"]), {"0", "1"})

    def test_unprepared_qubits_start_in_0(self):
        self.assert_always([create(2), prepare(1, 1), MEASURE], "10")

    def test_circuit_without_prepare_still_works(self):
        self.assert_always([create(1), gate("X", 0), MEASURE], "1")
        self.assert_always([create(2), gate("X", 1), MEASURE], "10")

    def test_new_circuit_resets_preparation(self):
        # The second circuit may prepare qubit 0 again, and its result has no trace of the first.
        self.assert_always(
            [create(1), prepare(0, 1), gate("H", 0), create(1), prepare(0, 0), MEASURE], "0")


class PrepareStateCircuitTest(unittest.TestCase):
    def build(self, blocks):
        executor = QuantumExecutor()
        executor._build_circuit(blocks)
        return executor.circuit

    def test_prepare_0_adds_no_gate(self):
        self.assertEqual(dict(self.build([create(1), prepare(0, 0)]).count_ops()), {})

    def test_prepare_1_adds_one_x(self):
        self.assertEqual(dict(self.build([create(2), prepare(1, 1)]).count_ops()), {"x": 1})

    def test_circuit_diagram_draws_prepared_circuit(self):
        image = create_circuit_diagram([create(2), prepare(0, 1), prepare(1, 0), gate("H", 1), MEASURE])
        self.assertTrue(image.startswith("data:image/png;base64,"))


class PrepareStateValidationTest(unittest.TestCase):
    def assert_error(self, blocks, expected, locale="en"):
        result = run(blocks, locale=locale)
        self.assertFalse(result["success"])
        self.assertIsNone(result["counts"])
        self.assertIn(expected, result["error"])

    def test_prepare_before_circuit(self):
        self.assert_error([prepare(0, 1), create(1), MEASURE], "create a circuit")

    def test_duplicate_prepare_same_state(self):
        self.assert_error([create(1), prepare(0, 1), prepare(0, 1), MEASURE], "already prepared")

    def test_duplicate_prepare_different_state(self):
        self.assert_error([create(1), prepare(0, 0), prepare(0, 1), MEASURE], "already prepared")

    def test_prepare_after_gate(self):
        self.assert_error([create(2), gate("H", 0), prepare(1, 1), MEASURE], "before any gate")

    def test_prepare_after_measure(self):
        self.assert_error([create(1), MEASURE, prepare(0, 1)], "before any gate")

    def test_prepare_after_cx(self):
        cx = {"opcode": "quantum_gateCX", "args": {"CONTROL": 0, "TARGET": 1}}
        self.assert_error([create(3), cx, prepare(2, 1), MEASURE], "before any gate")

    def test_bad_qubit_numbers(self):
        for qubit in (-1, 2, 1.5, "1.5", "abc", "", None, True):
            with self.subTest(qubit=qubit):
                self.assert_error([create(2), prepare(qubit, 1), MEASURE], "not in this circuit")

    def test_bad_states(self):
        for state in (2, -1, "2", "x", "", None, 0.5, True):
            with self.subTest(state=state):
                self.assert_error([create(1), prepare(0, state), MEASURE], "must be 0 or 1")

    def test_korean_messages(self):
        self.assert_error([create(1), prepare(0, 1), prepare(0, 1), MEASURE], "이미 준비했어요", locale="ko")
        self.assert_error([create(1), gate("H", 0), prepare(0, 1)], "게이트와 측정 블록보다 앞에", locale="ko")
        self.assert_error([prepare(0, 1)], "먼저 회로 만들기 블록을", locale="ko")
        self.assert_error([create(1), prepare(3, 1)], "회로에 없는 큐비트 번호예요", locale="ko")

    def test_circuit_diagram_rejects_invalid_prepare(self):
        with self.assertRaises(ValueError):
            create_circuit_diagram([create(1), gate("H", 0), prepare(0, 1)])


if __name__ == "__main__":
    unittest.main()
