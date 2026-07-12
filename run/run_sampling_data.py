import argparse
from pathlib import Path
from veripulse.pulse import run_grape_si, run_grape, run_crab, PulseConfig, PulseResult
from veripulse.gates import rx, rhox, hadamard, hadamardZ, pack_subspace_states, extract_subspace_states, Qobj, operator_to_vector, vector_to_operator
from numpy import pi, stack
import time


def run_experiment(
    method: str,
    num_tslots: int,
    detuning: float,
    dummy:bool,
    drive_error: float,
    identification: int,
    lam:float,
    verbose:bool,
) -> PulseResult:

    cfg = PulseConfig(
        num_tslots=num_tslots,
        detuning=detuning,
        drive_error=drive_error,
        max_iter=20000, # (int) Cap of iterations
        max_wall_time=200000,  #(s) Cap of compute time
        fid_err_targ=1e-10
    )
    
    # dummyless
   
    angles= [0, pi/4, pi/2, 3*pi/4, pi, 5*pi/4, 3*pi/2, 7*pi/4]
    err = 0 # initial states with a little noise 
    rho_init = Qobj([[1-err, 0], [0, err]])
    rho_targets = [Qobj(rhox(a)) for a in angles]
    unitary_rotations=[rx(t) for t in angles]
    
    # with dummy 
    if dummy == True : 
        save_dir = Path.cwd().parent/"data/dummy"
        angles = ["+", "-"]
        rho_targets = [Qobj([[0.5, 0.5],[0.5, 0.5]]), Qobj([[0.5, -0.5],[-0.5, 0.5]]) ]
        unitary_rotations = [hadamard(), hadamardZ()]
    else: 
        save_dir = Path.cwd().parent/"data/dummyless" 
 
    if method in ("CRAB", "GRAPE"):
        label = f"{method}_p{num_tslots}_det{detuning:.2f}_err{drive_error:.2f}-{identification}"
        run_fn = run_crab if method == "CRAB" else run_grape
        results = []

        s_time = time.time()
        for rho_targ in rho_targets:
            res = run_fn(
                operator_to_vector(rho_init),
                operator_to_vector(rho_targ),
                config=cfg,
            )
            results.append(res)
        e_time = time.time()
        
        pr = PulseResult(
            config=cfg,
            mode=method,
            results=results,
            rho_targets=rho_targets,
            final_amps=stack([r.final_amps for r in results]),
            state_labels=angles,
            label=label,
            run_time=e_time - s_time
        )

    elif method == "GRAPE_AVG":
        # also add ratio
        label = f"{method}_p{num_tslots}_det{detuning:.2f}_err{drive_error:.2f}-lam{lam:.4f}-{identification}"
        vRho_init, vRho_target, U_big = pack_subspace_states(
            rotations=unitary_rotations,
            rho_init=rho_init,
        )
        s_time = time.time()
        result = run_grape_si(vRho_init, vRho_target, U_big, lam=lam, config=cfg)
        e_time = time.time()
        pr = PulseResult(
            config=cfg,
            mode="GRAPE_AVG",
            result=result,
            rho_targets=rho_targets,
            final_amps=result.final_amps,
            label=label,
            state_labels=angles,
            run_time=e_time - s_time
        )
    else:
        raise ValueError(f"Unknown method '{method}'. Choose CRAB, GRAPE, or GRAPE_AVG")

    if verbose:
        pr.display()

    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        pr.save(save_dir / f"{label}.json")

    return pr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pulse optimisation experiment", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-m", "--method",     type=str,   default="GRAPE",  choices=["CRAB", "GRAPE", "GRAPE_AVG"], help="Optimisation method")
    parser.add_argument("-p", "--num_tslots", type=int,   default=10, help="number of pulse slots")
    parser.add_argument("-det", "--detuning",   type=float, default=0.0, help="detuning")
    parser.add_argument("-dum", "--dummy", action="store_true", default=False, help="with dummy qubits")
    parser.add_argument("-e", "--drive_error",type=float, default=0.0, help="miscalibration in control, coherent noise")
    parser.add_argument("-i", "--identification", type=int, default=0, help="id for sampling")
    parser.add_argument("-n", "--num_experiment", type=int, default=0, help="create in a loop for 1..n, thus executed in serial")
    parser.add_argument("-l", "--lam", type=float, default=100, help="lambda as the proportion of the secret independent")
    parser.add_argument("-v", "--verbose", action="store_true", help="print stuff out")
    args = parser.parse_args()

    
    if args.num_experiment > 0 :
        # do loop
        for i in range(1,args.num_experiment+1):
            run_experiment(
                method=args.method,
                num_tslots=args.num_tslots,
                detuning=args.detuning,
                dummy=args.dummy,
                drive_error=args.drive_error,
                identification=i,
                lam=args.lam,
                verbose=args.verbose
            )
    else :     
        run_experiment(
            method=args.method,
            num_tslots=args.num_tslots,
            detuning=args.detuning,
            dummy=args.dummy,
            drive_error=args.drive_error,
            identification=args.identification,
            lam=args.lam,
            verbose=args.verbose
        )
