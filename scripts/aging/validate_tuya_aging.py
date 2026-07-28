#!/usr/bin/env python
"""不连接真机的 TuyaRobot 老化架构验证。"""

from __future__ import annotations

import inspect
import sys
import tempfile
import threading
import time
import unittest
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pytuyarobot.command_result import CommandResult

from tuya_aging.config import AgingOptions
from tuya_aging import constants
from tuya_aging.domain.context import AgingContext
from tuya_aging.domain.models import MotionOutcome
from tuya_aging.domain.policy import FailurePolicy
from tuya_aging.errors import (
    CommunicationResponseError,
    ConsecutiveMotionFailureError,
    EmptyResponseError,
)
from tuya_aging.device.gateway import TuyaGateway
from tuya_aging.motion.upper_runner import UpperMotionRunner
from tuya_aging.report.collector import ReportCollector
from tuya_aging.runtime.coordinator import AgingCoordinator


class MemoryReport:
    def __init__(self) -> None:
        self.values = defaultdict(float)
        self.rows = []

    def count(
        self, category: str, metric: str, amount: float = 1.0
    ) -> None:
        self.values[(category, metric)] += amount

    def set_max(self, category: str, metric: str, value: float) -> None:
        key = (category, metric)
        self.values[key] = max(self.values.get(key, value), value)

    def append(self, sheet: str, row: Any) -> None:
        self.rows.append((sheet, row))

    def event(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def save(self) -> None:
        return None


class FakeArm:
    def __init__(self, owner: "FakeUpperDevice", side: str) -> None:
        self.owner = owner
        self.side = side

    def set_upper_fresh_mode(self, _mode: int) -> int:
        return 1

    def send_upper_angles(
        self, values: Any, _speed: int, _gripper: int, **_kwargs: Any
    ) -> int:
        self.owner.angles[self.side] = tuple(values)
        self.owner.events.append(
            ("angle", self.side, self.owner.angle_group(values))
        )
        return 0

    def send_upper_coords(
        self, values: Any, _speed: int, **_kwargs: Any
    ) -> int:
        self.owner.coords[self.side] = tuple(values)
        self.owner.events.append(
            ("coord", self.side, self.owner.coord_group(values))
        )
        return 0

    def send_upper_angle(
        self,
        joint_id: int,
        value: float,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        angles = list(self.owner.angles[self.side])
        angles[joint_id - 1] = value
        self.owner.angles[self.side] = tuple(angles)
        self.owner.events.append(
            ("limit", self.side, joint_id, float(value))
        )
        return 0

    def get_upper_angles(self) -> Any:
        return self.owner.angles[self.side]

    def upper_jog_angle(
        self,
        joint_id: int,
        direction: int,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        value = constants.JOINT_SOFT_LIMITS[joint_id][direction]
        angles = list(self.owner.angles[self.side])
        angles[joint_id - 1] = value
        self.owner.angles[self.side] = tuple(angles)
        self.owner.events.append(
            ("joint_jog", self.side, joint_id, direction)
        )
        return 0

    def upper_jog_angle_increment(
        self,
        joint_id: int,
        increment: float,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        angles = list(self.owner.angles[self.side])
        angles[joint_id - 1] += increment
        self.owner.angles[self.side] = tuple(angles)
        self.owner.events.append(
            ("joint_increment", self.side, joint_id)
        )
        return 0

    def send_upper_coord(
        self,
        coord_id: int,
        value: float,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        coords = list(self.owner.coords[self.side])
        coords[coord_id - 1] = value
        self.owner.coords[self.side] = tuple(coords)
        self.owner.events.append(
            ("single_coord", self.side, coord_id, float(value))
        )
        return 0

    def get_upper_coords(self) -> Any:
        return self.owner.coords[self.side]


class FakeUpperBody:
    def __init__(self, owner: "FakeUpperDevice") -> None:
        self.owner = owner

    def set_upper_fresh_mode(self, _mode: int) -> int:
        return 1

    def get_upper_fresh_mode(self) -> list[int]:
        return [0, 0]

    def get_upper_angles(self) -> dict[str, Any]:
        return dict(self.owner.angles)

    def get_upper_coords(self) -> dict[str, Any]:
        return dict(self.owner.coords)

    def send_upper_angles(
        self,
        left: Any,
        _left_speed: int,
        _left_gripper: int,
        right: Any,
        _right_speed: int,
        _right_gripper: int,
        **_kwargs: Any,
    ) -> int:
        self.owner.angles = {
            "left": tuple(left),
            "right": tuple(right),
        }
        self.owner.events.append(
            ("angle", "both", self.owner.angle_group(left))
        )
        return 0

    def send_upper_coords(
        self,
        left: Any,
        _left_speed: int,
        right: Any,
        _right_speed: int,
        **_kwargs: Any,
    ) -> int:
        self.owner.coords = {
            "left": tuple(left),
            "right": tuple(right),
        }
        self.owner.events.append(
            ("coord", "both", self.owner.coord_group(left))
        )
        return 0

    def write_upper_coords(
        self,
        left: Any,
        _left_speed: int,
        right: Any,
        _right_speed: int,
        **_kwargs: Any,
    ) -> int:
        self.owner.coords = {
            "left": tuple(left),
            "right": tuple(right),
        }
        self.owner.events.append(
            ("write_coord", "both", self.owner.coord_group(left))
        )
        return 0

    def upper_jog_angle(
        self,
        joint_id: int,
        direction: int,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        value = constants.JOINT_SOFT_LIMITS[joint_id][direction]
        for side in ("left", "right"):
            angles = list(self.owner.angles[side])
            angles[joint_id - 1] = value
            self.owner.angles[side] = tuple(angles)
        self.owner.events.append(
            ("joint_jog", "both", joint_id, direction)
        )
        return 0

    def upper_jog_angle_increment(
        self,
        joint_id: int,
        increment: float,
        _speed: int,
        **_kwargs: Any,
    ) -> int:
        for side in ("left", "right"):
            angles = list(self.owner.angles[side])
            angles[joint_id - 1] += increment
            self.owner.angles[side] = tuple(angles)
        self.owner.events.append(
            ("joint_increment", "both", joint_id)
        )
        return 0


class FakeUpperDevice:
    def __init__(self) -> None:
        self.events: list[tuple[Any, ...]] = []
        self.angles = {
            "left": constants.ZERO_ANGLES,
            "right": constants.ZERO_ANGLES,
        }
        self.coords = dict(constants.COORD_INITIAL_COORDS)
        self.left_arm = FakeArm(self, "left")
        self.right_arm = FakeArm(self, "right")
        self.upper_body = FakeUpperBody(self)

    @staticmethod
    def angle_group(values: Any) -> int:
        for group in constants.ANGLE_GROUPS:
            if tuple(values) == tuple(group["left"]) or tuple(values) == tuple(
                group["right"]
            ):
                return int(group["group"])
        raise AssertionError(values)

    @staticmethod
    def coord_group(values: Any) -> int:
        for group in constants.COORD_GROUPS:
            if tuple(values) == tuple(group["left"]) or tuple(values) == tuple(
                group["right"]
            ):
                return int(group["group"])
        raise AssertionError(values)

    @staticmethod
    def call(func: Any, *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    def go_zero(self, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("zero",))
        self.angles = {
            "left": constants.ZERO_ANGLES,
            "right": constants.ZERO_ANGLES,
        }

    def move_to_coord_initial_pose(
        self, *_args: Any, **_kwargs: Any
    ) -> dict[str, Any]:
        self.events.append(("initial",))
        self.coords = dict(constants.COORD_INITIAL_COORDS)
        return dict(self.coords)

    @staticmethod
    def wait_until_stopped(*_args: Any, **_kwargs: Any) -> None:
        return None

    @staticmethod
    def assert_dual_vectors(
        actual: Any,
        expected: Any,
        _tolerance: float,
        _name: str,
    ) -> float:
        for side, target in expected.items():
            if tuple(actual[side]) != tuple(target):
                raise AssertionError((actual, expected))
        return 0.0


def options(**overrides: Any) -> AgingOptions:
    values = {
        "run_upper_motion": True,
        "run_chassis_motion": False,
        "monitor_only": False,
        "duration_hours": 0.0,
        "cycle_limit": 1,
        "upper_speed": 20,
        "jog_speed": 10,
        "upper_timeout": 1.0,
        "jog_timeout": 1.0,
        "monitor_interval": 0.01,
        "autosave_interval": 60.0,
        "chassis_forward_mps": 0.05,
        "chassis_rotate_rads": 0.1,
        "chassis_segment_seconds": 0.01,
        "report_dir": Path("."),
        "angle_tolerance": 0.1,
        "coord_tolerance": 1.0,
        "consecutive_failure_limit": 3,
        "consecutive_motion_failure_limit": 10,
        "auto_report_max_age": 1.0,
    }
    values.update(overrides)
    return AgingOptions(**values)


def upper_runner_with_fake() -> tuple[UpperMotionRunner, FakeUpperDevice]:
    report = MemoryReport()
    policy = FailurePolicy(10, report)
    context = AgingContext(
        options=options(),
        report=report,
        policy=policy,
        stop_event=threading.Event(),
        fatal=lambda *_args: None,
        upper_blocking_motion=threading.Event(),
    )
    device = FakeUpperDevice()
    return UpperMotionRunner(device, context), device


class PolicyTests(unittest.TestCase):
    def test_tenth_unanswered_command_stops(self) -> None:
        report = MemoryReport()
        policy = FailurePolicy(10, report)
        for _ in range(9):
            policy.record_command_response(
                "upper", responded=False, api="send_upper_angle"
            )
        with self.assertRaises(ConsecutiveMotionFailureError):
            policy.record_command_response(
                "upper", responded=False, api="send_upper_angle"
            )

    def test_success_resets_motion_failure_streak(self) -> None:
        report = MemoryReport()
        policy = FailurePolicy(10, report)
        failed = MotionOutcome(
            api="send_upper_angle",
            target="left",
            command_responded=True,
            motion_completed=True,
            reached=False,
            exceeded=False,
            expected=10,
            actual=0,
            error=10,
            elapsed=1,
        )
        passed = MotionOutcome(
            **{
                **failed.__dict__,
                "reached": True,
                "actual": 10,
                "error": 0,
            }
        )
        for _ in range(9):
            policy.record_motion("upper", failed)
        policy.record_motion("upper", passed)
        for _ in range(9):
            policy.record_motion("upper", failed)
        self.assertEqual(policy.action_streak["upper"], 9)


class GatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = MemoryReport()
        self.policy = FailurePolicy(10, self.report)
        self.gateway = TuyaGateway(self.report, self.policy)

    def test_timeout_and_empty_are_counted(self) -> None:
        def get_upper_angles_timeout() -> CommandResult:
            return CommandResult(
                ok=False,
                status_code=0,
                message="response timeout cmd=0x0040",
            )

        with self.assertRaises(CommunicationResponseError):
            self.gateway.upper(get_upper_angles_timeout)

        def get_upper_angles_empty() -> None:
            return None

        with self.assertRaises(EmptyResponseError):
            self.gateway.upper(get_upper_angles_empty)
        self.assertEqual(
            self.report.values[("上半身通信汇总", "超时")], 1
        )
        self.assertEqual(
            self.report.values[("上半身通信汇总", "空返回")], 1
        )


class ArchitectureTests(unittest.TestCase):
    def test_upper_only_does_not_create_chassis_threads(self) -> None:
        coordinator = AgingCoordinator.__new__(AgingCoordinator)
        coordinator.options = options()
        coordinator._report_worker = lambda: None
        coordinator.upper_monitor = SimpleNamespace(run=lambda: None)
        coordinator.chassis_monitor = SimpleNamespace(run=lambda: None)
        coordinator._run_upper_motion = lambda: None
        coordinator._run_chassis_motion = lambda: None
        names = {thread.name for thread in coordinator._build_threads()}
        self.assertIn("UpperMonitor", names)
        self.assertIn("UpperMotion", names)
        self.assertNotIn("ChassisMonitor", names)
        self.assertNotIn("ChassisMotion", names)

    def test_upper_and_chassis_motion_overlap(self) -> None:
        intervals: dict[str, tuple[float, float]] = {}

        class TimedRunner:
            def __init__(self, name: str) -> None:
                self.name = name

            def run(self) -> None:
                started = time.monotonic()
                time.sleep(0.05)
                intervals[self.name] = (started, time.monotonic())

        coordinator = AgingCoordinator.__new__(AgingCoordinator)
        coordinator.upper_runner = TimedRunner("upper")
        coordinator.chassis_runner = TimedRunner("chassis")
        coordinator.finished_lock = threading.Lock()
        coordinator.finished_motion = set()
        upper = threading.Thread(target=coordinator._run_upper_motion)
        chassis = threading.Thread(target=coordinator._run_chassis_motion)
        upper.start()
        chassis.start()
        upper.join()
        chassis.join()
        overlap = min(
            intervals["upper"][1], intervals["chassis"][1]
        ) - max(intervals["upper"][0], intervals["chassis"][0])
        self.assertGreater(overlap, 0)

    def test_normal_joint_jog_has_no_stop_call(self) -> None:
        source = inspect.getsource(UpperMotionRunner.run_jog_angles)
        self.assertNotIn(".upper_stop", source)

    def test_angle_groups_have_no_zero_between_three_groups(self) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_angle_groups()
        angle_events = [
            event for event in device.events if event[0] == "angle"
        ]
        self.assertEqual(
            angle_events,
            [
                ("angle", target, group)
                for target in ("left", "right", "both")
                for group in (1, 2, 3)
            ],
        )
        for target in ("left", "right", "both"):
            indexes = [
                device.events.index(("angle", target, group))
                for group in (1, 2, 3)
            ]
            self.assertNotIn(
                ("zero",),
                device.events[indexes[0] + 1 : indexes[2]],
            )

    def test_coord_groups_have_no_zero_between_three_groups(self) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_coord_groups()
        coord_events = [
            event for event in device.events if event[0] == "coord"
        ]
        self.assertEqual(
            coord_events,
            [
                ("coord", target, group)
                for target in ("left", "right", "both")
                for group in (1, 2, 3)
            ],
        )

    def test_joint_limits_zero_only_after_negative_positive_pair(
        self,
    ) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_joint_limits()
        self.assertEqual(device.events.count(("zero",)), 15)
        for side in ("left", "right"):
            for joint_id, limits in constants.JOINT_SOFT_LIMITS.items():
                negative = ("limit", side, joint_id, limits[0])
                positive = ("limit", side, joint_id, limits[1])
                negative_index = device.events.index(negative)
                positive_index = device.events.index(positive)
                self.assertLess(negative_index, positive_index)
                self.assertNotIn(
                    ("zero",),
                    device.events[negative_index + 1 : positive_index],
                )
                self.assertEqual(
                    device.events[positive_index + 1],
                    ("zero",),
                )

    def test_joint_jog_zero_only_after_direction_pair(self) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_jog_angles()
        self.assertEqual(device.events.count(("zero",)), 22)
        for target in ("left", "right", "both"):
            for joint_id in constants.JOINT_SOFT_LIMITS:
                negative = ("joint_jog", target, joint_id, 0)
                positive = ("joint_jog", target, joint_id, 1)
                negative_index = device.events.index(negative)
                positive_index = device.events.index(positive)
                self.assertLess(negative_index, positive_index)
                self.assertNotIn(
                    ("zero",),
                    device.events[negative_index + 1 : positive_index],
                )
                self.assertEqual(
                    device.events[positive_index + 1],
                    ("zero",),
                )

    def test_joint_increment_keeps_one_zero_per_action(self) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_jog_increments()
        actions = [
            event
            for event in device.events
            if event[0] == "joint_increment"
        ]
        self.assertEqual(len(actions), 21)
        self.assertEqual(device.events.count(("zero",)), 22)
        for action in actions:
            index = device.events.index(action)
            self.assertEqual(device.events[index + 1], ("zero",))

    def test_single_coords_zero_once_after_all_actions(self) -> None:
        runner, device = upper_runner_with_fake()
        runner.run_single_coords()
        actions = [
            event for event in device.events if event[0] == "single_coord"
        ]
        self.assertEqual(len(actions), 24)
        self.assertEqual(device.events.count(("zero",)), 1)
        self.assertGreater(
            device.events.index(("zero",)),
            max(device.events.index(action) for action in actions),
        )

    def test_report_files_can_be_saved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = ReportCollector(Path(directory), {"mode": "simulation"})
            report.count("上半身通信汇总", "调用")
            report.count("上半身通信汇总", "失败")
            report.count("上半身通信汇总", "超时")
            report.save()
            self.assertTrue((Path(directory) / "summary.xlsx").exists())
            self.assertEqual(
                len(list(Path(directory).glob("details_*.xlsx"))), 1
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
