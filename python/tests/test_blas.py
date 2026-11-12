"""BLAS on one thread while the runtime runs (`_blas.py`), restored at
shutdown; LAPACK calls serialized only without control over the BLAS
threads."""

import numpy as np
import pytest

import numpy2x
from numpy2x import _blas, _linalg, _ufuncs


def test_blas_one_thread_and_restored():
    numpy2x.shutdown()
    before = _blas.threads()
    if before is None:
        pytest.skip("no BLAS library with a thread setting found")
    try:
        numpy2x.init()
        assert _blas.threads() == 1 and _blas.single()
        numpy2x.shutdown()
        assert _blas.threads() == before and not _blas.single()
    finally:
        numpy2x.init()


def _flags_seen(monkeypatch):
    seen = []
    real = _ufuncs.gufunc

    def spy(*args):
        seen.append(args[5])
        return real(*args)

    monkeypatch.setattr(_ufuncs, "gufunc", spy)
    return seen


def _inv80():
    a = np.random.default_rng(0).random((80, 80)) + 80 * np.eye(80)
    np.linalg.inv(numpy2x.asarray(a)).wait()


def test_lapack_not_serialized(monkeypatch):
    numpy2x.init()
    if not _blas.single():
        pytest.skip("no BLAS library with a thread setting found")
    seen = _flags_seen(monkeypatch)
    _inv80()
    assert not seen[-1] & _linalg._SERIAL


def test_lapack_serialized_without_blas_control(monkeypatch):
    numpy2x.init()
    seen = _flags_seen(monkeypatch)
    monkeypatch.setattr(_blas, "single", lambda: False)
    _inv80()
    assert seen[-1] & _linalg._SERIAL
