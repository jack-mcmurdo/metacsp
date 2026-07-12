"""Smoke tests for examples/tutorial/ (M23): each of the 8 ported
meta-csp-tutorial demo scripts is run via subprocess with immediately-closed
stdin (``input=""``) and asserted to exit 0 -- the 4 coordination demos exit
on their own; the 4 interactive dispatching/planning demos exit via the
``EOFError`` break in their stdin loop (see each script's own docstring).

Examples are not tests in spirit (see examples/README.md), but PLAN.md's
M23 acceptance criterion asks for this subprocess smoke test specifically,
so it lives here rather than duplicating example logic via import.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_TUTORIAL_DIR = Path(__file__).resolve().parents[1] / "examples" / "tutorial"
_TIMEOUT_S = 30

# (script path relative to examples/tutorial/, substrings expected in stdout)
_CASES = [
    ("coordination/test_trajectory_envelope_representation_three_robots.py", ["VARIABLE INFO"]),
    ("coordination/test_trajectory_envelope_refinement.py", ["Refinement added"]),
    ("coordination/test_trajectory_envelope_scheduling.py", ["Solved? True"]),
    ("coordination/test_trajectory_envelope_control.py", ["Solved? True"]),
    (
        "dispatching/simple_dispatching_example_manual_specification.py",
        ["Constraints consistent? True"],
    ),
    ("dispatching/simple_dispatching_example.py", ["Constraints consistent? True"]),
    (
        "dispatching/simple_dispatching_and_scheduling_example.py",
        ["Constraints consistent? True", "Solved? True"],
    ),
    ("planning/test_proactive_planning_and_dispatching.py", ["Executing activities"]),
]


@pytest.mark.parametrize("script,expected", _CASES, ids=[c[0] for c in _CASES])
def test_tutorial_example_runs_clean(script: str, expected: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(_TUTORIAL_DIR / script)],
        input="",
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        cwd=str(_TUTORIAL_DIR.parents[1]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in expected:
        assert marker in result.stdout, f"missing {marker!r} in stdout:\n{result.stdout}"
