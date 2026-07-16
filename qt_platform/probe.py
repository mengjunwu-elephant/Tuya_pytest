# -*- coding: utf-8 -*-
"""在独立进程中探测 TuyaRobot 连接。"""
from __future__ import annotations

import argparse

from settings import TuyaConnectionConfig, TuyaRobotBase


def main() -> None:
    defaults = TuyaConnectionConfig.from_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=defaults.upper_ip)
    parser.add_argument("--port", type=int, default=defaults.upper_port)
    parser.add_argument("--head-port", default=defaults.head_port)
    parser.add_argument("--head-baud", type=int, default=defaults.head_baud)
    parser.add_argument("--chassis-port", default=defaults.chassis_port)
    parser.add_argument("--chassis-baud", type=int, default=defaults.chassis_baud)
    parser.add_argument("--connect-head", action="store_true")
    args = parser.parse_args()

    config = TuyaConnectionConfig(
        upper_ip=args.ip,
        upper_port=args.port,
        head_port=args.head_port,
        head_baud=args.head_baud,
        chassis_port=args.chassis_port,
        chassis_baud=args.chassis_baud,
        head_auto_connect=args.connect_head,
        chassis_auto_connect=True,
        apply_limits_on_init=False,
        debug=True,
        plain_return=True,
    )
    device = TuyaRobotBase(config)
    try:
        version = device.robot.get_system_version()
        print(f"OK robot_type={device.robot.get_robot_type()!r} version={version!r}")
    finally:
        device.close()


if __name__ == "__main__":
    main()
