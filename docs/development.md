# Development

How to build, test, change and release numpy2x.

## Layout

```
include/numpy2x/   public C ABI (numpy2x.h), the only interface the Python bridge uses
src/runtime/       runtime core: arrays, tasks, stage events, workers, element pool
src/kernels/       adapters that call NumPy's loops (ufuncs, reductions, matmul, gufuncs, sort)
src/capi/          implementation of the C ABI
python/numpy2x/    Python package (_numpy2x.c: per-op hot path; Python fallbacks and wrappers)
python/tests/      pytest, every result compared with NumPy
python/benchmarks/ benchmark scripts and suite
tests/             C and C++ tests
docker/            Linux, Windows and Wine images
.github/workflows/ ci.yml (build and test on every push and PR), wheels.yml (wheels, releases)
```

## Build and test

`dev.cmd` (Windows, also by double-click) and `./dev.sh` (Linux) pull, build into `.venv` and
run the tests; run programs with `.venv\Scripts\python -m numpy2x prog.py` (Linux:
`.venv/bin/python -m numpy2x prog.py`). Later builds are incremental. Options:
`dev.cmd -NoPull -NoTest -Python <python.exe>`, `./dev.sh --no-pull --no-test`,
`PYTHON=python3.13 ./dev.sh`.

With CMake directly:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure            # needs: pip install pytest
PYTHONPATH=build/python python3 -m pytest -q python/tests
```

`pip wheel .` builds a wheel (`numpy2x-*.whl`) to install on other machines with the same
platform, Python version and architecture.

Every test compares numpy2x with NumPy running the same code: results must be bit-identical
(values, dtypes, shapes, strides, warnings, errors).

## Benchmarks

```bash
PYTHONPATH=build/python python3 python/benchmarks/readme_examples.py   # the README's examples and charts
PYTHONPATH=build/python python3 python/benchmarks/suite.py [--quick]   # ~100 programs, HTML report
PYTHONPATH=build/python python3 python/benchmarks/array_pipelining.py
```

Use a Release build. Reports go to `./reports` (untracked).

## Docker

Images for Linux, Windows (native, MSVC) and Windows under Wine build this checkout, run all
test suites by default and serve as a command line ([docker/README.md](../docker/README.md)):

```bash
docker build -f docker/linux/Dockerfile -t numpy2x:linux .
docker run --rm numpy2x:linux                                # all test suites
docker run --rm -v "$PWD:/work" numpy2x:linux python prog.py # run a program with numpy2x
```

## Rules for changes

- **Results stay bit-identical to NumPy**: values, dtypes, shapes, strides, flags, warnings and
  errors. numpy2x is a drop-in: no numpy2x-specific errors or results, no own kernels, no
  reordered sums, no fusion. What cannot run asynchronously with NumPy's semantics falls back
  to NumPy.
- **Two worker threads** (`worker_threads()` in `src/runtime/workers.cpp`), fixed: no option,
  environment variable or API argument for it.
- Every new operation gets a test against NumPy and a test that it runs asynchronously
  (`python/tests/async_path.py`).
- Changes to kernels, the issue path or the bridge's per-op code are performance changes:
  measure them against `main` and give the numbers in the pull request.
- Linux and Windows behave identically and run the same tests.
- The Python bridge reaches the runtime only through `include/numpy2x/numpy2x.h` (C ABI, `nx_`
  prefix); C++ lives in `namespace numpy2x`; Python is included via `src/numpy2x_python.h`.
- English for code, comments, docs and commit messages; format C/C++ with `clang-format -i`
  (`.clang-format`). Keep `README.md` short and its numbers measured
  (`python/benchmarks/readme_examples.py`).
- Build and run the tests before every commit; changes reach `main` through pull requests,
  merged when `ci` is green.

## Releases

The version is set in one place: `project(numpy2x VERSION x.y.z ...)` in `CMakeLists.txt`.
`pyproject.toml`, `numpy2x.__version__`, `nx_version()` and the version test take it from there.
Numbers follow semantic versioning: `x.y.z+1` for fixes, `x.y+1.0` for new features, `x+1.0.0`
for incompatible changes.

1. Change the version in `CMakeLists.txt` in a pull request and merge it once `ci` is green.
2. Tag the merge commit with `v` and the version, and push the tag:

   ```bash
   git checkout main && git pull
   git tag -a v1.0.1 -m "numpy2x 1.0.1"
   git push origin v1.0.1
   ```

3. The tag starts the `wheels` workflow (`.github/workflows/wheels.yml`):
   - it stops at once unless the tag matches the version in `CMakeLists.txt`;
   - it builds the wheels (CPython 3.12 and 3.13; Windows x64, Linux x86_64 manylinux) and the
     sdist, and tests every wheel with the full pytest suite;
   - it creates the GitHub Release for the tag, with the wheels and the sdist attached;
   - it uploads them to PyPI (trusted publishing, environment `pypi`; only while the repository
     variable `PYPI_PUBLISH` is `true`).
4. Add a title and release notes to the GitHub Release.

PyPI accepts each version only once: a broken release is fixed with a new version, never by
uploading the same one again. If the PyPI step failed, run the workflow again on the tag
(Actions, `wheels`, Run workflow, "Use workflow from": Tags, the tag); a run from a branch
does not upload. Every tagged release is a Released Version under the patent license
([PATENTS](../PATENTS)); branches and commits between releases are not.

A new Python version needs an entry in `[tool.cibuildwheel] build` in `pyproject.toml` and in
the matrix of `ci.yml`; until then, pip builds numpy2x from the sdist on it.
