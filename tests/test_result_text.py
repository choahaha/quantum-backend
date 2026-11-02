"""
Tests for the result text returned by "get result" and read back by the histogram.

Run from the quantum-backend directory:
    venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

from executor import QuantumExecutor, create_histogram, parse_text_result


def create(num_qubits):
    return {"opcode": "quantum_createCircuit", "args": {"NUM_QUBITS": num_qubits}}


def x(qubit):
    return {"opcode": "quantum_gateX", "args": {"QUBIT": qubit}}


MEASURE = {"opcode": "quantum_measureAll", "args": {}}


class ResultTextTest(unittest.TestCase):
    def test_single_qubit_uses_state_label(self):
        result = QuantumExecutor().execute([create(1), x(0), MEASURE], 10)
        self.assertEqual(result["result_text"], "state 1: 10 (100.0%)")

    def test_multi_qubit_keeps_qiskit_bit_order(self):
        result = QuantumExecutor().execute([create(2), x(0), MEASURE], 10)
        self.assertEqual(result["result_text"], "state 01: 10 (100.0%)")

    def test_two_outcomes_sorted_by_count(self):
        text = QuantumExecutor()._format_result({"0": 3, "1": 7}, 10)
        self.assertEqual(text, "state 1: 7 (70.0%), state 0: 3 (30.0%)")


class ParseResultTextTest(unittest.TestCase):
    def test_parses_state_format(self):
        self.assertEqual(parse_text_result("state 1: 525 (52.5%), state 0: 475 (47.5%)"),
                         {"1": 525, "0": 475})

    def test_parses_older_ket_format(self):
        self.assertEqual(parse_text_result("|01>: 512 (50.0%), |10>: 512 (50.0%)"),
                         {"01": 512, "10": 512})

    def test_histogram_accepts_both_formats(self):
        for text in ("state 1: 6 (60.0%), state 0: 4 (40.0%)", "|1>: 6 (60.0%), |0>: 4 (40.0%)"):
            with self.subTest(text=text):
                self.assertTrue(create_histogram(text).startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
