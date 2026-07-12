"""Port of tests/multi/TestPoseClass.java.

The Java test drives 1000 random trials per section with
``java.util.Random``; ported here with Python's ``random`` (seeded for
determinism) since the exact sequence of random values is not part of the
oracle -- only the assertions (2D vs. 2D equality, 3D vs. 3D equality, and
that comparing a 2D pose to a 3D one is an error) are.
"""

from __future__ import annotations

import math
import random

import pytest

from metacsp.multi.spatio_temporal.paths.pose import Pose

_NUM_TESTS = 1000


def test_pose_2d_compared_to_2d() -> None:
    rand = random.Random(42)
    for _ in range(_NUM_TESTS):
        yaw = -math.pi + 2 * math.pi * rand.random()
        p1 = Pose(rand.random(), rand.random(), yaw)
        p2 = Pose(p1.x, p1.y, p1.theta)
        x = 1 if p1.x == 0 else 2 * p1.x
        p3 = Pose(x, 0, 0)
        assert p1.is_pose2d
        assert p2.is_pose2d
        assert p3.is_pose2d
        assert p1 == p2
        assert p1 != p3


def test_pose_3d_compared_to_3d() -> None:
    rand = random.Random(43)
    for _ in range(_NUM_TESTS):
        roll1 = -math.pi + 2 * math.pi * rand.random()
        pitch1 = -math.pi + 2 * math.pi * rand.random()
        yaw1 = -math.pi + 2 * math.pi * rand.random()
        p1 = Pose(rand.random(), rand.random(), rand.random(), roll1, pitch1, yaw1)
        p2 = Pose(p1.x, p1.y, p1.z, p1.roll, p1.pitch, p1.yaw)
        x3 = 1 if p1.x == 0 else 2 * p1.x
        p3 = Pose(x3, 0, 0, 0, 0, 0)
        assert not p1.is_pose2d
        assert not p2.is_pose2d
        assert not p3.is_pose2d
        assert p1 == p2
        assert p1 != p3


def test_pose_2d_compared_to_3d_raises() -> None:
    rand = random.Random(44)
    for _ in range(_NUM_TESTS):
        roll = -math.pi + 2 * math.pi * rand.random()
        pitch = -math.pi + 2 * math.pi * rand.random()
        yaw = -math.pi + 2 * math.pi * rand.random()
        p1 = Pose(rand.random(), rand.random(), rand.random(), roll, pitch, yaw)
        p2 = Pose(p1.x, p1.y, p1.theta)
        assert not p1.is_pose2d
        assert p2.is_pose2d
        with pytest.raises(RuntimeError):
            _ = p1 == p2
