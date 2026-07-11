"""Port of the ``utility/`` math helpers (D8).

Java sources: utility/{Binomial,Combination,Gaussian,Matrix,Permutation,
PermutationsWithRepetition,PowerSet}.java. Same class and function names,
implemented with :mod:`math`/:mod:`numpy`.
"""

from __future__ import annotations

import math as _math
from typing import Any, Iterator, Sequence, TypeVar

import numpy as np
import numpy.typing as npt

__all__ = [
    "Binomial",
    "Combination",
    "Gaussian",
    "Matrix",
    "Permutation",
    "PermutationsWithRepetition",
    "PowerSet",
]

T = TypeVar("T")


class Binomial:
    """Port of utility/Binomial.java."""

    @staticmethod
    def binomial(n: int, k: int) -> int:
        """Return binomial(n, k); 0 when k > n (as the Java DP table yields)."""
        if k > n:
            return 0
        return _math.comb(n, k)


class Combination:
    """Port of utility/Combination.java.

    Enumerates nCr — all ways to choose ``r`` of ``n`` objects, order
    irrelevant, in the same lexicographic order as the Java class.
    """

    def __init__(self, n: int, r: int):
        self.n = n
        self.r = r
        self._index = list(range(r))
        self._has_next = True

    def has_next(self) -> bool:
        return self._has_next

    def next(self) -> list[int] | None:
        if not self._has_next:
            return None
        result = self._index[: self.r]
        self._move_index()
        return result

    def _move_index(self) -> None:
        i = self._rightmost_index_below_max()
        if i >= 0:
            self._index[i] += 1
            for j in range(i + 1, self.r):
                self._index[j] = self._index[j - 1] + 1
        else:
            self._has_next = False

    def _rightmost_index_below_max(self) -> int:
        for i in range(self.r - 1, -1, -1):
            if self._index[i] < self.n - self.r + i:
                return i
        return -1

    def __iter__(self) -> Iterator[list[int]]:
        while self.has_next():
            nxt = self.next()
            assert nxt is not None
            yield nxt


class Gaussian:
    """Port of utility/Gaussian.java."""

    @staticmethod
    def phi(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Gaussian pdf with mean ``mu`` and stddev ``sigma`` at ``x``."""
        z = (x - mu) / sigma
        return _math.exp(-z * z / 2) / _math.sqrt(2 * _math.pi) / sigma

    @staticmethod
    def Phi(z: float, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Gaussian cdf with mean ``mu`` and stddev ``sigma`` at ``z``.

        Uses the same Taylor approximation as the Java class.
        """
        z = (z - mu) / sigma
        if z < -8.0:
            return 0.0
        if z > 8.0:
            return 1.0
        total = 0.0
        term = z
        i = 3
        while total + term != total:
            total += term
            term = term * z * z / i
            i += 2
        return 0.5 + total * Gaussian.phi(z)

    @staticmethod
    def PhiInverse(y: float) -> float:
        """z such that Phi(z) = y, via bisection search."""
        lo, hi = -8.0, 8.0
        delta = 1e-8
        while hi - lo >= delta:
            mid = lo + (hi - lo) / 2
            if Gaussian.Phi(mid) > y:
                hi = mid
            else:
                lo = mid
        return lo + (hi - lo) / 2


class Matrix:
    """Port of utility/Matrix.java.

    A bare-bones M-by-N matrix of floats, numpy-backed. ``data`` is the
    underlying ``numpy.ndarray`` (Java exposed the raw ``double[][]``).
    """

    def __init__(self, m_or_data: int | Sequence[Sequence[float]] | npt.NDArray, n: int = -1):
        if isinstance(m_or_data, int):
            self.M = m_or_data
            self.N = n
            self.data = np.zeros((self.M, self.N), dtype=np.float64)
        else:
            self.data = np.array(m_or_data, dtype=np.float64)
            self.M, self.N = self.data.shape

    @staticmethod
    def random(m: int, n: int) -> Matrix:
        """An M-by-N matrix with values uniformly random in [0, 1)."""
        result = Matrix(m, n)
        result.data = np.random.random((m, n))
        return result

    @staticmethod
    def identity(n: int) -> Matrix:
        result = Matrix(n, n)
        result.data = np.eye(n, dtype=np.float64)
        return result

    def transpose(self) -> Matrix:
        return Matrix(self.data.T)

    def plus(self, b: Matrix) -> Matrix:
        if b.M != self.M or b.N != self.N:
            raise RuntimeError("Illegal matrix dimensions.")
        return Matrix(self.data + b.data)

    def minus(self, b: Matrix) -> Matrix:
        if b.M != self.M or b.N != self.N:
            raise RuntimeError("Illegal matrix dimensions.")
        return Matrix(self.data - b.data)

    def eq(self, b: Matrix) -> bool:
        if b.M != self.M or b.N != self.N:
            raise RuntimeError("Illegal matrix dimensions.")
        return bool(np.array_equal(self.data, b.data))

    def times(self, b: Matrix) -> Matrix:
        if self.N != b.M:
            raise RuntimeError("Illegal matrix dimensions.")
        return Matrix(self.data @ b.data)

    def solve(self, rhs: Matrix) -> Matrix:
        """x = A^-1 b, assuming A is square and has full rank."""
        if self.M != self.N or rhs.M != self.N or rhs.N != 1:
            raise RuntimeError(
                f"Illegal matrix dimensions:\nM1xN1 = {self.M}x{self.N}"
                f" and M2xN2 = {rhs.M}x{rhs.N}"
            )
        try:
            return Matrix(np.linalg.solve(self.data, rhs.data))
        except np.linalg.LinAlgError:
            raise RuntimeError("Matrix is singular.")

    @staticmethod
    def to_string(matrix: Sequence[Sequence[Any]]) -> str:
        """Java's static ``toString(Object[][])``: one ``[a, b, ...]`` row per line."""
        return "".join("[" + ", ".join(str(x) for x in row) + "]\n" for row in matrix)


class Permutation:
    """Port of utility/Permutation.java.

    Enumerates r-permutations of n integers without repetition, in the same
    order as the Java class.
    """

    def __init__(self, n: int, r: int):
        self.n = n
        self.r = r
        self._index = list(range(n))
        self._has_next = True
        self._reverse_after(r - 1)

    def has_next(self) -> bool:
        return self._has_next

    def next(self) -> list[int] | None:
        if not self._has_next:
            return None
        result = self._index[: self.r]
        self._move_index()
        return result

    def _move_index(self) -> None:
        i = self._rightmost_dip()
        if i < 0:
            self._has_next = False
            return
        smallest_to_right = i + 1
        for j in range(i + 2, self.n):
            if self._index[i] < self._index[j] < self._index[smallest_to_right]:
                smallest_to_right = j
        self._index[i], self._index[smallest_to_right] = (
            self._index[smallest_to_right],
            self._index[i],
        )
        if self.r - 1 > i:
            self._reverse_after(i)
            self._reverse_after(self.r - 1)

    def _reverse_after(self, i: int) -> None:
        self._index[i + 1 :] = self._index[i + 1 :][::-1]

    def _rightmost_dip(self) -> int:
        for i in range(self.n - 2, -1, -1):
            if self._index[i] < self._index[i + 1]:
                return i
        return -1

    def __iter__(self) -> Iterator[list[int]]:
        while self.has_next():
            nxt = self.next()
            assert nxt is not None
            yield nxt


class PermutationsWithRepetition:
    """Port of utility/PermutationsWithRepetition.java.

    Generates all r-permutations of n integers with repetition.
    """

    def __init__(self, n: int, r: int):
        self.n = n
        self.r = r

    def get_variations(self) -> list[list[int]]:
        """All n**r permutations, in the same order as the Java table."""
        permutations = self.n**self.r
        table = [[0] * self.r for _ in range(permutations)]
        for x in range(self.r):
            t2 = self.n**x
            p1 = 0
            while p1 < permutations:
                for al in range(self.n):
                    for _ in range(t2):
                        table[p1][x] = al
                        p1 += 1
        return table


class PowerSet:
    """Port of utility/PowerSet.java.

    Java returns ``Set<Set<T>>`` in unspecified HashSet order; per C7 this
    port returns a deterministic ``list[list[T]]`` (same recursive structure,
    insertion-ordered).
    """

    @staticmethod
    def power_set(original_set: Sequence[T]) -> list[list[T]]:
        items = list(original_set)
        if not items:
            return [[]]
        head, rest = items[0], items[1:]
        sets: list[list[T]] = []
        for subset in PowerSet.power_set(rest):
            sets.append([head] + subset)
            sets.append(subset)
        return sets
