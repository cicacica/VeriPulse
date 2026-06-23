"""
scan_convergence.py
-------------------
Scan a data folder and report which runs have not converged.

Usage in notebook
-----------------
    from scan_convergence import scan_convergence

    results = scan_convergence("data/dummyless/")

    # not converged only
    not_conv = [r for r in results if not r["converged"]]
    for r in not_conv:
        print(r["file"], r["termination"], r["fid_err"])
"""

from __future__ import annotations

import json
import re
from pathlib import Path


CONVERGED_REASONS = {
    "function converged",
    "goal achieved",
    "function converged (within tolerance)",  # CRAB/GRAPE per-state
}

NOT_CONVERGED_REASONS = {
    "maximum number of iterations reached",
    "max_iter exceeded",
    "max_wall_time exceeded",
    "cancelled",
    "error",
}


def _check(data: dict) -> tuple[bool, bool, str]:
    """
    Returns (converged, reached_target, termination_summary).

    For CRAB/GRAPE, termination_list has one entry per state.
    A run is converged if ALL states converged.
    """
    cfg          = data.get("config", {})
    fid_err_targ = float(cfg.get("fid_err_targ", float("nan")))
    fid_err_list = data.get("err_hs_list", [])
    terminations = data.get("termination_list") or ["unknown"]

    # check each state's termination (case-insensitive)
    all_converged = all(
        t.lower() in CONVERGED_REASONS for t in terminations
    )
    any_not_converged = any(
        t.lower() in NOT_CONVERGED_REASONS for t in terminations
    )

    # summary string: unique reasons
    unique = list(dict.fromkeys(t for t in terminations))
    termination_summary = " | ".join(unique)

    # fid_err: mean across states
    fid_err = sum(fid_err_list) / len(fid_err_list) if fid_err_list else float("nan")

    reached_target = (fid_err <= fid_err_targ) if fid_err == fid_err else False
    converged      = all_converged or reached_target

    return converged, reached_target, termination_summary


def scan_convergence(
    directory: str | Path,
    method:    str | None = None,
    verbose:   bool = True,
) -> list[dict]:
    """
    Scan directory for JSON result files and check convergence.

    Parameters
    ----------
    directory : str | Path
    method    : optional filter on 'mode' field, e.g. 'GRAPE_AVG'
    verbose   : print summary

    Returns
    -------
    list of dicts, one per file, with keys:
        file, method, num_tslots, detuning, drive_error, lam,
        termination, fid_err, fid_err_targ, reached_target,
        converged, si, mean_err_ul, run_time_s
    """
    results = []

    for path in sorted(Path(directory).glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue

        row_method = data.get("mode", "unknown")
        if method is not None and row_method != method:
            continue

        cfg          = data.get("config", {})
        fid_err_targ = float(cfg.get("fid_err_targ", float("nan")))
        fid_err_list = data.get("err_hs_list", [])
        fid_err      = sum(fid_err_list) / len(fid_err_list) if fid_err_list else float("nan")
        err_ul_list  = data.get("err_ul_list") or []
        si           = data.get("si")
        run_time     = data.get("run_time")

        # parse lam from label if needed
        lam = None
        label = data.get("label", path.stem)
        m = re.search(r"lam([\d.]+)", label)
        if m:
            lam = float(m.group(1))

        converged, reached_target, termination = _check(data)

        results.append({
            "file":           path.name,
            "method":         row_method,
            "num_tslots":     cfg.get("num_tslots"),
            "detuning":       cfg.get("detuning"),
            "drive_error":    cfg.get("drive_error"),
            "lam":            lam,
            "termination":    termination,
            "fid_err":        fid_err,
            "fid_err_targ":   fid_err_targ,
            "reached_target": reached_target,
            "converged":      converged,
            "si":             si,
            "mean_err_ul":    sum(err_ul_list) / len(err_ul_list) if err_ul_list else None,
            "run_time_s":     run_time,
        })

    if verbose:
        n_total     = len(results)
        n_converged = sum(r["converged"] for r in results)
        n_not       = n_total - n_converged

        reasons: dict[str, int] = {}
        for r in results:
            reasons[r["termination"]] = reasons.get(r["termination"], 0) + 1

        print(f"\n{'─'*60}")
        print(f"  Directory : {directory}")
        if method:
            print(f"  Method    : {method}")
        print(f"  Total     : {n_total}")
        print(f"  Converged : {n_converged}")
        print(f"  NOT conv. : {n_not}")
        print(f"{'─'*60}")
        print(f"  Termination reasons:")
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {count:>4}x  {reason}")

        if n_not > 0:
            print(f"\n  Not converged:")
            print(f"  {'file':<55} {'termination':<25} {'fid_err':>10} {'si':>10}")
            print(f"  {'─'*55} {'─'*25} {'─'*10} {'─'*10}")
            for r in results:
                if not r["converged"]:
                    si_str  = f"{r['si']:.3e}"  if r["si"]  is not None else "n/a"
                    fid_str = f"{r['fid_err']:.3e}" if r["fid_err"] == r["fid_err"] else "n/a"
                    print(f"  {r['file']:<55} {r['termination']:<25} {fid_str:>10} {si_str:>10}")
        print(f"{'─'*60}\n")

    return results