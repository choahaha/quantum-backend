"""
Quantum Circuit Executor
Converts Scratch blocks to Qiskit code and executes
"""

import time
import json
import base64
from io import BytesIO
from typing import List, Dict, Any

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import Aer
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-GUI backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def parse_text_result(text: str) -> dict:
    """Parse text format like '|1>: 525 (52.5%), |0>: 475 (47.5%)' to counts dict"""
    import re
    counts = {}
    # Match patterns like |1>: 525 or |01>: 512
    pattern = r'\|([01]+)>:\s*(\d+)'
    matches = re.findall(pattern, text)
    for state, count in matches:
        counts[state] = int(count)
    return counts


def create_histogram(data_str: str) -> str:
    """Create histogram image from quantum counts data"""
    if not MATPLOTLIB_AVAILABLE:
        raise ValueError("matplotlib is not installed")

    # Parse data (handles JSON, dict-like string, or text format)
    data_str = data_str.strip()

    if data_str.startswith('{'):
        # JSON or Python dict format: {"0": 475, "1": 525}
        data_str = data_str.replace("'", '"')
        counts = json.loads(data_str)
    elif '|' in data_str and '>:' in data_str:
        # Text format: |1>: 525 (52.5%), |0>: 475 (47.5%)
        counts = parse_text_result(data_str)
        if not counts:
            raise ValueError("Could not parse text result format")
    else:
        # Try JSON anyway
        counts = json.loads(data_str)

    # Create histogram with Scratch Blue Gradient style
    states = list(counts.keys())
    values = list(counts.values())

    # Scratch Blue gradient colors
    scratch_colors = [
        '#4C97FF',  # Scratch Blue
        '#9966FF',  # Scratch Purple
        '#FFAB19',  # Scratch Orange
        '#40BF4A',  # Scratch Green
        '#FF6680',  # Scratch Pink
        '#4CBFE6',  # Scratch Cyan
    ]

    # Format state labels with ket notation
    formatted_states = [f'|{s}⟩' for s in states]

    # Assign colors to bars
    bar_colors = [scratch_colors[i % len(scratch_colors)] for i in range(len(states))]

    fig, ax = plt.subplots(figsize=(6, 4), facecolor='#f8faff')
    ax.set_facecolor('#f8faff')

    bars = ax.bar(formatted_states, values, color=bar_colors, edgecolor='white', linewidth=2, width=0.6)

    # Style the chart (no title - shown in modal header)
    ax.set_xlabel('Quantum State', fontsize=11, color='#555', fontweight='500')
    ax.set_ylabel('Count', fontsize=11, color='#555', fontweight='500')

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#ccc')
    ax.spines['bottom'].set_color('#ccc')

    # Style tick labels
    ax.tick_params(axis='both', colors='#555', labelsize=10)

    # Add grid lines
    ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#ddd')
    ax.set_axisbelow(True)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                str(val), ha='center', va='bottom', fontsize=11, fontweight='600', color='#333')

    plt.tight_layout()

    # Convert to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{image_base64}"


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
