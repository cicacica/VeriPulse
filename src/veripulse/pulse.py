"""
Pulse engineering related functions
"""

from dataclasses import dataclass, field
from math import pi
from typing import Optional

import numpy as np
import qutip_qtrl.pulseoptim as cpo
from qutip import sigmax, sigmay, sigmaz, liouvillian, tensor, basis, qeye


# Type aliases
Matrix = np.ndarray


@dataclass
class PulseConfig:
    """Hardware and optimisation parameters for a GRAPE run (single or multi-qubit)."""

    # Hardware
    omega_drift: float = 10e6  # Drift in rotating frame frequency (Hz)
    T2_star: float = 2e-6  # Dephasing time, a few microsec (s)
    drive_error: float = 0.03  # Amplitude miscalibration on the XY-axis (fraction)
    detuning: float = 0.0  # Normalised detuning (multiplied by omega)
    # Optimisation
    evo_time: float = 300e-9  # Total evolution time (s)
    num_tslots: int = 100
    amp_lbound: float = -1.0
    amp_ubound: float = 1.0
    fid_err_targ: float = 1e-8
    max_iter: int = 500
    max_wall_time: float = 120.0
    init_pulse_type: str = "RND"
    fid_params: dict = field(default_factory=dict)
    fid_err_scale_factor: Optional[float] = None 


def nvcenter_system(K: int, cfg: PulseConfig):
    """Build drift and control Liouvillians for K qubits."""
    Sx_1 = 0.5 * sigmax()
    Sy_1 = 0.5 * sigmay()
    Sz_1 = 0.5 * sigmaz()

    if K == 1:
        Sx, Sy, Sz = Sx_1, Sy_1, Sz_1
    else:
        Sx = [tensor(basis(K, i) * basis(K, i).dag(), Sx_1) for i in range(K)]
        Sy = [tensor(basis(K, i) * basis(K, i).dag(), Sy_1) for i in range(K)]
        Sz = tensor(qeye(K), Sz_1)

    # Hamiltonians
    delta = cfg.detuning * cfg.omega_drift
    H_drift = 2 * pi * delta * Sz

    if K == 1:
        Hc_x = 2 * pi * cfg.omega_drift * (1 + cfg.drive_error) * Sx
        Hc_y = 2 * pi * cfg.omega_drift * (1 + cfg.drive_error) * Sy
    else:
        Hc_x = [2 * pi * cfg.omega_drift * (1 + cfg.drive_error) * sx for sx in Sx]
        Hc_y = [2 * pi * cfg.omega_drift * (1 + cfg.drive_error) * sy for sy in Sy]

    # Liouvillians
    L_drift = liouvillian(H_drift, [np.sqrt(1 / cfg.T2_star) * Sz])

    if K == 1:
        L_ctrl = [liouvillian(Hc_x, []), liouvillian(Hc_y, [])]
    else:
        L_ctrl = [liouvillian(hx, []) for hx in Hc_x] + [
            liouvillian(hy, []) for hy in Hc_y
        ]

    return L_drift, L_ctrl


def run_crab(
    init_state,
    target_state,
    config: Optional[PulseConfig] = None,
) -> None:
    """
    Run CRAB for a single-qubit system with TRACEDIFF fidelity.

    Produces smooth, bandwidth-limited pulses by parameterising
    the control as a sum of sinusoids. More realistic than GRAPE
    for hardware-constrained systems.

    Args:
        init_state:   Vectorised initial state (single qubit).
        target_state: Vectorised target state (single qubit).
        config:       PulseConfig — hardware and optimisation params.

    Returns:
        qutip-ctrl OptimResult.
    """
    cfg = config or PulseConfig()

    # max frequency = num_coeffs / evo_time
    # e.g. 10 / 300ns ≈ 33 MHz — within typical NV hardware bandwidth
    num_coeffs = int(cfg.num_tslots / 10)

    L_drift, L_ctrl = nvcenter_system(1, cfg)

    return cpo.optimize_pulse(
        L_drift, L_ctrl,
        init_state, target_state,
        num_tslots              = cfg.num_tslots,
        evo_time                = cfg.evo_time,
        amp_lbound              = cfg.amp_lbound,
        amp_ubound              = cfg.amp_ubound,
        fid_err_targ            = cfg.fid_err_targ,
        max_iter                = cfg.max_iter,
        max_wall_time           = cfg.max_wall_time,
        fid_err_scale_factor    = cfg.fid_err_scale_factor,
        alg                     = "CRAB",
        alg_params              = {"num_coeffs": num_coeffs},
        ramping_pulse_type      = "GAUSSIAN_EDGE",
        ramping_pulse_params    = {"sigma": 5e-9},
        dyn_type                = "GEN_MAT",
        fid_type                = "TRACEDIFF",
        gen_stats               = True,
    )




def run_grape(
    init_state,
    target_state,
    config: Optional[PulseConfig] = None,
    amps: Optional[Matrix] = None,
):
    """
    Run GRAPE for a single-qubit system with TRACEDIFF fidelity.

    Args:
        init_state:   Vectorised initial state (single qubit).
        target_state: Vectorised target state (single qubit).
        config:       PulseConfig — hardware and optimisation params.
        amps:         Optional warm-start amplitudes, shape (num_tslots, num_ctrls).

    Returns:
        qutip-ctrl OptimResult.
    """
    cfg = config or PulseConfig()
    
    L_drift, L_ctrl = nvcenter_system(1, cfg)

    optim_kwargs = dict(
        num_tslots=cfg.num_tslots,
        evo_time=cfg.evo_time,
        amp_lbound=cfg.amp_lbound,
        amp_ubound=cfg.amp_ubound,
        fid_err_targ=cfg.fid_err_targ,
        max_iter=cfg.max_iter,
        max_wall_time=cfg.max_wall_time,
        fid_err_scale_factor=cfg.fid_err_scale_factor,
        alg="GRAPE",
        dyn_type="GEN_MAT",
        fid_type="TRACEDIFF",
        gen_stats=True,
    )

    if amps is None:
        return cpo.optimize_pulse(
            L_drift,
            L_ctrl,
            init_state,
            target_state,
            init_pulse_type=cfg.init_pulse_type,
            **optim_kwargs,
        )
    else:
        optim = cpo.create_pulse_optimizer(
            L_drift,
            L_ctrl,
            init_state,
            target_state,
            **optim_kwargs,
        )
        dyn = optim.dynamics
        dyn.init_timeslots()
        dyn.initialize_controls(amps)
        return optim.run_optimization()


def run_grape_si(
    init_state,
    target_state,
    U: Matrix,
    lam: float = 1e-1,
    config: Optional[PulseConfig] = None,
    amps: Optional[Matrix] = None,
):
    """
    Run GRAPE enforcing secret-independence and high fidelity (SECRETIND).

    Args:
        init_state:   Vectorised initial state from pack_subspace_states.
        target_state: Vectorised target state from pack_subspace_states.
        U:            Block-diagonal unitary preparation from direct_sum.
        lam:          Secret-independence weight.
        config:       PulseConfig — hardware and optimisation params.
        amps:         Optional warm-start amplitudes, shape (num_tslots, num_ctrls).

    Returns:
        qutip-ctrl OptimResult.
    """
    cfg = config or PulseConfig()

    D = int(np.sqrt(np.shape(init_state)[0]))
    K = int(D / 2)

    L_drift, L_ctrl = nvcenter_system(K, cfg)

    optim_kwargs = dict(
        num_tslots=cfg.num_tslots,
        evo_time=cfg.evo_time,
        amp_lbound=cfg.amp_lbound,
        amp_ubound=cfg.amp_ubound,
        fid_err_targ=cfg.fid_err_targ,
        max_iter=cfg.max_iter,
        max_wall_time=cfg.max_wall_time,
        fid_err_scale_factor=cfg.fid_err_scale_factor,
        alg="GRAPE",
        dyn_type="GEN_MAT",
        fid_type="SECRETIND",
        fid_params={"U": U, "si_weight": lam},
        gen_stats=True,
    )

    if amps is None:
        return cpo.optimize_pulse(
            L_drift,
            L_ctrl,
            init_state,
            target_state,
            init_pulse_type=cfg.init_pulse_type,
            **optim_kwargs,
        )
    else:
        optim = cpo.create_pulse_optimizer(
            L_drift,
            L_ctrl,
            init_state,
            target_state,
            **optim_kwargs,
        )
        dyn = optim.dynamics
        dyn.init_timeslots()
        dyn.initialize_controls(amps)
        return optim.run_optimization()


# utils
def print_pulse_config(cfg: PulseConfig) -> None:
    """Print PulseConfig as a formatted table."""
    from dataclasses import fields

    print(f"{'Parameter':<20} {'Value':>15} {'Description'}")
    print("─" * 45)

    units = {
        "omega_drift": "Hz",
        "T2_star": "s",
        "amp_error": "fraction",
        "detuning": "normalised",
        "evo_time": "s",
        "num_tslots": "",
        "amp_lbound": "",
        "amp_ubound": "",
        "fid_err_targ": "",
        "max_iter": "",
        "max_wall_time": "s",
        "init_pulse_type": "",
        "fid_type": "",
        "fid_params": "",
    }

    for f in fields(cfg):
        val = getattr(cfg, f.name)
        unit = units.get(f.name, "")
        if isinstance(val, float):
            val_str = f"{val:.3e}"
        else:
            val_str = str(val)
        print(f"{f.name:<20} {val_str:>15}  {unit}")
