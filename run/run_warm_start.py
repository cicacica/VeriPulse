"""
run_warm_start.py
-----------------
Warm-start GRAPE_AVG from existing GRAPE or CRAB runs.
Can be used as a script (CLI) or imported in a notebook.

Notebook usage
--------------
    from run_warm_start import repack_amps, run_with_warm_start
    from veripulse.warm_start_inspect import find_best_grape_run, load_grape_run

    ws  = find_best_grape_run(data_dir, num_tslots=40, detuning=0.0,
                              drive_error=0.0, rank_by="si")
    # or:
    ws  = load_grape_run("data/dummyless/GRAPE_p40_det0.00_err0.00-3.json")

    res = run_with_warm_start(ws, angles, vRho_init, vRho_target,
                              U=U_big, lam=0.05)

    # with config overrides:
    res = run_with_warm_start(ws, angles, vRho_init, vRho_target,
                              U=U_big, lam=0.05,
                              max_iter=2000, fid_err_targ=1e-12)

Script usage (same style as run_sampling_data.py)
-------------------------------------------------
    # single run
    python run_warm_start.py -s GRAPE -p 40 -det 0.0 -e 0.0 -i 1 -l 0.05 -v

    # loop over n samples
    python run_warm_start.py -s GRAPE -p 40 -det 0.0 -e 0.0 -n 5 -l 0.05

    # with dummy qubits
    python run_warm_start.py -s CRAB -p 40 -det 0.0 -e 0.0 -n 5 -l 0.05 -dum
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

import numpy as np
from numpy import pi
from qutip import Qobj, operator_to_vector

from veripulse.warm_start_inspect import WarmStartResult, find_best_grape_run, load_grape_run
from veripulse.gates import rx, rhox, hadamard, hadamardZ, pack_subspace_states
from veripulse.pulse import PulseConfig, PulseResult, run_grape_si


# ── float comparison ──────────────────────────────────────────────────────────

def _feq(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tol)


# ── filename parser ───────────────────────────────────────────────────────────

_FNAME_RE = re.compile(
    r"^(?P<method>.+?)_p(?P<tslots>\d+)"
    r"_det(?P<det>[\d.]+)"
    r"_err(?P<err>[\d.]+)"
    r"(?:_lam(?P<lam>[\d.]+))?"
    r"-(?P<id>.+)$"
)

def _parse_stem(stem: str):
    m = _FNAME_RE.match(stem)
    if m is None:
        return None
    lam_str = m.group("lam")
    return {
        "method":      m.group("method"),
        "num_tslots":  int(m.group("tslots")),
        "detuning":    float(m.group("det")),
        "drive_error": float(m.group("err")),
        "lam":         float(lam_str) if lam_str is not None else None,
        "id":          m.group("id"),
    }


# ── find source runs ──────────────────────────────────────────────────────────

def find_source_runs(
    data_dir:    Path,
    source:      str,
    num_tslots:  int,
    detuning:    float,
    drive_error: float,
    n:           int = 0,
) -> list[tuple[str, dict, dict]]:
    """Return list of (id, meta, data) for matching source runs, sorted by id."""
    results = []
    for path in sorted(data_dir.glob("*.json")):
        meta = _parse_stem(path.stem)
        if meta is None:
            continue
        if meta["method"] != source:
            continue
        if meta["lam"] is not None:
            continue
        if meta["num_tslots"] != num_tslots:
            continue
        if not _feq(meta["detuning"],    detuning):
            continue
        if not _feq(meta["drive_error"], drive_error):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        if data.get("final_amps") is None:
            continue
        results.append((meta["id"], meta, data))

    if n > 0:
        results = results[:n]
    return results


# ── repack ────────────────────────────────────────────────────────────────────

def repack_amps(ws: WarmStartResult, angles: list) -> np.ndarray:
    """
    Repack (K, num_tslots, 2) GRAPE/CRAB amps into (num_tslots, K*2) joint format.

    Sorts amps to match the angle order passed to pack_subspace_states.
    L_ctrl order in nvcenter_system is grouped: [Lx_0,...,Lx_K, Ly_0,...,Ly_K]
    """
    amps   = ws.amps
    thetas = np.array(ws.raw["state_labels"])
    angles = np.array(angles)

    sort_idx    = [np.argmin(np.abs(thetas - a)) for a in angles]
    amps_sorted = amps[sort_idx]

    amps_x     = amps_sorted[:, :, 0].T
    amps_y     = amps_sorted[:, :, 1].T
    amps_joint = np.hstack([amps_x, amps_y])

    print(f"[repack] sorted labels : {[f'{thetas[i]:.4f}' for i in sort_idx]}")
    print(f"[repack] amps_joint    : {amps_joint.shape}")
    return amps_joint


def _repack_from_data(raw_amps, json_state_labels, numeric_angles) -> np.ndarray:
    """Repack directly from raw JSON data (used in CLI batch mode)."""
    amps   = np.array(raw_amps)
    thetas = np.array(json_state_labels)
    angles = np.array(numeric_angles)

    sort_idx    = [np.argmin(np.abs(thetas - a)) for a in angles]
    amps_sorted = amps[sort_idx]

    amps_x = amps_sorted[:, :, 0].T
    amps_y = amps_sorted[:, :, 1].T
    return np.hstack([amps_x, amps_y])


# ── notebook API ──────────────────────────────────────────────────────────────

def run_with_warm_start(
    ws: WarmStartResult,
    angles: list,
    init_state,
    target_state,
    U,
    lam: float,
    **config_overrides,
):
    """
    Run run_grape_si using config and amps from a WarmStartResult.

    Parameters
    ----------
    ws               : WarmStartResult from find_best_grape_run() or load_grape_run()
    angles           : sorted numeric angles passed to pack_subspace_states
    init_state       : vectorised initial state (from pack_subspace_states)
    target_state     : vectorised target state
    U                : block-diagonal unitary
    lam              : secret-independence weight
    **config_overrides : any PulseConfig field to override, e.g.
                         max_iter=2000, max_wall_time=3600, fid_err_targ=1e-12
    """
    cfg_dict = dict(ws.config)
    cfg_dict.update(config_overrides)
    cfg = PulseConfig(**cfg_dict)

    if config_overrides:
        print(f"[warm start] config overrides : {config_overrides}")

    amps_joint = repack_amps(ws, angles)

    print(f"[warm start] amps from     : {ws.path.name}")
    print(f"[warm start] si            : {ws.si:.3e}")
    print(f"[warm start] max_iter      : {cfg.max_iter}")
    print(f"[warm start] max_wall_time : {cfg.max_wall_time}")
    print(f"[warm start] fid_err_targ  : {cfg.fid_err_targ}")

    return run_grape_si(
        init_state, target_state,
        U=U, lam=lam,
        config=cfg,
        amps=amps_joint,
    )


# ── CLI batch mode ────────────────────────────────────────────────────────────

def run_experiment(
    source:         str,
    num_tslots:     int,
    detuning:       float,
    dummy:          bool,
    drive_error:    float,
    identification: int,
    lam:            float,
    verbose:        bool,
) -> PulseResult:
    """Single experiment run (mirrors run_sampling_data.py style)."""

    # system setup
    angles            = [0, pi/4, pi/2, 3*pi/4, pi, 5*pi/4, 3*pi/2, 7*pi/4]
    err               = 0
    rho_init          = Qobj([[1-err, 0], [0, err]])
    rho_targets       = [Qobj(rhox(a)) for a in angles]
    unitary_rotations = [rx(t) for t in angles]

    if dummy:
        save_dir = Path.cwd().parent / "data/dummyyes"
        angles            = angles + ["+", "-"]
        rho_targets       = rho_targets + [
            Qobj([[0.5,  0.5], [ 0.5, 0.5]]),
            Qobj([[0.5, -0.5], [-0.5, 0.5]]),
        ]
        unitary_rotations = unitary_rotations + [hadamard(), hadamardZ()]
    else:
        save_dir = Path.cwd().parent / "data/dummyless"

    cfg = PulseConfig(
        num_tslots    = num_tslots,
        detuning      = detuning,
        drive_error   = drive_error,
        max_iter      = 20000,
        max_wall_time = 100000,
        fid_err_targ  = 1e-10,
    )

    # find specific source run by id
    all_runs    = find_source_runs(save_dir, source, num_tslots, detuning, drive_error)
    source_run  = next(
        ((rid, meta, data) for rid, meta, data in all_runs
         if str(rid) == str(identification)),
        None
    )
    if source_run is None:
        raise FileNotFoundError(
            f"No {source} run with id={identification} found in '{save_dir}' "
            f"(tslots={num_tslots}, det={detuning}, err={drive_error})"
        )

    run_id, _, data = source_run
    method = f"W{source}"
    label  = (
        f"{method}_p{num_tslots}_det{detuning:.2f}_err{drive_error:.2f}"
        f"-lam{lam:.4f}-{run_id}"
    )

    # repack
    numeric_angles = [a for a in angles if isinstance(a, (int, float))]
    numeric_json   = [l for l in data.get("state_labels", []) if isinstance(l, (int, float))]
    amps_joint     = _repack_from_data(data["final_amps"], numeric_json, numeric_angles)
    print(f"[{method}] id={run_id}  amps_joint={amps_joint.shape}")

    # run
    vRho_init, vRho_target, U_big = pack_subspace_states(
        rotations=unitary_rotations,
        rho_init=rho_init,
    )

    s_time = time.time()
    result = run_grape_si(
        vRho_init, vRho_target, U_big,
        lam=lam, config=cfg, amps=amps_joint,
    )
    e_time = time.time()

    pr = PulseResult(
        config       = cfg,
        mode         = "GRAPE_AVG",
        result       = result,
        rho_targets  = rho_targets,
        final_amps   = result.final_amps,
        label        = label,
        state_labels = angles,
        run_time     = e_time - s_time,
    )

    if verbose:
        pr.display()

    save_dir.mkdir(parents=True, exist_ok=True)
    pr.save(save_dir / f"{label}.json")
    print(f"Saved → {save_dir / f'{label}.json'}")

    return pr


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Warm-start GRAPE_AVG from existing GRAPE or CRAB runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-s",   "--source",         type=str,   default="GRAPE",
                        choices=["GRAPE", "CRAB"],  help="Source method for warm start")
    parser.add_argument("-p",   "--num_tslots",     type=int,   default=40)
    parser.add_argument("-det", "--detuning",       type=float, default=0.0)
    parser.add_argument("-dum", "--dummy",          action="store_true", default=False)
    parser.add_argument("-e",   "--drive_error",    type=float, default=0.0)
    parser.add_argument("-i",   "--identification", type=int,   default=1)
    parser.add_argument("-n",   "--num_experiment", type=int,   default=0,
                        help="Loop over ids 1..n (same as run_sampling_data -n)")
    parser.add_argument("-l",   "--lam",            type=float, default=0.05)
    parser.add_argument("-v",   "--verbose",        action="store_true")
    args = parser.parse_args()

    if args.num_experiment > 0:
        for i in range(1, args.num_experiment + 1):
            run_experiment(
                source         = args.source,
                num_tslots     = args.num_tslots,
                detuning       = args.detuning,
                dummy          = args.dummy,
                drive_error    = args.drive_error,
                identification = i,
                lam            = args.lam,
                verbose        = args.verbose,
            )
    else:
        run_experiment(
            source         = args.source,
            num_tslots     = args.num_tslots,
            detuning       = args.detuning,
            dummy          = args.dummy,
            drive_error    = args.drive_error,
            identification = args.identification,
            lam            = args.lam,
            verbose        = args.verbose,
        )