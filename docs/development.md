# Development

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
