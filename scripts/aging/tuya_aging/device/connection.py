"""TuyaRobot 唯一连接生命周期。"""

from __future__ import annotations

from pytuyarobot import TuyaRobot

from ..config import AgingConnectionConfig


class TuyaConnection:
    def __init__(
        self,
        config: AgingConnectionConfig,
        *,
        connect_chassis: bool,
    ) -> None:
        self.config = config
        self.robot = TuyaRobot(
            config.upper_ip,
            config.upper_port,
            chassis_port=config.chassis_port,
            chassis_baud=config.chassis_baud,
            head_auto_connect=False,
            chassis_auto_connect=connect_chassis,
            apply_limits_on_init=config.apply_limits_on_init,
            debug=config.debug,
            plain_return=config.plain_return,
        )
        self.closed = False

    def close(self) -> None:
        if self.closed:
            return
        self.robot.close()
        self.closed = True
