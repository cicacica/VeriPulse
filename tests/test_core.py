import numpy as np
import cvxpy as cp
import json

from veripulse.sdp import choi_optimise_secret_indep, calc_secret_indep
from veripulse.gates import rhox

# Type aliases
#
Matrix = np.ndarray


# ---- helpers / fixtures ---- #


def trace_b_check(J: Matrix) -> float:
    """
    Calculate partial trace of a single-qubit choi map to sanity-check Tr_B(J) = I
    """
    J4 = J.reshape(2, 2, 2, 2)
    Tr_B = sum(J4[:, b, :, b] for b in range(2))  # correct partial trace
    return np.max(np.abs(Tr_B - np.eye(2)))


# --- tests ---- #


def test_sdp():
    print("estimate secret independence by testing SDP from tomography result ... ")
    # tomography result
    rho_ests = []
    with open("data/rhoEsti1.json") as f:
        experiment_tomography = json.load(f)
    for d in experiment_tomography:
        raw = np.array(list(d.values())[0])  # shape should be (2,2,2)
        Re = np.array(raw[0], dtype=float)
        Im = np.array(raw[1], dtype=float)
        rho_ests.append(Re + 1j * Im)

    # angles
    angles = [float(list(d.keys())[0]) for d in experiment_tomography]

    # target states
    rho_targs = [rhox(t) for t in angles]

    # calculate secret independence
    solver_opts = {"verbose": True, "eps": 1e-9, "max_iters": 10000}
    res = choi_optimise_secret_indep(
        rho_targs, rho_ests, solver=cp.SCS, solver_opts=solver_opts
    )

    print("status:", res.status)
    print("objective value:", res.objective)

    print("Manually calculating the resulting Choi matrix ... ")
    si = calc_secret_indep(res.choi, rho_targs, rho_ests)
    si_diff = res.objective - si
    print("si_opt - si_manual = ", si_diff)
    assert si_diff < 1e-8, "Resulting Choi might not be optimal"
    traceb = trace_b_check(res.choi)
    print("Tr_b(J_choi) = ", traceb)
    assert traceb < 1e-8, "Partial trace of choi matrix isn't an identity"

    return
