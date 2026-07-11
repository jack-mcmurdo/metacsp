"""Tests for metacsp.utility.math (M1), pinned to the Java classes' behavior
(the enumeration orders below are what the Java main() methods print)."""

import numpy as np
import pytest

from metacsp.utility.math import (
    Binomial,
    Combination,
    Gaussian,
    Matrix,
    Permutation,
    PermutationsWithRepetition,
    PowerSet,
)


def test_binomial():
    assert Binomial.binomial(4, 2) == 6
    assert Binomial.binomial(10, 3) == 120
    assert Binomial.binomial(5, 0) == 1
    assert Binomial.binomial(0, 3) == 0
    assert Binomial.binomial(52, 5) == 2598960


def test_combination_java_order():
    # Java: new Combination(4, 2) prints these, in this order
    assert list(Combination(4, 2)) == [
        [0, 1],
        [0, 2],
        [0, 3],
        [1, 2],
        [1, 3],
        [2, 3],
    ]


def test_combination_has_next_protocol():
    c = Combination(3, 3)
    assert c.has_next()
    assert c.next() == [0, 1, 2]
    assert not c.has_next()
    assert c.next() is None


def test_permutation_java_order():
    # Java: new Permutation(3, 2) enumerates all 6 ordered pairs
    assert list(Permutation(3, 2)) == [
        [0, 1],
        [0, 2],
        [1, 0],
        [1, 2],
        [2, 0],
        [2, 1],
    ]
    assert len(list(Permutation(4, 3))) == 24


def test_permutations_with_repetition():
    v = PermutationsWithRepetition(5, 3).get_variations()
    assert len(v) == 125
    # column 0 varies fastest (Java table layout)
    assert v[0] == [0, 0, 0]
    assert v[1] == [1, 0, 0]
    assert v[5] == [0, 1, 0]
    assert v[124] == [4, 4, 4]


def test_power_set():
    ps = PowerSet.power_set(["One", "Two", "Three"])
    assert len(ps) == 8
    assert [] in ps
    assert ["One", "Two", "Three"] in ps
    # deterministic: same input, same order
    assert ps == PowerSet.power_set(["One", "Two", "Three"])


def test_gaussian():
    assert Gaussian.phi(0.0) == pytest.approx(0.3989422804014327)
    assert Gaussian.phi(1.0, 1.0, 2.0) == pytest.approx(Gaussian.phi(0.0) / 2.0)
    assert Gaussian.Phi(0.0) == pytest.approx(0.5)
    assert Gaussian.Phi(-9.0) == 0.0
    assert Gaussian.Phi(9.0) == 1.0
    assert Gaussian.Phi(1.96) == pytest.approx(0.975, abs=1e-3)
    # round-trip as in the Java test client
    assert Gaussian.PhiInverse(Gaussian.Phi(1.234)) == pytest.approx(1.234, abs=1e-6)


def test_matrix():
    a = Matrix([[1.0, 2.0], [3.0, 4.0]])
    assert (a.M, a.N) == (2, 2)
    assert a.transpose().data.tolist() == [[1.0, 3.0], [2.0, 4.0]]
    assert a.plus(a).data.tolist() == [[2.0, 4.0], [6.0, 8.0]]
    assert a.minus(a).eq(Matrix(2, 2))
    ident = Matrix.identity(2)
    assert a.times(ident).eq(a)
    b = Matrix([[5.0], [6.0]])
    x = a.solve(b)
    assert np.allclose(a.times(x).data, [[5.0], [6.0]])
    with pytest.raises(RuntimeError):
        a.times(b.transpose())
    with pytest.raises(RuntimeError):
        Matrix([[1.0, 1.0], [1.0, 1.0]]).solve(b)
    assert Matrix.to_string([[1, 2], [3, 4]]) == "[1, 2]\n[3, 4]\n"
