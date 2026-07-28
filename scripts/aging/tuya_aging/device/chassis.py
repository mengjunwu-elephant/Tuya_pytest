"""底盘设备操作。"""

from __future__ import annotations

from typing import Any

from .gateway import TuyaGateway


class ChassisDevice:
    def __init__(self, robot: Any, gateway: TuyaGateway) -> None:
        self.robot = robot
        self.chassis = robot.chassis
        self.gateway = gateway

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return self.gateway.chassis(func, *args, **kwargs)

    def stop(self) -> Any:
        return self.call(self.chassis.agv_wheel_stop)

    def optional_read(self, method_name: str) -> Any:
        method = getattr(self.chassis, method_name, None)
        if method is None:
            return {"unsupported": method_name}
        return self.call(method)
