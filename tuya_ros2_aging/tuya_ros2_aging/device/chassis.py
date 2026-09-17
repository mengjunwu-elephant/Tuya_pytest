"""底盘 ROS 设备封装。"""

from __future__ import annotations

from typing import Any

from ..errors import CommunicationResponseError
from ..ros.client import RosBridge


def _srv(name: str) -> Any:
    import tuyarobot_msgs.srv as srv

    return getattr(srv, name)


class ChassisDevice:
    SUBSYSTEM = "chassis"

    def __init__(self, bridge: RosBridge) -> None:
        self.bridge = bridge

    def _call(
        self,
        name: str,
        srv_type: Any,
        request: Any,
        *,
        kind: str = "读取",
        require_success: bool = True,
    ) -> Any:
        return self.bridge.call(
            self.SUBSYSTEM,
            name,
            srv_type,
            request,
            kind=kind,
            require_success=require_success,
        )

    def is_powered_on(self) -> int:
        resp = self._call(
            "/chassis/is_agv_powered_on",
            _srv("GetInt"),
            _srv("GetInt").Request(),
            require_success=False,
        )
        return int(resp.data)

    def set_led_color(
        self, red: int, green: int, blue: int, brightness: int
    ) -> Any:
        req = _srv("SetAgvLedColor").Request()
        req.red = int(red)
        req.green = int(green)
        req.blue = int(blue)
        req.brightness = int(brightness)
        return self._call(
            "/chassis/set_agv_led_color",
            _srv("SetAgvLedColor"),
            req,
            kind="设置",
        )

    def set_lift(
        self,
        lift_mm: float,
        speed: int = 10,
        *,
        async_mode: bool = False,
        timeout: float | None = None,
    ) -> Any:
        from .. import constants

        req = _srv("SetAgvLiftControl").Request()
        req.lift_mm = float(lift_mm)
        req.speed = int(speed)
        req.async_mode = bool(async_mode)
        wait = (
            constants.CHASSIS_LIFT_JOIN_TIMEOUT
            if timeout is None and not async_mode
            else timeout
        )
        return self.bridge.call(
            self.SUBSYSTEM,
            "/chassis/set_agv_lift_control",
            _srv("SetAgvLiftControl"),
            req,
            kind="设置",
            timeout=wait,
        )

    def wheel_control(self, forward_mps: float, rotate_rads: float) -> Any:
        req = _srv("AgvWheelControl").Request()
        req.forward_mps = float(forward_mps)
        req.rotate_rads = float(rotate_rads)
        return self._call(
            "/chassis/agv_wheel_control",
            _srv("AgvWheelControl"),
            req,
            kind="运动",
        )

    def stop(self) -> Any:
        try:
            return self._call(
                "/chassis/agv_wheel_stop",
                _srv("TuyarobotTrigger"),
                _srv("TuyarobotTrigger").Request(),
                kind="运动",
            )
        except CommunicationResponseError:
            return self.wheel_control(0.0, 0.0)
