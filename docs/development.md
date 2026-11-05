# Development

How numpy2x is built, tested, measured and released. For using numpy2x, see the
[README](../README.md) and [testing.md](testing.md).

## How it works

numpy2x intercepts NumPy operations (through NumPy's array protocols and, with
`python -m numpy2x`, its own module) and issues each one as a task. The Python thread only
issues tasks and runs ahead; two worker threads run each task as soon as its inputs are
computed. Every task calls the inner loops of the installed NumPy (ufunc, reduction, gufunc and
sort loops), exactly as NumPy calls them, so results are bit-identical to NumPy. Whatever numpy2x
does not run itself falls back to NumPy, after waiting for the data it reads.

## Repository layout

```
include/numpy2x/numpy2x.h  C interface of the runtime; the Python bridge uses only this
src/runtime/               runtime: arrays, tasks, worker pool, element memory pool,
                           copy-on-write, layouts; no Python dependency
                           (workers.cpp: the number of worker threads)
src/kernels/               adapters that call NumPy's loops (element-wise, reductions,
                           matmul, gufuncs, sort)
src/capi/capi.cpp          implementation of the C interface
python/numpy2x/            Python package: _numpy2x.c (C extension, the per-operation hot
                           path), _ndarray.py (array class, fallbacks), _ufuncs.py, _linalg.py,
                           _fft.py, _join.py, _indexing.py, _compose.py, _sort.py
python/_numpy2x_hook.py    `import numpy` gives numpy2x in user code (python -m numpy2x,
                           NUMPY2X=1 through numpy2x.pth)
python/tests/              pytest suite: every test compares with NumPy
python/benchmarks/         README examples, benchmark suite, shape maps
tests/                     C/C++ tests (CTest)
docker/                    Linux, Windows and Wine images
tools/dev.ps1, dev.cmd, dev.sh   one-command build and test
.github/workflows/         ci.yml (build + tests), wheels.yml (wheels, releases, PyPI)
```

## Build and test

`dev.cmd` (Windows, also by double-click) and `./dev.sh` (Linux) pull, build into `.venv` and
run the tests; run programs with `.venv\Scripts\python -m numpy2x prog.py` (Linux:
`.venv/bin/python -m numpy2x prog.py`). Later builds are incremental. Options:
`dev.cmd -NoPull -NoTest -Python <python.exe>`, `./dev.sh --no-pull --no-test`,
`PYTHON=python3.13 ./dev.sh`.

Requirements: Python >= 3.12 (64 bit), NumPy >= 2.5, CMake >= 3.24 and a C++20 compiler
(Visual Studio 2022 with the C++ workload on Windows, GCC or Clang on Linux); pip fetches CMake
and Ninja itself.

With CMake directly:

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure            # needs: pip install pytest
PYTHONPATH=build/python python3 -m pytest -q python/tests
```

`pip wheel .` builds a wheel (`numpy2x-*.whl`) to install on other machines with the same
platform, Python version and architecture.

## Rules for changes

- **Bit-identical to NumPy.** Every result must equal plain NumPy's: values, dtypes, shapes,
  strides, warnings and errors. Never trade this for speed: no own kernels, no reordered sums.
- **Test against NumPy.** Every new operation needs a test that runs the same code with numpy2x
  and with NumPy and compares the results, and a test that it actually runs asynchronously
  (`python/tests/async_path.py`: `assert_async`).
- **Measure performance changes.** Changes to kernels, the issue path or the per-operation code
  are performance changes: compare with `main` (benchmark suite, cases the change targets)
  before merging.
- **Linux and Windows behave the same.** Platform-specific code stays behind small functions
  with one implementation per platform; CI tests both.
- **Two worker threads, single-stage execution.** The number of worker threads
  (`src/runtime/workers.cpp`) and the execution model (a task starts when its inputs are
  completely computed) are conditions of the patent license ([PATENTS](../PATENTS)). Changes to
  either are not covered by that license; see "Licenses" below.
- Formatting: `.clang-format` (C/C++). Code, comments and commit messages in English.

## Continuous integration

`ci.yml` runs on every push to `main` and on pull requests: pip build and the pytest suite on
Linux (GCC) and Windows (MSVC) with Python 3.12 and 3.13, and `tools/dev.ps1` as started from
Visual Studio's developer prompt. Pull requests are merged only with green CI.

## Benchmarks

```bash
PYTHONPATH=build/python python3 python/benchmarks/readme_examples.py   # the README's examples and charts
PYTHONPATH=build/python python3 python/benchmarks/suite.py [--quick]   # ~100 programs, HTML report
PYTHONPATH=build/python python3 python/benchmarks/array_pipelining.py
```

Use a Release build and an otherwise idle machine. Reports go to `./reports` (untracked).
`readme_examples.py` replaces the committed results in `python/benchmarks/results/readme` and
the charts in `docs/images`; commit them only from a run whose results are all bit-identical.

## Docker

Images for Linux, Windows (native, MSVC) and Windows under Wine build this checkout, run all
test suites by default and serve as a command line ([docker/README.md](../docker/README.md)):

```bash
docker build -f docker/linux/Dockerfile -t numpy2x:linux .
docker run --rm numpy2x:linux                                # all test suites
docker run --rm -v "$PWD:/work" numpy2x:linux python prog.py # run a program with numpy2x
```

## Releasing

The version is set in one place: `project(numpy2x VERSION x.y.z ...)` in the top-level
`CMakeLists.txt`. The package version (pyproject reads it), `numpy2x.__version__` and the version
test all take it from there.

1. On `main`, change the version in `CMakeLists.txt` and merge it (commit message
   `numpy2x x.y.z`). CI must be green. Versions follow semantic versioning: x.y.(z+1) for fixes,
   x.(y+1).0 for new features, (x+1).0.0 for incompatible changes.
2. Tag that commit with the same version and push the tag:

   ```bash
   git checkout main
   git pull origin main
   git tag -a vx.y.z -m "numpy2x x.y.z"
   git push origin vx.y.z
   ```

3. The tag starts `wheels.yml`. It first checks that the tag matches the version in
   `CMakeLists.txt` and stops otherwise; then it builds the wheels (CPython 3.12 and 3.13, Windows
   x64 and Linux x86_64 manylinux) and the sdist, runs the full test suite on each wheel, creates
   the GitHub Release `vx.y.z` with these files and uploads them to PyPI.
4. Add the title and release notes to the GitHub Release.
5. Check: `pip install numpy2x==x.y.z` in a fresh environment, `numpy2x.__version__`, and the
   project page on https://pypi.org/project/numpy2x/.

Notes:

- PyPI accepts each version only once. A broken release is fixed with a new version, not by
  uploading the same one again.
- The PyPI upload uses trusted publishing: the GitHub environment `pypi` and the repository
  variable `PYPI_PUBLISH = true` (a repository variable, not a secret or an environment
  variable) must exist; the PyPI project trusts `ILNumerics/numpy2x`, workflow `wheels.yml`,
  environment `pypi`.
- If the upload was skipped or failed, rerun it for the existing tag: Actions → wheels →
  Run workflow → "Use workflow from": Tags → the tag. A run on `main` builds and tests but
  neither releases nor uploads.
- New Python versions need an entry in the build matrix of `wheels.yml` (and `ci.yml`);
  until then, users on them build from the sdist.
- Every tagged release is a "Released Version" under the patent license; branches and commits
  between releases are not.

## Licenses

The code is under the Clear BSD License ([LICENSE](../LICENSE)); contributions are accepted
under the same license. numpy2x implements methods patented by ILNumerics; their use is licensed
by [PATENTS](../PATENTS). Versions that run more than two worker threads per process, perform
staged execution or are adapted to other languages, array libraries or runtimes are not covered
by that license, also as forks. Third-party notices: [NOTICE](../NOTICE). Patents:
https://ilnumerics.net/patents.html.
