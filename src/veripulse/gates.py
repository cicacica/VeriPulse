"""
Collection of gates, states, and manipulation of them
"""

import numpy as np
from numpy import cos, sin, exp
from scipy.linalg import block_diag
from qutip import Qobj, operator_to_vector, vector_to_operator

# Type aliases
Matrix = np.ndarray


def rz(theta: float) -> Matrix:
    """
    Rotation around Z: Exp[-i theta/2 Z].
    State preparation in the XY-plane can be obtained by application of  rz(theta)|+>
    """
    return np.array([[1, 0], [0, exp(1j * theta)]], dtype=complex)


def rx(theta: float) -> Matrix:
    """
    Rotation around X: Exp[-i theta/2 X].
    State preparation in the YZ-plane can be obtained by application of  rx(theta)|0>
    """
    return np.array(
        [
            [cos(theta / 2), -1j * sin(theta / 2)],
            [-1j * sin(theta / 2), cos(theta / 2)],
        ], dtype=complex
    )


def rhox(theta: float) -> Matrix:
    """
    Returns rho_theta: |theta><theta|  as the prepared state for YZ blind quantum computing
    """
    return np.array(
        [
            [cos(theta / 2) ** 2, 1j * 0.5 * sin(theta)],
            [-1j * 0.5 * sin(theta), sin(theta / 2) ** 2],
        ], dtype=complex
    )


def rhoz(theta: float) -> Matrix:
    """
    Returns rho_theta: |theta><theta|  as the prepared state for XY blind quantum computing
    """
    return np.array([[0.5, 0.5 * exp(-1j * theta)], [0.5 * exp(1j * theta), 0.5]], dtype=complex)


def hadamard() -> Matrix : 
    """
    Returns H matrix operation 
    """
    return np.array([[1/np.sqrt(2), 1/np.sqrt(2)], [1/np.sqrt(2), -1/np.sqrt(2)]], dtype=complex)


def hadamardZ() -> Matrix : 
    """
    Returns -- H -- Z -- matrix operation 
    """
    return np.array([[1/np.sqrt(2), 1/np.sqrt(2)], [-1/np.sqrt(2), 1/np.sqrt(2)]], dtype=complex)



def direct_sum(unitaries: list[Matrix]) -> Matrix:
    """Direct sum (block-diagonal) of a list of unitaries: U_0 ⊕ U_1 ⊕ ... ⊕ U_{K-1}."""
    return block_diag(*unitaries)


def pack_subspace_states(rotations: list[Matrix], rho_init: Matrix):
    """
    Prepare vectorised initial and target states for secret-independence GRAPE.
    by averaging method. Given that state can be prepared with rotations(rho_init)

    Returns:
        v_rho_0:      vectorised initial state (K copies of |0><0| / K)
        v_rho_target: vectorised target state (U @ rho0_tot @ U†)
    """
    K = len(rotations)
    rot_big = direct_sum(rotations)
    rho_init_big = Qobj(np.kron(np.eye(K), rho_init.full())) / K
    rho_fin_big = Qobj(rot_big @ rho_init_big.full() @ rot_big.conj().T)

    return operator_to_vector(rho_init_big), operator_to_vector(rho_fin_big), rot_big


def extract_subspace_states(
    result,
    K: int,
    d: int = 2,
) -> list[Qobj]:
    """
    Extract K individual density matrices from a block-diagonal GRAPE result.

    Inverse of prepare_si_states — undoes the direct sum structure.

    Args:
        result: qutip-ctrl OptimResult (evo_full_final).
        K:      number of subspaces.
        d:      single-qubit dimension (default 2).

    Returns:
        List of K density matrices, one per subspace.
    """
    rho_evo = vector_to_operator(result.evo_full_final) * K
    return [rho_evo[d * i : d * i + d, d * i : d * i + d] for i in range(K)]
