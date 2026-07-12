"""Port of examples/AckermannTest.java.

Unrelated to the geometry package itself; a plain recursion stress test
bundled among the M10 examples in the Java source tree. The recursion
limit is raised because CPython's default (1000) is far below the call
depth needed to evaluate ack(4, 1), unlike the JVM's default thread stack.
"""

from __future__ import annotations

import sys


def ack(m: int, n: int) -> int:
    if m == 0:
        return n + 1
    if n == 0:
        return ack(m - 1, 1)
    return ack(m - 1, ack(m, n - 1))


def main() -> None:
    sys.setrecursionlimit(1_000_000)
    print(ack(4, 1))


if __name__ == "__main__":
    main()
