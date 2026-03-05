"""
Secret-independent calculation related
"""

import numpy as np
import cvxpy as cp
from typing import Optional
from dataclasses import dataclass, field

# Type aliases
Matrix = np.ndarray


@dataclass
class SecretIndep:
    """Output of an SDP solver."""

    status: str  # 'optimal', 'infeasible', 'unbounded', etc.
    objective: Optional[float]
    choi: Optional[Matrix]
    info: dict = field(default_factory=dict)


def apply_choi_np(
    J: Matrix,
    rho: Matrix,
    dA: int = 2,
    dB: int = 2,
) -> Matrix:
    """
    Apply the channel E(rho) from Choi matrix J.

    Convention: J[a1, b1, a2, b2]
    E(rho)[b1, b2] = sum_{a1, a2} J[a1, b1, a2, b2] * rho[a1, a2]
    """
    J4 = J.reshape(dA, dB, dA, dB, order="C")  # (a1, b1, a2, b2)
    R = rho.reshape(dA, 1, dA, 1, order="C")  # (a1,  1, a2,  1)
    return np.sum(J4 * R, axis=(0, 2))  # sum over a1, a2 → (b1, b2)


def apply_choi_cp(
    J: cp.Variable,
    rho: Matrix,
    dA: int = 2,
    dB: int = 2,
) -> cp.Expression:
    """cvxpy version of apply_choi_np, for use inside SDP constraints."""
    J4 = cp.reshape(J, (dA, dB, dA, dB), order="C")
    R = cp.reshape(rho, (dA, 1, dA, 1), order="C")
    return cp.sum(cp.multiply(J4, R), axis=(0, 2))


def calc_secret_indep(
    J: Matrix, rho_targ: list[Matrix], rho_ests: list[Matrix]
) -> float:
    """
    Calculate secret independent manually
    """
    # Project J onto the nearest valid Choi matrix
    J_clean = (J + J.conj().T) / 2  # force Hermitian
    eigvals, eigvecs = np.linalg.eigh(J_clean)
    eigvals = np.maximum(eigvals, 0)  # force PSD
    J_clean = eigvecs @ np.diag(eigvals) @ eigvecs.conj().T

    # calcualte secret indep
    si_val = 0
    K = len(rho_targ)
    for i in range(K):
        X = apply_choi_np(J_clean, rho_targ[i]) - rho_ests[i]
        # force hamiltonian before eigvalsh
        X = (X + X.conj().T) / 2
        si_val += np.sum(np.abs(np.linalg.eigvalsh(X)))
    si_val /= 2 * K
    return si_val


def choi_optimise_secret_indep(
    rho_targ: list[Matrix],
    rho_ests: list[Matrix],
    solver: str = cp.SCS,
    solver_opts: Optional[dict] = None,
) -> SecretIndep:
    """
    Estimate secret independence by recover the Choi matrix J minimising the average trace-norm distance
    between target and estimated states.
    """
    K = len(rho_targ)
    solver_opts = solver_opts or {}

    J = cp.Variable((4, 4), complex=True, hermitian=True)
    P = [cp.Variable((2, 2), complex=True, hermitian=True) for _ in range(K)]
    Q = [cp.Variable((2, 2), complex=True, hermitian=True) for _ in range(K)]

    e = np.eye(2)
    Tr_B = sum(
        (np.kron(np.eye(2), e[b].reshape(1, 2)))
        @ J
        @ (np.kron(np.eye(2), e[b].reshape(2, 1)))
        for b in range(2)
    )
    constraints = [J >> 0, Tr_B == np.eye(2)]

    objective_terms = []
    for k in range(K):
        Delta = apply_choi_cp(J, rho_targ[k]) - rho_ests[k]
        constraints += [P[k] >> 0, Q[k] >> 0, Delta == P[k] - Q[k]]
        objective_terms.append(0.5 * cp.trace(P[k] + Q[k]) / K)

    prob = cp.Problem(cp.Minimize(cp.real(cp.sum(objective_terms))), constraints)
    prob.solve(solver=solver, canon_backend="SCIPY", **solver_opts)

    return SecretIndep(
        status=prob.status,
        objective=prob.value,
        choi=np.array(J.value),
    )
