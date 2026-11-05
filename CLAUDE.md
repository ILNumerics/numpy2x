# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

numpy2x runs ordinary NumPy programs on two worker threads next to the Python thread. Every
array operation becomes a task; the Python thread only issues tasks and runs ahead, and
independent tasks run concurrently. Each task calls the installed NumPy's own inner loops,
exactly as NumPy calls them. The core comes from viproc, a remake of the ILNumerics
Accelerator.

## Rules

- **Results are bit-identical to NumPy** (values, dtypes, shapes, strides, flags, warnings,
  errors). numpy2x is a semantic drop-in: never a numpy2x-specific error or a different result.
  No own kernels, no reordered sums, no fusion. Whatever cannot run asynchronously with NumPy's
  semantics falls back to NumPy.
- **The worker count is fixed at 2** (`worker_threads()` in `src/runtime/workers.cpp`). Do not
  add an option, environment variable or API argument for it.
- Decisions are local and made at runtime (is an input ready or pending?): no dependency graph,
  no ahead-of-time analysis.
- Bridges talk to the runtime only through `include/numpy2x/numpy2x.h` (C ABI, `nx_` prefix).
  C++ lives in `namespace numpy2x`. Include Python via `src/numpy2x_python.h`.
- Changes to kernels, the issue path or the bridge's per-op code are performance changes:
  measure them against `main`.
- Every new op needs a test against NumPy and a test that it runs asynchronously
  (`python/tests/async_path.py`).
- Linux and Windows behave identically; both run the same tests.
- English for code, comments, docs and commit messages. Format with `.clang-format`.
- Keep `README.md` short and the claims in it measured (`python/benchmarks/readme_examples.py`).

## Layout

```
include/numpy2x/  public C ABI
src/runtime/      runtime core: arrays, tasks, stage events, workers, element pool
src/kernels/      adapters calling NumPy's loops (ufuncs, reductions, matmul, gufuncs, sort)
src/capi/         C ABI implementation
python/numpy2x/   Python package (_numpy2x.c: per-op hot path; Python fallbacks and wrappers)
python/tests/     pytest, bit-identical to NumPy
python/benchmarks/ benchmark scripts and suite
tests/            C++ tests
docker/           Linux, Windows, Wine images
```

## Commands

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
PYTHONPATH=build/python python3 -m pytest -q python/tests
clang-format -i <files>
```

Always build and run the tests before committing.
