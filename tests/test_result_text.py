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
    def test_single_qubit_lists_state_and_count(self):
        result = QuantumExecutor().execute([create(1), x(0), MEASURE], 10)
        self.assertEqual(result["result_text"], "state 1: 10")

    def test_multi_qubit_keeps_qiskit_bit_order(self):
        result = QuantumExecutor().execute([create(2), x(0), MEASURE], 10)
        self.assertEqual(result["result_text"], "state 01: 10")

    def test_two_outcomes_listed_in_state_order(self):
        text = QuantumExecutor()._format_result({"1": 7, "0": 3}, 10)
        self.assertEqual(text, "state 0: 3, state 1: 7")

    def test_korean_uses_beon(self):
        text = QuantumExecutor("ko")._format_result({"1": 7, "0": 3}, 10)
        self.assertEqual(text, "0: 3번, 1: 7번")

    def test_keeps_five_most_frequent_states(self):
        counts = {"000": 1, "001": 9, "010": 8, "011": 7, "100": 6, "101": 5, "110": 2}
        text = QuantumExecutor()._format_result(counts, 38)
        self.assertEqual(text, "state 001: 9, state 010: 8, state 011: 7, state 100: 6, state 101: 5")


class ParseResultTextTest(unittest.TestCase):
    def test_parses_state_format(self):
        self.assertEqual(parse_text_result("state 1: 525 (52.5%), state 0: 475 (47.5%)"),
                         {"1": 525, "0": 475})

    def test_parses_older_ket_format(self):
        self.assertEqual(parse_text_result("|01>: 512 (50.0%), |10>: 512 (50.0%)"),
                         {"01": 512, "10": 512})

    def test_parses_get_counts_format(self):
        self.assertEqual(parse_text_result("0: 49, 1: 51"), {"0": 49, "1": 51})
        self.assertEqual(parse_text_result("00: 251, 11: 249"), {"00": 251, "11": 249})

    def test_parses_get_result_format(self):
        self.assertEqual(parse_text_result("state 0: 49, state 1: 51"), {"0": 49, "1": 51})
        self.assertEqual(parse_text_result("0: 49번, 1: 51번"), {"0": 49, "1": 51})

    def test_histogram_accepts_all_formats(self):
        for text in ("state 1: 6 (60.0%), state 0: 4 (40.0%)", "|1>: 6 (60.0%), |0>: 4 (40.0%)",
                     "0: 4, 1: 6", "state 0: 4, state 1: 6", "0: 4번, 1: 6번"):
            with self.subTest(text=text):
                self.assertTrue(create_histogram(text).startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
