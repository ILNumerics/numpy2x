"""Reproduces every number and chart of README.md's examples.

  example 1  loop     for i: ES[:i+1] = abs(sin(A[:, i])).sum(), A 1500 x 1500
                      (iterations must keep their order: each one overwrites
                      what the earlier ones wrote)
  example 2  kmeans   k-means as in the ILNumerics Accelerator benchmarks (a loop
                      over the points: distances to all centers, argmin; per
                      cluster nonzero and mean), 150^2 .. 1500^2 points
  example 3  toy      shape map of the programs without parallel potential (one
                      op per step: shape_map.py --groups single,dependent)
  note       few_ops  a few independent operations on 100 x 100 and 500 x 500

Each program runs unchanged as plain NumPy and on numpy2x: numpy2x.disabled()
makes numpy2x return plain NumPy arrays. A measurement is the best of several
runs; NumPy and numpy2x alternate over ROUNDS rounds, and the README shows the
median of the rounds. Results must be bit-identical.

Usage (Release build or pip install; one command for everything):
    python python/benchmarks/readme_examples.py            # all, then the charts
    python python/benchmarks/readme_examples.py --skip-toy # examples 1, 2, note only
    python python/benchmarks/readme_charts.py              # redraw from the results

Writes python/benchmarks/results/readme/examples.json, .../toy/shape_map.json
(committed: the README quotes them) and
docs/images/*.svg (readme_charts.py), and prints the README's numbers.
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

import numpy as onp

import numpy2x as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROUNDS = 4
KMEANS_SIZES = (150, 500, 1000, 1500)


def few_ops(a, b):
    c = np.sin(a) * b
    d = np.cos(b) - a
    e = np.exp(-a * a) + b
    return float((c + d + e).sum())


def loop(A):
    ES = np.zeros(A.shape[1])
    for i in range(A.shape[1]):
        ES[:i + 1] = np.abs(np.sin(A[:, i])).sum()
    return onp.array(ES)


def kmeans(X, k, rounds):
    n = X.shape[1]
    centers = X[:, np.linspace(0, n - 2, k, dtype=np.int64)].copy()
    classes = np.zeros((1, n))
    for _ in range(rounds):
        for i in range(n):
            dist = np.sqrt(np.sum(np.square(X[:, i, np.newaxis] - centers), axis=0))
            classes[0, i] = dist.argmin()
        for i in range(k):
            found = np.nonzero(classes == i)[1]
            in_class = X[:, found]
            if in_class.size > 0:
                centers[:, i] = in_class.mean(axis=1)
    return onp.array(classes), onp.array(centers)


def best(fn, data, reps):
    """Best time of `reps` runs; inputs are made fresh (as arrays of the mode)
    before each run."""
    t_best, result = float("inf"), None
    for _ in range(reps):
        args = tuple(np.asarray(x) if isinstance(x, onp.ndarray) else x for x in data)
        t = time.perf_counter()
        result = fn(*args)
        t_best = min(t_best, time.perf_counter() - t)
    return t_best, result


def identical(r1, r2):
    pairs = zip(r1, r2) if isinstance(r1, tuple) else [(r1, r2)]
    return all(onp.array_equal(onp.asarray(x), onp.asarray(y), equal_nan=True) for x, y in pairs)


def measure(name, fn, data, reps):
    """ROUNDS rounds of (numpy2x, NumPy), each the best of `reps` runs."""
    rounds = []
    for _ in range(ROUNDS):
        t_nx, r_nx = best(fn, data, reps)
        with np.disabled():
            t_np, r_np = best(fn, data, reps)
        rounds.append({"numpy_s": t_np, "numpy2x_s": t_nx, "speedup": t_np / t_nx,
                       "identical": identical(r_np, r_nx)})
    res = {"name": name,
           "numpy_s": statistics.median(r["numpy_s"] for r in rounds),
           "numpy2x_s": statistics.median(r["numpy2x_s"] for r in rounds),
           "speedup": statistics.median(r["speedup"] for r in rounds),
           "identical": all(r["identical"] for r in rounds),
           "rounds": rounds}
    print(f"{name:26s} NumPy {res['numpy_s'] * 1e3:8.2f} ms   numpy2x "
          f"{res['numpy2x_s'] * 1e3:8.2f} ms   {res['speedup']:4.2f}x "
          f"(rounds {', '.join(f'{r['speedup']:.2f}' for r in rounds)})   "
          f"identical: {res['identical']}", flush=True)
    return res


def machine():
    sys.path.insert(0, HERE)
    from suite import machine_info, physical_memory, usable_cores

    info = machine_info(usable_cores(), physical_memory())
    info["workers"] = np.workers()
    return info


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=os.path.join(HERE, "results", "readme"),
                   help="output directory (committed: the README quotes it)")
    p.add_argument("--skip-toy", action="store_true", help="no shape map (example 3)")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = onp.random.default_rng(0)

    results = {"machine": machine(), "rounds": ROUNDS, "examples": {}}
    print(results["machine"], flush=True)
    ex = results["examples"]
    ex["loop"] = [measure("loop 1500 x 1500", loop, (rng.standard_normal((1500, 1500)),), 5)]
    ex["kmeans"] = []
    for d in KMEANS_SIZES:
        X, k = rng.uniform(0, 10, size=(d, d)), min(50, d // 10)
        r = measure(f"kmeans {d} x {d}, k = {k}", lambda X, k=k: kmeans(X, k, 3), (X,),
                    5 if d < 1000 else 2)
        r.update(size=d, k=k)
        ex["kmeans"].append(r)
    ex["few_ops"] = []
    for n in (100, 500):
        a, b = rng.standard_normal((n, n)), rng.standard_normal((n, n))
        r = measure(f"few_ops {n} x {n}", few_ops, (a, b), 100)
        r.update(size=n)
        ex["few_ops"].append(r)
    path = os.path.join(args.out, "examples.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"written: {path}", flush=True)

    if not args.skip_toy:
        subprocess.run([sys.executable, os.path.join(HERE, "shape_map.py"), "--groups",
                        "single,dependent", "--out", os.path.join(args.out, "toy"),
                        "--reference"], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "readme_charts.py"), "--results",
                    args.out], check=True)


if __name__ == "__main__":
    main()
