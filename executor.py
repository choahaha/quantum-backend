"""
Quantum Circuit Executor
Converts Scratch blocks to Qiskit code and executes
"""

import time
from typing import List, Dict, Any

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import Aer
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


class QuantumExecutor:
    """Execute quantum circuits from block data"""

    # Limits
    MAX_QUBITS = 10
    MAX_GATES = 100
    MAX_SHOTS = 10000

    def __init__(self):
        self.circuit = None
        self.num_qubits = 0

    def is_available(self) -> bool:
        return QISKIT_AVAILABLE

    def execute(self, blocks: List[Dict[str, Any]], shots: int = 1024) -> Dict:
        """Execute blocks and return result"""

        if not QISKIT_AVAILABLE:
            return {
                "success": False,
                "error": "Qiskit is not installed",
                "counts": None,
                "result_text": None,
                "execution_time": 0
            }

        start_time = time.time()

        try:
            # Validate
            self._validate_blocks(blocks)

            # Build circuit
            self._build_circuit(blocks)

            if self.circuit is None:
                return {
                    "success": False,
                    "error": "No quantum circuit created. Use 'quantum_createCircuit' block first.",
                    "counts": None,
                    "result_text": None,
                    "execution_time": 0
                }

            # Execute
            simulator = Aer.get_backend('aer_simulator')
            job = simulator.run(self.circuit, shots=min(shots, self.MAX_SHOTS))
            result = job.result()
            counts = result.get_counts()

            execution_time = time.time() - start_time

            # Format result text
            result_text = self._format_result(counts, shots)

            return {
                "success": True,
                "counts": counts,
                "result_text": result_text,
                "error": None,
                "execution_time": execution_time
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "counts": None,
                "result_text": None,
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "counts": None,
                "result_text": None,
                "execution_time": time.time() - start_time
            }

    def _validate_blocks(self, blocks: List[Dict]) -> None:
        """Validate block data"""
        gate_count = 0

        for block in blocks:
            opcode = block.get('opcode', '')

            if opcode == 'quantum_createCircuit':
                num_qubits = int(block.get('args', {}).get('NUM_QUBITS', 1))
                if num_qubits > self.MAX_QUBITS:
                    raise ValueError(f"Maximum {self.MAX_QUBITS} qubits allowed")

            if opcode.startswith('quantum_gate'):
                gate_count += 1

        if gate_count > self.MAX_GATES:
            raise ValueError(f"Maximum {self.MAX_GATES} gates allowed")

    def _build_circuit(self, blocks: List[Dict]) -> None:
        """Build quantum circuit from blocks"""
        self.circuit = None

        for block in blocks:
            opcode = block.get('opcode', '')
            args = block.get('args', {})

            if opcode == 'quantum_createCircuit':
                self.num_qubits = int(args.get('NUM_QUBITS', 1))
                self.circuit = QuantumCircuit(self.num_qubits)

            elif self.circuit is not None:
                self._apply_gate(opcode, args)

    def _apply_gate(self, opcode: str, args: Dict) -> None:
        """Apply a gate to the circuit"""
        if opcode == 'quantum_gateH':
            qubit = int(args.get('QUBIT', 0))
            self._validate_qubit(qubit)
            self.circuit.h(qubit)

        elif opcode == 'quantum_gateX':
            qubit = int(args.get('QUBIT', 0))
            self._validate_qubit(qubit)
            self.circuit.x(qubit)

        elif opcode == 'quantum_gateY':
            qubit = int(args.get('QUBIT', 0))
            self._validate_qubit(qubit)
            self.circuit.y(qubit)

        elif opcode == 'quantum_gateZ':
            qubit = int(args.get('QUBIT', 0))
            self._validate_qubit(qubit)
            self.circuit.z(qubit)

        elif opcode == 'quantum_gateCX':
            control = int(args.get('CONTROL', 0))
            target = int(args.get('TARGET', 1))
            self._validate_qubit(control)
            self._validate_qubit(target)
            if control == target:
                raise ValueError("Control and target qubits must be different")
            self.circuit.cx(control, target)

        elif opcode == 'quantum_measureAll':
            self.circuit.measure_all()

    def _validate_qubit(self, qubit: int) -> None:
        """Validate qubit index"""
        if qubit < 0 or qubit >= self.num_qubits:
            raise ValueError(f"Qubit {qubit} out of range (0-{self.num_qubits-1})")

    def _format_result(self, counts: Dict[str, int], total_shots: int) -> str:
        """Format counts to readable text"""
        if not counts:
            return "No results"

        # Sort by count descending
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        # Format each state
        parts = []
        for state, count in sorted_counts[:5]:  # Top 5 results
            percentage = (count / total_shots) * 100
            parts.append(f"|{state}>: {count} ({percentage:.1f}%)")

        return ", ".join(parts)
