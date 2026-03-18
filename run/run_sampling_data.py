import argparse
from pathlib import Path
from veripulse.pulse import run_grape_si, run_grape, run_crab, PulseConfig, PulseResult
from veripulse.gates import rx, rhox, pack_subspace_states, extract_subspace_states, Qobj, operator_to_vector, vector_to_operator
from numpy import pi, stack

save_dir = Path.cwd().parent/"data"
angles= [0, pi, pi/4, 5*pi/4, pi/2, 3*pi/2, 3*pi/4, 7*pi/4]
# initial states with a little noise 
err = 0
rho_init = Qobj([[1-err, 0], [0, err]])
# target states 
rho_targets = [Qobj(rhox(a)) for a in angles]


def run_experiment(
    method: str,
    num_tslots: int,
    detuning: float,
    drive_error: float,
    identification: int,
) -> PulseResult:

    cfg = PulseConfig(
        num_tslots=num_tslots,
        detuning=detuning,
        drive_error=drive_error,
        max_iter=20000, # (int) Cap of iterations
        max_wall_time=500000,  #(s) Cap of compute time
    )

    label = f"{method}_p{num_tslots}_det{detuning:.2f}_err{drive_error:.2f}-{identification}"
    #print(f"\nRunning: {label}")
    #cfg.print()

    if method in ("CRAB", "GRAPE"):
        run_fn = run_crab if method == "CRAB" else run_grape
        results = []
        for rho_targ in rho_targets:
            res = run_fn(
                operator_to_vector(rho_init),
                operator_to_vector(rho_targ),
                config=cfg,
            )
            results.append(res)
        
        pr = PulseResult(
            config=cfg,
            mode=method,
            results=results,
            rho_targets=rho_targets,
            final_amps=stack([r.final_amps for r in results]),
            state_labels=angles,
            label=label,
        )

    elif method == "GRAPE_AVG":
        vRho_init, vRho_target, U_big = pack_subspace_states(
            rotations=[rx(t) for t in angles],
            rho_init=rho_init,
        )
        result = run_grape_si(vRho_init, vRho_target, U_big, lam=400, config=cfg)

        pr = PulseResult(
            config=cfg,
            mode="GRAPE_AVG",
            result=result,
            rho_targets=list(vRho_target),
            final_amps=result.final_amps,
            state_labels=state_labels,
            label=label,
        )
    else:
        raise ValueError(f"Unknown method '{method}'. Choose CRAB, GRAPE, or GRAPE_AVG")

    #pr.display()

    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        pr.save(save_dir / f"{label}.json")

    return pr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pulse optimisation experiment", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", "--method",     type=str,   default="GRAPE",  choices=["CRAB", "GRAPE", "GRAPE_AVG"], help="Optimisation method")
    parser.add_argument("-p", "--num_tslots", type=int,   default=100, help="number of pulse slots")
    parser.add_argument("-d", "--detuning",   type=float, default=0.0, help="detuning")
    parser.add_argument("-e", "--drive_error",type=float, default=0.0, help="miscalibration in control, coherent noise")
    parser.add_argument("-i", "--identification",  type=int,  default=0, help="id for sampling")
    parser.add_argument("-n", "--num_experiment", type=int, default=0, help="create in a loop for 1..n, thus executed in serial")
    args = parser.parse_args()

    if args.num_experiment > 0 :
        # do loop
        for i in range(1,args.num_experiment+1):
            run_experiment(
                method=args.method,
                num_tslots=args.num_tslots,
                detuning=args.detuning,
                drive_error=args.drive_error,
                identification=i,
            )
    else :     
        run_experiment(
            method=args.method,
            num_tslots=args.num_tslots,
            detuning=args.detuning,
            drive_error=args.drive_error,
            identification=args.identification,
        )