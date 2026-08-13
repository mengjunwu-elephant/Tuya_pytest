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

from tuya_aging.cli import discover_pag_files
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
from tuya_aging.motion.head_runner import HeadMotionRunner
from tuya_aging.report.collector import ReportCollector
from tuya_aging.runtime.coordinator import AgingCoordinator
from tuya_aging.utils import head_status_has_error


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
        "run_head_motion": False,
        "monitor_only": False,
        "duration_hours": 0.0,
        "cycle_limit": 1,
        "upper_speed": 20,
        "jog_speed": 10,
        "head_speed": 10,
        "upper_timeout": 1.0,
        "jog_timeout": 1.0,
        "head_timeout": 1.0,
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
        "head_animation_paths": (),
    }
    values.update(overrides)
    return AgingOptions(**values)


def make_context(**overrides: Any) -> AgingContext:
    report = MemoryReport()
    policy = FailurePolicy(10, report)
    return AgingContext(
        options=options(**overrides),
        report=report,
        policy=policy,
        stop_event=threading.Event(),
        fatal=lambda *_args: None,
        stop_head_motion=lambda *_args: None,
        upper_blocking_motion=threading.Event(),
        head_blocking_motion=threading.Event(),
        head_stop_event=threading.Event(),
        head_ready=threading.Event(),
    )


def upper_runner_with_fake() -> tuple[UpperMotionRunner, FakeUpperDevice]:
    context = make_context()
    device = FakeUpperDevice()
    return UpperMotionRunner(device, context), device


class FakeHead:
    def __init__(self, owner: "FakeHeadDevice") -> None:
        self.owner = owner
        self.enabled = True
        self.power_state = 1

    def is_head_powered_on(self) -> int:
        return self.power_state

    def head_power_on(self) -> int:
        self.power_state = 1
        self.owner.events.append(("power_on",))
        return 1

    def is_head_moving(self) -> int:
        return 0

    def get_head_angles(self) -> list[float]:
        return list(self.owner.angles)

    def send_head_angles(self, angles: Any, _speed: int, **_kwargs: Any) -> int:
        self.owner.angles = [float(value) for value in angles]
        self.owner.events.append(("angles", tuple(self.owner.angles)))
        return 1

    def send_head_angle(
        self, joint_id: int, angle: float, _speed: int, **_kwargs: Any
    ) -> int:
        self.owner.angles[joint_id - 1] = float(angle)
        self.owner.events.append(("angle", joint_id, float(angle)))
        return 1

    def set_head_led_control(self, *args: Any) -> int:
        self.owner.events.append(("led", args))
        return 1

    def play_head_animation(
        self,
        animation_path: str,
        intervals_ms: Any = None,
        play_times_ms: Any = None,
    ) -> int:
        self.owner.events.append(
            ("animation", animation_path, intervals_ms, play_times_ms)
        )
        return 1

    def get_head_robot_status(self) -> dict[str, Any]:
        return {"soft_error": 0, "motor_errors": [0, 0, 0, 0]}

    def get_head_joints_run_sp(self) -> list[float]:
        return [0.0] * 4

    def get_head_joints_current(self) -> list[float]:
        return [0.0] * 4

    def get_head_joints_temp(self) -> list[float]:
        return [0.0] * 4


class FakeHeadDevice:
    def __init__(self) -> None:
        self.angles = [0.0, 0.0, 0.0, 0.0]
        self.events: list[Any] = []
        self.head = FakeHead(self)

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    def wait_until_stopped(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def go_zero(self, *_args: Any, **_kwargs: Any) -> None:
        self.angles = [0.0, 0.0, 0.0, 0.0]
        self.events.append(("zero",))

    @staticmethod
    def vector_error(actual: Any, expected: Any) -> float:
        return max(
            abs(float(value) - float(target))
            for value, target in zip(actual, expected)
        )

    def assert_angles(self, actual: Any, expected: Any, *_args: Any) -> float:
        return self.vector_error(actual, expected)


def head_runner_with_fake(
    **option_overrides: Any,
) -> tuple[HeadMotionRunner, FakeHeadDevice, AgingContext]:
    context = make_context(run_upper_motion=False, run_head_motion=True, **option_overrides)
    stops: list[str] = []

    def stop_head(phase: str, exc: BaseException | str) -> None:
        stops.append(f"{phase}:{exc}")
        context.head_stop_event.set()

    context.stop_head_motion = stop_head  # type: ignore[method-assign]
    device = FakeHeadDevice()
    runner = HeadMotionRunner(device, context)
    runner._stop_calls = stops  # type: ignore[attr-defined]
    return runner, device, context


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
        coordinator.head_monitor = SimpleNamespace(run=lambda: None)
        coordinator._run_upper_motion = lambda: None
        coordinator._run_chassis_motion = lambda: None
        coordinator._run_head_motion = lambda: None
        names = {thread.name for thread in coordinator._build_threads()}
        self.assertIn("UpperMonitor", names)
        self.assertIn("UpperMotion", names)
        self.assertNotIn("ChassisMonitor", names)
        self.assertNotIn("ChassisMotion", names)
        self.assertNotIn("HeadMonitor", names)
        self.assertNotIn("HeadMotion", names)

    def test_head_only_creates_head_threads(self) -> None:
        coordinator = AgingCoordinator.__new__(AgingCoordinator)
        coordinator.options = options(
            run_upper_motion=False, run_head_motion=True
        )
        coordinator._report_worker = lambda: None
        coordinator.upper_monitor = SimpleNamespace(run=lambda: None)
        coordinator.chassis_monitor = SimpleNamespace(run=lambda: None)
        coordinator.head_monitor = SimpleNamespace(run=lambda: None)
        coordinator._run_upper_motion = lambda: None
        coordinator._run_chassis_motion = lambda: None
        coordinator._run_head_motion = lambda: None
        names = {thread.name for thread in coordinator._build_threads()}
        self.assertIn("HeadMonitor", names)
        self.assertIn("HeadMotion", names)
        self.assertNotIn("UpperMotion", names)
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

    def test_software_limits_use_latest_confirmed_values(self) -> None:
        self.assertEqual(
            constants.JOINT_SOFT_LIMITS,
            {
                1: (-150.0, 176.0),
                2: (-72.0, 125.0),
                3: (-163.0, 167.0),
                4: (-149.0, 1.0),
                5: (-179.0, 148.0),
                6: (-87.0, 42.0),
                7: (-80.0, 92.0),
            },
        )
        self.assertEqual(
            constants.COORD_SOFT_LIMITS[2], (-841.0, 841.0)
        )
        self.assertEqual(
            constants.COORD_SOFT_LIMITS[3], (-636.0, 685.0)
        )
        self.assertEqual(
            constants.HEAD_JOINT_SOFT_LIMITS,
            {
                1: (-60.0, 60.0),
                2: (-15.0, 15.0),
                3: (-40.0, 40.0),
                4: (-40.0, 40.0),
            },
        )
        self.assertEqual(constants.HEAD_ZERO_ANGLES, (0.0, 0.0, 0.0, 0.0))
        self.assertEqual(constants.HEAD_ANGLE_TOLERANCE, 1.0)

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
                if target == "both" and joint_id == 2:
                    # 双臂不执行 J2 正向；负向完成后仍回零
                    negative = ("joint_jog", target, joint_id, 0)
                    negative_index = device.events.index(negative)
                    self.assertNotIn(
                        ("joint_jog", target, joint_id, 1), device.events
                    )
                    self.assertEqual(
                        device.events[negative_index + 1],
                        ("zero",),
                    )
                    continue
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


class HeadAgingTests(unittest.TestCase):
    def test_full_joint_limits_negative_then_positive_then_zero(self) -> None:
        runner, device, _context = head_runner_with_fake()
        runner.run_full_joint_limits()
        negative = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[joint_id][0]
            for joint_id in range(1, 5)
        )
        positive = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[joint_id][1]
            for joint_id in range(1, 5)
        )
        self.assertEqual(device.events[0], ("zero",))
        self.assertEqual(device.events[1], ("angles", negative))
        self.assertEqual(device.events[2], ("angles", positive))
        self.assertEqual(device.events[3], ("zero",))

    def test_single_joint_limits_zero_after_each_pair(self) -> None:
        runner, device, _context = head_runner_with_fake()
        runner.run_single_joint_limits()
        # 初始回零 + 每关节一对限位后回零 ×4
        self.assertEqual(device.events.count(("zero",)), 5)
        for joint_id, limits in constants.HEAD_JOINT_SOFT_LIMITS.items():
            negative = ("angle", joint_id, limits[0])
            positive = ("angle", joint_id, limits[1])
            negative_index = device.events.index(negative)
            positive_index = device.events.index(positive)
            self.assertLess(negative_index, positive_index)
            self.assertNotIn(
                ("zero",),
                device.events[negative_index + 1 : positive_index],
            )
            self.assertEqual(device.events[positive_index + 1], ("zero",))

    def test_animation_skipped_without_paths(self) -> None:
        runner, device, _context = head_runner_with_fake()
        runner.run_animation()
        self.assertNotIn(
            "animation",
            [event[0] for event in device.events],
        )
        skipped = [
            row
            for sheet, row in runner.report.rows
            if sheet == "头部运动" and row[12] == "跳过"
        ]
        self.assertEqual(len(skipped), 1)

    def test_animation_plays_all_pag_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.pag"
            second = root / "b.pag"
            first.write_bytes(b"pag-a")
            second.write_bytes(b"pag-b")
            runner, device, _context = head_runner_with_fake(
                head_animation_paths=(first, second)
            )
            original_settle = constants.HEAD_ANIMATION_SETTLE_SECONDS
            constants.HEAD_ANIMATION_SETTLE_SECONDS = 0.0
            try:
                runner.run_animation()
            finally:
                constants.HEAD_ANIMATION_SETTLE_SECONDS = original_settle
            animation_events = [
                event for event in device.events if event[0] == "animation"
            ]
            self.assertEqual(len(animation_events), 2)
            self.assertEqual(animation_events[0][1], str(first))
            self.assertEqual(animation_events[1][1], str(second))

    def test_animation_continues_after_single_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.pag"
            second = root / "b.pag"
            first.write_bytes(b"pag-a")
            second.write_bytes(b"pag-b")
            runner, device, _context = head_runner_with_fake(
                head_animation_paths=(first, second)
            )
            calls = {"n": 0}
            original = device.head.play_head_animation
            original_settle = constants.HEAD_ANIMATION_SETTLE_SECONDS
            constants.HEAD_ANIMATION_SETTLE_SECONDS = 0.0

            def flaky(
                animation_path: str,
                intervals_ms: Any = None,
                play_times_ms: Any = None,
            ) -> int:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("upload failed")
                return original(
                    animation_path, intervals_ms, play_times_ms
                )

            device.head.play_head_animation = flaky  # type: ignore[method-assign]
            try:
                runner.run_animation()
            finally:
                constants.HEAD_ANIMATION_SETTLE_SECONDS = original_settle
            self.assertEqual(calls["n"], 2)
            self.assertEqual(
                [event[1] for event in device.events if event[0] == "animation"],
                [str(second)],
            )

    def test_discover_pag_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.pag").write_bytes(b"b")
            (root / "a.pag").write_bytes(b"a")
            (root / "note.txt").write_text("x", encoding="utf-8")
            paths = discover_pag_files(root)
            self.assertEqual(
                [path.name for path in paths],
                ["a.pag", "b.pag"],
            )
            self.assertEqual(discover_pag_files(root / "missing"), ())

    def test_head_local_stop_does_not_set_global_fatal(self) -> None:
        fatal_calls: list[str] = []
        head_stops: list[str] = []
        context = make_context(run_upper_motion=False, run_head_motion=True)
        context.fatal = lambda subsystem, phase, exc: fatal_calls.append(
            f"{subsystem}/{phase}:{exc}"
        )

        def stop_head(phase: str, exc: BaseException | str) -> None:
            head_stops.append(f"{phase}:{exc}")
            context.head_stop_event.set()

        context.stop_head_motion = stop_head
        context.stop_head_motion("运动连续失败/越界", "head streak")
        self.assertEqual(fatal_calls, [])
        self.assertTrue(context.head_stop_event.is_set())
        self.assertEqual(len(head_stops), 1)

    def test_ensure_powered_on_treats_state_2_as_not_ready(self) -> None:
        runner, device, context = head_runner_with_fake()
        device.head.power_state = 2
        runner.ensure_powered_on()
        self.assertIn(("power_on",), device.events)
        self.assertEqual(device.head.power_state, 1)
        self.assertTrue(context.head_ready.is_set())

    def test_ensure_powered_on_waits_after_ack_before_requery(self) -> None:
        runner, device, context = head_runner_with_fake()
        device.head.power_state = 0
        # 第一次 power_on 后仍保持 0，随后在 settle 轮询中变为 1
        calls = {"n": 0}
        original = device.head.is_head_powered_on

        def flaky_powered() -> int:
            calls["n"] += 1
            if calls["n"] == 1:
                return 0
            if calls["n"] <= 3:
                device.head.power_state = 0
                return 0
            device.head.power_state = 1
            return 1

        device.head.is_head_powered_on = flaky_powered  # type: ignore[method-assign]
        # 缩短 settle：直接复用 ensure，依赖 fake 快速变 1
        runner.ensure_powered_on()
        self.assertTrue(context.head_ready.is_set())
        self.assertGreaterEqual(calls["n"], 2)
        device.head.is_head_powered_on = original  # type: ignore[method-assign]

    def test_report_headers_include_head_sheets(self) -> None:
        self.assertIn("头部运动", ReportCollector.SHEET_HEADERS)
        self.assertIn("头部遥测", ReportCollector.SHEET_HEADERS)
        self.assertEqual(
            len(ReportCollector.SHEET_HEADERS["头部遥测"]), 11
        )
        self.assertEqual(
            len(ReportCollector.SHEET_HEADERS["头部运动"]), 14
        )

    def test_head_status_error_helper(self) -> None:
        self.assertFalse(
            head_status_has_error({"soft_error": 0, "motor_errors": [0, 0, 0, 0]})
        )
        self.assertTrue(
            head_status_has_error({"soft_error": 1, "motor_errors": [0, 0, 0, 0]})
        )
        self.assertTrue(
            head_status_has_error({"soft_error": 0, "motor_errors": [0, 2, 0, 0]})
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
