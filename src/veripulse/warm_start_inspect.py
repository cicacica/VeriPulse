"""
warm_start_inspect.py
---------------------
Notebook-friendly helper: finds the best GRAPE run matching given parameters
and returns its amps + full metadata, ready to inspect before passing into
run_grape_si.

Two workflows
-------------
# 1. Auto: let the function pick the best file
ws = find_best_grape_run(
    data_dir    = "data/dummyless/",
    num_tslots  = 40,
    detuning    = 0.0,
    drive_error = 0.0,
    rank_by     = "si",
)

# 2. Manual: inspect the table, then load a specific file by name
ws = load_grape_run("data/dummyless/GRAPE_p40_det0.00_err0.00-3.json")

print(ws)
ws.plot_amps()
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np


# ── float comparison ─────────────────────────────────────────────────────────

def _feq(a: float, b: float, tol: float = 1e-9) -> bool:
    """Absolute-tolerance float equality. Safe against .2f rounding traps."""
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tol)


# ── ranking metric extractor ─────────────────────────────────────────────────

RankBy = Literal["si", "err_ul_mean", "err_ul_median"]

def _compute_scores(data: dict) -> dict[str, Optional[float]]:
    si_val = data.get("si")
    si = float(si_val) if si_val is not None else None

    raw = data.get("err_ul_list")
    if raw and len(raw) > 0:
        arr = np.array(raw, dtype=float)
        ul_mean   = float(np.mean(arr))
        ul_median = float(np.median(arr))
    else:
        ul_mean = ul_median = None

    return {"si": si, "err_ul_mean": ul_mean, "err_ul_median": ul_median}


# ── result container ──────────────────────────────────────────────────────────

@dataclass
class WarmStartResult:
    amps:          np.ndarray
    rank_by:       str
    rank_value:    float
    si:            Optional[float]
    err_ul_list:   Optional[list]
    err_ul_mean:   Optional[float]
    err_ul_median: Optional[float]
    path:          Path
    method:        str
    num_tslots:    int
    detuning:      float
    drive_error:   float
    lam:           Optional[float]
    config:        dict[str, Any] = field(default_factory=dict)
    raw:           dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        def fmt(v): return f"{v:.3e}" if v is not None else "n/a"
        lines = [
            "WarmStartResult",
            f"  source        : {self.path.name}",
            f"  method        : {self.method}",
            f"  tslots        : {self.num_tslots}",
            f"  detuning      : {self.detuning}",
            f"  drive_error   : {self.drive_error}",
            f"  lam           : {self.lam}",
            f"  ── metrics ──────────────────────",
            f"  si            : {fmt(self.si)}",
            f"  err_ul_mean   : {fmt(self.err_ul_mean)}",
            f"  err_ul_median : {fmt(self.err_ul_median)}",
        ]
        if self.err_ul_list is not None:
            per = "  ".join(f"{v:.3e}" for v in self.err_ul_list)
            lines.append(f"  err_ul_list   : [{per}]")
        lines += [
            f"  ── selected by '{self.rank_by}' = {fmt(self.rank_value)} ──",
            f"  amps          : shape {self.amps.shape}"
                              f"  min={self.amps.min():.3f}"
                              f"  max={self.amps.max():.3f}",
        ]
        if self.config:
            lines.append(f"  config        : {self.config}")
        return "\n".join(lines)

    def plot_amps(self, evo_time: Optional[float] = None) -> None:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available — skipping plot.")
            return

        t_total = evo_time or self.config.get("evo_time") or self.raw.get("evo_time") or 1.0
        t = np.linspace(0, t_total, self.amps.shape[0])
        si_str  = f"{self.si:.3e}" if self.si is not None else "n/a"
        ulm_str = f"{self.err_ul_mean:.3e}" if self.err_ul_mean is not None else "n/a"

        fig, ax = plt.subplots(figsize=(8, 3))
        for i in range(self.amps.shape[1]):
            ax.step(t, self.amps[:, i], where="post", label=f"ctrl {i}")
        ax.set_xlabel("Time (s)" if t_total != 1.0 else "Time slot")
        ax.set_ylabel("Amplitude")
        ax.set_title(
            f"Warm-start pulse  [{self.path.name}]\n"
            f"si={si_str}   err_ul_mean={ulm_str}   (ranked by '{self.rank_by}')"
        )
        ax.legend()
        plt.tight_layout()
        plt.show()


# ── filename parser ───────────────────────────────────────────────────────────

_FNAME_RE = re.compile(
    r"^(?P<method>.+?)_p(?P<tslots>\d+)"
    r"_det(?P<det>[\d.]+)"
    r"_err(?P<err>[\d.]+)"
    r"(?:_lam(?P<lam>[\d.]+))?"
    r"(?:-(?P<id>.+))?$"
)

def _parse_stem(stem: str) -> Optional[dict]:
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
    }


def _build_result(path: Path, data: dict, scores: dict,
                  meta: dict, rank_by: str, rank_score: float) -> Optional[WarmStartResult]:
    raw_amps = data.get("final_amps")
    if raw_amps is None:
        return None
    amps = np.array(raw_amps, dtype=float)
    return WarmStartResult(
        amps          = amps,
        rank_by       = rank_by,
        rank_value    = rank_score,
        si            = scores["si"],
        err_ul_list   = data.get("err_ul_list"),
        err_ul_mean   = scores["err_ul_mean"],
        err_ul_median = scores["err_ul_median"],
        path          = path,
        method        = meta["method"],
        num_tslots    = meta["num_tslots"],
        detuning      = meta["detuning"],
        drive_error   = meta["drive_error"],
        lam           = meta["lam"],
        config        = data.get("config", {}),
        raw           = data,
    )


# ── load by explicit path ─────────────────────────────────────────────────────

def load_grape_run(path: str | Path, rank_by: RankBy = "si") -> Optional[WarmStartResult]:
    """
    Load a WarmStartResult from an explicit JSON file path.

    Use this after inspecting the verbose table from find_best_grape_run
    and deciding which file you want to use manually.

    Parameters
    ----------
    path    : path to the JSON file
    rank_by : which metric to report as rank_value (default "si")
    """
    path = Path(path)
    meta = _parse_stem(path.stem)
    if meta is None:
        raise ValueError(f"Cannot parse filename: {path.name}")

    with open(path) as f:
        data = json.load(f)

    scores     = _compute_scores(data)
    rank_score = scores.get(rank_by) or 0.0

    result = _build_result(path, data, scores, meta, rank_by, rank_score)
    if result is None:
        raise ValueError(f"No final_amps found in {path.name}")

    print(f"[load_grape_run] loaded: {path.name}")
    print(f"  si            : {scores['si']:.3e}" if scores['si'] else "  si: n/a")
    print(f"  err_ul_mean   : {scores['err_ul_mean']:.3e}" if scores['err_ul_mean'] else "  err_ul_mean: n/a")
    print(f"  amps shape    : {result.amps.shape}")
    return result


# ── auto search ───────────────────────────────────────────────────────────────

def find_best_grape_run(
    data_dir:    str | Path,
    num_tslots:  int,
    detuning:    float,
    drive_error: float,
    *,
    rank_by:     RankBy = "si",
    verbose:     bool   = True,
) -> Optional[WarmStartResult]:
    """
    Scan data_dir for plain GRAPE runs matching parameters, print a ranked
    table, and return the best as a WarmStartResult.

    To pick a specific file instead of the best, copy the filename from the
    table and use load_grape_run("data/.../<filename>.json").

    Parameters
    ----------
    data_dir    : directory containing *.json result files
    num_tslots  : must match exactly
    detuning    : matched with abs tolerance 1e-9
    drive_error : same tolerance
    rank_by     : "si" | "err_ul_mean" | "err_ul_median"
    verbose     : print ranked table
    """
    data_dir = Path(data_dir)
    candidates = []

    for path in sorted(data_dir.glob("*.json")):
        meta = _parse_stem(path.stem)
        if meta is None:
            continue
        if meta["method"] != "GRAPE":
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

        scores     = _compute_scores(data)
        rank_score = scores[rank_by]
        if rank_score is None:
            if verbose:
                print(f"  [skip] {path.name} — '{rank_by}' not found in JSON")
            continue

        candidates.append((rank_score, scores, path, meta, data))

    if not candidates:
        if verbose:
            print(
                f"[find_best_grape_run] No matching GRAPE runs in '{data_dir}'\n"
                f"  (tslots={num_tslots}, detuning={detuning}, "
                f"drive_error={drive_error}, rank_by='{rank_by}')"
            )
        return None

    candidates.sort(key=lambda x: x[0])

    if verbose:
        def fmt(v): return f"{v:.3e}" if v is not None else "  n/a  "
        header = f"{'file':<45}  {'si':>9}  {'ul_mean':>9}  {'ul_median':>9}  {'rank':>9}"
        print(
            f"\n[find_best_grape_run] {len(candidates)} candidate(s) "
            f"(tslots={num_tslots}, det={detuning}, err={drive_error}, "
            f"rank_by='{rank_by}'):"
        )
        print("  " + header)
        print("  " + "-" * len(header))
        best_path = candidates[0][2]
        for rscore, sc, p, _, _ in sorted(candidates, key=lambda x: x[2].name):
            marker = " ← best" if p == best_path else ""
            print(
                f"  {p.name:<45}  "
                f"{fmt(sc['si']):>9}  "
                f"{fmt(sc['err_ul_mean']):>9}  "
                f"{fmt(sc['err_ul_median']):>9}  "
                f"{rscore:.3e}"
                f"{marker}"
            )
        print(f"\n  → to load manually: load_grape_run('{best_path}')")

    for rank_score, scores, path, meta, data in candidates:
        result = _build_result(path, data, scores, meta, rank_by, rank_score)
        if result is None:
            if verbose:
                print(f"  [skip] {path.name} has no final_amps")
            continue
        return result

    if verbose:
        print("[find_best_grape_run] No candidate with valid final_amps — returning None.")
    return None