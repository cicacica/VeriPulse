"""
Pulse engineering related functions
"""

from dataclasses import dataclass, fields, field, asdict
from math import pi
from typing import Optional, Literal

import numpy as np
import qutip_qtrl.pulseoptim as cpo
from qutip import sigmax, sigmay, sigmaz, liouvillian, tensor, basis, qeye, fidelity, Qobj, operator_to_vector, vector_to_operator
import json
import matplotlib.pyplot as plt

from .sdp import choi_optimise_secret_indep, calc_secret_indep
from .gates import extract_subspace_states


# Type aliases
Matrix = np.ndarray
# mode of running optimization 
Mode = Literal["CRAB", "GRAPE", "GRAPE_AVG"]


#-----------------------------
# Main configuration of pulse
#-----------------------------

@dataclass
class PulseConfig:
    """Hardware and optimisation parameters for a GRAPE/CRAB run (single or multi-qubit)."""

    # Hardware charactristics
    omega_drift: float = 10e6  # Drift in rotating frame frequency (Hz)
    T2_star: float = 2e-6  # Dephasing time, a few microsec (s)
    # Hardware control error 
    drive_error: float = 0.0  # Amplitude miscalibration on the XY-axis (fraction)
    detuning: float = 0.0  # Normalised detuning (multiplied by omega)
    # Control 
    evo_time: float = 75e-9  # ~75ns Total evolution time (s)
    num_tslots: int = 100 # number of pulses 
    amp_lbound: float = -1.0 # upper bound of pulse 
    amp_ubound: float = 1.0 # lower bound of pulse
    awg_resolution: float = 15e-12 # ~15 ps 
    # Optimization
    fid_err_targ: float = 1e-9
    max_iter: int = 500
    max_wall_time: float = 1000
    init_pulse_type: str = "RND"
    fid_params: dict = field(default_factory=dict)
    fid_err_scale_factor: Optional[float] = None 

    # check some sensible values 
    def __post_init__(self):
        res = self.evo_time/self.num_tslots 
        if res < self.awg_resolution :
            raise ValueError(f"Resolution is too low {res:.2e}. Expected resolution is {self.awg_resolution}")

    def print(self) -> None:
        """Print config as a formatted table."""
        descs = {
            "omega_drift":         "(Hz) Drift/Rabi frequency",
            "T2_star":             "(s) T2-star",
            "drive_error":         "[0,1] Misalignment of control on the x- and y-axis",
            "detuning":            "(coefficient) Detuning with respect to omega",
            "evo_time":            "(s) Total evolution time",
            "awg_resolution":      "(ps) AWG resolution",
            "num_tslots":          "(int) Number of pulses",
            "amp_lbound":          "(coefficient) Lower bound of pulse amplitude",
            "amp_ubound":          "(coefficient) Upper bound of pulse amplitude",
            "fid_err_targ":        "(float) Convergence criteria",
            "max_iter":            "(int) Cap of iterations",
            "max_wall_time":       "(s) Cap of compute time",
            "init_pulse_type":     "(str) First pulse guess",
            "fid_params":          "(dict) if any",
            "fid_err_scale_factor":"(float) if any",
        }
        print(f"{'Parameter':<20} {'Value':>13}  {'Description':<30}")
        print("─" * 75)
        for f in fields(self):
            val = getattr(self, f.name)
            val_str = f"{val:.3e}" if isinstance(val, float) else str(val)
            print(f"{f.name:<20} {val_str:>13}  {descs.get(f.name, '')}")
        print(f"{'resolution':<20} {(self.evo_time / self.num_tslots):>13.3e}  {'(s) Current pulse resolution'}")
        print("─" * 75)

#------------------
# Quantum system
#-------------------

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
    L_drift = liouvillian(H_drift, [np.sqrt(2 / cfg.T2_star) * Sz])

    if K == 1:
        L_ctrl = [liouvillian(Hc_x, []), liouvillian(Hc_y, [])]
    else:
        L_ctrl = [liouvillian(hx, []) for hx in Hc_x] + [
            liouvillian(hy, []) for hy in Hc_y
        ]

    return L_drift, L_ctrl



#----------------------
# Pulse optimisations
#----------------------

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


def lam_from_ratio(ratio, n=1):
    """
    Return lambda given the desired ratio of fSI influence over fHS.
        f = 1/8 * n^-2 * fHS + lam * fSI
        ratio = lam / coeff_hs = 2 * lam * n^3

    n=1    -> GRAPE
    n=8,10 -> GRAPE AVG
    """
    coeff_hs = 0.125 / (n ** 2)
    lam = ratio * coeff_hs  
    return lam


def ratio_from_lam(lam, n=1):
    """
    Return ration lambda/alpha, which intuitively identify the sensitivity/rate for s.i vs fidelity in grape_avg
        f = 0.5n^-3 fHS + lam fSI
        n=1, GRAPE
        n=8,10, for GRAPE AVG
    Returns ratio x, which means f_si is x times more influental than the fidelity.
    Thus, ratio >> 1 means si first, then fidelity
    """
    c_hs = 0.125/(n**2)
    c_si = lam
    ratio = c_si / c_hs
    return ratio



def run_grape_si(
    init_state,
    target_state,
    U: Matrix,
    lam: Optional[float] = 100,
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

        # debug: verify amps loaded and SI before optimization
        #print(f"[grape_si] ctrl_amps[0, :4]   = {dyn.ctrl_amps[0, :4]}")
        #print(f"[grape_si] expected amps[0,:4] = {amps[0, :4]}")
        #print(f"[grape_si] amps match          : {np.allclose(dyn.ctrl_amps, amps)}")
        fid_comp = dyn.fid_computer
        fid_comp.flag_system_changed()
        dyn.compute_evolution()
        #print(f"[grape_si] initial fid_err     = {fid_comp.get_fid_err():.3e}")

        return optim.run_optimization()


#----------------------------------
# Organising optimisation data
#----------------------------------

@dataclass
class PulseResult:
    """
    Stores everything from one pulseoptim run.

    Modes:
      CRAB / GRAPE  — loop over rho_targets, results is a list of qutip results
      GRAPE_AVG     — single packed run, result is a single qutip result

    state_labels — optional metadata (angle + axis) per target state, for
                   display and plotting. Not used to reconstruct rho_targets.
    """
    config: PulseConfig
    mode: Mode
    rho_targets: list                           # list of Qobj, always required
    label: str = ""

    # CRAB / GRAPE
    results: Optional[list] = None              # list of qutip optim results

    # GRAPE_AVG
    result: any = None                          # single qutip optim result

    # metadata — one per target state (e.g. angles, names)
    state_labels: Optional[list] = None

    # pulse — 2D (num_tslots, num_ctrls) or 3D (num_states, num_tslots, num_ctrls)
    final_amps: Optional[np.ndarray] = None

    # runtime
    run_time: Optional[float] = None

    def __post_init__(self):
        if self.mode in ("CRAB", "GRAPE"):
            if self.results is None:
                raise ValueError(f"Mode '{self.mode}' requires results (list of qutip results)")
            if len(self.results) != len(self.rho_targets):
                raise ValueError(
                    f"results length {len(self.results)} != "
                    f"rho_targets length {len(self.rho_targets)}"
                )
        elif self.mode == "GRAPE_AVG":
            if self.result is None:
                raise ValueError("Mode 'GRAPE_AVG' requires result (single qutip result)")
        else:
            raise ValueError(f"Unknown mode '{self.mode}', choose CRAB, GRAPE, or GRAPE_AVG")

        if self.state_labels is not None:
            if len(self.state_labels) != len(self.rho_targets):
                raise ValueError(
                    f"state_labels length {len(self.state_labels)} != "
                    f"rho_targets length {len(self.rho_targets)}"
                )

        if self.final_amps is not None and self.final_amps.ndim not in (2, 3):
            raise ValueError(
                f"final_amps must be 2D (num_tslots, num_ctrls) or "
                f"3D (num_states, num_tslots, num_ctrls), got shape {self.final_amps.shape}"
            )

    # ── Display ───────────────────────────────

    def display(self):
        self._print_header()
        if self.results is not None or self.result is not None:
            self._display_live()
        else:
            self._display_loaded()


    def _display_live(self):
        K = len(self.rho_targets)
        rho_targ = [r.full() for r in self.rho_targets]

        if self.mode in ("CRAB", "GRAPE"):
            err_hs_list      = [r.fid_err for r in self.results]
            fid_compute_list = [r.stats.num_fidelity_computes for r in self.results]
            termination_list = [r.termination_reason for r in self.results]
            rho_fin          = [vector_to_operator(self.results[j].evo_full_final).full() for j in range(K)]
            err_ul_list      = [
                1 - fidelity(vector_to_operator(self.results[j].evo_full_final), self.rho_targets[j])
                for j in range(K)
            ]
            self._print_table(err_hs_list, err_ul_list, fid_compute_list, termination_list)

        else:
            # GRAPE_AVG — global metrics
            rho_fin     = extract_subspace_states(self.result, K)
            err_ul_list = [1 - fidelity(Qobj(rho_targ[j]), Qobj(rho_fin[j])) for j in range(K)]

            # per-state HS: ||rho_fin - rho_targ||^2
            err_hs_individual = [
                float(np.real(np.trace((rho_fin[j] - rho_targ[j]) @ (rho_fin[j] - rho_targ[j]))))
                for j in range(K)
            ]

            # global summary line
            print(f"{'[global]':<10} {'err_HS':>12} {'fid_compute':>13} {'termination':>25}")
            print("─" * 65)
            print(f"{'':10} {self.result.fid_err:>12.3e} {self.result.stats.num_fidelity_computes:^15d} {self.result.termination_reason:>25}")
            print()

            # per-state breakdown
            lbl_col = "state_label" if self.state_labels else "state"
            print(f"{'[per state]':<14} {lbl_col:<18} {'err_HS':>12} {'err_Uhlmann':>13}")
            print("─" * 60)
            for j in range(K):
                lbl = str(self.state_labels[j]) if self.state_labels else str(j)
                print(f"{'':14} {lbl:<18} {err_hs_individual[j]:>12.3e} {err_ul_list[j]:>13.3e}")
            print("─" * 60)
            print(f"{'avg':<14} {'':18} {np.mean(err_hs_individual):>12.3e} {np.mean(err_ul_list):>13.3e}")

        res_choi = choi_optimise_secret_indep(rho_targ, rho_fin)
        print(f"\n{'si:':<6} {res_choi.objective:>12.3e}")
        print(f"{'si_lb:':<6} {calc_secret_indep(rho_targ, rho_fin):>12.3e}")

    
    def _print_table(self, err_hs_list, err_ul_list, fid_compute_list, termination_list):
        print(f"{'err_HS':>15} {'err_Uhlmann':>13} {'fid_compute':>13} {'termination':>25}")
        print("─" * 70)
        for hs, ul, fc, tr in zip(err_hs_list, err_ul_list, fid_compute_list, termination_list):
            print(f"{hs:>15.3e} {ul:>13.3e} {fc:^15d} {tr:>25}")
        print("─" * 70)
        print(f"{'avg:':<4} {np.mean(err_hs_list):>15.3e} {np.mean(err_ul_list):>13.3e} {int(np.mean(fid_compute_list)):^15d}")

        

    def _display_loaded(self):
        print(f"{'err_HS':>15} {'err_Uhlmann':>18} {'fid_compute':>13} {'termination':>25}")
        print("─" * 75)
        for hs, ul, fc, tr in zip(
            self.err_hs_list, self.err_ul_list,
            self.fid_compute_list, self.termination_list
        ):
            print(f"{hs:>15.3e} {ul:>18.3e} {fc:^15d} {tr:>25}")
        print("─" * 75)
        print(f"{'avg:':<4} {np.mean(self.err_hs_list):>15.3e} {np.mean(self.err_ul_list):>18.3e} {int(np.mean(self.fid_compute_list)):^15d}")
        if self.si is not None:
            print(f"{'si:':<4} {self.si:>15.3e}")
            print(f"{'si_lb:':<4} {self.si_lb:>15.3e}")



    def plot_pulse(self) -> None:
        """Plot optimized control pulses. Works both live and after load."""

        if self.final_amps is None and (self.results is None and self.result is None):
            raise ValueError("No pulse data available — set final_amps or provide live results")

        # reconstruct time axis from config (works after load)
        t = np.linspace(0, self.config.evo_time, self.config.num_tslots + 1)

        if self.results is not None or self.result is not None:
            self._plot_live(t)
        else:
            self._plot_loaded(t)

    
    def _plot_live(self, t: np.ndarray) -> None:
        if self.mode in ("CRAB", "GRAPE"):
            for k, res in enumerate(self.results):
                lbl = str(self.state_labels[k]) if self.state_labels else f"state {k}"
                fig, ax = plt.subplots()
                ax.set_title(f"{lbl}  fid_err={res.fid_err:.3e}")
                ax.set_xlabel("Time (ns)")
                ax.set_ylabel("Amplitude")
                for i in range(res.final_amps.shape[1]):
                    amps = np.hstack((res.final_amps[:, i], res.final_amps[-1, i]))
                    ax.step(res.time, amps, where="post", label=f"ctrl {i}")
                ax.legend()
                plt.tight_layout()
                plt.show()
        else:
            self._plot_packed_live(t)



    def _plot_packed_live(self, t: np.ndarray) -> None:
        K        = len(self.rho_targets)
        amps     = self.result.final_amps
        t        = self.result.time[:-1]   # use actual time from result, not reconstructed
        rho_fin  = extract_subspace_states(self.result, K)
        rho_targ = [r.full() for r in self.rho_targets]
        for j in range(K):
            err_ul = 1 - fidelity(Qobj(rho_targ[j]), Qobj(rho_fin[j]))
            lbl    = str(self.state_labels[j]) if self.state_labels else f"state {j}"
            amps_j = amps[:, j*2 : j*2 + 2]   # (num_tslots, 2 control per qubit)
            fig, ax = plt.subplots()
            ax.set_title(f"{lbl}  err_Uhlmann={err_ul:.3e}")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            ax.step(t, amps_j[:, 0], where="post", label="ctrl 0")
            ax.step(t, amps_j[:, 1], where="post", label="ctrl 1")
            ax.legend()
            plt.tight_layout()
            plt.show()

    def _plot_loaded(self, t: np.ndarray) -> None:
        amps = self.final_amps  # 2D or 3D
        if amps.ndim == 3:
            # (num_states, num_tslots, num_ctrls) — CRAB/GRAPE
            for k in range(amps.shape[0]):
                lbl = str(self.state_labels[k]) if self.state_labels else f"state {k}"
                fig, ax = plt.subplots()
                ax.set_title(f"{lbl}  fid_err={self.err_hs_list[k]:.3e}")
                ax.set_xlabel("Time (ns)")
                ax.set_ylabel("Amplitude")
                for i in range(amps.shape[2]):
                    a = np.hstack((amps[k, :, i], amps[k, -1, i]))
                    ax.step(t, a, where="post", label=f"ctrl {i}")
                ax.legend()
                plt.tight_layout()
                plt.show()
        else:
            # (num_tslots, K * 2) — GRAPE_AVG, one figure per state
            t = np.linspace(0, self.config.evo_time, amps.shape[0])
            for j in range(len(self.err_ul_list)):
                lbl    = str(self.state_labels[j]) if self.state_labels else f"state {j}"
                amps_j = amps[:, j*2 : j*2 + 2] # assume 2 controls per qubit
                fig, ax = plt.subplots()
                ax.set_title(f"{lbl}  err_Uhlmann={self.err_ul_list[j]:.3e}")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Amplitude")
                ax.step(t, amps_j[:, 0], where="post", label="ctrl 0 (I)")
                ax.step(t, amps_j[:, 1], where="post", label="ctrl 1 (Q)")
                ax.legend()
                plt.tight_layout()
                plt.show()

    def _print_header(self):
        print(f"\n{'═'*60}")
        print(f"  {self.label or 'Run'}  [{self.mode}]")
        print(f"  detuning={self.config.detuning:.3e}  drive_error={self.config.drive_error:.3e}")
        if self.state_labels:
            print(f"  states: {', '.join(str(s) for s in self.state_labels)}")
        print(f"{'═'*60}")

    # ── Serialization ─────────────────────────

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self._to_dict(), f, indent=2)
        print(f"Saved → {path}")

    @classmethod
    def load(cls, path: str) -> "PulseResult":
        with open(path) as f:
            data = json.load(f)
        return cls._from_dict(data)

    # ── Numpy access (after load) ─────────────

    @property
    def rho_finals_np(self) -> list[np.ndarray]:
        return [
            np.array(re) + 1j * np.array(im)
            for re, im in zip(self._rho_finals_re, self._rho_finals_im)
        ]

    @property
    def rho_targets_np(self) -> list[np.ndarray]:
        return [
            np.array(re) + 1j * np.array(im)
            for re, im in zip(self._rho_targets_re, self._rho_targets_im)
        ]

    # ── Internal helpers ──────────────────────

    def _extract_matrices(self):
        K = len(self.rho_targets)
        rho_targ = [r.full() for r in self.rho_targets]
        if self.mode in ("CRAB", "GRAPE"):
            rho_fin = [vector_to_operator(self.results[j].evo_full_final).full() for j in range(K)]
        else:
            rho_fin = extract_subspace_states(self.result, K)
        return rho_fin, rho_targ

    def _extract_metrics(self, rho_fin, rho_targ):
        K = len(rho_targ)

        if self.mode in ("CRAB", "GRAPE"):
            err_hs_list      = [r.fid_err for r in self.results]
            fid_compute_list = [r.stats.num_fidelity_computes for r in self.results]
            termination_list = [r.termination_reason for r in self.results]
            err_ul_list      = [
                1 - fidelity(vector_to_operator(self.results[j].evo_full_final), self.rho_targets[j])
                for j in range(K)
            ]
        else:
            err_hs_list      = [self.result.fid_err]
            fid_compute_list = [self.result.stats.num_fidelity_computes]
            termination_list = [self.result.termination_reason]
            err_ul_list      = [1 - fidelity(Qobj(rho_targ[j]), Qobj(rho_fin[j])) for j in range(K)]

        try:
            solver_opts = {"verbose": False, "eps": 1e-13, "max_iters": 10000}
            res_choi = choi_optimise_secret_indep(rho_targ, rho_fin, solver_opts=solver_opts)
            si    = float(res_choi.objective)
            si_lb = float(calc_secret_indep(rho_targ, rho_fin))
        except Exception:
            si = si_lb = None

        return err_hs_list, err_ul_list, fid_compute_list, termination_list, si, si_lb

    def _to_dict(self) -> dict:
        rho_fin, rho_targ = self._extract_matrices()
        err_hs_list, err_ul_list, fid_compute_list, termination_list, si, si_lb = \
            self._extract_metrics(rho_fin, rho_targ)

        def split(matrices):
            return [m.real.tolist() for m in matrices], [m.imag.tolist() for m in matrices]

        rho_finals_re,  rho_finals_im  = split(rho_fin)
        rho_targets_re, rho_targets_im = split(rho_targ)

        return {
            "label":            self.label,
            "mode":             self.mode,
            "config":           asdict(self.config),
            "state_labels":     self.state_labels,
            "err_hs_list":      err_hs_list,
            "err_ul_list":      err_ul_list,
            "fid_compute_list": fid_compute_list,
            "termination_list": termination_list,
            "si":               si,
            "si_lb":            si_lb,
            "rho_finals_re":    rho_finals_re,
            "rho_finals_im":    rho_finals_im,
            "rho_targets_re":   rho_targets_re,
            "rho_targets_im":   rho_targets_im,
            "final_amps":       self.final_amps.tolist() if self.final_amps is not None else None,
            "run_time":         self.run_time
        }

    @classmethod
    def _from_dict(cls, d: dict) -> "PulseResult":
        obj = object.__new__(cls)
        obj.config      = PulseConfig(**d["config"])
        obj.mode        = d["mode"]
        obj.label       = d["label"]
        obj.result      = None
        obj.results     = None
        obj.rho_targets = None
        obj.state_labels = d.get("state_labels")
        # matrices
        obj._rho_finals_re  = d["rho_finals_re"]
        obj._rho_finals_im  = d["rho_finals_im"]
        obj._rho_targets_re = d["rho_targets_re"]
        obj._rho_targets_im = d["rho_targets_im"]
        # metrics
        obj.err_hs_list      = d["err_hs_list"]
        obj.err_ul_list      = d["err_ul_list"]
        obj.fid_compute_list = d["fid_compute_list"]
        obj.termination_list = d["termination_list"]
        obj.si               = d.get("si")
        obj.si_lb            = d.get("si_lb")
        # pulse
        amps = d.get("final_amps")
        obj.final_amps = np.array(amps) if amps is not None else None
        # stat 
        rtime = d.get("run_time")
        obj.run_time = rtime if rtime is not None else None
        
        return obj



